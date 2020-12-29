import sqlite3 as sqlite3
import pandas as pd
import numpy as np
import os as os
import talib as talib
from datetime import datetime, timedelta, date, time


def percentB_belowzero(percentB, price):
    signal   = []
    previous = -1.0
    for date,value in percentB.iteritems():
        if value < 0 and previous >= 0:
            signal.append(price[date]*0.998)
        else:
            signal.append(np.nan)
        previous = value
    return signal

def percentB_aboveone(percentB, price):
    signal   = []
    previous = 2
    for date,value in percentB.iteritems():
        if value > 1 and previous <= 1:
            signal.append(price[date]*1.002)
        else:
            signal.append(np.nan)
        previous = value
    return signal

def kdj(high, low, close, window_size):
    slowk, slowd = talib.STOCH(high, low, close, fastk_period=5*window_size, slowk_period=3*window_size, slowk_matype=0, slowd_period=3*window_size, slowd_matype=0)
    slowj = list(map(lambda x,y: 3 * x - 2 * y, slowk, slowd))
    return slowk, slowd, slowj

def separate_daily(df2_1, return_type):
    data1 = {}
    # 2.1 交易日
    days1 = list(dict.fromkeys([v.date() for v in df2_1['udate']]))
    for day in days1:
        # 2.2 交易時間
        day_start = datetime(day.year, day.month, day.day, 17, 0, 0)
        day2 = day + timedelta(days=1)
        day_end = datetime(day2.year, day2.month, day2.day, 16, 0, 0)
        mask = ((df2_1['udate'] >= day_start) & (df2_1['udate'] <= day_end))
        df2_2 = df2_1.loc[mask]
        if (df2_2.shape[0] > 1):
            data1[day] = df2_2
    # 2.3 合併
    df2_3 = pd.DataFrame()
    for k, df2_4 in data1.items():
        df2_3 = pd.concat([df2_3, df2_4], axis=0, join='outer', ignore_index=False, keys=None, levels=None, names=None, verify_integrity=False, copy=True)
    # 2.4 返回類型
    if return_type=='df':
        return df2_3
    elif return_type=='dict':
        return data1

def algo(file1, file2, direction, vol, vol2, cutloss, is_adjust, minutes):
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
            if cur_time == close_time:  # 周2~5过夜
                is_over_night = True
            elif v1['udate'].weekday() == 0 and cur_time == time(9, 59, 0):  # 周1过夜
                is_over_night = True
            else:
                is_over_night = False
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

    df5.columns = ['udate', 'last', 'predict1(T+1)', 'predict1(T+5)', 'atr', 'shift', 'predict2(T+1)', 'predict2(T+5)',
                   'p-percent1', 'p-percent5', 'real(t+1)', 'real(t+5)',
                   'action', 'cash', 'profit', 'message', 'hold time']
    return df5
