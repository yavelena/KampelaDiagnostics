import time
import datetime

from flask import Flask, render_template, g, flash, request, abort
import sqlite3
import os
import json
from datetime import datetime
from FDataBase import FDataBase

DATABASE = '/db/kampure.db'
DEBUG = True
SECRET_KEY = '9945152becf2348576d35508'


app = Flask(__name__)

app.config.from_object(__name__)
app.config.update(dict(DATABASE=os.path.join(app.root_path, 'db', 'kampure.db')))


def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db



dbase = None
@app.before_request
def before_request():
    global dbase
    db = get_db()
    dbase = FDataBase(db)


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()


@app.template_filter('ctime')
def ut_to_str(ut):
    return datetime.utcfromtimestamp(int(ut)).strftime('%Y-%m-%d %H:%M:%S')


@app.route("/", methods=['POST', 'GET'])
def index():
    if request.method == "GET":
        print(request.args)
    reports = dbase.getReportList(request.args)


    return render_template('index.html', title='Testing reports', reports=reports)


@app.route("/<UniqueID>/")
def reports_by_kambala(UniqueID):
    return f"ID: {UniqueID}"


@app.route("/<UniqueID>/<unixtime>/")
def report_detailed(UniqueID, unixtime):
    report = dbase.getReport(kampure=UniqueID, unixtime=unixtime)
    if not report:
        abort(404)
    detail_data = json.loads(report['detail_text'])
    errors_text = json.loads(report['errors_text'])
    return render_template('detail.html',
                           title=f'{UniqueID}-{unixtime}',
                           kampure_id=UniqueID,
                           datetime=unixtime,
                           report=report,
                           errors_text=errors_text,
                           detail_data=detail_data)


@app.errorhandler(404)
def pageNotFound(error):
    return render_template('404.html', title='404: Page not found'), 404


if __name__ == "__main__":
    app.run(debug=True)
