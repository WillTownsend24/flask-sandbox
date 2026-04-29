"""
app.py - Main Flask application entry point.

Handles all routing, authentication, and business logic for the
NutriTrack health and nutrition web application.
"""

from flask import Flask, render_template, redirect, request, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests
import json

# ---------------------------------------------------------------------------
# App & DB setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = "nutritrack_secret_key_2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///nutritrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class User(db.Model):
    """
    Represents both subscribers and health professionals.
    The `role` field distinguishes between the two ('subscriber' or 'professional').
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="subscriber")  # 'subscriber' or 'professional'
    full_name = db.Column(db.String(150), nullable=False)
    # Professional-specific fields
    specialisation = db.Column(db.String(200), nullable=True)  # e.g. "Weight Loss, Diabetes"
    bio = db.Column(db.Text, nullable=True)
    # Subscriber health stats
    weight_kg = db.Column(db.Float, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    blood_pressure = db.Column(db.String(20), nullable=True)  # e.g. "120/80"
    goal = db.Column(db.String(50), nullable=True)  # 'lose_weight', 'gain_weight', 'maintain'
    # Relationship to professional
    professional_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    food_entries = db.relationship("FoodEntry", backref="user", lazy=True, foreign_keys="FoodEntry.user_id")
    notifications = db.relationship("Notification", backref="recipient", lazy=True, foreign_keys="Notification.user_id")
    saved_recipes = db.relationship("SavedRecipe", backref="user", lazy=True)

    def set_password(self, password):
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class FoodEntry(db.Model):
    """
    A single food item logged by a subscriber in their food diary.
    Stores nutrition data fetched from the Open Food Facts API.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    food_name = db.Column(db.String(200), nullable=False)
    quantity_g = db.Column(db.Float, nullable=False, default=100.0)
    calories = db.Column(db.Float, nullable=True)
    protein_g = db.Column(db.Float, nullable=True)
    carbs_g = db.Column(db.Float, nullable=True)
    fat_g = db.Column(db.Float, nullable=True)
    fibre_g = db.Column(db.Float, nullable=True)
    sugar_g = db.Column(db.Float, nullable=True)
    meal_type = db.Column(db.String(20), nullable=False, default="lunch")  # breakfast/lunch/dinner/snack
    logged_date = db.Column(db.Date, nullable=False, default=date.today)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    professional_comment = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<FoodEntry {self.food_name} by user {self.user_id}>"


class NutritionalGuideline(db.Model):
    """
    Daily nutritional targets set by a health professional for a specific subscriber.
    """
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    daily_calories = db.Column(db.Float, nullable=True)
    daily_protein_g = db.Column(db.Float, nullable=True)
    daily_carbs_g = db.Column(db.Float, nullable=True)
    daily_fat_g = db.Column(db.Float, nullable=True)
    daily_fibre_g = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Guideline for subscriber {self.subscriber_id}>"


class Recipe(db.Model):
    """
    A recipe stored in the system, either seeded or user-submitted.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ingredients = db.Column(db.Text, nullable=False)  # JSON string
    instructions = db.Column(db.Text, nullable=False)
    cook_time_mins = db.Column(db.Integer, nullable=True)
    prep_time_mins = db.Column(db.Integer, nullable=True)
    servings = db.Column(db.Integer, nullable=True, default=2)
    cost_estimate = db.Column(db.String(20), nullable=True)  # e.g. "£3–£5"
    calories_per_serving = db.Column(db.Float, nullable=True)
    protein_per_serving = db.Column(db.Float, nullable=True)
    carbs_per_serving = db.Column(db.Float, nullable=True)
    fat_per_serving = db.Column(db.Float, nullable=True)
    tags = db.Column(db.String(300), nullable=True)  # comma-separated e.g. "chicken,high-protein"
    image_url = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    comments = db.relationship("RecipeComment", backref="recipe", lazy=True)
    saves = db.relationship("SavedRecipe", backref="recipe", lazy=True)

    def average_rating(self):
        """Calculate and return the average star rating for this recipe."""
        if not self.comments:
            return None
        rated = [c.rating for c in self.comments if c.rating is not None]
        return round(sum(rated) / len(rated), 1) if rated else None

    def __repr__(self):
        return f"<Recipe {self.title}>"


class RecipeComment(db.Model):
    """
    A comment (and optional rating) left by a user on a recipe.
    """
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # 1–5
    created = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="recipe_comments")

    def __repr__(self):
        return f"<RecipeComment by user {self.user_id} on recipe {self.recipe_id}>"


class SavedRecipe(db.Model):
    """
    Tracks which recipes a subscriber has saved (tried / favourite / want to try).
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="want_to_try")  # tried / favourite / want_to_try
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SavedRecipe user={self.user_id} recipe={self.recipe_id} status={self.status}>"


