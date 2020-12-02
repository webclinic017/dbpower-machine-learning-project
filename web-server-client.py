from flask import Flask, render_template
from os import listdir, walk
from os.path import isfile, join
import pandas as pd
import warnings
import os
template_dir = os.path.join(os.path.abspath('data'), 'templates', 'client')
static_folder = os.path.join(os.path.abspath('data'))
app = Flask(__name__, template_folder=template_dir, static_url_path='', static_folder=static_folder)
warnings.simplefilter(action='ignore', category=FutureWarning)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('./index.html')

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=83)
