import json
import sys
import socket
import select
import request_server as rs
import pymysql as sql
import message as ms
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
                                  charset='utf8', autocommit=True)
        self.cursor = self.sql_db.cursor()
        print("SQL connection succeed.")
        self.socket_machine.socket.bind(self.socket_machine.SERVER)
        self.socket_machine.socket.listen(5)

        self.all_sockets.append(self.socket_machine.socket)

        self.sonnet = pind.PIndex("AllSonnets.txt")

    def new_client(self, new_sock):
        print("new connection attempt..")
        new_sock.setblocking(0)
        self.new_clients.append(new_sock)
        self.all_sockets.append(new_sock)
        # self.all_sockets.append()

    def login(self, sock, msg: ms.Message):
        print("login request received.")
        sql_query = f"select uid,username,password,publickey from users where binary username=\'{msg.from_name}\';"
        self.cursor.execute(sql_query)
        self.sql_db.commit()
        results = self.cursor.fetchall()
        feedback = ms.Message("system", msg.from_name, "login_feedback", "")
        flg = False
        if len(results) == 0:
            feedback.content = "not_exist"
        else:
            if msg.content != results[0][2]:
                feedback.content = "wrong"
            elif results[0][3] == "":
                feedback.content = "no_publickey"
            else:
                feedback.content = "success+" + self.query_relation(msg.from_name)
                flg = True

        rs.MySocketClient.custom_send(sock, feedback)
        if flg:
            print("login success")
            # self.all_sockets.append(sock)
            self.new_clients.remove(sock)
            self.logged_name2sock[msg.from_name] = sock
            self.logged_sock2name[sock] = msg.from_name
            sql_query = f"update state set state=1 where uid={results[0][0]};"
            self.cursor.execute(sql_query)
            self.sql_db.commit()

    def logout(self, sock, name):
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        sock.close()
        uid = self.get_uid_by_name(name)
        sql_query = f"update state set state=0 where uid={uid};"
        self.cursor.execute(sql_query)
        self.sql_db.commit()

    def register(self, sock, msg: ms.Message):
        sql_query = f"select username from users where binary username=\'{msg.from_name}\';"
        self.cursor.execute(sql_query)
        results = self.cursor.fetchall()
        feedback = ms.Message("system", msg.from_name, "register_feedback", "")
        print("register results", results)
        if len(results) > 0:
            feedback.content = "duplicate"
        else:
            try:
                create = f"insert into users (username, password, publickey) values (\'{msg.from_name}\', \'{msg.content}\', \'\');"
                self.cursor.execute(create)
                self.sql_db.commit()

                feedback.content = "success"
            except Exception as err:
                self.sql_db.rollback()
                feedback.content = "database error"
        rs.MySocketClient.custom_send(sock, feedback)
        if feedback.content == "success":
            u_query = f"select uid from users where binary username = \'{msg.from_name}\';"
            self.cursor.execute(u_query)
            self.sql_db.commit()
            results = self.cursor.fetchall()

            try:
                create = f"insert into state (uid, state) values ({results[0][0]}, 0);"
                self.cursor.execute(create)
                self.sql_db.commit()

            except Exception as err:
                print("state machine error.")
                self.sql_db.rollback()

    # sql operation methods begin ---

    def get_uid_by_name(self, name):
        sql_query = f"select uid from users where binary username=\'{name}\';"
        self.cursor.execute(sql_query)
        results = self.cursor.fetchall()
        if len(results) > 0:
            return results[0][0]
        else:
            return -1

    def check_online(self, name):
        print("Checking Online.")
        new_cursor = self.sql_db.cursor()
        uid = f"select uid, username from users where binary username=\'{name}\';"
        print("checking:" + name)
        print(uid)
        new_cursor.execute(uid)
        results = new_cursor.fetchall()
        print("online checker", len(results))
        self.sql_db.commit()
        if len(results) == 0:
            return False
        uid = results[0][0]
        time.sleep(1)
        sql_query = f"select uid,state from state where uid=\'{uid}\';"  # to be modified
        new_cursor.execute(sql_query)
        results = new_cursor.fetchall()
        self.sql_db.commit()
        new_cursor.close()
        time.sleep(1)
        if results[0][1] == 1:
            return True
        else:
            return False

    def add_msg_queue(self, msg):
        # ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
        sql_query = f"""insert into msgQueue(fromname, toname, actiontype, content, time) values (\'{msg.from_name}\', \'{msg.to_name}\', \'{msg.action_type}\', \'{msg.content}\', NOW());"""
        new_cursor = self.sql_db.cursor()
        try:
            new_cursor.execute(sql_query)
            self.sql_db.commit()
        except Exception as err:
            print("msgQueue inserting failed.", err)
            self.sql_db.rollback()
        new_cursor.close()

    def fetch_rsa_table(self, name):
        sql_query = f"select publickey from users where binary username=\'{name}\'"
        self.cursor.execute(sql_query)
        self.sql_db.commit()
        results = self.cursor.fetchall()
        time.sleep(2)
        return results[0][0]

    def query_relation(self, name):
        uid_query = f"select uid from users where binary username=\'{name}\';"
        self.cursor.execute(uid_query)
        results = self.cursor.fetchall()
        relation_query = f"""select uid2name as friends from friendrelation where uid1={results[0][0]}
                             union all
                             select uid1name as friends from friendrelation where uid2={results[0][0]};"""
        self.cursor.execute(relation_query)
        relation_list = self.cursor.fetchall()
        relation_string = ""
        if len(relation_list) > 0:
            # relation_string += sum([line[0] + "," for line in relation_list])
            n = len(relation_list)
            for i in range(n):
                relation_string += relation_list[i][0]
                relation_string += ","
        # relation_list should be added
        relation_string += ""
        return relation_string

    def add_publickey(self, msg):
        update = f"update users set publickey=\'{msg.content}\' where binary username=\'{msg.from_name}\'"
        try:
            self.cursor.execute(update)
            self.sql_db.commit()
        except:
            self.sql_db.rollback()

    def query_blocked_msg(self, name):
        sql_query = f"select fromname, toname, actiontype, content, mid from msgQueue where binary toname=\'{name}\';"
        self.cursor.execute(sql_query)
        results = self.cursor.fetchall()
        blocked = []
        for msg in results:
            blocked.append(ms.Message(msg[0], msg[1], msg[2], msg[3]))
            sql_query = f"delete from msgQueue where mid={msg[4]};"
            self.cursor.execute(sql_query)
            self.sql_db.commit()
        return blocked

    def fetch_uid_pair(self, username1, username2):
        uid1 = f"select uid from users where username=\'{username1}\';"
        uid2 = f"select uid from users where username=\'{username2}\';"
        self.cursor.execute(uid1)
        self.sql_db.commit()
        uid1 = self.cursor.fetchall()
        uid1 = uid1[0][0]
        time.sleep(0.5)
        if username2 != "":
            self.cursor.execute(uid2)
            self.sql_db.commit()
            uid2 = self.cursor.fetchall()
            if len(uid2) == 0:  # target not exist.
                return -1
            else:
                uid2 = uid2[0][0]
        else:
            uid2 = -1  # for group, empty meaning.
        print("uid fetched.")
        return uid1, uid2

    def fetch_gid(self, name):
        sql_query = f"select gid from groupinfo where groupname=\'{name}\'"
        self.cursor.execute(sql_query)
        results = self.cursor.fetchall()
        self.sql_db.commit()
        if len(results) == 0:
            return -1
        else:
            return results[0][0]

    def create_relation(self, username1, username2):
        uid1, uid2 = self.fetch_uid_pair(username1, username2)
        if uid1 > uid2:
            uid2, uid1 = uid1, uid2
            username2, username1 = username1, username2
        print("try adding data.")
        inserting = f"insert into friendrelation (uid1, uid2, uid1name, uid2name) values ({uid1}, {uid2}, \'{username1}\', \'{username2}\');"
        try:
            self.cursor.execute(inserting)
            self.sql_db.commit()
        except:
            print("relation error.")
            self.sql_db.rollback()

    def delete_relation(self, username1, username2):
        uid1, uid2 = self.fetch_uid_pair(username1, username2)
        if uid1 > uid2:
            uid2, uid1 = uid1, uid2
        deleting = f"delete from friendrelation where uid1={uid1} and uid2={uid2};"
        try:
            self.cursor.execute(deleting)
            self.sql_db.commit()
        except:
            self.sql_db.rollback()

    def check_relation(self, name1, name2):
        if name2[0] == "(":
            uid, uid2 = self.fetch_uid_pair(name1, "")
            gid = self.fetch_gid(name2)
            if gid == -1:
                return -1  # group not exist
            sql_query = f"select uid, gid from grouprelation where uid={uid} and gid={gid};"
            length = self.cursor.execute(sql_query)
            results = self.cursor.fetchall()
            if length == 0:
                return 0  # not in group
            else:
                return 1  # in group

        else:
            uid1, uid2 = self.fetch_uid_pair(name1, name2)
            if uid2 == -1:
                return -1  # friend not exist
            if uid1 > uid2:
                uid2, uid1 = uid1, uid2
            sql_query = f"select pkey from friendrelation where uid1={uid1} and uid2={uid2};"
            self.cursor.execute(sql_query)
            results = self.cursor.fetchall()
            if len(results) > 0:
                return 1  # already friend
            else:
                return 0  # not friend yet

    def get_group_members(self, name):
        members = []
        gid = self.fetch_gid(name)
        sql_query = f"""select grouprelation.uid, users.username from grouprelation
                        left join users
                        on grouprelation.uid=users.uid
                        where grouprelation.gid={gid};"""
        self.cursor.execute(sql_query)
        results = self.cursor.fetchall()
        for member in results:
            members.append(member[1])
        return members

    def enroll(self, username, name):
        gid = self.fetch_gid(name)
        uid, uid2 = self.fetch_uid_pair(username, "")
        inserting = f"insert into grouprelation (uid, gid) values ({uid}, {gid});"
        try:
            self.cursor.execute(inserting)
            self.sql_db.commit()
        except:
            self.sql_db.rollback()

    def new_group(self, username, name):
        uid, uid2 = self.fetch_uid_pair(username, "")
        create = f"insert into groupinfo (creatorid, emptystate, groupname) values ({uid}, 0, \'{name}\')"
        try:
            self.cursor.execute(create)
            self.sql_db.commit()
        except:
            self.sql_db.rollback()
        self.enroll(username, name)

    # sql operation methods end ---

    def remove_sock(self, sock):
        self.all_sockets.remove(sock)
        self.new_clients.remove(sock)
        sock.close()

    def offline_proc(self, new_sock):
        msg = rs.MySocketClient.custom_recv(new_sock)
        if msg.action_type == "error":
            self.logout(new_sock, msg.from_name)
        # if len(msg) > 0:
        if msg.action_type == "login":
            self.login(new_sock, msg)
        elif msg.action_type == "register":
            self.register(new_sock, msg)
        elif msg.action_type == "register_key":
            self.add_publickey(msg)
        elif msg.action_type == "close" or msg.action_type == "empty":
            self.remove_sock(new_sock)

    def online_proc(self, sock):
        msg = rs.MySocketClient.custom_recv(sock)
        if msg.action_type == "close" or msg.action_type == "empty":
            self.logout(sock, msg.from_name)
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
            rsa_key = self.fetch_rsa_table(msg.to_name)
            new_msg = ms.Message(msg.from_name, msg.to_name, "fetch_key", rsa_key)
            rs.MySocketClient.custom_send(sock, new_msg)
        elif msg.action_type == "exchange":  # transfer
            if msg.to_name[0] == "(":
                members = self.get_group_members(msg.to_name)
                for member in members:
                    state = self.check_online(member)
                    if state:
                        rs.MySocketClient.custom_send(self.logged_name2sock[member], msg)
                    else:
                        self.add_msg_queue(msg)
            else:
                state = self.check_online(msg.to_name)
                if state:
                    rs.MySocketClient.custom_send(self.logged_name2sock[msg.to_name], msg)
                else:
                    self.add_msg_queue(msg)
        elif msg.action_type == "add_friend":  # transfer a change request
            print("add_friend executing")
            relation_state = self.check_relation(msg.from_name, msg.to_name)
            if relation_state == 1:
                new_msg = ms.Message(msg.to_name, msg.from_name, "friend_respond", "duplicate")
                rs.MySocketClient.custom_send(sock, new_msg)
            elif relation_state == 0:
                state = self.check_online(msg.to_name)
                publickey = self.fetch_rsa_table(msg.from_name)
                new_msg = ms.Message(msg.from_name, msg.to_name, "change", publickey+"___"+msg.content)
                if state:
                    rs.MySocketClient.custom_send(self.logged_name2sock[msg.to_name], new_msg)
                else:
                    self.add_msg_queue(new_msg)
            else:
                new_msg = ms.Message(msg.to_name, msg.from_name, "friend_respond", "not_exist")
                rs.MySocketClient.custom_send(sock, new_msg)
        elif msg.action_type == "add_group":  # transfer a negotiate request
            if msg.content == "first_trial":
                relation_state = self.check_relation(msg.from_name, msg.to_name)
                if relation_state == 1:
                    new_msg = ms.Message("system", msg.from_name, "group_respond", "duplicate")
                    rs.MySocketClient.custom_send(sock, new_msg)
                elif relation_state == -1:
                    new_msg = ms.Message("system", msg.to_name, "group_respond", "not_exist")
                    self.new_group(msg.from_name, msg.to_name)
                    rs.MySocketClient.custom_send(sock, new_msg)
                elif relation_state == 0:
                    all_members = self.get_group_members(msg.to_name)
                    new_msg = ms.Message("system", msg.from_name, "group_respond", "waiting")
                    rs.MySocketClient.custom_send(sock, new_msg)
                    for member in all_members:
                        rsa_key = self.fetch_rsa_table(member)
                        new_msg = ms.Message(member, msg.from_name, "fetch_key", rsa_key)
                        rs.MySocketClient.custom_send(sock, new_msg)
                    member_list = ""
                    for member in all_members:
                        member_list += member + ","
                    new_msg = ms.Message("system", msg.to_name, "group_respond", member_list)
                    rs.MySocketClient.custom_send(sock, new_msg)
                    new_msg = ms.Message("system", msg.from_name, "group_respond", "finished")
                    rs.MySocketClient.custom_send(sock, new_msg)
            elif msg.content == "second_trial":
                # create group relation
                self.enroll(msg.from_name, msg.to_name)
                new_msg = ms.Message("system", msg.to_name, "group_respond", "success")
                rs.MySocketClient.custom_send(sock, new_msg)
            else:
                rsa_key = self.fetch_rsa_table(msg.from_name)
                new_msg = ms.Message(self.logged_sock2name[sock], msg.from_name, "negotiate", rsa_key + "___" + msg.content)  # username, group name, negotiate pack.
                state = self.check_online(msg.to_name)
                if state:
                    self.socket_machine.custom_send(self.logged_name2sock[msg.to_name], new_msg)
                else:
                    self.add_msg_queue(new_msg)
        elif msg.action_type == "friend_respond":  # transfer to origin
            print("respond received.")
            state = self.check_online(msg.to_name)
            new_msg = ms.Message(msg.from_name, msg.to_name, "friend_respond", msg.content)
            if state:
                rs.MySocketClient.custom_send(self.logged_name2sock[msg.to_name], new_msg)
                print("friend respond sent.")
            else:
                self.add_msg_queue(new_msg)
            self.create_relation(msg.from_name, msg.to_name)
            print("relation added.")
        elif msg.action_type == "key":  # transfer to origin
            pass
        elif msg.action_type == "fetch_key":
            rsa = self.fetch_rsa_table(msg.to_name)
            new_msg = ms.Message(msg.from_name, msg.to_name, msg.action_type, rsa)
            rs.MySocketClient.custom_send(sock, new_msg)
        elif msg.action_type == "logout":
            self.logout(sock, msg.from_name)
        elif msg.action_type == "disconnect":
            if msg.to_name[0] == "(":
                pass
            else:
                state = self.check_online(msg.to_name)
                self.delete_relation(msg.from_name, msg.to_name)
                if state:
                    rs.MySocketClient.custom_send(self.logged_name2sock[msg.to_name], msg)
                else:
                    self.add_msg_queue(msg)
        elif msg.action_type == "begin":
            blocked = self.query_blocked_msg(msg.from_name)
            for line in blocked:
                rs.MySocketClient.custom_send(sock, line)
            print("blocked sent.")
        else:
            pass

    def run(self):
        print("starting server...")
        while True:
            read, write, error = select.select(self.all_sockets, [], [])
            print("checking logged clients...")
            # proc msg
            for log_c in list(self.logged_name2sock.values()):
                if log_c in read:
                    self.online_proc(log_c)
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
