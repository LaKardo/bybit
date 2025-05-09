from flask_login import UserMixin
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password
    def check_password(self, password):
        return self.password == password
