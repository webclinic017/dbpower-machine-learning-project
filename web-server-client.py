from flask import Flask, render_template, request
from os import listdir, walk
from os.path import isfile, join
from datetime import datetime, timedelta, date, time
from threading import Thread
import sqlite3 as sqlite3
import pandas as pd
import warnings as warnings
import os as os
import numpy as np
import talib as talib
import json as json
import common as common
import time as time1
import joblib as joblib
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
    file1 = request.form.get('file1') # 文件1
    file2 = request.form.get('file2') # 文件2
    direction = request.form.get('direction') # 方向
    vol = float(request.form.get('vol'))  # 买卖波幅
    vol2 = float(request.form.get('vol2'))  # 止蚀波幅
    cutloss = float(request.form.get('cutLoss'))  # 止蚀
    is_adjust = False if request.form.get('adjection')=='false' else True # 调整
    minutes = int(request.form.get('minutes')) # 预测x分钟后
    
    # 1.1 数据集
    path1 = os.path.abspath(os.path.join('data', 'nq', 'prediction', file1, file2+'.csv'))
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

    df2['real(t+1)'] = df2['Close'].shift(periods=-1)
    df2['real(t+5)'] = df2['Close'].shift(periods=-5)

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
        if v1['udate'].hour <= 14 or v1['udate'].hour >= 19:
            # 时间
            cur_time, close_time = time(v1.udate.hour, v1.udate.minute, 0), time(14, 59, 0)
            is_over_night = (cur_time == close_time) # 过夜
            # 3.2 买入
            if is_trigger(v1, vol) and not is_over_night and not holding:
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
                    profit3 = '<span class="text-danger">+'+str(round(profit2, 1))+'</span>'
                elif profit2 <= 0:
                    profit3 = '<span class="text-success">'+str(round(profit2, 1))+'</span>'
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
    df6.columns = ['udate', 'last', 'predict1(T+1)', 'predict1(T+5)', 'atr', 'shift', 'predict2(T+1)', 'predict2(T+5)', 'p-percent1', 'p-percent5', 'real(t+1)', 'real(t+5)', 
                   'action', 'cash', 'profit', 'message', 'hold time']
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


class Worker(Thread):
    # 1.0 抓取数据
    def get_data(self, no_day):
        path_db = os.path.abspath(os.path.join('data', 'nq', 'data', 'nq.db'))
        db = sqlite3.connect(path_db)
        cursor = db.cursor()
        stmt1 = "select strftime('%Y-%m-%d', udate) as 'udate' from nq group by strftime('%Y-%m-%d', udate) " \
                "order by udate desc LIMIT "+str(no_day)
        df1 = pd.read_sql_query(stmt1, db)
        end_date, start_date = df1.iloc[0].udate, df1.iloc[-1].udate
        stmt2 = "select udate, high, low, open, close, vol from nq where (strftime('%Y-%m-%d', udate) between '"+start_date+\
                "' AND '"+end_date+"') AND strftime('%S', udate) == '00'"
        df2 = pd.read_sql_query(stmt2, db)
        db.commit()
        cursor.close()
        db.close()
        # 1.1 格式化
        df2 = df2.rename(columns={'high': 'High', 'low': 'Low', 'open': 'Open', 'close': 'Close', 'vol': 'Volume'})
        types1 = {'udate': 'object', 'High': 'float64', 'Low': 'float64', 'Open': 'float64', 'Close': 'float64', 'Volume': 'int64'}
        df2.astype(types1).dtypes
        df2.udate = pd.to_datetime(df2.udate)
        df2.index = pd.to_datetime(df2.udate)
        return df2

    # 2.0 技术指标
    def get_ta(self, df):
        # 2.0
        highs = np.array(df['High'], dtype='float')
        lows = np.array(df['Low'], dtype='float')
        opens = np.array(df['Open'], dtype='float')
        closes = np.array(df['Close'], dtype='float')
        vols = np.array(df['Volume'], dtype='float')
        # 2.1 Bollinger 保力加
        df['upper-band'], df['middle-band'], df['lower-band'] = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        # 3.2 %B %保力加
        df['%b'] = (df['Close'] - df['lower-band']) / (df['upper-band'] - df['lower-band']) * 100
        df['%b-high'] = common.percentB_belowzero(df['%b'], df['Close'])
        df['%b-low'] = common.percentB_aboveone(df['%b'], df['Close'])
        # 2.3 MACD
        weight = 1.5
        df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(closes, fastperiod=12 * weight, slowperiod=26 * weight, signalperiod=9 * weight)
        # 2.4 RSI
        df['rsi-2'] = talib.RSI(closes, timeperiod=14 * weight)
        df['rsi'] = df['rsi-2']
        df['rsi'].loc[((df['rsi'] < 85) & (df['rsi'] > 25))] = 0
        # 2.5 KDJ
        df['k-kdj'], df['d-kdj'], df['j-kdj'] = common.kdj(highs, lows, closes, window_size=5)
        df['diff-kdj'] = df['k-kdj'] - df['d-kdj']
        df['j-kdj'].loc[((df['j-kdj'] > 20) & (df['j-kdj'] < 100))] = 0
        # 3.7 SMA 均線
        for v in [15, 50, 100, 200]:
            df['sma-' + str(v)] = talib.SMA(closes, timeperiod=v)
        df.drop(df.columns.difference(['Close', '%b', '%b-high', '%b-low', 'macdhist', 'rsi', 'j-kdj', 'diff-kdj', 'sma-15', 'sma-50', 'sma-100', 'sma-200']), 1, inplace=True)
        return df

    # 3.0 预测模型
    def run_model(self, df, prefix1, prefix2):
        # 3.1 正则化
        path_name = os.path.abspath(os.path.join('min_max_scaler', prefix1 + '-' + prefix2 + '.pkl'))
        scalers = joblib.load(path_name)
        scaler = scalers[list(scalers.keys())[-1]]
        df2 = scaler['scaler'].transform(df)
        df2 = pd.DataFrame(df2, columns=df.columns, index=df.index)
        df2['udate'] = df.index

        # 3.2 模型
        path_model = os.path.abspath(os.path.join('saved_model', prefix1 + '-' + prefix2 + '.h5'))
        print(path_model)
        return df2

    def run(self):
        while True:
            cur_minute, cur_second = datetime.today().minute, datetime.today().second
            if cur_second == 5:
                # 1.0 抓取数据

                # 2.0 技术指标

                # 3.0 预测模型

                # 4.0 买卖策略

                # 5.0 IB接囗
                pass
            time1.sleep(2)


if __name__ == '__main__':
    Worker().start()
    df = Worker().get_data(30)
    df = Worker().get_ta(df)
    df2 = Worker().run_model(df, 'nq-lstm', '20201214-142731')
    app.debug = True
    app.run(host='0.0.0.0', port=83)
