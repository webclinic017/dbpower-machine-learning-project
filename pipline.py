from datetime import datetime
from threading import Thread
from itertools import repeat
from pathlib import Path
import sqlite3 as sqlite3
import pandas as pd
import os as os
import numpy as np
import talib as talib
import common as common
import time as time1
import joblib as joblib
import tensorflow as tf
import requests as requests
import urllib as urllib
import json as json

pd.options.mode.chained_assignment = None
np.warnings.filterwarnings('ignore', category=np.VisibleDeprecationWarning)

my_devices = tf.config.experimental.list_physical_devices(device_type='CPU')
tf.config.experimental.set_visible_devices(devices= my_devices, device_type='CPU')
path_ib = 'http://127.0.0.1:84'


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
    def run_model(self, df, df_o, prefix1, prefix2):
        # 3.1 正则化
        path_name = os.path.abspath(os.path.join('min_max_scaler', prefix1 + '-' + prefix2 + '.pkl'))
        scalers = joblib.load(path_name)
        scaler = scalers[list(scalers.keys())[-1]]
        df2 = scaler['scaler'].transform(df)
        df2 = pd.DataFrame(df2, columns=df.columns, index=df.index)
        df2['udate'] = df.index

        # 3.2 预处理
        t_pus_no = 5
        window_size = 50
        x_valid, date_valid = np.array([]), []
        data2 = common.separate_daily(df2, 'dict')
        for day, df3 in data2.items():
            # print(day, df3.iloc[0]['udate'], df3.iloc[-1]['udate'])
            if df3.shape[0] > window_size+t_pus_no:
                df3.drop(['udate'], axis=1, inplace=True)
                # 5.5.3 窗口
                no_max = df3.shape[0]+1
                x_data = []
                for i in range(window_size, no_max):
                    start, end = i - window_size, i
                    # y label
                    temp_2 = df3.iloc[end - 1: end + t_pus_no - 1]  # current time
                    # x matrix
                    temp_1 = df3.iloc[start: end]
                    x_data.append(temp_1)
                    # date
                    days4 = temp_2.index.tolist()
                    date_valid.append(days4)
                x_data = np.array(x_data)
                x_data[np.isnan(x_data)] = 0.0
                # 5.5.4 分集1
                if x_valid.any():
                    x_valid = np.concatenate((x_valid, x_data), axis=0)
                # 5.5.5 分集2
                elif not x_valid.any():
                    x_valid = x_data
        print('验证集: X_Valid Data: {}, Date_Valid: {}'.format(x_valid.shape, np.array(date_valid).shape), date_valid[-1])

        # 3.3 模型
        path_model = os.path.abspath(os.path.join('saved_model', prefix1 + '-' + prefix2 + '.h5'))
        model = tf.keras.models.load_model(path_model, compile=False)
        predict1 = model.predict(x_valid)
        df3 = pd.DataFrame(predict1, columns=['t1', 't2', 't3', 't4', 't5'])
        date_valid2 = [v[0] for v in date_valid]
        df3['udate'] = date_valid2
        df3.index = df3['udate']

        # 3.4 逆向
        len_shape_y = df2.shape[1] - 2
        fill_list = list(repeat(0, len_shape_y))
        df3_1 = df3.drop(['udate'], axis=1)
        df4_1 = pd.DataFrame()
        data4 = []
        for k1, v1 in df3_1.iterrows():
            data4_1 = []
            for v2 in v1:
                data4_1.append([v2] + fill_list)
            data4_2 = scaler['scaler'].inverse_transform(data4_1)
            data4_3 = [v[0] for v in data4_2]
            data4.append(data4_3)
        # 3.4.1
        df4_5 = pd.DataFrame(data4, columns=['t1', 't2', 't3', 't4', 't5'])
        df4_5.index = df3['udate']
        # 3.4.2 合併
        if df4_5.shape[0] > 0:
            df4_1 = pd.concat([df4_1, df4_5], axis=0, join='outer', ignore_index=False, keys=None, levels=None, names=None, verify_integrity=False, copy=True)

        # 3.5 后处理
        df_o = df_o.drop(['udate'], axis=1)
        df5 = pd.concat([df_o, df4_1], axis=1)
        path3_1 = os.path.abspath(os.path.join('data', 'nq', 'prediction', 'production'))
        Path(path3_1).mkdir(parents=True, exist_ok=True)
        df6 = df5.loc[(df5['t1'] > 0)]
        df7 = pd.concat([df5.head(window_size), df6], axis=0, join='outer', ignore_index=False, keys=None, levels=None, names=None, verify_integrity=False, copy=True)
        path3_2 = os.path.abspath(os.path.join(path3_1, 'nq-prediction-production.csv'))
        if os.path.exists(path3_2):
            os.remove(path3_2)
        df7.to_csv(path3_2)
        return df7

    # 4.0 买卖策略
    def algo2(self):
        df4 = common.algo(file1='production', file2='nq-prediction-production', direction='long', vol=0.08, vol2=0.00, cutloss=2.00, is_adjust=False, minutes=5)
        cur_action = df4.iloc[-1]['action']
        params = {'side': None, 'quantity': '1', 'symbol': 'NQ', 'exchange': 'GLOBEX'}

        # 4.1
        with urllib.request.urlopen(path_ib+'/list-positions') as url:
            data = json.loads(url.read().decode())
            if data and data[0]['position'] >= 1:
                is_holding = True
            else:
                is_holding = False

        # 4.2
        if cur_action in ['buy'] and not is_holding:
            params['side'] = 'buy'
        elif cur_action in ['sell', 'cut',  'cut overnight'] and is_holding:
            params['side'] = 'sell'

        # 4.3
        if params['side'] is not None:
            res = requests.get(url=path_ib+'/place-market-order', params=params)
            print(res.json())
        return df4

    def do(self):
        try:
            # 1.0 抓取数据
            df = self.get_data(no_day=4)
            # df = df.loc[(df['udate'] <= datetime(2020, 12, 18, 4, 41, 0))] # 时间拦截器
            # 2.0 技术指标
            df2 = df.copy(deep=True)
            df2 = self.get_ta(df2)
            # 3.0 预测模型
            df3 = self.run_model(df=df2, df_o=df, prefix1='nq-lstm', prefix2='20201214-142731')
            # 4.0 买卖策略
            df4 = self.algo2()
            # 5.0
            res5_1 = requests.get(url=path_ib+'/list-orders')
            res5_2 = requests.get(url=path_ib+'/list-trades')
        except:
            pass

    def run(self):
        while True:
            cur_minute, cur_second = datetime.today().minute, datetime.today().second
            if cur_second == 6:
                self.do()
            time1.sleep(1)


if __name__ == '__main__':
    Worker().start()
