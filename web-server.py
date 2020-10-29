from flask import Flask, render_template
from os import listdir, walk
from os.path import isfile, join
import warnings
import os
template_dir = os.path.join(os.path.abspath('data'), 'templates')
static_folder = os.path.abspath('data')
app = Flask(__name__, template_folder=template_dir, static_url_path='', static_folder=static_folder)
warnings.simplefilter(action='ignore', category=FutureWarning)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('./index.html')


@app.route('/chart', methods=['GET', 'POST'])
def chart():
    path_chart = os.path.join(static_folder, 'img-nq')
    files_name = None
    for root, dirs, files in walk(path_chart):
        files_name = files
    return render_template('./chart.html', files_name=files_name)


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=82)
