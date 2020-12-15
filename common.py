import sqlite3 as sqlite3
import pandas as pd
import numpy as np
import os as os
import talib as talib
from datetime import datetime, timedelta, date, time

class Common:
    def __init__(self):
        return self

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
