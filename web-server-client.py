from flask import Flask, render_template, request
from os import listdir, walk
import pandas as pd
import warnings as warnings
import os as os
import numpy as np
import json as json
import common as common

pd.options.mode.chained_assignment = None
np.warnings.filterwarnings('ignore', category=np.VisibleDeprecationWarning)

template_dir = os.path.join(os.path.abspath('data'), 'templates', 'client')
static_folder = os.path.join(os.path.abspath('data'))
app = Flask(__name__, template_folder=template_dir, static_url_path='', static_folder=static_folder)
warnings.simplefilter(action='ignore', category=FutureWarning)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('./index.html')


@app.route('/result', methods=['GET', 'POST'])
def result():
    # 1.0 传叁
    file1 = request.form.get('file1')               # 文件1
    file2 = request.form.get('file2')               # 文件2
    direction = request.form.get('direction')       # 方向
    vol = float(request.form.get('vol'))            # 买卖波幅
    vol2 = float(request.form.get('vol2'))          # 止蚀波幅
    cutloss = float(request.form.get('cutLoss'))    # 止蚀
    is_adjust = False if request.form.get('adjection')=='false' else True   # 调整
    is_show_all = False if request.form.get('isShowAll')=='false' else True # 顯示全部
    minutes = int(request.form.get('minutes'))  # 预测x分钟后
    
    df5 = common.algo(file1, file2, direction, vol, vol2, cutloss, is_adjust, minutes)

    # 5.0 渲染1
    if not is_show_all:
        df6 = df5.loc[(df5['action']=='buy') | (df5['action']=='sell') | (df5['action']=='cut') | (df5['action']=='cut overnight')]
    else:
        df6 = df5.copy(deep=True)
    df6['cash'] = df6['cash'].round(4)
    df6['profit'] = df6['profit'].round(2)

    # 5.1 渲染2
    if direction == 'long':
        no_trade = df6.loc[(df6['action']=='buy')].shape[0]
    elif direction == 'short':
        no_trade = df6.loc[(df6['action']=='sell')].shape[0]
    total_profit = df6.loc[(df6['cash'] > 0)]['cash'].values.tolist()[-1]
    avg_profit = df6['profit'].mean().round(2)
    max_win = df6['profit'].max().round(2)
    max_loss = df6['profit'].min().round(2)
    no_win = int(np.sum(df6['profit'] > 0))
    no_loss = int(np.sum(df6['profit'] <= 0))
    no_cut_loss = int(np.sum(df6['action'] == 'cut')) + int(np.sum(df6['action'] == 'cut overnight'))
    no_total_day = len(df5.groupby(df5['udate'].dt.date).size())
    no_trade_day = len(df5.groupby(df6['udate'].dt.date).size())
    avg_no_trade = round(no_trade/no_total_day, 2)
    hold_time_max = df6['hold time'].max().round(0)
    hold_time_min = df6['hold time'].min().round(0)
    hold_time_avg = (df6['hold time'].sum()/no_trade).round(0)

    # 5.2 加颜色
    df7 = df6.copy(deep=True)
    for k5, v5 in df7.iterrows():
        # 5.3 profit
        if v5['profit'] > 0:
            df7.loc[k5, 'profit'] = '<font class="text-danger">+'+str(df7.loc[k5, 'profit'])+'</font>'
        elif v5['profit'] <= 0:
            df7.loc[k5, 'profit'] = '<font class="text-success">'+str(df7.loc[k5, 'profit'])+'</font>'
        # 5.4 cash
        if v5['cash'] > 0:
            df7.loc[k5, 'cash'] = '<font class="text-danger">+'+str(df7.loc[k5, 'cash'])+'</font>'
        elif v5['cash'] <= 0:
            df7.loc[k5, 'cash'] = '<font class="text-success">'+str(df7.loc[k5, 'cash'])+'</font>'
    df7.sort_index(ascending=True, inplace=True)
    html = df7.to_html(classes='table table-sm table-striped', index=False, escape=False, border=0, justify='left').replace('border="1"', 'border="0"').replace('NaN', '')
    data4 = {'total_profit': total_profit, 'avg_profit': avg_profit, 'max_win': max_win, 'max_loss': max_loss,
             'no_trade': no_trade, 'no_win': no_win, 'no_loss': no_loss, 'no_cut_loss': no_cut_loss, 'avg_no_trade': avg_no_trade, 'no_total_day': no_total_day, 
             'hold_time_max': hold_time_max, 'hold_time_min': hold_time_min, 'hold_time_avg': hold_time_avg,
             'html': html}
    data5 = json.dumps(data4)
    return data5


@app.route('/files', methods=['GET', 'POST'])
def files():
    data = {}
    for root, dirs, files in walk(os.path.abspath(os.path.join('data', 'nq', 'prediction'))):
        if not dirs:
            data[os.path.basename(os.path.normpath(root))] = [file.replace('.csv', '') for file in sorted(files)]
    data2 = {}
    for k in sorted(data, reverse=True):
        data2[k] = data[k]
    return json.dumps(data2)


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=83)
