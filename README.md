# NutriTrack – Healthy Eating & Nutrition Platform

## Overview

NutriTrack is a full-stack web application designed to promote healthier eating habits and support nutritional monitoring for members of the public. The platform allows subscribers to record daily food intake, monitor nutritional trends, receive dietary guidance, and discover healthy recipes tailored to their goals.

The system also supports health professionals such as nutritionists and dieticians, allowing them to manage subscribers, monitor progress, provide personalised guidance, and help users improve their eating habits over time.

The project was developed as part of the COMP2850 Software Engineering module at the University of Leeds.

---

# Key Features

## Subscriber Features

- User registration and secure login
- Food diary system for logging meals and snacks
- Nutritional analysis using third-party nutrition APIs
- View historical food intake and nutrition data
- Health statistics tracking:
  - Weight
  - Blood pressure
  - Calories
  - Nutritional intake
- Personal dietary goals:
  - Weight loss
  - Weight gain
  - General healthy eating
- Daily and weekly nutrition trend visualisations
- Notifications from health professionals
- Recipe recommendations based on:
  - Nutritional requirements
  - Ingredients available
  - Dietary goals
- Save favourite recipes
- Track recipes previously cooked
- Save recipes to try in the future
- Comment and interact with recipes
- Home cooking recommendations
- Ingredient-based recipe searching

---

## Health Professional Features

- Separate professional authentication system
- Dashboard for managing subscribers
- Assign subscribers to professionals
- Monitor subscriber progress and nutritional trends
- Create personalised dietary guidelines
- Review whether subscribers are meeting targets
- Provide feedback and encouragement to subscribers
- Comment directly on subscriber food diary entries
- Receive access based on professional specialisation

---

## Nutritional Tracking & Analysis

The application analyses food intake data and converts logged meals into nutritional information using external APIs and internal ingredient databases.

The platform can:
- Calculate calorie intake
- Track macronutrients
- Compare intake against personalised targets
- Detect over-eating and under-eating patterns
- Suggest dietary improvements when targets are missed

Visual feedback is provided through graphs and charts to help users better understand their eating habits.

---

# Recipe & Home Cooking Support

NutriTrack encourages healthier home cooking through an integrated recipe system.

Features include:
- Nutritional recipe recommendations
- Estimated cooking time
- Estimated cost
- Ingredient searching
- User recipe interactions and favourites
- Recipe comments and feedback
- Personal recipe collections

Example:
Users can search for ingredients such as:
- Chicken
- Broccoli
- Spinach

…and receive suitable healthy recipes using those ingredients.

---

# Technologies Used

## Frontend
- HTML5
- CSS3
- JavaScript

## Backend
- Python / Flask

## Database
- SQLite / PostgreSQL

## APIs
- Nutrition and food analysis APIs
- Recipe APIs

## Development Tools
- Git & GitHub
- GitHub Actions
- VS Code / IntelliJ

## Testing
- PyTest / Unit Testing Frameworks

---

# System Architecture

The application follows a client-server architecture.

### Main Components
- Frontend web interface
- Backend application server
- Database layer
- Third-party nutrition and recipe APIs

The backend handles:
- Authentication
- Data processing
- Nutritional calculations
- Database operations
- API communication

---

# Accessibility Considerations

Accessibility and usability were considered throughout development.

Implemented considerations include:
- Responsive layouts for mobile and desktop devices
- Clear navigation structure
- Consistent styling and formatting
- Accessible forms and buttons
- Appropriate colour contrast
- Semantic HTML structure

---

# Security Considerations

The application includes several security measures including:
- Password hashing
- Session management
- Input validation
- Protection against invalid form submission
- Authentication checks for protected pages
- Role-based access for subscribers and professionals

---

# Testing

The system includes automated tests covering core functionality including:
- Authentication
- Food logging
- Recipe functionality
- Database operations
- User management
- Validation handling

Tests are run regularly throughout development to ensure system stability and reliability.

To run tests locally:

```bash
pytest