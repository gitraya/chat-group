import os
import sqlite3
import pytz
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, g, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from email_validator import validate_email, EmailNotValidError
from datetime import datetime

from helpers import apology, login_required, validate_password, row_to_object, allowed_file, make_initial

load_dotenv()

# Configure application
app = Flask(__name__)
app.config['DATABASE'] = os.getenv("DATABASE")

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

cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

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
    """Show home page"""
    
    # Get database connection
    db = get_db()
    cursor = db.cursor()
    cursor.row_factory = sqlite3.Row
    
    # Query database for channels
    rows = cursor.execute("SELECT * FROM channels ORDER BY created_at DESC").fetchall()
    
    # Query database for user
    users = cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
    
    channels = [row_to_object(row) for row in rows]
    
    for channel in channels:
        channel.initial = make_initial(channel.name)
    
    return render_template("index.html", channels=channels, user=users[0])


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


@app.route("/profile/edit", methods=["GET", "PUT"])
@login_required
def edit_profile():
    """Edit user profile"""
    
    # Get database connection
    db = get_db()
    cursor = db.cursor()
    cursor.row_factory = sqlite3.Row
    
    users = cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
     
    if request.method == "PUT":
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
        
        # Query database for username
        rows = cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchall()

        # Ensure username doesn't exists
        if len(rows) > 0 and rows[0]["id"] != session["user_id"]:
            return apology("username or email already exists", 400)
        
        # Ensure if user uploaded a profile picture
        profile_url = users[0]["profile_url"]
        if "profile_url" in request.files:
            profile_picture = request.files["profile_url"]
            
            if profile_picture.filename == "":
                return apology("no file selected", 400)
            
            if not allowed_file(profile_picture.filename):
                return apology("file type not allowed", 400)
            
            # Upload profile picture to Cloudinary
            profile_url = cloudinary.uploader.upload(profile_picture,
                folder="chat-group",
                public_id=session["user_id"],
                overwrite=True,
            )["url"]
        
        # Ensure password match
        if not check_password_hash(users[0]["hash"], password):
            return apology("invalid password", 403)
        
        # Update user profile
        cursor.execute("UPDATE users SET username = ?, email = ?, name = ?, profile_url = ? WHERE id = ?", (username, email, name, profile_url, session["user_id"]))
        db.commit()
        
        user = row_to_object(users[0])
        user.username = username
        user.email = email
        user.name = name
        user.profile_url = profile_url
        
        # Redirect user to home page
        flash("Profile updated!")
        return render_template("profile/index.html", user=user)

    return render_template("profile/edit.html", user=users[0])


@app.route("/password", methods=["GET", "PUT"])
@login_required
def password():
    """Change User Password"""

    if request.method == "PUT":
        old = request.form.get("old")
        password = request.form.get("password")
        confirmation = request.form.get("confirm_password")

        # Ensure old was submitted
        if not old:
            return apology("must provide old password", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide new password", 400)

        # Ensure confirmation match with the password
        elif not confirmation or password != confirmation:
            return apology("new passwords don't match", 400)
        
        # Get database connection
        db = get_db()
        cursor = db.cursor()
        cursor.row_factory = sqlite3.Row
        
        users = cursor.execute("SELECT hash FROM users WHERE id = ?", (session["user_id"],)).fetchall()

        if not check_password_hash(users[0]["hash"], old):
            return apology("old password didn't match", 403)

        # Validate new password
        isvalid, message = validate_password(password)

        if isvalid is False:
            return apology(message, 400)

        password_hash = generate_password_hash(password)
        # Update password hash
        cursor.execute("UPDATE users SET hash = ? WHERE id = ?", (password_hash, session["user_id"]))
        db.commit()

        # Redirect user to home page
        flash("Password Changed!")
        return redirect("/")

    return render_template("password.html")


@app.route("/channel", methods=["POST"])
@login_required
def channel():
    """Create new channel"""

    name = request.form.get("name")
    description = request.form.get("description")
        
    # Ensure input fields are not empty
    if not name:
        return apology("must provide channel name", 400)
    elif not description:
        return apology("must provide channel description", 400)
        
    # Get database connection
    db = get_db()
    cursor = db.cursor()
        
    # Register new channel into database
    cursor.execute("INSERT INTO channels (name, description, admin_id) VALUES(?, ?, ?)", (name, description, session["user_id"]))
    
    # Insert new member into channel
    channel_id = cursor.lastrowid
    cursor.execute("INSERT INTO members (channel_id, user_id) VALUES(?, ?)", (channel_id, session["user_id"]))
    
    db.commit()
    
    # Redirect user to home page
    flash("Channel Created!")
    return redirect("/channel/" + str(channel_id))


@app.route("/channel/search", methods=["GET"])
@login_required
def search_channel():
    """Search channel by name"""
    
    name = request.args.get("name")
    
    # Get database connection
    db = get_db()
    cursor = db.cursor()
    cursor.row_factory = sqlite3.Row
    
    # Query database for channels
    channels = cursor.execute("SELECT * FROM channels WHERE name LIKE ?", ('%' + name + '%',)).fetchall()
    
    return jsonify([row_to_object(channel) for channel in channels])


@app.route("/member", methods=["POST"])
@login_required
def member():
    """Add new member to channel"""

    channel_id = request.form.get("channel_id")
        
    # Ensure input fields are not empty
    if not channel_id:
        return apology("must provide channel id", 400)
        
    # Get database connection
    db = get_db()
    cursor = db.cursor()
    
    # Register new member into channel
    cursor.execute("INSERT INTO members (channel_id, user_id) VALUES(?, ?)", (channel_id, session["user_id"]))
    db.commit()
    
    # Redirect user to home page
    flash("Member Added!")
    return redirect("/channel/" + str(channel_id))
