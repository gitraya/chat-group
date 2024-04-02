import os
import sqlite3
import pytz
from flask import Flask, flash, redirect, render_template, request, session, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from email_validator import validate_email, EmailNotValidError
from datetime import datetime

from helpers import apology, login_required, validate_password, row_to_object

# Configure application
app = Flask(__name__)
app.config['DATABASE'] = 'chat_group.db'

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure SQLite database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")

        # Ensure input fields are not empty
        if not username:
            return apology("must provide username", 400)
        elif not email:
            return apology("must provide email", 400)
        elif not name:
            return apology("must provide name", 400)
        elif not password:
            return apology("must provide password", 400)
        
        # Ensure email is valid
        elif email:
            try:
                validate_email(email)
            except EmailNotValidError as e:
                return apology(str(e), 400)

        # Ensure confirmation match with the password
        elif not request.form.get("confirm_password") or password != request.form.get("confirm_password"):
            return apology("passwords don't match", 400)

        isvalid, message = validate_password(password)

        if isvalid is False:
            return apology(message, 400)
        
        # Get database connection
        db = get_db()
        cursor = db.cursor()

        # Query database for username
        rows = cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchall()
        
        # Ensure username doesn't exists
        if (len(rows) > 0):
            return apology("username or email already exists", 400)

        password_hash = generate_password_hash(password)
        # Register new user into database
        user_id = cursor.execute("INSERT INTO users (username, email, name, hash) VALUES(?, ?, ?, ?)", (username, email, name, password_hash)).lastrowid
        db.commit()
        
        # Remember which user are already registered
        session["user_id"] = user_id

        # Redirect user to home page
        flash("Registered!")
        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure input fields are not empty
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        
        # Get database connection
        db = get_db()
        cursor = db.cursor()
        cursor.row_factory = sqlite3.Row

        # Query database for username
        rows = cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/profile")
@login_required
def profile():
    """Show user profile"""
    # Get database connection
    db = get_db()
    cursor = db.cursor()
    cursor.row_factory = sqlite3.Row
    
    users = cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()

    # Convert UTC time to Asia/Jakarta timezone
    created_at = datetime.strptime(users[0]["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
    created_at = created_at.astimezone(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
    
    user = row_to_object(users[0])
    user.created_at = created_at
    
    return render_template("profile/index.html", user=user)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit user profile"""
    
    # Get database connection
    db = get_db()
    cursor = db.cursor()
    cursor.row_factory = sqlite3.Row
    
    users = cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
     
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")
        
        # Ensure input fields are not empty
        if not username:
            return apology("must provide username", 403)
        elif not email:
            return apology("must provide email", 403)
        elif not name:
            return apology("must provide name", 403)
        elif not password:
            return apology("must provide password", 403)

        # Ensure email is valid
        elif email:
            try:
                validate_email(email)
            except EmailNotValidError as e:
                return apology(str(e), 400)

        # Ensure confirmation match with the password
        elif not request.form.get("confirm_password") or password != request.form.get("confirm_password"):
            return apology("passwords don't match", 400)

        isvalid, message = validate_password(password)

        if isvalid is False:
            return apology(message, 400)
        
        # Query database for username
        rows = cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchall()

        # Ensure username doesn't exists
        if (len(rows) > 0):
            return apology("username or email already exists", 400)
        
        # Ensure password match
        if not check_password_hash(users[0]["hash"], password):
            return apology("invalid password", 403)
        
        # Update user profile
        profile_url = None
        cursor.execute("UPDATE users SET username = ?, email = ?, name = ?, profile_url = ? WHERE id = ?", (username, email, name, profile_url, session["user_id"]))
        db.commit()
        
        # Redirect user to home page
        flash("Profile updated!")
        return render_template("profile.html")

    return render_template("profile/edit.html", user=users[0])
