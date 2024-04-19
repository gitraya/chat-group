import os
import sqlite3
import pytz
import cloudinary
import cloudinary.uploader
import cloudinary.api
import json
import uuid
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, g, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from email_validator import validate_email, EmailNotValidError
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room

from helpers import apology, login_required, validate_password, allowed_file, make_initial, format_message_date

load_dotenv()

# Configure application
app = Flask(__name__)
app.config['DATABASE'] = os.getenv("DATABASE")
app.config['TIMEZONE'] = os.getenv("TIMEZONE")

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

socketio = SocketIO(app)

client_rooms = {}

@socketio.on('reset_room')
def reset_room():
    id = session.get("id")
    channel_id = session.get("channel_id")

    # Leave current room
    if id and id in client_rooms:
        leave_room(client_rooms[id])
        print(f"User {id} left room {client_rooms[id]}")

    # Join new room
    if id and channel_id:
        join_room(channel_id)
        client_rooms[id] = channel_id
        print(f"User {id} joined room {channel_id}")


@socketio.on('new_message')
def new_message(message):
    print('received message: ' + str(message))
    # Get database connection
    db = get_db()
    cursor = db.cursor()
    cursor.row_factory = sqlite3.Row
    
    # Query database for user
    users = cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
    
    # Query latest message
    messages = cursor.execute("SELECT created_at FROM messages WHERE channel_id = ? ORDER BY created_at DESC LIMIT 1", (session["channel_id"],)).fetchall()
    
    # Check if the message is the start date
    is_start_date = False
    if len(messages) == 0:
        is_start_date = True
    elif datetime.now().date() != datetime.fromisoformat(messages[0]["created_at"]).date():
        is_start_date = True
    
    # Insert new message into database
    cursor.execute("INSERT INTO messages (channel_id, user_id, message, is_start_date) VALUES(?, ?, ?, ?)", (session["channel_id"], session["user_id"], message, is_start_date))
    db.commit()

    data = { 
        "name": users[0]["name"],
        "profile_url": users[0]["profile_url"],
        "created_at": "today at " + datetime.now().strftime("%I:%M %p"),
        "message": message,
    }
    
    if is_start_date:
        data["start_date_at"] = datetime.now().strftime("%B %d, %Y")

    emit('new_message', json.dumps(data), include_self=True, to=session["channel_id"])

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
    
    # Query database for messages
    messages = cursor.execute("""
        SELECT users.name, users.profile_url, messages.message, messages.created_at, messages.is_start_date FROM messages
        JOIN users ON messages.user_id = users.id
        WHERE channel_id = ?
        ORDER BY messages.created_at ASC
    """, (session["channel_id"],)).fetchall()
    
    channels = [dict(row) for row in rows]

    for channel in channels:
        channel["initial"] = make_initial(channel.get("name"))
        
    messages = [dict(message) for message in messages]
    
    for message in messages:
        if message["is_start_date"]:
            message["start_date_at"] = datetime.fromisoformat(message["created_at"]).strftime("%B %d, %Y")
            
        message["created_at"] = format_message_date(message["created_at"])
        
    active_channel = None
    
    if "channel_id" in session:
        active_channel = cursor.execute("SELECT * FROM channels WHERE id = ? LIMIT 1", (session["channel_id"],)).fetchall()
        active_channel = dict(active_channel[0])
    
    return render_template("index.html", channels=channels, user=users[0], channel=active_channel, messages=messages)


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
        return redirect("/channel/1")

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
        session["id"] = uuid.uuid4()

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

    # Convert UTC time to environment timezone
    created_at = datetime.strptime(users[0]["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
    created_at = created_at.astimezone(pytz.timezone(app.config['TIMEZONE'])).strftime("%Y-%m-%d %H:%M:%S")
    
    user = dict(users[0])
    user["created_at"] = created_at
    
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
        
        user = dict(users[0])
        user["username"] = username
        user["email"] = email
        user["name"] = name
        user["profile_url"] = profile_url
        
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
def create_channel():
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


@app.route("/channel/<int:channel_id>")
@login_required
def channel_detail(channel_id):
    """Show channel page"""
    
    # Get database connection
    db = get_db()
    cursor = db.cursor()
    cursor.row_factory = sqlite3.Row
    
    # Query database for channel
    channels = cursor.execute("SELECT * FROM channels WHERE id = ? LIMIT 1", (channel_id,)).fetchall()
    
    # Query database for user
    users = cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
    
    # Check and insert new member into channel if not exists
    members = cursor.execute("SELECT * FROM members WHERE channel_id = ? AND user_id = ?", (channel_id, session["user_id"])).fetchall()
    
    is_new_member = False
    if len(members) == 0:
        # Register new member into channel
        is_new_member = True
        cursor.execute("INSERT INTO members (channel_id, user_id) VALUES(?, ?)", (channel_id, session["user_id"]))
        db.commit()
        
    members = cursor.execute("""
        SELECT users.name, users.profile_url FROM members
        JOIN users ON members.user_id = users.id
        WHERE channel_id = ?
        ORDER BY members.created_at DESC
    """, (channel_id,)).fetchall()
    
    # Send new member data to connected clients
    if is_new_member:
        emit('new_member', json.dumps(dict(members[0])), include_self=True, to=channel_id, namespace='/')
    
    # Query database for messages
    messages = cursor.execute("""
        SELECT users.name, users.profile_url, messages.message, messages.created_at, messages.is_start_date FROM messages
        JOIN users ON messages.user_id = users.id
        WHERE channel_id = ?
        ORDER BY messages.created_at ASC
    """, (channel_id,)).fetchall()
    
    channel = dict(channels[0])
    channel["members"] = [dict(member) for member in members]
    user = dict(users[0])
    
    messages = [dict(message) for message in messages]
    
    for message in messages:
        if message["is_start_date"]:
            message["start_date_at"] = datetime.fromisoformat(message["created_at"]).strftime("%B %d, %Y")
            
        message["created_at"] = format_message_date(message["created_at"])

    # Remember which channel has been selected  
    session["channel_id"] = channel_id
    
    return render_template("channel.html", channel=channel, user=user, messages=messages)


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
    rows = cursor.execute("SELECT * FROM channels WHERE name LIKE ? ORDER BY created_at DESC", ('%' + name + '%',)).fetchall()
    
    channels = [dict(row) for row in rows]
    
    for channel in channels:
        channel["initial"] = make_initial(channel.get("name"))
    
    return render_template("components/channel.html", channels=channels)


if __name__ == "__main__":
    socketio.run(app)
