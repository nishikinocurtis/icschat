import json
import sys
import socket
import select
import request_server as rs
import pymysql as sql
import message as ms
import encrypter as enc


class Server:
    def __init__(self):
        self.socket_machine = rs.MySocketClient()
        self.all_sockets = []
        self.new_clients = []
        self.logged_name2sock = {}
        self.logged_sock2name = {}
        self.sql_db = sql.connect(host="localhost", user="curtis", password="Curtis.1020", database="ICSCHAT",
                                  charset='utf8')
        self.cursor = self.sql_db.cursor()
        self.socket_machine.socket.bind(self.socket_machine.SERVER)
        self.socket_machine.socket.listen(5)

        self.all_sockets.append(self.socket_machine.socket)

    def new_client(self, new_sock):
        print("new connection attempt..")
        new_sock.setblocking(0)
        self.new_clients.append(new_sock)
        # self.all_sockets.append()

    def login(self, sock, msg: ms.Message):
        sql_query = "select uid,username,password from userinfo where username='%s';" % msg.from_name
        self.cursor.execute(sql_query)
        results = self.cursor.fetchall()
        feedback = ms.Message("system", msg.from_name, "login_feedback", "")
        if len(results) == 0:
            feedback.content = "not_exist"
        else:
            if msg.content != results[0][2]:
                feedback.content = "wrong"
            else:
                feedback.content = "success"

        rs.MySocketClient.custom_send(sock, feedback)
        if feedback.content == "success":
            self.all_sockets.append(sock)
            sql_query = "update state set state=1 where uid=%d" % results[0][0]
            self.cursor.execute(sql_query)
            self.sql_db.commit()
            # push blocked messages

    def logout(self, sock, msg: ms.Message):
        pass

    def register(self, sock, msg: ms.Message):
        pass

    def offline_proc(self, new_sock):
        msg = rs.MySocketClient.custom_recv(new_sock)
        if len(msg) > 0:
            if msg.action_type == "login":
                self.login(new_sock, msg)
            elif msg.action_type == "register":
                self.register(new_sock, msg)

    def online_proc(self, sock):
        msg = rs.MySocketClient.custom_recv(sock)
        if msg.action_type == "time":  # reply with info
            pass
        elif msg.action_type == "poem":  # reply with info
            pass
        elif msg.action_type == "exchange":  # transfer
            pass
        elif msg.action_type == "add_friend":  # transfer a change request
            pass
        elif msg.action_type == "add_group":  # transfer a negotiate request
            pass
        elif msg.action_type == "friend_respond":  # transfer to origin
            pass
        elif msg.action_type == "key":  # transfer to origin
            pass
        else:
            pass

    def run(self):
        print("starting server...")
        while True:
            read, write, error = select.select(self.all_sockets, [], [])
            print("checking logged clients...")
            # proc msg
            print("checking new clients...")
            # proc initial msg
            for new_c in self.new_clients[:]:
                if new_c in read:
                    self.offline_proc(new_c)
            print("checking new connections")
            if self.socket_machine.socket in read:
                sock, address = self.socket_machine.socket.accept()
                self.new_client(sock)
            # server process order:
            # online:
            #
            #   accept negotiate pack or respond pack and transfer
            #     if target ON_LINE: send
            #     else enter blocked queue sql
            #   accept exchange request and transfer
            #     if target ON_LINE: send
            #     else enter blocked queue sql
            #   accept time and poem request
            #   accept add_friend or add_group request and transfer
            #     if target friend not exist: send notification sql
            #     if target group not exist: send group_respond "new", create group. maintain relationship chart
            #     if target ON_LINE: send friend request or negotiate info
            #     else enter blocked queue
            #   accept disconnect request:
            #     maintain relationship chart.
            #     if no members in target group, delete it. sql
            #     if target is single user, send "disconnect" pack
            #   accept logout request:
            #     delete sock, set OFF_LINE. sql
            # new client:
            #   accept register request, create account, send feedback, set OFF_LINE sql
            #   accept login request, send negotiate info, send friend request, send respond pack, send blocked message, set ON_LINE, move to online socket list sql
            # accept new client. socket

    def proc(self, msg):
        pass


if __name__ == "__main__":
    server = Server()
    server.run()
    # KeyInterruptionError: make all members OFF_LINE.
