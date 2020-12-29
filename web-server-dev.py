from flask import Flask, render_template
from os import listdir, walk
from os.path import isfile, join
import sqlite3 as sqlite3
import pandas as pd
import warnings
import os
template_dir = os.path.join(os.path.abspath('data'), 'templates', 'dev')
static_folder = os.path.join(os.path.abspath('data'))
app = Flask(__name__, template_folder=template_dir, static_url_path='', static_folder=static_folder)
warnings.simplefilter(action='ignore', category=FutureWarning)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('./index.html')

@app.route('/data', methods=['GET', 'POST'])
def data():
    file_1 = os.path.abspath(os.path.join('data', 'nq', 'clean-data', 'nq-clean-data-with-features.csv'))
    df1 = pd.read_csv(file_1)
    df1.drop(['udate'], axis=1, inplace=True)
    df1 = df1.tail(100)
    return render_template('./data.html', data=df1.to_html(classes='table table-sm table-striped', index=False).replace('border="1"','border="0"'))

@app.route('/chart', methods=['GET', 'POST'])
def chart():
    path_chart = os.path.join(static_folder, 'img-nq', 'features')
    files_name = None
    for root, dirs, files in walk(path_chart):
        files_name = files
    files_name.sort(reverse=False)
    return render_template('./chart.html', files_name=files_name)

@app.route('/result', methods=['GET', 'POST'])
def result():
    path_chart = os.path.join(static_folder, 'img-nq', 'results')
    files_name = None
    for root, dirs, files in walk(path_chart):
        files_name = files
    files_name.sort(reverse=False)
    return render_template('./result.html', files_name=files_name[-32:])

@app.route('/result-describe', methods=['GET', 'POST'])
def result_describe():
    path_describe = os.path.join(static_folder, 'nq', 'result-describe')
    data = {}
    for root, dirs, files in walk(path_describe):
        files.sort(reverse=True)
        for path_file in files:
            path_file2 = path_file.replace('.csv', '')
            df1 = pd.read_csv(root+'/'+path_file).round(3)
            data[path_file2] = df1.to_html(classes='table table-sm table-striped', index=False).replace('border="1"','border="0"')
    return render_template('./result-describe.html', data=data)

@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    file_2 = os.path.abspath(os.path.join('data', 'nq', 'prediction', 'nq-prediction.csv'))
    df2 = pd.read_csv(file_2).tail(20000)
    return render_template('./prediction.html', data=df2.to_html(classes='table table-sm table-striped', index=False).replace('border="1"','border="0"'))

@app.route('/markdown', methods=['GET', 'POST'])
def markdown():
    return render_template('./markdown.html')

@app.route('/install', methods=['GET', 'POST'])
def install():
    return render_template('./install.html')

@app.route('/market-data', methods=['GET', 'POST'])
def market_data():
    path_db = os.path.abspath(os.path.join('data', 'nq', 'data', 'nq.db'))
    db = sqlite3.connect(path_db)
    cursor = db.cursor()
    stmt1 = "select strftime('%Y-%m-%d', udate) as 'udate', count(udate) as no from nq where strftime('%S', udate) == '00' group by strftime('%Y-%m-%d', udate) order by udate desc"
    df1 = pd.read_sql_query(stmt1, db)
    cur_date = df1.iloc[0]['udate']
    stmt2 = "select * from nq where strftime('%Y-%m-%d', udate) == '"+cur_date+"' order by udate desc"
    df2 = pd.read_sql_query(stmt2, db)
    db.commit()
    cursor.close()
    db.close()
    return render_template('./market-data.html', 
                           data3="{:,}".format(int(df2.shape[0])),
                           data4=df2.head(100).to_html(classes='table table-sm table-striped', index=False, justify='left').replace('border="1"','border="0"'),
                           data2=df1.shape[0], 
                           data=df1.head(100).to_html(classes='table table-sm table-striped', index=False, justify='left').replace('border="1"','border="0"'),
                           data5="{:,}".format(int(df1.sum()['no'])))

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=82)
