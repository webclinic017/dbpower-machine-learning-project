import os
import time
import socket
import numpy as np
import datetime
import re
from io import BytesIO
from flask import Flask, render_template, request
from flask_socketio import SocketIO

# 1.0 flask
template_dir = os.path.join(os.path.abspath('data'), 'templates', 'dev')
static_folder = os.path.join(os.path.abspath('data'))
app = Flask(__name__, template_folder=template_dir, static_url_path='', static_folder=static_folder)
# 2.0 socket
socketio = SocketIO(app, cors_allowed_origins="*", async_handlers=True, async_mode='threading')
clients = []
# 3.0 tcp
def init_tcp():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip = socket.gethostbyname("192.168.21.132")
    port = 5000
    s.connect((ip, port))
    return s
s = init_tcp()


@app.route('/')
def index():
    return render_template('market-data-socket.html')


@socketio.on('connect')
def connect():
    clients.append(request.sid)


@socketio.on('disconnect')
def handle_disconnect():
    clients.remove(request.sid)
    print('disconnect', clients)


def encode2(buf):
    v1 = np.frombuffer(buf, dtype=np.uint16, count=1, offset=0)[0]
    v2 = np.frombuffer(buf, dtype=np.uint16, count=1, offset=2)[0]
    v3 = np.frombuffer(buf, dtype=np.uint16, count=1, offset=4)[0]
    v4 = np.frombuffer(buf, dtype=np.uint16, count=1, offset=6)[0]

    if v4 == 201:
        v5 = buf[8:24].decode()
        v5_1 = re.sub(r"[^\w\s]", '', v5)

        v6 = np.frombuffer(buf, dtype=np.uint32, count=1, offset=28)[0]
        v6_1 = float(str(v6)[:-4] + '.' + str(v6)[-4:])
        v7 = np.frombuffer(buf, dtype=np.uint32, count=1, offset=32)[0]
        v7_1 = float(str(v7)[:-4] + '.' + str(v7)[-4:])

        v8 = np.frombuffer(buf, dtype=np.uint64, count=1, offset=36)[0]
        v9 = np.frombuffer(buf, dtype=np.uint64, count=1, offset=44)[0]
        v10 = np.frombuffer(buf, dtype=np.uint64, count=1, offset=52)[0]
        v10_1 = int(str(v10)[:-10]) * 10
        v10_2 = datetime.datetime.utcfromtimestamp(v10_1).strftime('%Y-%m-%d %H:%M:%S')

        return {'omd_size': v1, 'omd_type': v2, 'dbp_size': v3, 'dbp_type': v4, 'code': v5_1,
                'best_bid': v6_1, 'best_ask': v7_1, 'best_bid_vol': v8, 'best_ask_vol': v9, 'datetime': v10_2}
    else:
        return {'result': 'False'}


@socketio.on('receive')
def handle_receive(data):
    print('receive: ', data)
    while True:
        data = s.recv(1024 * 100)
        f = BytesIO(data)
        buf = f.getvalue()
        if not data:
            break
        socketio.emit('receive2', buf, room=clients[-1])

        print(encode2(buf))

        time.sleep(1)


if __name__ == '__main__':
    socketio.run(app, debug=False, host='0.0.0.0', port=83)
