"""
Simple test script for the web interface.
This script creates a minimal Flask application to test the login functionality.
"""

from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'test-secret-key'
app.config['WTF_CSRF_ENABLED'] = True

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Add template context processor
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

class LoginForm(FlaskForm):
    """Login form for web interface."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class User(UserMixin):
    """User class for authentication."""
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def check_password(self, password):
        """Check if password is correct."""
        return self.password == password

# Create user
users = {
    'admin': User(1, 'admin', 'admin')
}

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    for user in users.values():
        if user.id == int(user_id):
            return user
    return None

@app.route('/')
@login_required
def index():
    """Render dashboard page."""
    return render_template('index.html', bot=None, config={'WEB_USERNAME': 'admin'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = users.get(form.username.data)
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    """Handle logout."""
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("Starting simple web interface test...")
    app.run(host='0.0.0.0', port=5000, debug=True)
