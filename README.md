# NutriTrack

NutriTrack is a Flask-based nutrition tracking web application designed for subscribers and health professionals.
It allows users to log meals, monitor nutritional intake, browse healthy recipes, and receive guidance from assigned professionals.

## Features

### Subscriber Features

* Create an account and log in securely
* Track daily food intake
* Search foods using the Open Food Facts API
* View calorie and nutrition totals
* Update personal health statistics
* Choose a health professional
* Browse and save recipes
* Receive nutritional guidelines and notifications

### Professional Features

* Create professional accounts
* Accept and manage subscribers
* View client food diaries
* Set nutritional guidelines
* Comment on client nutrition logs
* Monitor client progress

## Technologies Used

* Python
* Flask
* Flask-SQLAlchemy
* SQLite
* HTML / CSS / JavaScript
* Open Food Facts API

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd nutritrack
```

2. Create and activate a virtual environment:

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Mac/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install flask flask_sqlalchemy werkzeug requests
```

4. Run the application:

```bash
python app.py
```

5. Open in your browser:

```text
http://127.0.0.1:5000
```

## Project Structure

```text
NutriTrack/
│
├── app.py
├── static/
├── templates/
├── nutritrack.db
└── README.md
```

## Database

The application uses SQLite and automatically creates the database on first launch.

Sample recipes are also seeded automatically.

## Notes

* Passwords are securely hashed using Werkzeug.
* The Open Food Facts API may occasionally return limited results or timeout.
* The application currently runs in debug mode for development purposes.

## Future Improvements

* Recipe saving system with database support
* Messaging between subscribers and professionals
* Better analytics and nutrition charts
* Profile pictures
* Deployment and environment variable support

## Author

Created as part of a university coursework project.
