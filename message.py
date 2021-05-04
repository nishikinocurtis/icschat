class Message:
    action_list = ["login",  # client login
                   "register",  # client register
                   "exchange",  # protocol: texts, client send message or recv message
                   "time",  # client request time
                   "poem",  # client request poem
                   "add_friend",  # client request new friend
                   "add_group",  # client request new group
                   "logout",  # client request logout
                   "notification"  # server send notification
                   "change",  # server recv friend request
                   "friend_respond",  # client reply to request, server feedback
                   "group_respond",  # server feedback
                   "negotiate",  # server send negotiate information to group members
                   "key",  # previous offline members send their keys to me/server
                   "communication",
                   "register_feedback",
                   "login_feedback",
                   "disconnect",
                   "empty",
                   "error",
                   "register_key",]  # register generating key

    def __init__(self, from_name="", to_name="", action_type="", content=""):
        self.__from_name = ""
        self.from_name = from_name
        self.__to_name = ""
        self.to_name = to_name
        self.__action_type = ""
        self.action_type = action_type
        self.__content = ""
        self.content = content

    @property
    def from_name(self):
        return self.__from_name

    @property
    def to_name(self):
        return self.__to_name

    @property
    def action_type(self):
        return self.__action_type

    @property
    def content(self):
        return self.__content

    @from_name.setter
    def from_name(self, value):
        if isinstance(value, str):
            self.__from_name = value
        else:
            print("from name TypeErr")

    @action_type.setter
    def action_type(self, value):
        if value in Message.action_list:
            self.__action_type = value
        else:
            print("invalid action type")

    @to_name.setter
    def to_name(self, value):
        if isinstance(value, str):
            self.__to_name = value
        else:
            print("to name TypeErr")

    @content.setter
    def content(self, value):
        if isinstance(value, str):
            self.__content = value
        else:
            print("content TypeErr")
