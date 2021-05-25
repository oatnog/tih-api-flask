from pathlib import Path
from datetime import date
import logging

import pandas as pd

from flask import Flask, jsonify
from flask_cors import CORS

# TODO: move these into the Flask app explicitly

# place output from xcm spreadsheets here
feather_path = Path.cwd().joinpath('search_results')

# statuses as defined in this installation of XCM tracker
TAX_RETURN_STATUS = (
    "No Info In",
    "Staff Change No Info In",
    "Partial Info In",
    "Verification",
    "To Be Scanned",
    "Preparation",
    "Awaiting Info",
    "Review",
    "To Be Assembled",
    "To Be Shipped",
    "Completed",
    "No Longer Task/To Be Deleted",  # merge with FNR & NLC
    "Prepared By Client",
    "Filing Not Required",  # merge with NLT/TBD & NLC
    "NLC",  # merge with NLT/TBD & FNR
    "eFile-Awaiting Taxpayer Consent Form",  # mistaken entry we will later merge with "Completed"
    "NLT/FNR/NLC",  # merge these three categories into one
    )

app = Flask(__name__)
app.config.from_object(__name__)

CORS(app)


@app.route('/ping', methods=['GET'])
def ping_pong():
    """ simple test route """
    return jsonify('pong!')


@app.route('/load-data')
def load_data():
    """ Import and process Excel file snapshots of XCM data"""
    spreadsheets = Path.cwd().joinpath('spreadsheets')
    for excel_file in spreadsheets.rglob('*.xlsx'):
        # depends on openpyxl
        app.logger.info(f"Importing {excel_file}")
        status_on_date = pd.read_excel(excel_file, usecols=['Current Status', 'Responsible Person', 'Tax Staff'])

        filename_head = Path(excel_file).stem.split(' GMT')[0][14:].split('_')
        search_date = date(int(filename_head[2][0:4]), int(filename_head[1]), int(filename_head[0]))

        # from configuration
        if not feather_path.exists():
            feather_path.mkdir()

        feather_pathname = feather_path.joinpath(search_date.isoformat())
        status_on_date.to_feather(feather_pathname)
    app.logger.info("Completed loading data from spreadsheets")
    return "OK"

@app.route('/available-dates')
def available_dates():
    """show all the dates for which we have a report run and analzyed"""
    # All the dates we know about!
    # Could look up by year...
    if not feather_path.exists():
        load_data()
    return jsonify([feather.stem for feather in feather_path.iterdir()])


# unimplemented--wound up doing this via the frontend
#@app.route('/status/latest')
#def status_latest():
#    pass

@app.route('/status/<isodate>', methods=['GET'])
def status(isodate):
    """List all tax filings, sorted by status """
    feather_filename = feather_path.joinpath(isodate)
    if feather_filename.exists():
        app.logger.info(f"Reading in {feather_filename}")
        status_on_date = pd.read_feather(feather_filename)
        status_counts = status_on_date.value_counts('Current Status')
        # clean up a possible but unwanted Category Status
        if 'eFile-Awaiting Taxpayer Consent Form' in status_counts.keys():
            app.logger.info("Found and removed a bad status")
            status_counts['Completed'] += status_counts['eFile-Awaiting Taxpayer Consent Form']
            new_frame = status_counts.drop('eFile-Awaiting Taxpayer Consent Form')
            status_counts = new_frame

        # Merge these three into NLT/FNR/NLC
        status_counts['NLT/FNR/NLC'] = 0
        categories_to_merge = ('No Longer Task/To Be Deleted', 'Filing Not Required', 'NLC')
        for category in categories_to_merge:
            if category in status_counts.keys():
                status_counts['NLT/FNR/NLC'] += status_counts[category]
                new_frame = status_counts.drop(category)
                status_counts = new_frame

        # we want the JSON in a particular process order. So match it to a look-up table.
        mystatus = {
            'filings': [{'status': tr_status, 'total': int(status_counts[tr_status])} for tr_status in TAX_RETURN_STATUS
                        if
                        tr_status in status_counts.keys()]}

        return jsonify(mystatus)
    else:
        app.logger.error(f"No {feather_filename} here")
        return "Error!"  # should I return a real http error? Look up REST stuff
