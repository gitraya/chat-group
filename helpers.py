import os
import pytz
from datetime import datetime, timedelta
from flask import redirect, render_template, session
from functools import wraps

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def validate_password(password):
    # Check if password meets minimum length requirement
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    # Check if password contains at least one letter, one number, and one symbol
    has_letter = any(char.isalpha() for char in password)
    has_number = any(char.isdigit() for char in password)
    has_symbol = any(not char.isalnum() for char in password)

    if not (has_letter and has_number and has_symbol):
        return False, "Password must contain at least one letter, one number, and one symbol"

    return True, "Password is valid"


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def make_initial(name):
    # Split the name into words
    words = name.split()
    # If the name contains more than one word, take the first letter of the first two words
    if len(words) >= 2:
        return words[0][0].upper() + words[1][0].upper()
    else:
        return words[0][0].upper() + words[0][1].upper()


def format_message_date(iso_date):
    dt_object = datetime.fromisoformat(iso_date)
    dt_object = dt_object.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(os.getenv("TIMEZONE")))
    
    # Check if the date is today
    if dt_object.date() == datetime.now().date():
        return "today at " + dt_object.strftime("%I:%M %p")
    
    # Check if the date is yesterday
    elif dt_object.date() == datetime.now().date() - timedelta(days=1):
        return "yesterday at " + dt_object.strftime("%I:%M %p")
    
    # Return the date in the format /month/day/year time
    else:
        return dt_object.strftime("%m/%d/%Y %I:%M %p")
