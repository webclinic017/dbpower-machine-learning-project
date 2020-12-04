import os
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import ib_insync as ib
import json as json
from tornado.options import define, options

define("ib_host", default='127.0.0.1', help="host", type=str)
define("ib_port", default=4002, help="port", type=int)
define("ib_client", default=1, help="client id", type=int)
define("ib_timeout", default=5000, help="timeout", type=int)
define("web_port", default=84, help="run on the given port", type=int)

conn = ib.IB()
conn.connect(options.ib_host, port=options.ib_port, clientId=options.ib_client, timeout=options.ib_timeout)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/place-order", OrderHandler),
            (r"/list-positions", ListPositions),
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


class OrderHandler(tornado.web.RequestHandler):
    def get(self):
        data = {}
        for k, v in self.request.arguments.items():
            data[k] = v[0].decode("utf-8")
        self.write(json.dumps(data))


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


def main():
    tornado.options.parse_command_line()
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.web_port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
