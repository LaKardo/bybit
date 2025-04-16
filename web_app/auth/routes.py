from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from web_app.auth import auth_bp
from web_app.auth.forms import LoginForm
from web_app.models import User
from web_app import login_manager
@login_manager.user_loader
def load_user(user_id):
    from config import WEB_USERNAME, WEB_PASSWORD
    if int(user_id) == 1:
        return User(1, WEB_USERNAME, WEB_PASSWORD)
    return None
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()

    # Handle POST request directly if CSRF validation fails
    if request.method == 'POST':
        from config import WEB_USERNAME, WEB_PASSWORD
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = 'remember_me' in request.form

        if username == WEB_USERNAME and password == WEB_PASSWORD:
            user = User(1, WEB_USERNAME, WEB_PASSWORD)
            login_user(user, remember=remember_me)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('login.html', form=form)
@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))
