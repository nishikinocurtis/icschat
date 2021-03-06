import json
from pathlib import Path


class Indexer:
    def __init__(self):
        self.name = ""
        self.messages = dict()
        self.messages["system_total"] = ["0"]
        self.total_message = 0

    def add_new(self, from_name, content):
        if from_name in self.messages.keys():
            self.messages[from_name].append(content)
        else:
            self.messages[from_name] = [content]
        self.total_message += 1

    def load_message(self, username):
        self.name = username
        try:
            file_pointer = open("./" + self.name + "/messages.json")
            self.messages = json.load(file_pointer)
            file_pointer.close()
            self.total_message = int(self.messages["system_total"][0])
            print("message loaded.")
        except FileNotFoundError:
            pass

    def save_message(self):
        Path("./" + self.name).mkdir(exist_ok=True)
        file_pointer = open("./" + self.name + "/messages.json", 'w+')
        self.messages["system_total"] = [str(self.total_message)]
        json.dump(self.messages, file_pointer)
        file_pointer.close()

    def get_message_list(self, name):
        if name in self.messages.keys():
            return self.messages[name]
        else:
            return []
