import socket
import json
import message as ms

sz_spec = 5


class MySocketClient:

    def __init__(self, args=None):
        self.CHAT_PORT = 1112
        self.CHAT_IP = "159.65.242.12" # socket.gethostbyname(socket.gethostname())
        if args is not None:
            self.CHAT_IP = self.CHAT_IP if args.p is None else args.p
        self.SERVER = (self.CHAT_IP, self.CHAT_PORT)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.SIZE_SPEC = 5

        self.CHAT_WAIT = 1.0

    def recv_request(self):
        size = ''
        while len(size) < self.SIZE_SPEC:
            text = self.socket.recv(self.SIZE_SPEC - len(size)).decode()
            if not text:
                print('disconnected')
                return ms.Message(action_type="error")
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
        if len(msg) > 0:
            msg = json.loads(msg)
            return ms.Message(msg["from"], msg["to"], msg["head"], msg["content"])
        else:
            return ms.Message(action_type="error")

    def init_connection(self):
        self.socket.connect(self.SERVER)

    def send_request(self, msg=ms.Message("empty")):
        content = json.dumps({"from": msg.from_name, "to": msg.to_name, "head": msg.action_type, "content": msg.content})
        content = f"%05d" % (len(content)) + str(content)  # SIZE_SPEC
        content = content.encode()
        total_sent = 0
        while total_sent < len(content):
            sent = self.socket.send(content[total_sent:])
            if sent == 0:
                print('server disconnected')
                break
            total_sent += sent

    @staticmethod
    def custom_send(to_sock, msg: ms.Message):
        """send to custom sock"""
        content = json.dumps({"from": msg.from_name, "to": msg.to_name, "head": msg.action_type, "content": msg.content})
        content = f"%05d" % (len(content)) + str(content)  # SIZE_SPEC
        content = content.encode()
        total_sent = 0
        while total_sent < len(content):
            sent = to_sock.send(content[total_sent:])
            if sent == 0:
                print('server disconnected')
                break
            total_sent += sent

    @staticmethod
    def custom_recv(from_sock) -> ms.Message:
        size = ''
        while len(size) < sz_spec:
            text = from_sock.recv(sz_spec - len(size)).decode()
            if not text:
                print('disconnected')
                return ms.Message(action_type="empty")
            size += text
        size = int(size)

        msg = ''
        while len(msg) < size:
            text = from_sock.recv(size - len(msg)).decode()
            if text == b'':
                print('disconnected')
                break
            msg += text
        # print ('received '+message)
        if len(msg) > 0:
            msg = json.loads(msg)
            return ms.Message(msg["from"], msg["to"], msg["head"], msg["content"])
        else:
            return ms.Message(action_type="error")

    def quit(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
