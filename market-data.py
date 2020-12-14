import os
import json
import time
import pandas as pd
import urllib.request
import sqlite3 as sqlite3
from datetime import datetime
pd.options.mode.chained_assignment = None


df1 = pd.DataFrame(columns=['udate', 'high', 'low', 'open', 'close', 'vol'])
url = 'http://chart.dbpower.com.hk/buysellchart/tradeticker_routerxxxxx.cgi?bar=999999&code=NQZ20&format=json&data=nqorderflow&date=&period=&minute=1'
path_db = os.path.abspath(os.path.join('data', 'nq', 'data', 'nq.db'))


def get_date(df2, cur_second2):
    res = urllib.request.urlopen(url, timeout=10).read().decode('utf-8')
    if res:
        # 1.0
        res2 = json.loads(res)
        udate1 = res2['time']
        udate2 = datetime(year=datetime.today().year, month=int(udate1[-8:-6]), day=int(udate1[-6:-4]),
                          hour=int(udate1[-4:-2]), minute=int(udate1[-2:]), second=cur_second2)
        row = {'udate': udate2.strftime("%Y-%m-%d %H:%M:%S"), 'high': res2['high'], 'low': res2['low'],
               'open': res2['open'], 'close': res2['close'], 'vol': res2['volume']}
        # df2 = df2.append(row, ignore_index=True)
        # 2.0
        if (udate2.weekday() in [0, 1, 2, 3] and (udate2.hour <= 14 or udate2.hour >= 17)) \
                or (udate2.weekday() in [4] and udate2.hour <= 16) \
                or (udate2.weekday() in [6] and udate2.hour >= 17):
            # 3.0
            db = sqlite3.connect(path_db)
            cursor = db.cursor()
            cursor.execute('REPLACE INTO nq (udate, high, low, open, close, vol) VALUES (?, ?, ?, ?, ?, ?)', [v for k, v in row.items()])
            if cursor.rowcount == 1:
                print('Insert Success:{}  weekday:{}'.format(udate2, udate2.weekday()))
            else:
                print('Insert Fail:{}  weekday:{}'.format(udate2, udate2.weekday()))
            db.commit()
            cursor.close()
            db.close()
            return df2
        else:
            print('Not Trading Time:{}  weekday:{}'.format(udate2, udate2.weekday()))
            return df2
    else:
        print('No Data:{}  weekday:{}'.format(datetime.today().strftime("%Y-%m-%d %H:%M:%S"), datetime.today().weekday()))
        return df2


while True:
    try:
        cur_second = datetime.today().second
        # 每隔5秒
        if cur_second % 5 == 0:
            df1 = get_date(df1, cur_second)
        time.sleep(1)
    except:
        print('Except: {}'.format(datetime.today().strftime("%Y-%m-%d %H:%M:%S")))
