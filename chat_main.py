import argparse
import threading
import tkinter as tk
import encrypter as enc
import client_state_machine as csm
import request_server as rs
import message as ms
import indexer as idx
import time
import select
import random


class Client:
    def __init__(self, name, root, args):
        self.args = args
        self.name = name
        self.root_window = root
        self.state = csm.ClientState()
        root.title("ICS Chat")
        root.geometry("600x520+16+9")

        self.ms_indexer = idx.Indexer()
        self.socket_machine = rs.MySocketClient(self.args)
        self.encrypt_machine = enc.ClientEncryptor()

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

        self.relation_string = tk.StringVar()  # Protocol: "(Group)GroupName FriendName"
        self.relation_origin = []
        self.relations_list = tk.Listbox(self.relations_frame, selectmode=tk.SINGLE, listvariable=self.relation_string,
                                         yscrollcommand=self.relations_scroll.set, height=21, width=25)
        self.relations_scroll.config(command=self.relations_list.yview)
        self.relations_list.grid(row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W)

        self.relations_list.bind('<ButtonRelease-1>', self.change_current_relation)

        self.add_friend_button = tk.Button(self.relations_frame, text="+ Add Friend/Group", command=self.add_friend,
                                           width=25)
        self.add_friend_button.grid(row=1, column=0, columnspan=2, sticky=tk.W + tk.E + tk.S)

        self.messages_frame = tk.LabelFrame(self.content_frame, text="Messages", height=500)
        self.disconnect_button = tk.Button(self.messages_frame, text="Disconnect from this User/Group", width=40)
        self.disconnect_button.grid(row=0, column=0, columnspan=3, sticky=tk.E + tk.W)

        self.messages_scroll = tk.Scrollbar(self.messages_frame, orient=tk.VERTICAL)
        self.messages_scroll.grid(row=1, column=2, sticky=tk.N + tk.S)

        self.message_string = tk.StringVar()  # Protocol: "Username yyyy.mm.dd,hh:mm \n texts"
        self.message_origin = []
        self.messages_list = tk.Listbox(self.messages_frame, height=20, yscrollcommand=self.messages_scroll.set,
                                        listvariable=self.message_string, width=50, activestyle='none')
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
            print(msg.content)
            keys = msg.content.split("___")
            from_rsa_public_key = keys[0].encode('utf-8')
            encrypted_aes_key = keys[1]
            signature = keys[2]
            from_rsa_public_key = enc.ClientEncryptor.any_rsa_instance(from_rsa_public_key)
            if self.encrypt_machine.negotiate_aes(msg.from_name, from_rsa_public_key, encrypted_aes_key, signature):
                encrypted_aes_key, signature = self.encrypt_machine.create_negotiate_pack(from_rsa_public_key)
                attachment = encrypted_aes_key + "___" + signature
                new_msg = ms.Message(str(self.username.get()), msg.from_name, "friend_respond", attachment)
                self.socket_machine.send_request(new_msg)
                print("sent", new_msg)
                self.refresh_relation(self.relation_origin + [msg.from_name])
                self.notification(self.root_window, "New Friends: " + msg.from_name + " added!")
            else:
                print("Negotiation error.")
        elif msg.action_type == "exchange":
            # decrypt with sender's aes128 key, when in group, the to_name attribute is group_name
            # update record and msg list
            actual_message = enc.ClientEncryptor.aes_decrypt(bytes(msg.content, 'utf-8'), self.encrypt_machine.keyring[msg.from_name])
            actual_message = actual_message.decode('utf-8')
            display_message = Client.window_message_generator(msg.from_name, actual_message)
            self.ms_indexer.add_new(msg.from_name, display_message)
            if len(self.relations_list.curselection()) > 0\
               and msg.from_name == self.relation_origin[self.relations_list.curselection()[0]]:
                self.update_message(display_message)
        elif msg.action_type == "friend_respond":
            # negotiate and save sender's aes128 key
            # update relation listbox
            # notice user success
            print("respond received,", msg.content)
            keys = msg.content.split('___')
            # from_rsa_public_key = keys[0].encode('utf-8')
            encrypted_aes_key = keys[0]
            signature = keys[1]
            from_rsa_public_key = enc.ClientEncryptor.any_rsa_instance(self.encrypt_machine.rsa_keyring[msg.from_name])
            self.encrypt_machine.negotiate_aes(msg.from_name, from_rsa_public_key, encrypted_aes_key, signature)
            self.refresh_relation(self.relation_origin + [msg.from_name])
            self.notification(self.root_window, "Adding a friend successfully!")
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
        elif msg.action_type == "fetch_key":
            self.encrypt_machine.rsa_keyring[msg.to_name] = bytes(msg.content, 'utf-8')
            print(self.encrypt_machine.rsa_keyring[msg.to_name])

    def refresh_event(self):
        current_relation = self.relation_origin[self.relations_list.curselection()[0]]
        self.message_origin = self.ms_indexer.messages[current_relation]
        self.refresh_message(self.message_origin)

    def scan_loop(self):
        while self.state.get() == csm.USER_ONLINE:
            msg = self.try_get_msg()
            if isinstance(msg, ms.Message):
                self.proc_package(msg)
            time.sleep(self.socket_machine.CHAT_WAIT)

    def send_package(self, msg):
        self.socket_machine.send_request(msg)

    def try_get_msg(self):
        ret_msg = []
        read, write, error = select.select([self.socket_machine.socket], [], [], 0)
        if self.socket_machine.socket in read:
            ret_msg = self.socket_machine.recv_request()
        return ret_msg

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

        new_username_entry = tk.Entry(register_pop_up, textvariable=new_username)
        new_password_entry = tk.Entry(register_pop_up, textvariable=new_password, show="*")

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
        us = str(self.username.get())
        pwd = str(self.password.get())

        login_result, info = self.login_request_server(us, pwd)

        if login_result:
            print("request success.")
            self.ms_indexer.load_message(us)
            self.state.set(csm.USER_ONLINE)
            self.encrypt_machine.start(us)
            self.login_window_destroy()
            friends_groups = info.split("+")[1]
            self.refresh_relation(friends_groups.split(","))
            self.chat_window()
            self.start_thread(self.scan_loop)
            msg = ms.Message(us, "system", "begin", "")
            self.socket_machine.send_request(msg)
        else:
            if info == "wrong_password":
                self.password_entry.delete(0, 'end')
                self.notification(self.root_window, "Wrong Password, Please Try Again.")
            elif info == "not_exist":
                self.password_entry.delete(0, 'end')
                self.username_entry.delete(0, 'end')
                self.register_window()
            elif info == "no_publickey":
                self.notification(self.root_window, "PublicKey invalid.")
            else:
                pass

    def register_request(self, username, password):
        print(username, password)
        register_result, info = self.register_request_server(username, password)
        if register_result:
            self.encrypt_machine.start(username)
            msg = ms.Message(username, "system", "register_key", self.encrypt_machine.public_key_string())
            self.encrypt_machine.export_key()
            self.socket_machine.send_request(msg)
            self.notification(self.root_window, "Registration Succeed, Please Log In.")
        else:
            if info == "duplicate":
                self.notification(self.root_window, "Duplicate username. Please use another one.")
            else:
                pass

    def login_request_server(self, username, password):
        # return True, "success"
        # debug using
        msg = ms.Message(username, "system", "login", password)
        self.socket_machine.send_request(msg)
        print("login request sent.")
        feedback_msg = self.socket_machine.recv_request()
        print("login feedback received.")
        ls = feedback_msg.content.split("+")
        if ls[0] == "success":  # contain relation lists.
            return True, feedback_msg.content
        elif ls[0] == "wrong":
            return False, "wrong_password"
        elif ls[0] == "not_exist":
            return False, "not_exist"
        elif ls[0] == "no_publickey":
            return False, "no_publickey"
        else:
            return False, ""

    def register_request_server(self, username, password):
        msg = ms.Message(username, "system", "register", password)
        self.socket_machine.send_request(msg)
        feedback_msg = self.socket_machine.recv_request()
        print("register feedback received.")
        if feedback_msg.content == "success":
            return True, "success"
        elif feedback_msg.content == "duplicate":
            return False, "duplicate"
        else:
            return False, "others"
        # check existing username
        # let encryptor generates new public key on server
        # receive a package

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

    def change_current_relation(self, arg):
        current_relation = self.relation_origin[self.relations_list.curselection()[0]]
        print(current_relation)
        new_list = self.ms_indexer.get_message_list(current_relation)
        self.refresh_message(new_list)
        print(new_list)
        print("event called.")

    def refresh_relation(self, new_relation_list):
        self.relation_origin = new_relation_list
        new_string = ""
        if len(self.relation_origin) > 0:
            n = len(self.relation_origin)
            for i in range(n):
                new_string += self.relation_origin[i]
                if i < n - 1:
                    new_string += " "
        self.relation_string.set(new_string)

    def update_message(self, new_msg: str):  # a Message of change action
        self.message_origin.append(new_msg)
        self.messages_list.insert(tk.END, new_msg)

    def refresh_message(self, new_msg_list):
        self.message_string.set("")
        for msg in new_msg_list:
            self.messages_list.insert(tk.END, msg)

    def offline_quit(self):
        # socket disconnect
        msg = ms.Message("", "system", "close", "")
        self.socket_machine.send_request(msg)
        self.socket_machine.quit()
        self.root_window.quit()

    def logout_request(self):
        self.ms_indexer.save_message()
        self.state.set(csm.USER_OFFLINE)
        self.encrypt_machine.export_key()
        msg = ms.Message(self.username.get(), "system", "logout", "")
        self.socket_machine.send_request(msg)
        self.socket_machine.quit()
        # do something save record
        # socket disconnect
        self.root_window.quit()

    def server_time_request(self):
        msg = ms.Message(str(self.username.get()), "system", "time", "")
        self.socket_machine.send_request(msg)
        # result = "Server Time: 05.01.2021,08:00:00 CST"
        # result = send pack to server type: time
        # self.notification(self.root_window, result)

    def poem_request(self):
        number = random.randint(1, 109)
        msg = ms.Message(str(self.username.get()), "system", "poem", str(number))
        self.socket_machine.send_request(msg)
        # result = "Sonnet Chapter 3"
        # result = send pack to server type: poem
        # self.notification(self.root_window, result)

    def fetch_key(self, name):
        msg = ms.Message(self.username.get(), name, action_type="fetch_key", content="")
        self.socket_machine.send_request(msg)

    def add_friend_request(self, name):  # need to wait until friend go online.
        print("friend request called")
        if name not in self.encrypt_machine.rsa_keyring.keys():
            self.notification(self.root_window, "RSA Public Key invalid, please wait fetching")
            self.fetch_key(name)
            return
        else:
            rsa_public_key = enc.ClientEncryptor.any_rsa_instance(self.encrypt_machine.get_rsa_by_name(name))
            encrypted_aes_key, signature = self.encrypt_machine.create_negotiate_pack(rsa_public_key)  # protocol: extract signature, and make it a tuple when receving.
            attachment = encrypted_aes_key + "___" + signature
            msg = ms.Message(str(self.username.get()), name, "add_friend", attachment)
            self.socket_machine.send_request(msg)  # maybe need special port ?

    def add_group_request(self, name):
        print("group request called")
        encrypted_aes_key, signature = self.encrypt_machine.create_negotiate_pack()  # protocol: extract signature, and make it a tuple when receving.
        attachment = encrypted_aes_key + b"_" + signature[0]
        msg = ms.Message(str(self.username.get()), name, "add_group", attachment)
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

    @staticmethod
    def window_message_generator(username, content):
        ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
        return username + " " + ctime + " " + content

    def broadcast(self):
        current_content = self.message.get()
        if len(self.relation_origin) == 0:
            self.notification(self.root_window, "You have no friend or group now.")
            current_content = "To myself: " + Client.window_message_generator(self.username.get(), current_content)
            self.message_entry.delete(0, 'end')
            self.update_message(current_content)
            return
        else:
            self.message_entry.delete(0, 'end')
            selected = self.relations_list.curselection()[0]
            display_content = Client.window_message_generator(self.username.get(), current_content)
            self.update_message(Client.window_message_generator(self.username.get(), display_content))
            current_content = self.encrypt_machine.aes_encrypt(current_content).decode('utf-8')
            msg = ms.Message(from_name=self.username.get(), to_name=self.relation_origin[selected], action_type="exchange", content=current_content)
            self.socket_machine.send_request(msg)
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
    client = Client("ICS", master, args)
    client.start()
