## TIH API README

Uses Pandas to import and extract data from manually-run reports.
Exposes data via REST API (uses Flask).

Test it out like this:
FLASK_APP=app.py FLASK_ENV=development flask run

Requires Excel spreadsheets to import (not included--private data!)

TODO:
- API design: good? Bad? good enough?
- Gather data via XCM API rather than reports run by hand.
- Pregenerate "stub" data to demo
- ~~change "print" debugging to using "logging" module~~
