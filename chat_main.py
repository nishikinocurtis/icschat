import argparse
import threading
import tkinter as tk
import encrypter as enc
import client_state_machine as csm
import socket
import select
import sys
import request_server as rs
import message as ms
import pickle


class Client:
    def __init__(self, args, name, root):
        self.args = args
        self.name = name
        self.root_window = root
        self.state = csm.ClientState()
        root.title("ICS Chat")
        root.geometry("600x520+16+9")

        self.socket_machine = rs.MySocketClient(self.args)

        # log_in_window initialize
        self.login_frame = tk.Frame(self.root_window)

        self.welcome_label = tk.Label(self.login_frame, text="Welcome to ICS Chat!")

        self.username = tk.StringVar()
        self.password = tk.StringVar()

        self.username_label = tk.Label(self.login_frame, text="Username: ")
        self.password_label = tk.Label(self.login_frame, text="Password: ")

        self.username_entry = tk.Entry(self.login_frame, textvariable=self.username)
        self.password_entry = tk.Entry(self.login_frame, textvariable=self.password, show="*")

        self.login_button = tk.Button(self.login_frame, text="Log In", command=self.login_request)
        self.login_back_button = tk.Button(self.login_frame, text="Back", command=self.offline_quit)

        self.login_blank = tk.Label(self.login_frame, text="")

        # chat window initialize
        self.tool_frame = tk.Frame(self.root_window)
        self.chat_back_button = tk.Button(self.tool_frame, text="Quit", command=self.logout_request, width=20)
        self.time_button = tk.Button(self.tool_frame, text="Time", command=self.server_time_request, width=10)
        self.poem_button = tk.Button(self.tool_frame, text="Poem", command=self.poem_request, width=10)
        self.current_label = tk.Label(self.tool_frame, text="Welcome to ICS Chat!", width=40)

        self.chat_back_button.grid(row=0, column=0, sticky=tk.W)
        self.time_button.grid(row=0, column=1, sticky=tk.W)
        self.poem_button.grid(row=0, column=2, sticky=tk.W)
        self.current_label.grid(row=0, column=3, sticky=tk.W)

        self.content_frame = tk.Frame(self.root_window)

        self.relations_frame = tk.LabelFrame(self.content_frame, text="Friends", height=500)

        self.relations_scroll = tk.Scrollbar(self.relations_frame, orient=tk.VERTICAL)
        self.relations_scroll.grid(row=0, column=1, sticky=tk.N + tk.S)

        self.relations_list = tk.Listbox(self.relations_frame, selectmode=tk.SINGLE,
                                         yscrollcommand=self.relations_scroll.set, height=21, width=25)
        self.relations_scroll.config(command=self.relations_list.yview)
        self.relations_list.grid(row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W)

        self.add_friend_button = tk.Button(self.relations_frame, text="+ Add Friend/Group", command=self.add_friend,
                                           width=25)
        self.add_friend_button.grid(row=1, column=0, columnspan=2, sticky=tk.W + tk.E + tk.S)

        self.messages_frame = tk.LabelFrame(self.content_frame, text="Messages", height=500)
        self.disconnect_button = tk.Button(self.messages_frame, text="Disconnect from this User/Group", width=40)
        self.disconnect_button.grid(row=0, column=0, columnspan=3, sticky=tk.E + tk.W)

        self.messages_scroll = tk.Scrollbar(self.messages_frame, orient=tk.VERTICAL)
        self.messages_scroll.grid(row=1, column=2, sticky=tk.N + tk.S)

        self.messages_list = tk.Listbox(self.messages_frame, height=20, yscrollcommand=self.messages_scroll.set,
                                        width=50)
        self.messages_scroll.config(command=self.messages_list.yview)
        self.messages_list.grid(row=1, column=0, columnspan=2, sticky=tk.N + tk.S + tk.E + tk.W)

        self.message = tk.StringVar()
        self.message_entry = tk.Entry(self.messages_frame, textvariable=self.message, width=45)
        self.send_button = tk.Button(self.messages_frame, text="Send", command=self.broadcast, width=5)
        self.message_entry.grid(row=2, column=0)
        self.send_button.grid(row=2, column=1, columnspan=2)

        self.relations_frame.grid(row=0, column=0, sticky=tk.N + tk.S)
        self.messages_frame.grid(row=0, column=1, sticky=tk.N + tk.S)

        # remember to bind change in relations list.

    def proc_package(self, msg):
        if msg.action_type == "notification":
            self.notification(self.root_window, msg.content)
        elif msg.action_type == "change":
            # negotiate and save sender's aes128 key
            # send my aes128 key "respond pack"
            # update relation listbox
            pass
        elif msg.action_type == "exchange":
            # decrypt with sender's aes128 key, when in group, the to_name attribute is group_name
            # update record and msg list
            pass
        elif msg.action_type == "friend_respond":
            # negotiate and save sender's aes128 key
            # update relation listbox
            # notice user success
            pass
        elif msg.action_type == "group_respond":
            if msg.content == "new":
                # update relation listbox
                # notice user creating a group
                pass
            else:
                # update relation listbox
                # fetch online member's aes128 key
                pass
        elif msg.action_type == "negotiate":
            # send my aes128key
            pass
        elif msg.action_type == "key":
            # previous offline members send their keys to me
            pass
        elif msg.action_type == "disconnect":
            # update relation listbox
            pass

    def scan_loop(self):
        while self.state.get() == csm.USER_ONLINE:
            msg = self.recv_package()
            self.proc_package(msg)

    def send_package(self, msg):
        self.socket_machine.send_request(msg)

    def recv_package(self):
        msg = self.socket_machine.recv_request()
        msg = ms.Message(from_name=msg["from"], to_name=msg["to"], action_type=msg["head"], content=msg["content"])
        return msg

    def start(self):
        self.log_in_window()
        self.socket_machine.init_connection()
        self.root_window.mainloop()

    def log_in_window(self):
        self.welcome_label.pack()

        self.username_label.pack()
        self.username_entry.pack()
        self.password_label.pack()
        self.password_entry.pack()

        self.login_blank.pack()

        self.login_button.pack(side=tk.RIGHT)
        self.login_back_button.pack(side=tk.RIGHT)

        self.login_frame.pack(pady=120, padx=160)

    def register_window(self):
        register_pop_up = tk.Toplevel(self.root_window)
        new_username = tk.StringVar()
        new_password = tk.StringVar()

        registering = lambda: self.register_request(new_username.get(), new_password.get())

        register_alert = tk.Label(register_pop_up, text="User does not exist. Please register.")

        new_username_label = tk.Label(register_pop_up, text="Username: ")
        new_password_label = tk.Label(register_pop_up, text="Password: ")

        new_username_entry = tk.Entry(register_pop_up, textvariable=self.username)
        new_password_entry = tk.Entry(register_pop_up, textvariable=self.password, show="*")

        register_button = tk.Button(register_pop_up, text="Register", command=registering)
        register_back_button = tk.Button(register_pop_up, text="Back", command=register_pop_up.destroy)

        register_blank = tk.Label(register_pop_up, text="")

        register_alert.pack()

        new_username_label.pack()
        new_username_entry.pack()
        new_password_label.pack()
        new_password_entry.pack()
        register_blank.pack()
        register_button.pack()
        register_back_button.pack()

    @staticmethod
    def start_thread(loop_func):
        new_thread = threading.Thread(target=loop_func)
        new_thread.daemon = True
        new_thread.start()

    @staticmethod
    def notification(root, content):
        new_dialog = tk.Toplevel(root)
        notification_content = tk.Label(new_dialog, text=content)
        ok_button = tk.Button(new_dialog, text="OK", command=new_dialog.destroy)

        notification_content.pack(pady=10, padx=10, anchor='n')
        ok_button.pack(pady=10, padx=10, anchor='s')

    def login_request(self):
        print(str(self.username.get()))
        print(str(self.password.get()))

        login_result, info = self.login_request_server(str(self.username.get()), str(self.password.get()))

        if login_result:
            self.state.set(csm.USER_ONLINE)
            self.login_window_destroy()
            self.chat_window()
            self.start_thread(self.scan_loop)
        else:
            if info == "wrong_password":
                self.password_entry.delete(0, 'end')
                self.notification(self.root_window, "Wrong Password, Please Try Again.")
            elif info == "not_exist":
                self.password_entry.delete(0, 'end')
                self.username_entry.delete(0, 'end')
                self.register_window()
            else:
                pass

    def register_request(self, username, password):
        print(username, password)
        register_result, info = self.register_request_server(username, password)
        if register_result:
            self.notification(self.root_window, "Registration Succeed, Please Log In.")
        else:
            pass

    @staticmethod
    def login_request_server(username, password):
        if username == "curtis" and password == "123":  # to be modified, socket success
            return True, "success"
        elif username == "curtis" and password != "123":  # to be modified, socket password wrong
            return False, "wrong_password"
        elif username != "curtis":  # to be modified, socked user not exist
            return False, "not_exist"
        else:
            pass

    @staticmethod
    def register_request_server(username, password):
        msg = ms.Message(username, "system", "register", password)
        # let encryptor generates new public key on server
        # receive a package
        return True, "success"

    def login_window_destroy(self):
        self.welcome_label.destroy()
        self.username_label.destroy()
        self.username_entry.destroy()
        self.password_entry.destroy()
        self.password_label.destroy()
        self.login_blank.destroy()
        self.login_back_button.destroy()
        self.login_button.destroy()
        self.login_frame.destroy()

    def chat_window(self):
        self.tool_frame.pack(pady=10, padx=10, anchor='nw')
        self.content_frame.pack(pady=10, padx=10, anchor='s')

    def offline_quit(self):
        # socket disconnect
        self.root_window.quit()

    def logout_request(self):
        # do something save record
        # socket disconnect
        self.state.set(csm.USER_OFFLINE)
        self.root_window.quit()

    def server_time_request(self):
        msg = ms.Message(str(self.username.get()), "system", "time", "")
        self.socket_machine.send_request(msg)
        # result = "Server Time: 05.01.2021,08:00:00 CST"
        # result = send pack to server type: time
        # self.notification(self.root_window, result)

    def poem_request(self):
        msg = ms.Message(str(self.username.get()), "system", "poem", "")
        self.socket_machine.send_request(msg)
        # result = "Sonnet Chapter 3"
        # result = send pack to server type: poem
        # self.notification(self.root_window, result)

    def add_friend_request(self, name):  # need to wait until friend go online.
        print("friend request called")
        attachment = ""  # keys
        msg = ms.Message(str(self.username.get()), name, "add_friend", attachment)
        self.socket_machine.send_request(msg)  # maybe need special port ?

    def add_group_request(self, name):
        print("group request called")
        msg = ms.Message(str(self.username.get()), name, "add_group", "")
        self.socket_machine.send_request(msg)  # maybe need special port ?

    def add_friend(self):  # raise new window
        add_window = tk.Toplevel(self.root_window)
        add_status = tk.IntVar()
        info_str = tk.StringVar()

        def add_request():
            if add_status.get() == 0:
                self.add_friend_request(str(info_str.get()))
            else:
                self.add_group_request(str(info_str.get()))
            info_entry.delete(0, 'end')

        guide_label = tk.Label(add_window, justify=tk.LEFT, padx=10,
                               text="Choose to add a friend or subscribe to a group")
        friend_radio = tk.Radiobutton(add_window, text="Friend", padx=10, variable=add_status,
                                      value=0)
        group_radio = tk.Radiobutton(add_window, text="Group", padx=10, variable=add_status,
                                     value=1)
        info_entry = tk.Entry(add_window, textvariable=info_str)
        add_button = tk.Button(add_window, text="Add", command=add_request)
        back_button = tk.Button(add_window, text="Back", command=add_window.destroy)

        guide_label.pack()
        friend_radio.pack()
        group_radio.pack()
        info_entry.pack()
        add_button.pack()
        back_button.pack()

    def request_friend_real(self):
        pass

    def request_group_real(self):
        pass

    def broadcast(self):
        current_content = self.message.get()
        self.message_entry.delete(0, 'end')
        # current_content enter file.
        # fetch current users
        #   encrypt by my AES128
        #   send to server
        # insert to message list


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', type=str, default=None)
    args = parser.parse_args()

    master = tk.Tk()
    client = Client(args, "ICS", master)
    client.start()
