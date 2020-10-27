import sqlite3 as sqlite3
import pandas as pd
import os

class DataSource:
    def __init__(self):
        self.db = None
        self.cursor = None
        self.data = {}
        self.name = os.path.abspath(os.path.join('data', 'hk', 'data.db'))
    
    def connect(self):
        self.db = sqlite3.connect(self.name)
        self.cursor = self.db.cursor()

    def get_data(self, ucodes):
        try:
            self.stocks = {}
            self.connect()
            self.db.row_factory = lambda cursor, row: row[0]
            for ucode in ucodes:
                sql = """SELECT t.code, t.lot, t.nmll, t.stime, t.high, t.low, t.open, t.close, t.volume
                            FROM (SELECT n.code, n.lot, n.nmll, c.stime, c.high, c.low, c.open, c.close, c.volume 
                                FROM s_{} AS c INNER JOIN name AS n 
                                    ON c.code=n.code ORDER BY c.stime DESC LIMIT 365*20) AS t 
                        ORDER BY t.stime""".format(ucode)
                self.cursor.execute(sql)
                columns = ['code', 'lot', 'nmll', 'sdate', 'high', 'low', 'open', 'last', 'vol']
                self.data[ucode] = pd.DataFrame(self.cursor.fetchall(), columns=columns)
            self.db.commit()
            self.cursor.close()
            self.db.close()
            return self.data
        except sqlite3.Error as e:
            print(e)

    def get_performance(self, ucodes):
        try:
            self.performance = {}
            self.connect()
            self.db.row_factory = lambda cursor, row: row[0]
            for ucode in ucodes:
                sql = """SELECT 
                            f.code, f.year, n.nmll, f.revenue, f.grossProfit, f.grossMargin, f.operatingIncome, f.pe, 
                            f.cashOperating,  f.netIncomeSemi, f.netIncomeEnd, 
                            f.epsEnd, f.cpsEnd, f.roeEnd, f.dteEnd, f.pegEnd, 
                            f.netIncomeQ1, f.netIncomeQ2, f.netIncomeQ3, f.netIncomeQ4,
                            f.epsQ1, f.epsQ2, f.epsQ3, f.epsQ4,
                            f.pegQ1, f.pegQ2, f.pegQ3, f.pegQ4,
                            f.cpsQ1, f.cpsQ2, f.cpsQ3, f.cpsQ4, 
                            f.roeQ1, f.roeQ2, f.roeQ3, f.roeQ4
                                FROM financial AS f
                                    INNER JOIN name AS n ON f.code = n.code
                                    WHERE f.code LIKE ?
                                        ORDER BY f.year"""
                if ucode[:1] == '0':
                    temp = ucode[1:]
                elif ucode[-1:] == 'o':
                    temp = ucode[:-1] + '.o'
                elif ucode[-1:] == 'k':
                    temp = ucode[:-1] + '.k'
                else:
                    temp = ucode
                self.cursor.execute(sql, ['%' + temp + '%', ])
                columns = ['code', 'year', 'nmll', 'revenue', 'grossProfit', 'grossMargin', 'operatingIncome', 'pe',
                           'cashOperating', 'netIncomeSemi', 'netIncomeEnd',
                           'epsEnd', 'cpsEnd', 'roeEnd', 'dteEnd', 'pegEnd',
                           'netIncomeQ1', 'netIncomeQ2', 'netIncomeQ3', 'netIncomeQ4',
                           'epsQ1', 'epsQ2', 'epsQ3', 'epsQ4',
                           'pegQ1', 'pegQ2', 'pegQ3', 'pegQ4',
                           'cpsQ1', 'cpsQ2', 'cpsQ3', 'cpsQ4',
                           'roeQ1', 'roeQ2', 'roeQ3', 'roeQ4']
                self.performance[ucode] = pd.DataFrame(self.cursor.fetchall(), columns=columns)
            self.db.commit()
            self.cursor.close()
            self.db.close()
            return self.performance
        except sqlite3.Error as e:
            print(e)
