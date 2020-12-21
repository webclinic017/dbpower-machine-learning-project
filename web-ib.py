import os
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import ib_insync as ib
import pandas as pd
import json as json
import sqlite3 as sqlite3
from tornado.options import define, options
from datetime import datetime, timedelta, date

define("ib_host", default='127.0.0.1', help="host", type=str)
define("ib_port", default=4002, help="port", type=int)
define("ib_client", default=1, help="client id", type=int)
define("ib_timeout", default=5000, help="timeout", type=int)
define("web_port", default=84, help="run on the given port", type=int)

path_db = os.path.abspath(os.path.join('data', 'ib', 'ib.db'))

conn = ib.IB()
conn.connect(options.ib_host, port=options.ib_port, clientId=options.ib_client, timeout=options.ib_timeout)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            # index
            (r"/", MainHandler),
            # view
            (r"/show-account-info", ShowAccountInfo),
            (r"/list-positions", ListPositions),
            (r"/list-orders", ListOrders),
            (r"/list-trades", ListTrades),
            (r"/list-commission", ListCommission),
            # action
            (r"/place-limit-order", PlaceLimitOrder),
            (r"/place-market-order", PlaceMarketOrder),
        ]
        settings = dict(
            template_path=os.path.join(os.path.abspath('data'), 'templates', 'ib'),
            static_path=os.path.join(os.path.abspath('data'), 'templates', 'static'),
            static_url_prefix='/templates/static/',
            debug=False
        )
        super().__init__(handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class ShowAccountInfo(tornado.web.RequestHandler):
    def get(self):
        data = [v for v in conn.accountValues() if v.tag == 'NetLiquidationByCurrency' and v.currency == 'BASE'][0]
        data2 = {
            'account': data.account,
            'value': data.value,
            'tag': data.tag,
            'currency': data.currency,
            'modelCode': data.modelCode
        }
        self.write(json.dumps(data2))


class ListPositions(tornado.web.RequestHandler):
    def get(self):
        data = []
        for pos in conn.positions():
            data.append({
                'account': pos.account,
                'contract': {'conId': pos.contract.conId,
                             'symbol': pos.contract.symbol,
                             'lastTradeDateOrContractMonth': pos.contract.lastTradeDateOrContractMonth,
                             'multiplier': pos.contract.multiplier,
                             'currency': pos.contract.currency},
                'position': pos.position,
                'avgCost': pos.avgCost
            })
        self.write(json.dumps(data))


class ListOrders(tornado.web.RequestHandler):
    def get(self):
        data = []
        for order in conn.orders():
            data.append({
                'account': order.account,
                'permId': order.permId,
                'refFuturesConId': order.refFuturesConId,
                'action': order.action,
                'orderType': order.orderType,
                'filledQuantity': order.filledQuantity,
                'lmtPrice': order.lmtPrice,
                'trailStopPrice': order.trailStopPrice,
                'trailStopPrice': order.trailStopPrice,
                'parentPermId': order.parentPermId
            })
        # save db
        db = sqlite3.connect(path_db)
        cursor = db.cursor()
        df = pd.DataFrame(data=data)
        df['trailStopPrice'] = 0.0
        data2 = [v.values.tolist() for k, v in df.iterrows()]
        cursor.executemany("""replace into ib_order (account, permId, refFuturesConId, action, orderType, filledQuantity, 
        lmtPrice, trailStopPrice, parentPermId) values (?, ?, ?, ?, ?, ?, ?, ?, ?)""", data2)
        db.commit()
        cursor.close()
        db.close()
        #
        self.write(json.dumps(data))


class ListTrades(tornado.web.RequestHandler):
    def get(self):
        data = []
        for trade in conn.trades():
            if trade.fills:
                data.append({
                    'contract': {'conId': trade.fills[0].contract.conId,
                                 'symbol': trade.fills[0].contract.symbol,
                                 'localSymbol': trade.fills[0].contract.localSymbol,
                                 'exchange': trade.fills[0].contract.exchange,
                                 'currency': trade.fills[0].contract.currency,
                                 'lastTradeDateOrContractMonth': trade.contract.lastTradeDateOrContractMonth},
                    'execution': {'execId': trade.fills[0].execution.execId,
                                  'time': trade.fills[0].execution.time.strftime('%Y-%m-%d %H:%M:%S'),
                                  'acctNumber': trade.fills[0].execution.acctNumber,
                                  'exchange': trade.fills[0].execution.exchange,
                                  'price': trade.fills[0].execution.price,
                                  'permId': trade.fills[0].execution.permId,
                                  'clientId': trade.fills[0].execution.clientId,
                                  'orderId': trade.fills[0].execution.orderId},
                    'commissionReport': {'execId': trade.fills[0].commissionReport.execId,
                                         'commission': trade.fills[0].commissionReport.commission,
                                         'currency': trade.fills[0].commissionReport.currency}
                })
        # save db 1
        keys2 = []
        data2_2 = []
        for v in data:
            data2_1 = {}
            for k1, v1 in v.items():
                data2_1.update(v1)
            data2_2.append([v3 for k3, v3 in data2_1.items()])
            keys2 = list(data2_1.keys())
        keys2_2 = ", ".join(keys2)
        # save db 2
        db = sqlite3.connect(path_db)
        cursor = db.cursor()
        cursor.executemany("replace into ib_trade ("+keys2_2+") values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data2_2)
        db.commit()
        cursor.close()
        db.close()
        #
        self.write(json.dumps(data))


class ListCommission(tornado.web.RequestHandler):
    def get(self):
        data = []
        for fill in conn.fills():
            data.append({
                'execId': fill.commissionReport.execId,
                'commission': fill.commissionReport.commission,
                'currency': fill.commissionReport.currency
            })
        self.write(json.dumps(data))


class PlaceLimitOrder(tornado.web.RequestHandler):
    def get(self):
        data = {}
        for k, v in self.request.arguments.items():
            data[k] = v[0].decode("utf-8")
        if 'side' not in data or 'quantity' not in data or 'price' not in data or 'symbol' not in data \
                or 'exchange' not in data:
            self.write(json.dumps({'status': 'fail', 'params': {'side': 'buy/sell', 'quantity': 'int', 'price': 'float', 'symbol': 'NQ', 'exchange': 'GLOBEX'}}))
        elif not data['side'] == 'buy' and not data['side'] == 'sell':
            self.write(json.dumps({'status': 'fail', 'message': 'side must be buy or sell'}))
        elif int(data['quantity']) <= 0:
            self.write(json.dumps({'status': 'fail', 'message': 'quantity must be > 0'}))
        elif int(data['price']) <= 0:
            self.write(json.dumps({'status': 'fail', 'message': 'price must be > 0'}))
        else:
            order1 = ib.LimitOrder(data['side'].upper(), int(data['quantity']), int(data['price']))
            date1 = date.today().strftime('%Y%m')
            date1 = '202103'
            future1 = ib.Future(data['symbol'], date1, data['exchange'])
            trade1 = conn.placeOrder(future1, order1)
            data = {
                'contract': {'symbol': trade1.contract.symbol,
                             'lastTradeDateOrContractMonth': trade1.contract.lastTradeDateOrContractMonth,
                             'exchange': trade1.contract.exchange},
                'order': {'orderId': trade1.order.orderId,
                          'clientId': trade1.order.clientId,
                          'action': trade1.order.action,
                          'totalQuantity': trade1.order.totalQuantity,
                          'lmtPrice': trade1.order.lmtPrice}
            }
            self.write(json.dumps(data))


class PlaceMarketOrder(tornado.web.RequestHandler):
    def get(self):
        data = {}
        for k, v in self.request.arguments.items():
            data[k] = v[0].decode("utf-8")
        if 'side' not in data or 'quantity' not in data or 'symbol' not in data or 'exchange' not in data:
            self.write(json.dumps({'status': 'fail', 'params': {'side': 'buy/sell', 'quantity': 'int', 'symbol': 'NQ', 'exchange': 'GLOBEX'}}))
        elif not data['side'] == 'buy' and not data['side'] == 'sell':
            self.write(json.dumps({'status': 'fail', 'message': 'side must be buy or sell'}))
        elif int(data['quantity']) <= 0:
            self.write(json.dumps({'status': 'fail', 'message': 'quantity must be > 0'}))
        else:
            order1 = ib.MarketOrder(data['side'].upper(), int(data['quantity']))
            date1 = date.today().strftime('%Y%m')
            date1 = '202103'
            future1 = ib.Future(data['symbol'], date1, data['exchange'])
            trade1 = conn.placeOrder(future1, order1)
            data = {
                'contract': {'symbol': trade1.contract.symbol,
                             'lastTradeDateOrContractMonth': trade1.contract.lastTradeDateOrContractMonth,
                             'exchange': trade1.contract.exchange},
                'order': {'orderId': trade1.order.orderId,
                          'clientId': trade1.order.clientId,
                          'action': trade1.order.action,
                          'totalQuantity': trade1.order.totalQuantity}
            }
            self.write(json.dumps(data))


def main():
    tornado.options.parse_command_line()
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.web_port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
