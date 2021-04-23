import sys
import socket
import select
import request_server as rs


class Server:
    def __init__(self):
        self.socket_machine = rs.MySocketClient()
        self.all_sockets = []
        self.logged_name2sock = {}
        self.logged_sock2name = {}

        self.socket_machine.socket.bind(self.socket_machine.SERVER)
        self.socket_machine.socket.listen(5)

        self.all_sockets.append(self.socket_machine.socket)

    def run(self):
        print("starting server...")
        while True:
            read, write, error = select.select(self.all_sockets, [], [])
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
