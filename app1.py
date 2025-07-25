from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong key in production

# Connect to MongoDB

from pymongo import MongoClient
import certifi

uri = "mongodb+srv://vandyamayya02:pantrypilot3@cluster3.me22ety.mongodb.net/?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"

client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
#client = MongoClient('mongodb+srv://vandyamayya02:pantrypilot3@cluster3.me22ety.mongodb.net/?retryWrites=true&w=majority&appName=Cluster3')
db = client['project']
users_collection = db['register']

@app.route('/')
def home():
    return redirect(url_for('login'))
@app.route('/about')
def about():
    return render_template('about.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if users_collection.find_one({"email": email}):
            flash("Email already registered!")
            return redirect(url_for('register'))

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
            session['user_id'] = str(user['_id'])
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
    session.pop('user_id', None)
    flash("Logged out successfully.")
    return redirect(url_for('login'))

@app.route('/pantry')
def pantry():
    if 'user_id' not in session:
        flash("Please log in to view your pantry.", "error")
        return redirect(url_for('login'))

    from datetime import datetime, timedelta
    user_id = session['user_id']
    items = db.pantry.find({"user_id": user_id})

    def parse_expiry(expiry):
        try:
            return datetime.strptime(expiry, "%Y-%m-%d")
        except:
            return datetime.max  # No expiry => sent to end

    sorted_items = sorted(items, key=lambda x: parse_expiry(x.get('expiry_date')))

    return render_template('pantry.html', items=sorted_items, current_date=datetime.today(), timedelta=timedelta)
from bson import ObjectId

@app.route('/delete/<item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session:
        flash("Please log in.", "error")
        return redirect(url_for('login'))

    db.pantry.delete_one({"_id": ObjectId(item_id), "user_id": session['user_id']})
    flash("Item deleted.")
    return redirect(url_for('pantry'))



from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from bson import ObjectId

@app.route('/update/<item_id>', methods=['GET', 'POST'])
def update_item(item_id):
    if 'user_id' not in session:
        flash("Please log in.", "error")
        return redirect(url_for('login'))

    item = db.pantry.find_one({"_id": ObjectId(item_id), "user_id": session['user_id']})
    if not item:
        flash("Item not found or unauthorized access.", "error")
        return redirect(url_for('pantry'))

    if request.method == 'POST':
        # Update values from form
        updated_data = {
            "name": request.form['name'].strip(),
            "quantity": float(request.form['quantity']),
            "unit": request.form['unit'].strip(),
            "category": request.form['category'],
            "expiry_date": request.form['expiry'],
            "added_date": item.get("added_date", datetime.today().strftime('%Y-%m-%d')),  # Keep old date if available
            "user_id": session['user_id']
        }

        db.pantry.update_one({"_id": ObjectId(item_id)}, {"$set": updated_data})
        flash("Item updated successfully!", "success")
        return redirect(url_for('pantry'))

    return render_template('add_item.html', item=item, today=date.today().isoformat())



from datetime import datetime, date

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session:
        flash("Please log in.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        quantity_val = float(request.form['quantity'])  # ensure it's stored as float
        unit = request.form['unit'].strip()
        category = request.form['category']
        expiry = request.form['expiry']

        db.pantry.insert_one({
            "name": name,
            "quantity": quantity_val,
            "unit": unit,
            "category": category,
            "expiry_date": expiry,
            "user_id": session['user_id'],
            "added_date": datetime.today().strftime('%Y-%m-%d')
        })

        flash("Item added to pantry!")
        return redirect(url_for('pantry'))

    # If GET request, show the form and pass today's date for expiry limit
    return render_template('add_item.html', today=date.today().isoformat(), item=None)

    
@app.route('/my_recipes')
def suggest_personal_recipes():
    if 'user_id' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']

    pantry_items = db.pantry.find({"user_id": user_id})
    user_ingredients = set()

    def is_in_stock(item):
        try:
            qty = float(str(item['quantity']).split()[0])
            return qty > 0
        except:
            return False

    # ✅ Add only in-stock items
    for item in pantry_items:
        if is_in_stock(item):
            user_ingredients.add(item['name'].strip().lower())

    # Fetch all recipes
    all_recipes = list(db.receipe.find())
    matched_recipes = []

    for recipe in all_recipes:
        required_ingredients = [ing['name'].strip().lower() for ing in recipe['ingredients']]

        match_count = sum(1 for ing in required_ingredients if ing in user_ingredients)
        total_ingredients = len(required_ingredients)

        if match_count >= 5 or (match_count / total_ingredients) >= 0.7:
            recipe['match_percent'] = round((match_count / total_ingredients) * 100, 1)
            recipe['missing_count'] = total_ingredients - match_count
            matched_recipes.append(recipe)

    matched_recipes.sort(key=lambda r: r['match_percent'], reverse=True)

    return render_template("receipe.html", recipes=matched_recipes, user_ingredients=user_ingredients)

@app.route('/test_pantry')
def test_pantry():
    user_id = session.get('user_id')
    if not user_id:
        return "Not logged in"
    items = db.pantry.find({"user_id": user_id})
    return "<br>".join(f"{item['name']} - {item['quantity']}" for item in items)


from bson import ObjectId

from bson import ObjectId

from bson import ObjectId
from flask import request, session, redirect, url_for, flash

# Unit conversion mapping
'''
unit_conversion = {
    'liters': ('ml', 1000), 'liter': ('ml', 1000), 'l': ('ml', 1000),
    'ml': ('ml', 1),
    'cups': ('ml', 240), 'cup': ('ml', 240),
    'kg': ('g', 1000), 'kilogram': ('g', 1000),
    'g': ('g', 1), 'grams': ('g', 1),
    'piece': ('piece', 1), 'pieces': ('piece', 1),
    'packet': ('packet', 1), 'packets': ('packet', 1)
}

def convert_to_base(quantity, unit):
    unit = unit.lower().strip()
    if unit in unit_conversion:
        base_unit, factor = unit_conversion[unit]
        return quantity * factor, base_unit
    return quantity, unit  # return as is if not convertible

'''

# === General unit conversions ===
unit_conversion = {
    'liters': ('ml', 1000), 'liter': ('ml', 1000), 'l': ('ml', 1000),
    'ml': ('ml', 1),
    'cups': ('ml', 240), 'cup': ('ml', 240),
    'kg': ('g', 1000), 'kilogram': ('g', 1000),
    'g': ('g', 1), 'grams': ('g', 1),
    'tsp': ('ml', 5), 'tbsp': ('ml', 15),
    'piece': ('piece', 1), 'pieces': ('piece', 1),
    'packet': ('packet', 1), 'packets': ('packet', 1),
    'large': ('piece', 1), 'medium': ('piece', 1), 'small': ('piece', 1),
    'leaves': ('piece', 1)
}

# === Ingredient-specific overrides ===
ingredient_unit_conversions = {
    
    'salt': {
        'tsp': ('g', 6),
        'tbsp': ('g', 18),
        'g': ('tsp', 1 / 6),
        'kg': ('tsp', 1000 / 6)  # 1 kg = 1000g → 1000/6 tsp
    },
    'sugar': {'tsp': ('g', 4), 'tbsp': ('g', 12)},
    'mustard seeds': {'tsp': ('g', 2.5), 'tbsp': ('g', 7.5)},
    # add more ingredients as needed
}


# Approximate grams per tsp for dry ingredients
approx_density_g_per_tsp = {
    'default_powder': 2.5,  # like mustard seeds, spices
    'default_solid_piece': 100  # like onion, tomato
}

def convert_to_base(quantity, unit, ingredient_name=""):
    unit = unit.lower().strip()
    ingredient = ingredient_name.lower().strip()

    try:
        # Custom overrides
        if ingredient in ingredient_unit_conversions:
            specific = ingredient_unit_conversions[ingredient]
            if unit in specific:
                base_unit, factor = specific[unit]
                return quantity * factor, base_unit

        # Generic conversion
        if unit in unit_conversion:
            base_unit, factor = unit_conversion[unit]
            return quantity * factor, base_unit

        # Fallback: estimate based on general density
        if unit in ['tsp', 'tbsp']:
            est_grams = approx_density_g_per_tsp['default_powder'] * quantity
            return est_grams, 'g'
        if unit in ['small', 'medium', 'large', 'piece', 'pieces']:
            est_grams = approx_density_g_per_tsp['default_solid_piece'] * quantity
            return est_grams, 'g'

    except:
        pass

    return quantity, unit  # fallback if unknown


def convert_from_base(quantity, base_unit, target_unit, ingredient_name=""):
    target_unit = target_unit.lower().strip()
    ingredient = ingredient_name.lower().strip()

    # Try ingredient-specific reverse conversion
    if ingredient in ingredient_unit_conversions:
        reverse_map = ingredient_unit_conversions[ingredient]
        for k, v in reverse_map.items():
            if v[0] == base_unit and k == target_unit:
                return quantity / v[1]

    # Fallback to general conversion
    if target_unit in unit_conversion:
        unit_base, factor = unit_conversion[target_unit]
        if unit_base == base_unit:
            return quantity / factor

    return quantity

@app.route('/cook_recipe', methods=['POST'])
def cook_recipe():
    if 'user_id' not in session:
        flash("Please log in.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    recipe_id = request.form.get('recipe_id')

    recipe = db.receipe.find_one({"_id": ObjectId(recipe_id)})
    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for('my_recipes'))

    pantry_items = list(db.pantry.find({"user_id": user_id}))
    pantry_dict = {item['name'].strip().lower(): item for item in pantry_items}

    for ing in recipe['ingredients']:
        ing_name = ing['name'].strip().lower()

        if ing_name in pantry_dict:
            pantry_item = pantry_dict[ing_name]

            try:
                pantry_qty_str = pantry_item.get('quantity', '0')
                pantry_unit = pantry_item.get('unit', '').strip().lower()

                if not pantry_qty_str or not pantry_unit:
                    print(f"⚠️ Missing unit or quantity for '{ing_name}'")
                    continue

                pantry_qty = float(pantry_qty_str)
                recipe_qty = float(ing.get('quantity', 0))
                recipe_unit = ing.get('unit', '').strip().lower()

                # Convert both to base units
                pantry_val, pantry_base_unit = convert_to_base(pantry_qty, pantry_unit, ing_name)
                recipe_val, recipe_base_unit = convert_to_base(recipe_qty, recipe_unit, ing_name)

                # Debug prints
                print(f"\n🧂 Ingredient: {ing_name}")
                print(f"Initial pantry quantity: {pantry_qty} {pantry_unit}")
                print(f"Recipe requires: {recipe_qty} {recipe_unit}")
                print(f"Converted pantry: {pantry_val} {pantry_base_unit}")
                print(f"Converted recipe: {recipe_val} {recipe_base_unit}")


                # ✅ Auto-adjust unit mismatch (e.g., pantry=kg, recipe=piece)
                if pantry_base_unit != recipe_base_unit:
                    # If pantry in grams and recipe in piece, estimate 1 piece = 100g
                    if pantry_base_unit == 'g' and recipe_base_unit == 'piece':
                        recipe_val *= approx_density_g_per_tsp['default_solid_piece']
                        recipe_base_unit = 'g'
                    elif pantry_base_unit == 'piece' and recipe_base_unit == 'g':
                        recipe_val /= approx_density_g_per_tsp['default_solid_piece']
                        recipe_base_unit = 'piece'
                    # Try converting grams ↔ tsp based on density
                    elif pantry_base_unit == 'g' and recipe_base_unit == 'tsp':
                        density = ingredient_unit_conversions.get(ing_name, {}).get('tsp')
                        if density:
                            _, factor = density
                        else:
                            factor = approx_density_g_per_tsp['default_powder']
                        recipe_val *= factor
                        recipe_base_unit = 'g'

                    elif pantry_base_unit == 'tsp' and recipe_base_unit == 'g':
                        density = ingredient_unit_conversions.get(ing_name, {}).get('tsp')
                        if density:
                            _, factor = density
                        else:
                            factor = approx_density_g_per_tsp['default_powder']
                        recipe_val /= factor
                        recipe_base_unit = 'tsp'

                    # Optional: extend for kg → tsp by converting kg → g first
                    elif pantry_base_unit == 'g' and recipe_base_unit == 'kg':
                        recipe_val *= 1000
                        recipe_base_unit = 'g'

                    else:
                        print(f"⚠️ Unit mismatch not resolved for '{ing_name}'")
                        continue
                

                # Subtract and update
                remaining_base = max(0, pantry_val - recipe_val)
                remaining_converted = convert_from_base(remaining_base, pantry_base_unit, pantry_unit, ing_name)
               
                new_quantity = str(round(remaining_converted, 3))

                print(f"Remaining in base: {remaining_base} {pantry_base_unit}")
                print(f"Converted back: {remaining_converted} {pantry_unit}\n")

                db.pantry.update_one(
                    {"_id": pantry_item['_id']},
                    {"$set": {"quantity": new_quantity}}
                )
                


            except Exception as e:
                print(f"❌ Error processing '{ing_name}': {e}")
                continue

    flash("✅ Pantry updated after cooking recipe!", "success")
    return redirect(url_for('pantry'))




if __name__ == '__main__':
    app.run(debug=True)
