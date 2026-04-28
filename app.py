# Imports
from contextlib import contextmanager
from flask import Flask, render_template, redirect, request
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# My app
app = Flask(__name__)
Scss(app)

# Create databases
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clients.db"
user_db = SQLAlchemy(app)

# Data class ~ row of data
class MyClient(user_db.Model):
    id = user_db.Column(user_db.Integer, primary_key=True)
    username = user_db.Column(user_db.String(100), nullable=False)
    password = user_db.Column(user_db.String(100), nullable=False)
    created = user_db.Column(user_db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"Task {self.id}"


# Routes to webpages

# Login to account
@app.route("/")
def login():
    return render_template("login.html")

# Client Home page
@app.route("/client-home")
def index():
    return render_template("home-client.html")

# Accept a client
@app.route("/accept-client")
def accept_client():
    return render_template("accept-client.html")

# Create a client account
@app.route("/create-client",methods=["POST","GET"])
def create_client():
    # Add a client
    if request.method == "POST":
        current_username = request.form['username_client']
        current_password = request.form['password_client']
        new_username = MyClient(content=current_username)
        try:
            user_db.session.add(new_username)
            user_db.commit()
            return redirect("/create-client")
        except Exception as error:
            print(f"ERROR:{error}")
            return f""

    # See all clients
    else:
        clients = MyClient.query.order_by(MyClient.created).all()
        return render_template("create-client.html")

# Create a professional account
@app.route("/create-professional")
def create_professional():
    return render_template("create-professional.html")

# Find a client
@app.route("/find-client")
def find_client():
    return render_template("find-clients.html")

# Select a client's food diary
@app.route("/food-diary-select-client")
def food_diary_select_client():
    return render_template("food-diary-select-client.html")

# Look through a food diary as a client
@app.route("/food-diary")
def food_diary():
    return render_template("food-diary-client.html")

# Look through a client's food diary as a professional
@app.route("/food-diary-professional")
def food_diary_professional():
    return render_template("food-diary-professional.html")

# Home page for professionals
@app.route("/home-professional")
def home_professional():
    return render_template("home-professional.html")

# Message a client
@app.route("/message-client")
def message_client():
    return render_template("message-clients.html")

# Message a professional
@app.route("/message-professional")
def message_professional():
    return render_template("message-professional.html")

# Raise a new issue as a client
@app.route("/raise-new-issue")
def raise_issue():
    return render_template("raise-new-issue.html")

# Comment on a recipe for clients
@app.route("/recipe-comment")
def comment():
    return render_template("recipe-comment-client.html")

# Comment on a recipe for professional
@app.route("/recipe-comment-professional")
def comment_professional():
    return render_template("recipe-comment-professional.html")

# Rate a recipe as a client
@app.route("/recipe-rating")
def rating():
    return render_template("recipe-rating-client.html")

# Rate a recipe as a professional
@app.route("/recipe-rating-professional")
def rating_professional():
    return render_template("recipe-rating-professional.html")

# Search for a recipe as a client
@app.route("/search-for-recipe")
def search_recipe():
    return render_template("search-for-recipe-client.html")

# Search for a recipe as a professional
@app.route("/search-for-recipe-professional")
def search_recipe_professional():
    return render_template("search-for-recipe-professional.html")

# Send a message as a client
@app.route("/send-message")
def send_message():
    return render_template("send-message-client.html")

# Send a message as a professional
@app.route("/send-message-professional")
def send_message_professional():
    return render_template("send-message-professional.html")

# Speak to a client
@app.route("/speak-to-client")
def speak_client():
    return render_template("speak-to-clients.html")

# Speak to a professional
@app.route("/speak-to-professional")
def speak_professional():
    return render_template("speak-to-professional.html")

# View first page of a recipe as a client
@app.route("/view-recipe")
def view_recipe_first():
    return render_template("view-recipe-first-client.html")

# View first page of a recipe as a professional
@app.route("/view-recipe-professional")
def view_recipe_first_professional():
    return render_template("view-recipe-first-professional.html")

# View middle pages of a recipe as a client
@app.route("/view-recipe-middle")
def view_recipe_middle():
    return render_template("view-recipe-middle-client.html")

# View middle pages of a recipe as a professional
@app.route("/view-recipe-middle")
def view_recipe_middle_professional():
    return render_template("view-recipe-middle-professional.html")

#View last page of a recipe as a client
@app.route("/view-recipe-last")
def view_recipe_last():
    return render_template("view-recipe-last-client.html")

#View last page of a recipe as a professional
@app.route("/view-recipe-last")
def view_recipe_last_professional():
    return render_template("view-recipe-last-professional.html")



if __name__ in "__main__":
    with app.app_context():
        user_db.create_all()

    app.run(debug=True)