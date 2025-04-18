"""
Authentication routes for the web interface.
"""

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from web_app.auth import auth_bp
from web_app.auth.forms import LoginForm
from web_app.models import User
from web_app import login_manager

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    from config import WEB_USERNAME, WEB_PASSWORD
    
    if int(user_id) == 1:
        return User(1, WEB_USERNAME, WEB_PASSWORD)
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        from config import WEB_USERNAME, WEB_PASSWORD
        
        if form.username.data == WEB_USERNAME and form.password.data == WEB_PASSWORD:
            user = User(1, WEB_USERNAME, WEB_PASSWORD)
            login_user(user, remember=form.remember_me.data)
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            
            return redirect(next_page)
        
        flash('Invalid username or password', 'danger')
        return redirect(url_for('auth.login'))
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
def logout():
    """Handle logout."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))
