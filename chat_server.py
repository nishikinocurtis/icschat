import json
import sys
import socket
import select
import request_server as rs
import pymysql as sql
import message as ms
import encrypter as enc
import time
import pindexer as pind


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

        self.sonnet = pind.PIndex("AllSonnets.txt")

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
            self.logged_name2sock[msg.from_name] = sock
            self.logged_sock2name[sock] = msg.from_name
            sql_query = "update state set state=1 where uid=%d" % results[0][0]
            self.cursor.execute(sql_query)
            self.sql_db.commit()
            # push blocked messages

    def logout(self, sock, name):
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        sock.close()
        sql_query = "update state set state=0 where username=%s" % name
        self.cursor.execute(sql_query)
        self.sql_db.commit()

    def register(self, sock, msg: ms.Message):
        pass

    # sql operation methods begin ---

    def check_online(self, username):
        sql = "select username,state from state where username=%s" % username  # to be modified
        self.cursor.execute(sql)
        results = self.cursor.fetchall()
        if results[0][1] == 1:
            return True
        else:
            return False

    def add_msg_queue(self, msg):
        ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
        sql = f"""insert into msgQueue(fromname,
                  toname, actiontype, content, time)
                  values (\'{msg.from_name}\', \'{msg.to_name}\', \'{msg.action_type}\', \'{msg.content}\', \'{ctime}\')"""
        try:
            self.cursor.execute(sql)
            self.sql_db.commit()
        except Exception as err:
            print("msgQueue inserting failed.")
            self.sql_db.rollback()

    # sql operation methods end ---

    def offline_proc(self, new_sock):
        msg = rs.MySocketClient.custom_recv(new_sock)
        #if len(msg) > 0:
        if msg.action_type == "login":
            self.login(new_sock, msg)
        elif msg.action_type == "register":
            self.register(new_sock, msg)

    def online_proc(self, sock):
        msg = rs.MySocketClient.custom_recv(sock)
        if msg.action_type == "time":  # reply with info
            ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
            new_msg = ms.Message("system", msg.from_name, "notification", "Server time: " + ctime)
            rs.MySocketClient.custom_send(sock, new_msg)
        elif msg.action_type == "poem":  # reply with info
            poem_list = self.sonnet.get_poem(int(msg.content))
            poem = ""
            for sentence in poem_list:
                poem += sentence + "\n"
            poem += "\n"
            new_msg = ms.Message("system", msg.from_name, "notification", poem)
            rs.MySocketClient.custom_send(sock, new_msg)
        elif msg.action_type == "fetch_key":
            pass
        elif msg.action_type == "exchange":  # transfer
            state = self.check_online(msg.to_name)
            if state:
                rs.MySocketClient.custom_send(self.logged_name2sock[msg.to_name], msg)
            else:
                self.add_msg_queue(msg)
        elif msg.action_type == "add_friend":  # transfer a change request
            state = self.check_online(msg.to_name)
            new_msg = ms.Message(msg.from_name, msg.to_name, "change", msg.content)
            if state:
                rs.MySocketClient.custom_send(self.logged_name2sock[msg.to_name], new_msg)
            else:
                self.add_msg_queue(new_msg)
        elif msg.action_type == "add_group":  # transfer a negotiate request
            pass
        elif msg.action_type == "friend_respond":  # transfer to origin
            rs.MySocketClient.custom_send(self.logged_name2sock[msg.to_name], msg)
        elif msg.action_type == "key":  # transfer to origin
            pass
        elif msg.action_type == "fetch_key":
            rsa = self.fetch_rsa_table(msg.to_name)
            new_msg = ms.Message(msg.from_name, msg.to_name, msg.action_type, rsa)
            rs.MySocketClient.custom_send(sock, new_msg)
        elif msg.action_type == "logout":
            self.logout(sock, msg.from_name)
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
