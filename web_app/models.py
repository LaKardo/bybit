"""
Models for the web interface.
"""

from flask_login import UserMixin

class User(UserMixin):
    """User class for authentication."""
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def check_password(self, password):
        """Check if password is correct."""
        return self.password == password