class Notification(db.Model):
    """
    In-app notifications sent to users (e.g. professional comments on a food diary day).
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Notification for user {self.user_id}>"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator: redirect to login if the user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def professional_required(f):
    """Decorator: only allow health professionals to access the route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "professional":
            flash("Access restricted to health professionals.", "danger")
            return redirect(url_for("subscriber_home"))
        return f(*args, **kwargs)
    return decorated


def subscriber_required(f):
    """Decorator: only allow subscribers to access the route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "subscriber":
            flash("Access restricted to subscribers.", "danger")
            return redirect(url_for("professional_home"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """Return the currently logged-in User object, or None."""
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])


def unread_notification_count():
    """Return the number of unread notifications for the current user."""
    user = get_current_user()
    if not user:
        return 0
    return Notification.query.filter_by(user_id=user.id, is_read=False).count()


# Make notification count available in all templates
@app.context_processor
def inject_globals():
    return {
        "unread_count": unread_notification_count(),
        "current_user": get_current_user()
    }


# ---------------------------------------------------------------------------
# Nutrition API helper (Open Food Facts)
# ---------------------------------------------------------------------------

def search_food_api(query):
    """
    Search Open Food Facts for a food item.
    Returns a list of result dicts with nutrition per 100g.
    Falls back to an empty list on any error.
    """
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 8,
            "fields": "product_name,nutriments,brands"
        }
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for product in data.get("products", []):
            name = product.get("product_name", "").strip()
            if not name:
                continue
            n = product.get("nutriments", {})
            results.append({
                "name": name,
                "brand": product.get("brands", ""),
                "calories": round(n.get("energy-kcal_100g", 0) or 0, 1),
                "protein": round(n.get("proteins_100g", 0) or 0, 1),
                "carbs": round(n.get("carbohydrates_100g", 0) or 0, 1),
                "fat": round(n.get("fat_100g", 0) or 0, 1),
                "fibre": round(n.get("fiber_100g", 0) or 0, 1),
                "sugar": round(n.get("sugars_100g", 0) or 0, 1),
            })
        return results
    except Exception as e:
        print(f"[API ERROR] search_food_api: {e}")
        return []


# ---------------------------------------------------------------------------
# Nutrition calculation helper
# ---------------------------------------------------------------------------

def get_daily_totals(user_id, target_date):
    """
    Return summed nutrition totals for a user on a given date.
    Returns a dict of nutrient -> total value.
    """
    entries = FoodEntry.query.filter_by(user_id=user_id, logged_date=target_date).all()
    totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fibre": 0, "sugar": 0}
    for e in entries:
        factor = e.quantity_g / 100.0
        totals["calories"] += (e.calories or 0) * factor
        totals["protein"] += (e.protein_g or 0) * factor
        totals["carbs"] += (e.carbs_g or 0) * factor
        totals["fat"] += (e.fat_g or 0) * factor
        totals["fibre"] += (e.fibre_g or 0) * factor
        totals["sugar"] += (e.sugar_g or 0) * factor
    return {k: round(v, 1) for k, v in totals.items()}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Redirect root to login page."""
    if "user_id" in session:
        if session.get("role") == "professional":
            return redirect(url_for("professional_home"))
        return redirect(url_for("subscriber_home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login for both subscribers and professionals."""
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Input validation
        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["role"] = user.role
            session["username"] = user.username
            flash(f"Welcome back, {user.full_name}!", "success")
            if user.role == "professional":
                return redirect(url_for("professional_home"))
            return redirect(url_for("subscriber_home"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/create-subscriber", methods=["GET", "POST"])
def create_subscriber():
    """Register a new subscriber account."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        goal = request.form.get("goal", "maintain")

        # Validation
        if not all([username, email, password, full_name]):
            flash("All fields are required.", "danger")
            return render_template("create-subscriber.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("create-subscriber.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("create-subscriber.html")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("create-subscriber.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("create-subscriber.html")

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role="subscriber",
            goal=goal
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    professionals = User.query.filter_by(role="professional").all()
    return render_template("create-subscriber.html", professionals=professionals)


@app.route("/create-professional", methods=["GET", "POST"])
def create_professional():
    """Register a new health professional account."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        specialisation = request.form.get("specialisation", "").strip()
        bio = request.form.get("bio", "").strip()

        if not all([username, email, password, full_name]):
            flash("All fields are required.", "danger")
            return render_template("create-professional.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("create-professional.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("create-professional.html")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("create-professional.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("create-professional.html")

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role="professional",
            specialisation=specialisation,
            bio=bio
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Professional account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("create-professional.html")


# ---------------------------------------------------------------------------
# Subscriber routes
# ---------------------------------------------------------------------------

@app.route("/home")
@subscriber_required
def subscriber_home():
    """Subscriber dashboard showing today's diary summary and nutrition progress."""
    user = get_current_user()
    today = date.today()
    totals = get_daily_totals(user.id, today)
    today_entries = FoodEntry.query.filter_by(user_id=user.id, logged_date=today).order_by(FoodEntry.logged_at).all()

    guideline = NutritionalGuideline.query.filter_by(subscriber_id=user.id).order_by(
        NutritionalGuideline.created.desc()).first()

    # Build 7-day calorie history for the chart
    chart_labels = []
    chart_calories = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime("%a %d"))
        day_total = get_daily_totals(user.id, d)
        chart_calories.append(day_total["calories"])

    professional = User.query.get(user.professional_id) if user.professional_id else None

    return render_template(
        "home-client.html",
        user=user,
        today=today,
        totals=totals,
        today_entries=today_entries,
        guideline=guideline,
        chart_labels=json.dumps(chart_labels),
        chart_calories=json.dumps(chart_calories),
        professional=professional
    )


@app.route("/food-diary", methods=["GET"])
@subscriber_required
def food_diary():
    """Show the subscriber's food diary for a selected date."""
    user = get_current_user()
    date_str = request.args.get("date", date.today().isoformat())

    try:
        selected_date = date.fromisoformat(date_str)
    except ValueError:
        selected_date = date.today()

    entries = FoodEntry.query.filter_by(user_id=user.id, logged_date=selected_date).order_by(
        FoodEntry.meal_type, FoodEntry.logged_at).all()

    totals = get_daily_totals(user.id, selected_date)
    guideline = NutritionalGuideline.query.filter_by(subscriber_id=user.id).order_by(
        NutritionalGuideline.created.desc()).first()

    # Group entries by meal type
    meals = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
    for e in entries:
        meals.get(e.meal_type, meals["snack"]).append(e)

    return render_template(
        "food-diary-client.html",
        user=user,
        selected_date=selected_date,
        meals=meals,
        totals=totals,
        guideline=guideline
    )


@app.route("/log-food", methods=["GET", "POST"])
@subscriber_required
def log_food():
    """Search for a food item and log it to today's diary."""
    user = get_current_user()
    results = []
    query = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "search":
            query = request.form.get("query", "").strip()
            if not query:
                flash("Please enter a food to search for.", "warning")
            else:
                results = search_food_api(query)
                if not results:
                    flash("No results found. Try a different search term.", "info")

        elif action == "log":
            # Log the selected food item
            food_name = request.form.get("food_name", "").strip()
            quantity = request.form.get("quantity", "100")
            meal_type = request.form.get("meal_type", "lunch")
            log_date_str = request.form.get("log_date", date.today().isoformat())

            # Validate inputs
            if not food_name:
                flash("Food name is required.", "danger")
                return redirect(url_for("log_food"))
            try:
                quantity = float(quantity)
                if quantity <= 0:
                    raise ValueError
            except ValueError:
                flash("Please enter a valid quantity in grams.", "danger")
                return redirect(url_for("log_food"))
            try:
                log_date = date.fromisoformat(log_date_str)
            except ValueError:
                log_date = date.today()

            entry = FoodEntry(
                user_id=user.id,
                food_name=food_name,
                quantity_g=quantity,
                calories=float(request.form.get("calories", 0) or 0),
                protein_g=float(request.form.get("protein", 0) or 0),
                carbs_g=float(request.form.get("carbs", 0) or 0),
                fat_g=float(request.form.get("fat", 0) or 0),
                fibre_g=float(request.form.get("fibre", 0) or 0),
                sugar_g=float(request.form.get("sugar", 0) or 0),
                meal_type=meal_type,
                logged_date=log_date
            )
            db.session.add(entry)
            db.session.commit()
            flash(f"{food_name} logged successfully!", "success")
            return redirect(url_for("food_diary", date=log_date_str))

    return render_template("log-food.html", user=user, results=results, query=query)


@app.route("/delete-entry/<int:entry_id>", methods=["POST"])
@subscriber_required
def delete_entry(entry_id):
    """Delete a food diary entry belonging to the current subscriber."""
    user = get_current_user()
    entry = FoodEntry.query.get_or_404(entry_id)

    if entry.user_id != user.id:
        flash("You cannot delete someone else's entry.", "danger")
        return redirect(url_for("food_diary"))

    entry_date = entry.logged_date.isoformat()
    db.session.delete(entry)
    db.session.commit()
    flash("Entry deleted.", "info")
    return redirect(url_for("food_diary", date=entry_date))


@app.route("/update-stats", methods=["GET", "POST"])
@subscriber_required
def update_stats():
    """Allow a subscriber to update their health stats (weight, height, BP)."""
    user = get_current_user()
    if request.method == "POST":
        try:
            weight = request.form.get("weight_kg", "").strip()
            height = request.form.get("height_cm", "").strip()
            bp = request.form.get("blood_pressure", "").strip()

            if weight:
                user.weight_kg = float(weight)
            if height:
                user.height_cm = float(height)
            if bp:
                user.blood_pressure = bp

            db.session.commit()
            flash("Health stats updated.", "success")
        except ValueError:
            flash("Please enter valid numeric values.", "danger")
        return redirect(url_for("subscriber_home"))
    return render_template("update-stats.html", user=user)


@app.route("/choose-professional", methods=["GET", "POST"])
@subscriber_required
def choose_professional():
    """Allow a subscriber to select or change their health professional."""
    user = get_current_user()
    if request.method == "POST":
        prof_id = request.form.get("professional_id")
        if not prof_id:
            flash("Please select a professional.", "warning")
        else:
            professional = User.query.get(int(prof_id))
            if not professional or professional.role != "professional":
                flash("Invalid selection.", "danger")
            else:
                user.professional_id = professional.id
                db.session.commit()
                flash(f"You are now assigned to {professional.full_name}.", "success")
                return redirect(url_for("subscriber_home"))

    professionals = User.query.filter_by(role="professional").all()
    return render_template("choose-professional.html", user=user, professionals=professionals)


@app.route("/notifications")
@login_required
def notifications():
    """Show all notifications for the current user and mark them as read."""
    user = get_current_user()
    all_notifications = Notification.query.filter_by(user_id=user.id).order_by(
        Notification.created.desc()).all()

    # Mark all as read
    for n in all_notifications:
        n.is_read = True
    db.session.commit()

    return render_template("notifications.html", user=user, notifications=all_notifications)


# ---------------------------------------------------------------------------
# Professional routes
# ---------------------------------------------------------------------------

@app.route("/home-professional")
@professional_required
def professional_home():
    """Professional dashboard showing their assigned subscribers."""
    user = get_current_user()
    subscribers = User.query.filter_by(professional_id=user.id, role="subscriber").all()

    # For each subscriber, get today's nutrition summary
    today = date.today()
    subscriber_data = []
    for s in subscribers:
        totals = get_daily_totals(s.id, today)
        guideline = NutritionalGuideline.query.filter_by(subscriber_id=s.id).order_by(
            NutritionalGuideline.created.desc()).first()
        subscriber_data.append({"user": s, "totals": totals, "guideline": guideline})

    return render_template("home-professional.html", user=user, subscriber_data=subscriber_data)


@app.route("/find-clients")
@professional_required
def find_clients():
    """Show all subscribers not yet assigned to any professional."""
    user = get_current_user()
    unassigned = User.query.filter_by(role="subscriber", professional_id=None).all()
    my_subscribers = User.query.filter_by(role="subscriber", professional_id=user.id).all()
    return render_template("find-clients.html", user=user, unassigned=unassigned, my_subscribers=my_subscribers)


@app.route("/accept-client/<int:subscriber_id>", methods=["POST"])
@professional_required
def accept_client(subscriber_id):
    """Assign a subscriber to the current professional."""
    user = get_current_user()
    subscriber = User.query.get_or_404(subscriber_id)

    if subscriber.role != "subscriber":
        flash("That user is not a subscriber.", "danger")
        return redirect(url_for("find_clients"))

    subscriber.professional_id = user.id
    # Send a notification to the subscriber
    notif = Notification(
        user_id=subscriber.id,
        message=f"You have been accepted by {user.full_name} as your health professional."
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"{subscriber.full_name} is now your client.", "success")
    return redirect(url_for("find_clients"))


@app.route("/view-client/<int:subscriber_id>")
@professional_required
def view_client(subscriber_id):
    """View a subscriber's food diary and health data as a professional."""
    user = get_current_user()
    subscriber = User.query.get_or_404(subscriber_id)

    if subscriber.professional_id != user.id:
        flash("This subscriber is not your client.", "danger")
        return redirect(url_for("professional_home"))

    date_str = request.args.get("date", date.today().isoformat())
    try:
        selected_date = date.fromisoformat(date_str)
    except ValueError:
        selected_date = date.today()

    entries = FoodEntry.query.filter_by(user_id=subscriber.id, logged_date=selected_date).order_by(
        FoodEntry.meal_type).all()
    totals = get_daily_totals(subscriber.id, selected_date)
    guideline = NutritionalGuideline.query.filter_by(subscriber_id=subscriber.id).order_by(
        NutritionalGuideline.created.desc()).first()

    # 7-day chart data for the subscriber
    today = date.today()
    chart_labels = []
    chart_calories = []
    calorie_target = guideline.daily_calories if guideline else None
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime("%a %d"))
        day_total = get_daily_totals(subscriber.id, d)
        chart_calories.append(day_total["calories"])

    meals = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
    for e in entries:
        meals.get(e.meal_type, meals["snack"]).append(e)

    return render_template(
        "view-client.html",
        user=user,
        subscriber=subscriber,
        selected_date=selected_date,
        meals=meals,
        totals=totals,
        guideline=guideline,
        chart_labels=json.dumps(chart_labels),
        chart_calories=json.dumps(chart_calories),
        calorie_target=calorie_target
    )


@app.route("/set-guidelines/<int:subscriber_id>", methods=["GET", "POST"])
@professional_required
def set_guidelines(subscriber_id):
    """Set or update nutritional guidelines for a subscriber."""
    user = get_current_user()
    subscriber = User.query.get_or_404(subscriber_id)

    if subscriber.professional_id != user.id:
        flash("This subscriber is not your client.", "danger")
        return redirect(url_for("professional_home"))

    existing = NutritionalGuideline.query.filter_by(subscriber_id=subscriber.id).order_by(
        NutritionalGuideline.created.desc()).first()

    if request.method == "POST":
        try:
            guideline = NutritionalGuideline(
                subscriber_id=subscriber.id,
                professional_id=user.id,
                daily_calories=float(request.form.get("daily_calories") or 0) or None,
                daily_protein_g=float(request.form.get("daily_protein_g") or 0) or None,
                daily_carbs_g=float(request.form.get("daily_carbs_g") or 0) or None,
                daily_fat_g=float(request.form.get("daily_fat_g") or 0) or None,
                daily_fibre_g=float(request.form.get("daily_fibre_g") or 0) or None,
                notes=request.form.get("notes", "").strip()
            )
            db.session.add(guideline)
            # Notify subscriber
            notif = Notification(
                user_id=subscriber.id,
                message=f"{user.full_name} has updated your nutritional guidelines."
            )
            db.session.add(notif)
            db.session.commit()
            flash(f"Guidelines updated for {subscriber.full_name}.", "success")
            return redirect(url_for("view_client", subscriber_id=subscriber.id))
        except ValueError:
            flash("Please enter valid numeric values for guidelines.", "danger")

    return render_template("set-guidelines.html", user=user, subscriber=subscriber, existing=existing)


@app.route("/comment-on-day/<int:subscriber_id>", methods=["POST"])
@professional_required
def comment_on_day(subscriber_id):
    """Professional comments on a subscriber's food diary day."""
    user = get_current_user()
    subscriber = User.query.get_or_404(subscriber_id)

    if subscriber.professional_id != user.id:
        flash("This subscriber is not your client.", "danger")
        return redirect(url_for("professional_home"))

    comment_text = request.form.get("comment", "").strip()
    comment_date_str = request.form.get("comment_date", date.today().isoformat())

    if not comment_text:
        flash("Comment cannot be empty.", "warning")
        return redirect(url_for("view_client", subscriber_id=subscriber_id, date=comment_date_str))

    # Attach comment to each entry on that day
    try:
        comment_date = date.fromisoformat(comment_date_str)
    except ValueError:
        comment_date = date.today()

    entries = FoodEntry.query.filter_by(user_id=subscriber.id, logged_date=comment_date).all()
    for entry in entries:
        entry.professional_comment = comment_text

    # Notify subscriber
    notif = Notification(
        user_id=subscriber.id,
        message=f"{user.full_name} commented on your food diary for {comment_date.strftime('%d %B %Y')}: \"{comment_text[:80]}{'...' if len(comment_text) > 80 else ''}\""
    )
    db.session.add(notif)
    db.session.commit()
    flash("Comment sent and subscriber notified.", "success")
    return redirect(url_for("view_client", subscriber_id=subscriber_id, date=comment_date_str))


# ---------------------------------------------------------------------------
# Recipe routes
# ---------------------------------------------------------------------------

@app.route("/recipes")
@login_required
def recipes():
    """Browse all recipes with optional ingredient search."""
    user = get_current_user()
    search = request.args.get("search", "").strip()
    tag = request.args.get("tag", "").strip()

    query = Recipe.query

    if search:
        query = query.filter(
            db.or_(
                Recipe.title.ilike(f"%{search}%"),
                Recipe.ingredients.ilike(f"%{search}%"),
                Recipe.tags.ilike(f"%{search}%")
            )
        )
    if tag:
        query = query.filter(Recipe.tags.ilike(f"%{tag}%"))

    all_recipes = query.order_by(Recipe.created.desc()).all()

    # Get user's saved recipe IDs
    saved = {}
    if user.role == "subscriber":
        for sr in user.saved_recipes:
            saved[sr.recipe_id] = sr.status

    return render_template("recipes.html", user=user, recipes=all_recipes, saved=saved,
                           search=search, tag=tag)


@app.route("/recipe/<int:recipe_id>")
@login_required
def view_recipe(recipe_id):
    """View a single recipe with ingredients, instructions, and comments."""
    user = get_current_user()
    recipe = Recipe.query.get_or_404(recipe_id)
    comments = RecipeComment.query.filter_by(recipe_id=recipe_id).order_by(
        RecipeComment.created.desc()).all()

    ingredients = json.loads(recipe.ingredients) if recipe.ingredients else []

    saved_status = None
    if user.role == "subscriber":
        sr = SavedRecipe.query.filter_by(user_id=user.id, recipe_id=recipe_id).first()
        saved_status = sr.status if sr else None

    return render_template("view-recipe.html", user=user, recipe=recipe,
                           ingredients=ingredients, comments=comments, saved_status=saved_status)


@app.route("/recipe/<int:recipe_id>/comment", methods=["POST"])
@login_required
def add_recipe_comment(recipe_id):
    """Add a comment and optional rating to a recipe."""
    user = get_current_user()
    Recipe.query.get_or_404(recipe_id)

    comment_text = request.form.get("comment", "").strip()
    rating_str = request.form.get("rating", "").strip()

    if not comment_text:
        flash("Comment cannot be empty.", "warning")
        return redirect(url_for("view_recipe", recipe_id=recipe_id))

    rating = None
    if rating_str:
        try:
            rating = int(rating_str)
            if rating < 1 or rating > 5:
                rating = None
        except ValueError:
            rating = None

    comment = RecipeComment(
        recipe_id=recipe_id,
        user_id=user.id,
        comment=comment_text,
        rating=rating
    )
    db.session.add(comment)
    db.session.commit()
    flash("Comment added!", "success")
    return redirect(url_for("view_recipe", recipe_id=recipe_id))


@app.route("/recipe/<int:recipe_id>/save", methods=["POST"])
@subscriber_required
def save_recipe(recipe_id):
    """Save a recipe with a status: tried / favourite / want_to_try."""
    user = get_current_user()
    Recipe.query.get_or_404(recipe_id)
    status = request.form.get("status", "want_to_try")

    if status not in ("tried", "favourite", "want_to_try"):
        flash("Invalid status.", "danger")
        return redirect(url_for("view_recipe", recipe_id=recipe_id))

    existing = SavedRecipe.query.filter_by(user_id=user.id, recipe_id=recipe_id).first()
    if existing:
        existing.status = status
    else:
        sr = SavedRecipe(user_id=user.id, recipe_id=recipe_id, status=status)
        db.session.add(sr)

    db.session.commit()
    flash("Recipe saved!", "success")
    return redirect(url_for("view_recipe", recipe_id=recipe_id))


@app.route("/my-recipes")
@subscriber_required
def my_recipes():
    """Show a subscriber's saved recipes grouped by status."""
    user = get_current_user()
    saved = SavedRecipe.query.filter_by(user_id=user.id).all()

    grouped = {"favourite": [], "tried": [], "want_to_try": []}
    for sr in saved:
        grouped.get(sr.status, grouped["want_to_try"]).append(sr)

    return render_template("my-recipes.html", user=user, grouped=grouped)


@app.route("/add-recipe", methods=["GET", "POST"])
@login_required
def add_recipe():
    """Allow any logged-in user to submit a new recipe."""
    user = get_current_user()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        instructions = request.form.get("instructions", "").strip()
        cook_time = request.form.get("cook_time_mins", "").strip()
        prep_time = request.form.get("prep_time_mins", "").strip()
        servings = request.form.get("servings", "2").strip()
        cost = request.form.get("cost_estimate", "").strip()
        tags = request.form.get("tags", "").strip()
        calories = request.form.get("calories_per_serving", "").strip()

        # Collect ingredients from dynamic form fields
        ing_names = request.form.getlist("ingredient_name[]")
        ing_amounts = request.form.getlist("ingredient_amount[]")
        ingredients_list = [
            {"name": n.strip(), "amount": a.strip()}
            for n, a in zip(ing_names, ing_amounts) if n.strip()
        ]

        if not title or not instructions or not ingredients_list:
            flash("Title, instructions, and at least one ingredient are required.", "danger")
            return render_template("add-recipe.html", user=user)

        recipe = Recipe(
            title=title,
            description=description,
            instructions=instructions,
            ingredients=json.dumps(ingredients_list),
            cook_time_mins=int(cook_time) if cook_time.isdigit() else None,
            prep_time_mins=int(prep_time) if prep_time.isdigit() else None,
            servings=int(servings) if servings.isdigit() else 2,
            cost_estimate=cost,
            tags=tags,
            calories_per_serving=float(calories) if calories else None,
            created_by=user.id
        )
        db.session.add(recipe)
        db.session.commit()
        flash("Recipe added!", "success")
        return redirect(url_for("view_recipe", recipe_id=recipe.id))

    return render_template("add-recipe.html", user=user)


# ---------------------------------------------------------------------------
# API endpoint for food search (AJAX)
# ---------------------------------------------------------------------------

@app.route("/api/food-search")
@login_required
def api_food_search():
    """JSON endpoint for food search used by the log-food AJAX form."""
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"results": []})
    results = search_food_api(query)
    return jsonify({"results": results})


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def seed_recipes():
    """Seed the database with sample recipes if none exist."""
    if Recipe.query.first():
        return

    sample_recipes = [
        {
            "title": "High-Protein Chicken & Quinoa Bowl",
            "description": "A filling, nutritious bowl packed with lean protein and complex carbs.",
            "ingredients": json.dumps([
                {"name": "Chicken breast", "amount": "150g"},
                {"name": "Quinoa (dry)", "amount": "80g"},
                {"name": "Cherry tomatoes", "amount": "100g"},
                {"name": "Spinach", "amount": "50g"},
                {"name": "Olive oil", "amount": "1 tbsp"},
                {"name": "Lemon juice", "amount": "1 tbsp"},
                {"name": "Garlic clove", "amount": "1"},
                {"name": "Salt & pepper", "amount": "to taste"},
            ]),
            "instructions": "1. Cook quinoa according to packet instructions.\n2. Season chicken breast with salt, pepper, and garlic.\n3. Heat olive oil in a pan and cook chicken for 6–7 minutes each side.\n4. Slice chicken and serve over quinoa with cherry tomatoes and spinach.\n5. Drizzle with lemon juice.",
            "cook_time_mins": 20, "prep_time_mins": 10, "servings": 1,
            "cost_estimate": "£3–£4", "calories_per_serving": 480,
            "protein_per_serving": 48, "carbs_per_serving": 42, "fat_per_serving": 10,
            "tags": "chicken,high-protein,quinoa,healthy,gluten-free"
        },
        {
            "title": "Lentil & Vegetable Soup",
            "description": "A hearty, budget-friendly soup high in fibre and plant protein.",
            "ingredients": json.dumps([
                {"name": "Red lentils", "amount": "150g"},
                {"name": "Carrot", "amount": "2 medium"},
                {"name": "Celery sticks", "amount": "2"},
                {"name": "Onion", "amount": "1 large"},
                {"name": "Garlic", "amount": "2 cloves"},
                {"name": "Tinned tomatoes", "amount": "400g"},
                {"name": "Vegetable stock", "amount": "800ml"},
                {"name": "Cumin", "amount": "1 tsp"},
                {"name": "Olive oil", "amount": "1 tbsp"},
            ]),
            "instructions": "1. Dice onion, carrot and celery. Sauté in olive oil for 5 minutes.\n2. Add garlic and cumin, cook for 1 minute.\n3. Add lentils, tinned tomatoes, and stock. Bring to boil.\n4. Simmer for 25 minutes until lentils are soft.\n5. Season and serve with crusty bread.",
            "cook_time_mins": 30, "prep_time_mins": 10, "servings": 4,
            "cost_estimate": "£1–£2 per serving", "calories_per_serving": 220,
            "protein_per_serving": 14, "carbs_per_serving": 38, "fat_per_serving": 4,
            "tags": "vegan,vegetarian,lentils,soup,high-fibre,budget"
        },
        {
            "title": "Overnight Oats with Berries",
            "description": "A no-cook breakfast that's ready when you wake up.",
            "ingredients": json.dumps([
                {"name": "Rolled oats", "amount": "80g"},
                {"name": "Milk (or plant milk)", "amount": "200ml"},
                {"name": "Greek yogurt", "amount": "100g"},
                {"name": "Chia seeds", "amount": "1 tbsp"},
                {"name": "Honey", "amount": "1 tsp"},
                {"name": "Mixed berries", "amount": "100g"},
            ]),
            "instructions": "1. Mix oats, milk, yogurt, chia seeds, and honey in a jar.\n2. Stir well, cover and refrigerate overnight.\n3. In the morning, top with mixed berries and serve cold.",
            "cook_time_mins": 0, "prep_time_mins": 5, "servings": 1,
            "cost_estimate": "£1–£2", "calories_per_serving": 390,
            "protein_per_serving": 18, "carbs_per_serving": 58, "fat_per_serving": 8,
            "tags": "breakfast,oats,no-cook,vegetarian,berries,quick"
        },
        {
            "title": "Baked Salmon with Roasted Veg",
            "description": "Omega-3 rich salmon with a colourful mix of roasted vegetables.",
            "ingredients": json.dumps([
                {"name": "Salmon fillet", "amount": "180g"},
                {"name": "Courgette", "amount": "1"},
                {"name": "Bell pepper", "amount": "1"},
                {"name": "Red onion", "amount": "1"},
                {"name": "Olive oil", "amount": "2 tbsp"},
                {"name": "Lemon", "amount": "1"},
                {"name": "Fresh dill", "amount": "handful"},
                {"name": "Salt & pepper", "amount": "to taste"},
            ]),
            "instructions": "1. Preheat oven to 200°C.\n2. Chop vegetables, toss with olive oil, salt and pepper.\n3. Spread on a baking tray and roast for 15 minutes.\n4. Place salmon on top of vegetables, add lemon slices and dill.\n5. Bake for a further 12–15 minutes until salmon is cooked through.",
            "cook_time_mins": 30, "prep_time_mins": 10, "servings": 1,
            "cost_estimate": "£5–£6", "calories_per_serving": 420,
            "protein_per_serving": 38, "carbs_per_serving": 18, "fat_per_serving": 22,
            "tags": "salmon,fish,omega-3,gluten-free,roasted,healthy"
        },
        {
            "title": "Black Bean Tacos",
            "description": "Quick, filling plant-based tacos with avocado and salsa.",
            "ingredients": json.dumps([
                {"name": "Tinned black beans", "amount": "400g"},
                {"name": "Corn tortillas", "amount": "4"},
                {"name": "Avocado", "amount": "1"},
                {"name": "Cherry tomatoes", "amount": "100g"},
                {"name": "Red onion", "amount": "½"},
                {"name": "Lime juice", "amount": "1 tbsp"},
                {"name": "Cumin", "amount": "1 tsp"},
                {"name": "Smoked paprika", "amount": "½ tsp"},
                {"name": "Fresh coriander", "amount": "handful"},
            ]),
            "instructions": "1. Drain and rinse black beans. Heat in a pan with cumin, paprika, and a splash of water.\n2. Mash avocado with lime juice and season.\n3. Dice tomatoes and red onion.\n4. Warm tortillas in a dry pan.\n5. Assemble tacos with beans, avocado, tomato salsa, and coriander.",
            "cook_time_mins": 10, "prep_time_mins": 10, "servings": 2,
            "cost_estimate": "£2–£3", "calories_per_serving": 380,
            "protein_per_serving": 16, "carbs_per_serving": 52, "fat_per_serving": 14,
            "tags": "vegan,vegetarian,tacos,black bean,quick,budget"
        },
    ]

    for r in sample_recipes:
        recipe = Recipe(**r)
        db.session.add(recipe)
    db.session.commit()
    print("[SEED] Sample recipes added.")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_recipes()
    app.run(debug=True)