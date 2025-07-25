from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong key in production

# Connect to MongoDB
client = MongoClient('mongodb+srv://vandyamayya02:pantrypilot3@cluster3.me22ety.mongodb.net/?retryWrites=true&w=majority&appName=Cluster3')
db = client['project']
users_collection = db['register']

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        # Check if user exists
        if users_collection.find_one({"email": email}):
            flash("Email already registered!")
            return redirect(url_for('register'))

        # Insert new user
        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": password
        })

        flash("Registration successful! Please login.")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users_collection.find_one({"email": email})

        if user and check_password_hash(user['password'], password):
            session['user'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.")
    return redirect(url_for('login'))

from datetime import datetime, timedelta

@app.route('/pantry')
def pantry():
    items = db.pantry.find()
    return render_template('pantry.html', items=items, current_date=datetime.today(), timedelta=timedelta)



@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        category = request.form['category']
        expiry = request.form['expiry']

        # Convert expiry to datetime for validation
        expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
        today = datetime.today()

        # Check: Expiry date must not be in the past
        if expiry_date.date() < today.date():
            flash("⚠️ Expiry date cannot be in the past!", "error")
            return redirect(url_for('add_item'))

        # Save to MongoDB
        db.pantry.insert_one({
            "name": name,
            "quantity": quantity,
            "category": category,
            "expiry_date": expiry,
            "user_id": session.get("user_id", "guest")  # fallback if no session
        })

        flash("✅ Item added successfully!", "success")
        return redirect(url_for('pantry'))

    # Send today's date to form for input min validation
    today_str = datetime.today().strftime('%Y-%m-%d')
    return render_template('add_item.html', today=today_str)


if __name__ == '__main__':
    app.run(debug=True)
