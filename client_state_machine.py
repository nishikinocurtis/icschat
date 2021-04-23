USER_OFFLINE = 0
USER_ONLINE = 1


class ClientState:
    def __init__(self):
        self.state_value = USER_OFFLINE

    def set(self, value):
        if value in [USER_OFFLINE, USER_ONLINE]:
            self.state_value = value
        else:
            print("clientState value error.")

    def get(self):
        return self.state_value
