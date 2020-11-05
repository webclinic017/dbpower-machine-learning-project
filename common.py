import sqlite3 as sqlite3
import pandas as pd
import numpy as np
import os as os
import talib as talib

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

def kdj(high, low, close, fastk_period, slowk_period, slowk_matype ,slowd_period ,slowd_matype):
    slowk, slowd = talib.STOCH(high, low, close, fastk_period, slowk_period, slowk_matype, slowd_period ,slowd_matype)
    slowj = list(map(lambda x,y: 3 * x - 2 * y, slowk, slowd))
    return slowk, slowd, slowj
