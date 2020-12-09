from flask import Flask, render_template, request
from os import listdir, walk
from os.path import isfile, join
import pandas as pd
import warnings as warnings
import os as os
import numpy as np
import talib as talib
import json as json
pd.options.mode.chained_assignment = None

template_dir = os.path.join(os.path.abspath('data'), 'templates', 'client')
static_folder = os.path.join(os.path.abspath('data'))
app = Flask(__name__, template_folder=template_dir, static_url_path='', static_folder=static_folder)
warnings.simplefilter(action='ignore', category=FutureWarning)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('./index.html')


@app.route('/result', methods=['GET', 'POST'])
def result():
    # 1.0
    path1 = os.path.abspath(os.path.join('data', 'nq', 'prediction', 't5-0608-0922-e12-u512-w50.csv'))
    path1 = os.path.abspath(os.path.join('data', 'nq', 'prediction', 't5-0608-0922-e10-u512-w50.csv'))
    path1 = os.path.abspath(os.path.join('data', 'nq', 'prediction', request.form.get('file')+'.csv'))
    df1 = pd.read_csv(path1)
    df1.udate = pd.to_datetime(df1.udate)
    df1.index = pd.to_datetime(df1.udate)

    # 2.0
    df2 = df1.copy(deep=True)

    highs = np.array(df2['High'], dtype='float')
    lows = np.array(df2['Low'], dtype='float')
    opens = np.array(df2['Open'], dtype='float')
    closes = np.array(df2['Close'], dtype='float')
    vols = np.array(df2['Volume'], dtype='float')
    df2['atr'] = talib.ATR(highs, lows, closes, timeperiod=14 * 2)

    df2['last1'] = df2['Close'].shift(periods=-1)  # 上笔数据 最后价
    df2['adjust'] = df2['Close'] - df2['t5']  # 5分钟后的 波幅
    df2['pchange1'] = (df2['t1'] - df2['Close']) / df2['Close'] * 100  # 1分钟后的 波幅率
    df2['pchange'] = (df2['t5'] - df2['Close']) / df2['Close'] * 100  # 5分钟后的 波幅率

    # 3.0
    direction = request.form.get('direction') # 方向
    vol = float(request.form.get('vol'))  # 买卖波幅
    vol2 = float(request.form.get('vol2'))  # 止蚀波幅
    cutloss = float(request.form.get('cutLoss'))  # 止蚀

    # 3.1
    df4 = pd.DataFrame(columns = ['udate', 'action', 'cash', 'profit', 'message'])
    holding = False # 是否持有仓位
    top_profit_price = 0 # 买入点数
    fee = 2.1 # 交易费
    cash = 0

    def is_trigger(v2, vol):
        if direction == 'long':
            return (v2['pchange'] >= vol)
        elif direction == 'short':
            return (v2['pchange'] <= -vol)

    def is_cut_loss(v2, top_profit_price, direction):
        if direction == 'long':
            return (abs(v1['Close']-top_profit_price) >= abs(cutloss*v1['atr']))
        elif direction == 'short':
            return (abs(top_profit_price-v1['Close']) >= abs(cutloss*v1['atr']))

    def is_stop_profit(v2, vol2):
        if direction == 'long':
            return (v2['pchange1'] <= vol2)
        elif direction == 'short':
            return (v2['pchange1'] >= vol2)

    df3 = df2.copy(deep=True)
    for k1, v1 in df3.iterrows():
        if v1['udate'].hour < 15 or v1['udate'].hour >= 19:
            # 3.2 买入
            if is_trigger(v1, vol) and not holding:
                holding = True
                cost1 = v1['Close']
                top_profit_price = v1['Close']
                action = 'buy' if direction == 'long' else 'sell'
                df4 = df4.append({'udate': k1, 'action': action, 'cash': np.nan, 'profit': np.nan, 'message': np.nan}, ignore_index=True)
                continue
            # 3.3
            cut_loss2 = is_cut_loss(v1, top_profit_price, direction) # 止蚀
            stop_profit2 = is_stop_profit(v1, vol2) # 止盈
            if (cut_loss2 or stop_profit2) and holding:
                holding = False
                profit2 = (v1['Close']-cost1)*20 - (fee*2)
                cash = cash + profit2
                # 3.4 长仓
                if direction == 'long' and stop_profit2:
                    action = 'sell'
                elif direction == 'long' and cut_loss2:
                    action = 'cut'
                # 3.5 短仓
                elif direction == 'short' and stop_profit2:
                    action = 'buy'
                elif direction == 'short' and cut_loss2:
                    action = 'cut'
                df4 = df4.append({'udate': k1, 'action': action, 'cash': cash, 'profit': profit2, 'message': np.nan}, ignore_index=True)

    df4.index = df4['udate']
    df4.drop(['udate'], axis=1, inplace=True)

    # 4.0
    df5 = pd.concat([df2, df4], axis=1)
    drop_list_5 = ['High', 'Low', 'Open', 'Volume', 't2', 't3', 't4']
    df5.drop(drop_list_5, axis=1, inplace=True)
    
    # 5.0
    df6 = df5.loc[(df5['action']=='buy') | (df5['action']=='sell') | (df5['action']=='cut')]
    df6.columns = ['time', 'last', 'predict1(T+1)', 'predict1(T+5)', 'atr', 'predict2(T+1)', 'adjust', 'p-percent1', 'p-percent5', 'action', 'cash', 'profit', 'message']
    df6['cash'] = df6['cash'].round(4)
    # 5.1 
    if direction == 'long':
        no_trade = df6.loc[(df6['action']=='buy')].shape[0]
    elif direction == 'short':
        no_trade = df6.loc[(df6['action']=='sell')].shape[0]
    total_profit = df6.iloc[-1]['cash'].round(2)
    avg_profit = df6['profit'].mean().round(2)
    max_win = df6['profit'].max().round(2)
    max_loss = df6['profit'].min().round(2)
    no_win = int(np.sum(df6['profit'] > 0))
    no_loss = int(np.sum(df6['profit'] <= 0))
    # 5.2 加颜色
    for k5, v5 in df6.iterrows():
        # 5.3 profit
        if df6.loc[k5, 'profit'] > 0:
            df6.loc[k5, 'profit'] = '<font class="text-danger">+'+str(df6.loc[k5, 'profit'])+'</font>'
        elif df6.loc[k5, 'profit'] <= 0:
            df6.loc[k5, 'profit'] = '<font class="text-success">'+str(df6.loc[k5, 'profit'])+'</font>'
        # 5.4 cash
        if df6.loc[k5, 'cash'] > 0:
            df6.loc[k5, 'cash'] = '<font class="text-danger">+'+str(df6.loc[k5, 'cash'])+'</font>'
        elif df6.loc[k5, 'cash'] <= 0:
            df6.loc[k5, 'cash'] = '<font class="text-success">'+str(df6.loc[k5, 'cash'])+'</font>'
    html = df6.to_html(classes='table table-sm table-striped', index=False, escape=False, border=0).replace('border="1"', 'border="0"').replace('NaN', '')
    data5 = json.dumps({'no_trade': no_trade, 'no_win': no_win, 'no_loss': no_loss,
                        'total_profit': total_profit, 'avg_profit': avg_profit, 'max_win': max_win, 'max_loss': max_loss,
                        'html': html})

    return data5


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=83)
