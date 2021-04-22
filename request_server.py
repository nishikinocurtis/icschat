import socket
import json

CHAT_PORT = 1112
CHAT_IP = socket.gethostbyname(socket.gethostname())
SERVER = (CHAT_IP, CHAT_PORT)

SIZE_SPEC = 5

CHAT_WAIT = 0.2


def send_request(my_socket, from_name=None, to_name=None, head=None, content=None):
    content = json.dumps({"from": from_name, "to": to_name, "head": head, "content": content})
    content = f"%05d" % (len(content)) + str(content)  # SIZE_SPEC
    content = content.encode()
    total_sent = 0
    while total_sent < len(content):
        sent = my_socket.send(content[total_sent:])
        if sent == 0:
            print('server disconnected')
            break
        total_sent += sent


def recv_request(my_socket):
    size = ''
    while len(size) < SIZE_SPEC:
        text = my_socket.recv(SIZE_SPEC - len(size)).decode()
        if not text:
            print('disconnected')
            return ('')
        size += text
    size = int(size)

    msg = ''
    while len(msg) < size:
        text = my_socket.recv(size - len(msg)).decode()
        if text == b'':
            print('disconnected')
            break
        msg += text
    # print ('received '+message)
    return json.load(msg)
