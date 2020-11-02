import sqlite3 as sqlite3
import pandas as pd
import numpy as np
import os as os

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
    import numpy as np
    signal   = []
    previous = 2
    for date,value in percentB.iteritems():
        if value > 1 and previous <= 1:
            signal.append(price[date]*1.002)
        else:
            signal.append(np.nan)
        previous = value
    return signal
