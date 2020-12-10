from flask import Flask, render_template, request
from os import listdir, walk
from os.path import isfile, join
from datetime import datetime, timedelta, date, time
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
    # 1.0 传叁
    file = request.form.get('file') # 文件
    direction = request.form.get('direction') # 方向
    vol = float(request.form.get('vol'))  # 买卖波幅
    vol2 = float(request.form.get('vol2'))  # 止蚀波幅
    cutloss = float(request.form.get('cutLoss'))  # 止蚀
    is_adjust = False if request.form.get('adjection')=='false' else True # 调整
    minutes = int(request.form.get('minutes')) # 预测x分钟后
    
    # 1.1 数据集
    path1 = os.path.abspath(os.path.join('data', 'nq', 'prediction', file+'.csv'))
    df1 = pd.read_csv(path1)
    df1.udate = pd.to_datetime(df1.udate)
    df1.index = pd.to_datetime(df1.udate)

    # 2.0 数据集2
    df2 = df1.copy(deep=True)

    highs = np.array(df2['High'], dtype='float')
    lows = np.array(df2['Low'], dtype='float')
    opens = np.array(df2['Open'], dtype='float')
    closes = np.array(df2['Close'], dtype='float')
    vols = np.array(df2['Volume'], dtype='float')
    df2['atr'] = talib.ATR(highs, lows, closes, timeperiod=14*2)

    df2['last1'] = df2['Close'].shift(periods=-1) # 上笔数据 最后价
    df2['adjust'] = df2['Close'] - df2['last1'] # 前1分钟 结算价 波幅

    key2 = 't'+str(minutes)
    if not is_adjust:
        df2['plast'] = df2[key2] # 预测 5分钟后的 波幅 
        df2['plast1'] = df2['t1'] # 预测 1分钟后的 波幅
    else:
        df2['plast'] = df2[key2] + df2['adjust'] # 已调整
        df2['plast1'] = df2['t1'] + df2['adjust'] # 已调整

    df2['pchange'] = (df2['plast'] - df2['Close']) / df2['Close']*100 # 预测 5分钟后的 波幅率
    df2['pchange1'] = (df2['plast1'] - df2['Close']) / df2['Close']*100 # 预测 1分钟后的 波幅率

    # 3.0 回测
    df4 = pd.DataFrame(columns = ['udate', 'action', 'cash', 'profit', 'message'])
    holding = False # 是否持有仓位
    top_profit_price = 0 # 买入点数
    fee = 2.1 # 交易费
    cash = 0 # 资金流

    def is_trigger(v2, vol):
        if direction == 'long':
            return (v2['pchange'] >= vol)
        elif direction == 'short':
            return (v2['pchange'] <= -vol)

    def is_stop_profit(v2, top_profit_price, direction):
        if direction == 'long':
            return (abs(v1['Close']-top_profit_price) >= abs(cutloss*v1['atr']))
        elif direction == 'short':
            return (abs(top_profit_price-v1['Close']) >= abs(cutloss*v1['atr']))

    def is_cut_loss(v2, vol2):
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
                start_hold_time = k1
                df4 = df4.append({'udate': k1, 'action': action, 'cash': np.nan, 'profit': np.nan, 'hold time': np.nan, 'message': np.nan}, ignore_index=True)
                continue
            # 3.3 卖出
            cut_loss2 = is_cut_loss(v1, vol2) # 止蚀
            stop_profit2 = is_stop_profit(v1, top_profit_price, direction) # 止盈
            cur_time, close_time = time(v1.udate.hour, v1.udate.minute, 0), time(14, 59, 0)
            is_over_night = (cur_time == close_time) # 过夜
            if (cut_loss2 or stop_profit2 or is_over_night) and holding:
                holding = False
                # 3.4 持有时长
                mins_diff = (k1 - start_hold_time).total_seconds() / 60
                # 3.5 盈亏
                if direction == 'long':
                    profit2 = (v1['Close']-cost1)*20 - (fee*2)
                elif direction == 'short':
                    profit2 = (cost1-v1['Close'])*20 - (fee*2)
                if profit2 > 0:
                    profit3 = '<span class="text-danger">+'+str(profit2)+'</span>'
                elif profit2 <= 0:
                    profit3 = '<span class="text-success">'+str(profit2)+'</span>'
                message = '('+str(cost1)+' - '+str(v1['Close'])+')*20 - ('+str(fee)+'*2) = '+profit3
                # 3.6 长仓
                if direction == 'long' and stop_profit2:
                    action = 'sell'
                elif direction == 'long' and cut_loss2:
                    action = 'cut'
                elif direction == 'long' and is_over_night:
                    action = 'cut overnight'
                # 3.7 短仓
                elif direction == 'short' and stop_profit2:
                    action = 'buy'
                elif direction == 'short' and cut_loss2:
                    action = 'cut'
                elif direction == 'short' and is_over_night:
                    action = 'cut overnight'
                # 3.8 资金流
                cash = cash + profit2
                
                df4 = df4.append({'udate': k1, 'action': action, 'cash': cash, 'profit': profit2, 'hold time': mins_diff, 'message': message}, ignore_index=True)
                continue

    df4.index = df4['udate']
    df4.drop(['udate'], axis=1, inplace=True)

    # 4.0 清理数据集
    df5 = pd.concat([df2, df4], axis=1)
    drop_list_5 = ['High', 'Low', 'Open', 'Volume', 't2', 't3', 't4', 'last1']
    df5.drop(drop_list_5, axis=1, inplace=True)
    
    # 5.0 渲染1
    df6 = df5.loc[(df5['action']=='buy') | (df5['action']=='sell') | (df5['action']=='cut') | (df5['action']=='cut overnight')]
    df6.columns = ['udate', 'last', 'predict1(T+1)', 'predict1(T+5)', 'atr', 'shift', 'predict2(T+1)', 'predict2(T+5)', 'p-percent1', 'p-percent5', 'action', 'cash', 'profit', 'message', 'hold time']
    df6['cash'] = df6['cash'].round(4)
    df6['profit'] = df6['profit'].round(2)
    # 5.1 渲染2
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
    no_cut_loss = int(np.sum(df6['action'] == 'cut')) + int(np.sum(df6['action'] == 'cut overnight'))
    no_total_day = len(df5.groupby(df5['udate'].dt.date).size())
    no_trade_day = len(df5.groupby(df6['udate'].dt.date).size())
    avg_no_trade = round(no_trade/no_total_day, 2)
    hold_time_max = df6['hold time'].max().round(0)
    hold_time_min = df6['hold time'].min().round(0)
    hold_time_avg = (df6['hold time'].sum()/no_trade).round(0)

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
    html = df6.to_html(classes='table table-sm table-striped', index=False, escape=False, border=0, justify='left').replace('border="1"', 'border="0"').replace('NaN', '')
    data4 = {'total_profit': total_profit, 'avg_profit': avg_profit, 'max_win': max_win, 'max_loss': max_loss,
             'no_trade': no_trade, 'no_win': no_win, 'no_loss': no_loss, 'no_cut_loss': no_cut_loss, 'avg_no_trade': avg_no_trade, 'no_total_day': no_total_day, 
             'hold_time_max': hold_time_max, 'hold_time_min': hold_time_min, 'hold_time_avg': hold_time_avg,
             'html': html}
    data5 = json.dumps(data4)

    return data5


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=83)
