from flask import Flask, render_template
from os import listdir, walk
from os.path import isfile, join
import pandas as pd
import warnings
import os
template_dir = os.path.join(os.path.abspath('data'), 'templates')
static_folder = os.path.abspath('data')
app = Flask(__name__, template_folder=template_dir, static_url_path='', static_folder=static_folder)
warnings.simplefilter(action='ignore', category=FutureWarning)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('./index.html')

@app.route('/data', methods=['GET', 'POST'])
def data():
    file_1 = os.path.abspath(os.path.join('data', 'nq', 'nq-clean-data-with-features.csv'))
    df1 = pd.read_csv(file_1)
    df1 = df1.tail(200).round(1)
    return render_template('./data.html', data=df1.to_html(classes='table table-sm table-striped'))

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
    return render_template('./result.html', files_name=files_name)

@app.route('/markdown', methods=['GET', 'POST'])
def markdown():
    return render_template('./markdown.html')

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=82)