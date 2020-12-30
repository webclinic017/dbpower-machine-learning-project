import time
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ip = socket.gethostbyname("192.168.21.132")
port = 5000
s.connect((ip, port))
while True:
    data = s.recv(1024*100)
    if not data:
        break
    print(data)
    time.sleep(1)
s.close()
