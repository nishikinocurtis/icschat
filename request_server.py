import socket
import json


class MySocketClient:

    def __init__(self, args):
        self.CHAT_PORT = 1112
        self.CHAT_IP = socket.gethostbyname(socket.gethostname()) if args.d is None else args.d
        self.SERVER = (self.CHAT_IP, self.CHAT_PORT)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.SIZE_SPEC = 5

        self.CHAT_WAIT = 0.2

    def recv_request(self):
        size = ''
        while len(size) < self.SIZE_SPEC:
            text = self.socket.recv(self.SIZE_SPEC - len(size)).decode()
            if not text:
                print('disconnected')
                return ''
            size += text
        size = int(size)

        msg = ''
        while len(msg) < size:
            text = self.socket.recv(size - len(msg)).decode()
            if text == b'':
                print('disconnected')
                break
            msg += text
        # print ('received '+message)
        return json.load(msg)

    def init_connection(self):
        self.socket.connect(self.SERVER)

    def send_request(self, from_name=None, to_name=None, head=None, content=None):
        content = json.dumps({"from": from_name, "to": to_name, "head": head, "content": content})
        content = f"%05d" % (len(content)) + str(content)  # SIZE_SPEC
        content = content.encode()
        total_sent = 0
        while total_sent < len(content):
            sent = self.socket.send(content[total_sent:])
            if sent == 0:
                print('server disconnected')
                break
            total_sent += sent





