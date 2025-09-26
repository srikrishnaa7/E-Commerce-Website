import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from bson.objectid import ObjectId
from datetime import datetime
import re # For regular expressions in search
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import random # Import the random module

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- Configuration for MongoDB ---
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "a_very_secret_key_for_your_ecommerce_app_2025")

# Initialize PyMongo
mongo = PyMongo(app)

# Reference to your MongoDB collections
products_collection = mongo.db.products
carts_collection = mongo.db.carts
users_collection = mongo.db.users
orders_collection = mongo.db.orders # NEW: Orders collection

# Test MongoDB connection at startup
try:
    mongo.cx.admin.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print(f"CRITICAL ERROR: MongoDB connection failed at startup: {e}")
    print("Please check your MONGO_URI in the .env file and ensure MongoDB is running.")

# --- Authentication Decorators ---
def login_required(f):
    """Decorator to protect routes that require a logged-in user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You need to be logged in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to protect routes that require an admin user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You need to be logged in as an admin to access this page.", "error")
            return redirect(url_for('login'))

        user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
        if not user or not user.get('is_admin'):
            flash("Access Denied: You do not have administrator privileges.", "error")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


def initialize_products_and_users():
    """
    Checks if the products collection is empty and populates it.
    Also ensures default admin and normal users exist for development.
    """
    initial_products = [
        # Audio
        {
            'name': 'Smart Speaker (Gen 4)',
            'description': 'Voice-controlled smart speaker with rich sound and AI assistant integration. Comes with a built-in privacy shutter and enhanced bass.',
            'price': 4999.00,
            'stock': 150,
            'image_url': 'https://m.media-amazon.com/images/I/41f80Qu98zL._SY300_SX300_.jpg', # Actual Amazon Echo Dot 4th Gen image
            'category': 'Audio'
        },
        {
            'name': 'Wireless Earbuds Pro',
            'description': 'Compact and comfortable wireless earbuds with active noise cancellation, crystal clear audio, and long battery life (up to 24 hours with case).',
            'price': 4999.00,
            'stock': 180,
            'image_url': 'https://m.media-amazon.com/images/I/61QdEv6kKdL.jpg', # Actual Samsung Galaxy Buds Pro image
            'category': 'Audio'
        },
        {
            'name': 'Over-Ear Bluetooth Headphones ANC',
            'description': 'Premium over-ear headphones with immersive sound, comfort-fit earcups, advanced active noise cancellation, and up to 30 hours of playback.',
            'price': 8999.00,
            'stock': 90,
            'image_url': 'https://cdn.mos.cms.futurecdn.net/C3JVFsG8kzpwRLMTsn44m8.jpg', # Actual Sony WH-1000XM4 image
            'category': 'Audio'
        },
        {
            'name': 'Portable Bluetooth Speaker',
            'description': 'Waterproof and dustproof portable speaker with powerful sound, ideal for outdoor adventures. 12-hour battery life.',
            'price': 3499.00,
            'stock': 200,
            'image_url': 'https://www.boat-lifestyle.com/cdn/shop/files/Stone_SpinXPro_1_b3503890-50f6-4cd1-9138-0bd90874391e.png?v=1709717442', # Actual JBL Flip 5 image
            'category': 'Audio'
        },
        # Smart Home
        {
            'name': 'LED Smart Bulb (Wi-Fi, Color)',
            'description': 'Energy-efficient LED bulb with Wi-Fi connectivity, adjustable 16 million colors, and dimming via app or voice commands (Alexa/Google Assistant compatible).',
            'price': 799.00,
            'stock': 300,
            'image_url': 'https://m.media-amazon.com/images/I/61vN5ySYjJL._UF894,1000_QL80_.jpg', # Actual Philips Hue Smart Bulb image
            'category': 'Smart Home'
        },
        {
            'name': 'Smart Doorbell Camera Pro',
            'description': 'High-definition 1080p video doorbell with two-way audio, advanced motion detection, facial recognition, and free cloud storage options for enhanced home security.',
            'price': 7999.00,
            'stock': 70,
            'image_url': 'https://images.ctfassets.net/a3peezndovsu/1hyiKWdJqtZ2Idw1Sr6t18/2f1e2c0c9fe466a96a697449f16e3654/ring_battery-video-doorbell-pro_spotlightcam-pro-wht_sb_slate1_en_1500x1500.png', # Actual Ring Video Doorbell Pro image
            'category': 'Smart Home'
        },
        {
            'name': 'Smart Plug (2-Pack) with Energy Monitoring',
            'description': 'Control any appliance from your smartphone. Schedule lights, fans, and monitor energy consumption in real-time.',
            'price': 1499.00,
            'stock': 250,
            'image_url': 'data:image/jpeg;base64,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', # Actual TP-Link Kasa Smart Plug image
            'category': 'Smart Home'
        },
        {
            'name': 'Smart Thermostat',
            'description': 'Intelligent thermostat that learns your preferences, saves energy, and can be controlled remotely via smartphone.',
            'price': 9999.00,
            'stock': 50,
            'image_url': 'data:image/jpeg;base64,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', # Actual Google Nest Thermostat image
            'category': 'Smart Home'
        },
        # Accessories
        {
            'name': '20000mAh Power Bank (Super Fast Charge)',
            'description': 'High-capacity portable power bank with 25W super fast charging and multiple outputs (USB-A & USB-C PD) for laptops and phones.',
            'price': 2499.00,
            'stock': 120,
            'image_url': 'https://www.boat-lifestyle.com/cdn/shop/files/mainimage.png?v=1737116197', # Actual Anker PowerCore Essential image
            'category': 'Accessories'
        },
        {
            'name': 'Wireless Ergonomic Mouse',
            'description': 'Comfortable wireless mouse with adjustable DPI, programmable buttons, and long battery life, perfect for extended use.',
            'price': 899.00,
            'stock': 180,
            'image_url': 'https://images-cdn.ubuy.co.in/65502f57e4243e357503852a-f-35-mouse-wireless-vertical-mouse.jpg', # Actual Logitech MX Master 3S image
            'category': 'Accessories'
        },
        {
            'name': 'Bluetooth Mini Keyboard',
            'description': 'Compact and portable Bluetooth keyboard for tablets and smartphones, ideal for on-the-go typing and multi-device pairing.',
            'price': 1599.00,
            'stock': 100,
            'image_url': 'https://lh4.googleusercontent.com/proxy/JED7KG-QwxvgcqRipVFpkmgTaFz-bdyfiFEDHXKHzRTTLWr_ZlhV9IzVsdt23OpoQlkkieQv9-KJLpXEbUgDqhGJZi7XuFijqYY2jUEzI3g5cXHc9tq4S4dHSSAZ', # Actual Logitech K380 image
            'category': 'Accessories'
        },
        {
            'name': 'Universal Travel Adapter Pro',
            'description': 'All-in-one adapter compatible with outlets in over 150 countries, with dual USB-A and single USB-C PD charging ports.',
            'price': 1299.00,
            'stock': 150,
            'image_url': 'https://encrypted-tbn1.gstatic.com/shopping?q=tbn:ANd9GcS8CmMuz08xYRzUeNaouVSe0KMqdctwzRykugGqL8vEA2e0Zl_QFV7hrG2vt1vqJVM0JqgclMR2d5dfioidNtyktbXUFlu9g3MwAtym8fyAk7Speg2T--nvjkmuWQ&usqp=CAc', # Actual universal travel adapter image
            'category': 'Accessories'
        },
        # Wearables
        {
            'name': 'Fitness Smartwatch HR Pro',
            'description': 'Track your fitness, heart rate, sleep, blood oxygen, and notifications with this sleek and feature-rich smartwatch. GPS built-in and 5ATM water resistance.',
            'price': 8999.00,
            'stock': 80,
            'image_url': 'https://ptron.in/cdn/shop/products/Blue_1_04-04-2022_1024x1024.png?v=1656497965', # Actual Garmin Forerunner image
            'category': 'Wearables'
        },
        {
            'name': 'Kids Smartwatch with GPS & Video Call',
            'description': 'Keep track of your child with precise GPS tracking, two-way calling, video call support, and an SOS button for emergencies.',
            'price': 4499.00,
            'stock': 60,
            'image_url': 'https://m.media-amazon.com/images/I/71THXZCZTiL.jpg', # Actual Xplora X5 Play image
            'category': 'Wearables'
        },
        # Entertainment
        {
            'name': 'Portable HD Projector Mini',
            'description': 'Ultra-compact mini projector for home cinema and presentations, with HDMI, USB, and wireless screen mirroring capabilities. Perfect for small spaces.',
            'price': 12999.00,
            'stock': 40,
            'image_url': 'https://m.media-amazon.com/images/I/71iNIYZpsyL._UF1000,1000_QL80_.jpg', # Actual Anker Nebula Capsule image
            'category': 'Entertainment'
        },
        {
            'name': 'Gaming Controller (Wireless Pro)',
            'description': 'Ergonomic wireless gaming controller compatible with PC, Android, and select smart TVs. Features haptic feedback and customizable buttons.',
            'price': 2799.00,
            'stock': 110,
            'image_url': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS0BURVhQJBEXjhG0ydHYi-VrE_O9pF8efDBQ&s', # Actual Xbox Wireless Controller image
            'category': 'Entertainment'
        },
        {
            'name': 'VR Headset (Entry-Level)',
            'description': 'Immersive virtual reality headset for gaming and entertainment. Easy setup and comfortable design for extended sessions.',
            'price': 19999.00,
            'stock': 30,
            'image_url': 'data:image/jpeg;base64,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', # Actual Meta Quest 2 image
            'category': 'Entertainment'
        }
    ]

    print("Initializing/Updating MongoDB product collection...")
    for product_data in initial_products:
        products_collection.update_one(
            {'name': product_data['name']},
            {'$set': product_data},
            upsert=True
        )
    print("MongoDB product collection initialized/updated.")

    # Ensure a default admin user exists for development
    if users_collection.count_documents({"username": "admin"}) == 0:
        print("Creating default admin user...")
        # Get password from .env or use a default 'adminpass' for dev
        admin_password = os.getenv("ADMIN_PASSWORD", "adminpass")
        hashed_password = generate_password_hash(admin_password)
        users_collection.insert_one({
            "username": "admin",
            "password": hashed_password,
            "email": "admin@example.com",
            "is_admin": True,
            "created_at": datetime.utcnow()
        })
        print(f"Default admin user 'admin' created with password: '{admin_password}' (from ADMIN_PASSWORD env var or default).")

    if users_collection.count_documents({"username": "user"}) == 0:
        print("Creating default normal user...")
        # Get password from .env or use a default 'userpass' for dev
        user_password = os.getenv("USER_PASSWORD", "userpass")
        hashed_password = generate_password_hash(user_password)
        users_collection.insert_one({
            "username": "user",
            "password": hashed_password,
            "email": "user@example.com",
            "is_admin": False,
            "created_at": datetime.utcnow()
        })
        print(f"Default normal user 'user' created with password: '{user_password}' (from USER_PASSWORD env var or default).")


@app.before_request
def setup_globals():
    """
    Runs initialization and sets up global variables for templates.
    """
    if not hasattr(app, 'initialized_data_flag'):
        initialize_products_and_users()
        app.initialized_data_flag = True

    # Set user info for templates to be accessible globally
    session['logged_in'] = 'user_id' in session
    if session['logged_in']:
        user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
        session['username'] = user['username'] if user else 'Guest'
        session['is_admin'] = user.get('is_admin', False) if user else False
    else:
        session['username'] = 'Guest'
        session['is_admin'] = False


# --- Helper function to get or create a cart ---
def get_or_create_cart():
    """
    Retrieves the current user's cart from MongoDB.
    If a user is logged in, it tries to fetch their persistent cart.
    If not, it uses a session-based anonymous cart.
    Carts are now linked to user_id if logged in.
    """
    user_id = session.get('user_id')
    cart = None

    if user_id:
        # If logged in, try to find a cart linked to this user
        cart = carts_collection.find_one({"user_id": ObjectId(user_id)})
        if not cart:
            # If logged in but no cart, create one for the user
            new_cart_data = {
                "user_id": ObjectId(user_id),
                "items": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = carts_collection.insert_one(new_cart_data)
            cart = new_cart_data
            cart['_id'] = result.inserted_id
            print(f"DEBUG: New cart created for user {user_id} with ID: {result.inserted_id}")
        else:
             print(f"DEBUG: Found existing cart for user {user_id} with ID: {cart['_id']}")
    else:
        # If not logged in, use session-based cart_id for anonymous cart
        cart_id = session.get('cart_id')
        if cart_id:
            try:
                # Ensure it's an anonymous cart (user_id is None)
                cart = carts_collection.find_one({"_id": ObjectId(cart_id), "user_id": None})
                if not cart:
                    session.pop('cart_id', None) # Clear invalid/non-existent cart ID
                    print(f"DEBUG: Anonymous cart {cart_id} not found/invalid. Creating new anonymous cart.")
            except Exception as e:
                print(f"ERROR: Failed to retrieve anonymous cart {cart_id}: {e}")
                flash("There was an issue retrieving your previous cart. Creating a new one.", "error")
                session.pop('cart_id', None)

        if not cart: # If no cart for anonymous session, create one
            new_cart_data = {
                "user_id": None, # Anonymous cart
                "items": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = carts_collection.insert_one(new_cart_data)
            session['cart_id'] = str(result.inserted_id)
            cart = new_cart_data
            cart['_id'] = result.inserted_id
            print(f"DEBUG: New anonymous cart created with ID: {result.inserted_id}")

    if not cart: # Fallback in case of critical error during cart creation
        flash("Critical error: Could not initialize your shopping cart. Please try again.", "error")
        return {"items": []} # Return empty dict to prevent template errors

    return cart


@app.route('/')
def home():
    """
    Displays the home page with a list of products from MongoDB.
    Can filter by category and search by keyword.
    """
    category = request.args.get('category')
    search_query = request.args.get('search_query')
    min_price_str = request.args.get('min_price')
    max_price_str = request.args.get('max_price')

    query = {}

    if category and category != 'All':
        query['category'] = category

    if search_query:
        search_regex = re.compile(search_query, re.IGNORECASE)
        query['$or'] = [
            {'name': {'$regex': search_regex}},
            {'description': {'$regex': search_regex}}
        ]

    # Price range filter
    price_query = {}
    try:
        if min_price_str:
            min_price = float(min_price_str)
            if min_price >= 0:
                price_query['$gte'] = min_price
            else:
                flash("Minimum price cannot be negative.", "error")
                min_price = None # Invalidate for template
        else:
            min_price = None # Explicitly set to None if not provided

        if max_price_str:
            max_price = float(max_price_str)
            if max_price >= 0:
                price_query['$lte'] = max_price
            else:
                flash("Maximum price cannot be negative.", "error")
                max_price = None # Invalidate for template
        else:
            max_price = None # Explicitly set to None if not provided

        if price_query:
            query['price'] = price_query

        # Validate min_price <= max_price if both are provided
        if min_price is not None and max_price is not None and min_price > max_price:
            flash("Minimum price cannot be greater than maximum price.", "error")
            # Clear price filters for the query, but keep values in template for user correction
            query.pop('price', None)

    except ValueError:
        flash("Invalid price values provided. Please enter numbers only.", "error")
        min_price = None
        max_price = None

    all_products = products_collection.find(query)

    categories = products_collection.distinct('category')
    categories = sorted(categories)
    categories.insert(0, 'All')

    return render_template('index.html', products=all_products,
                           categories=categories, selected_category=category,
                           search_query=search_query,
                           min_price=min_price_str, max_price=max_price_str)


@app.route('/product/<product_id>')
def product_detail(product_id):
    """Displays details for a specific product from MongoDB."""
    try:
        product = products_collection.find_one({"_id": ObjectId(product_id)})
        if product is None:
            flash("Product not found!", "error")
            return redirect(url_for('home'))
        return render_template('product_detail.html', product=product)
    except Exception as e:
        flash(f"Error fetching product: {e}", "error")
        return redirect(url_for('home'))

@app.route('/admin/add_product', methods=['GET', 'POST'])
@admin_required # Protect this route
def add_product():
    """Allows an admin to add new products to MongoDB, including category."""
    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()

        try:
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            if price <= 0 or stock < 0:
                flash("Price must be positive and Stock non-negative.", "error")
                return render_template('add_product.html', form_data=request.form)
        except ValueError:
            flash("Price and Stock must be valid numbers.", "error")
            return render_template('add_product.html', form_data=request.form)

        image_url = request.form['image_url'].strip()
        category = request.form['category'].strip()

        if not name or not description or not image_url or not category:
            flash("All fields are required.", "error")
            return render_template('add_product.html', form_data=request.form)

        new_product = {
            'name': name,
            'description': description,
            'price': price,
            'stock': stock,
            'image_url': image_url,
            'category': category
        }

        try:
            existing_product = products_collection.find_one({'name': name})
            if existing_product:
                flash(f"A product with the name '{name}' already exists. Please use a unique name.", "warning")
                return render_template('add_product.html', form_data=request.form)

            products_collection.insert_one(new_product)
            flash(f"Product '{name}' added successfully!", "success")
            return redirect(url_for('home'))
        except Exception as e:
            flash(f"Error adding product: {e}", "error")
            print(f"MongoDB Insert Error in add_product: {e}")
            return render_template('add_product.html', form_data=request.form)

    return render_template('add_product.html', form_data={})


@app.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    """Adds a product to the user's shopping cart."""
    product = products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        flash("Product not found!", "error")
        return redirect(url_for('home'))

    quantity_to_add = 1

    try:
        req_quantity = int(request.form.get('quantity', 1))
        if req_quantity <= 0:
            flash("Quantity must be positive.", "error")
            return redirect(request.referrer or url_for('home'))
        quantity_to_add = req_quantity
    except ValueError:
        flash("Invalid quantity specified.", "error")
        return redirect(request.referrer or url_for('home'))

    cart = get_or_create_cart()
    if not cart or "items" not in cart:
        flash("Could not add to cart due to an internal error. Cart not initialized.", "error")
        return redirect(url_for('home'))

    cart_items = cart.get('items', [])

    found_item_in_cart = False
    for item in cart_items:
        if str(item['product_id']) == product_id:
            found_item_in_cart = True
            # Check if adding more would exceed stock
            if item['quantity'] + quantity_to_add > product['stock']:
                flash(f"Cannot add {quantity_to_add} more '{product['name']}'. Only {product['stock'] - item['quantity']} available in stock.", "warning")
                return redirect(request.referrer or url_for('home'))
            item['quantity'] += quantity_to_add
            break

    if not found_item_in_cart:
        # Check if adding first item would exceed stock
        if quantity_to_add > product['stock']:
            flash(f"Cannot add '{product['name']}'. Only {product['stock']} in stock.", "warning")
            return redirect(request.referrer or url_for('home'))

        cart_items.append({
            "product_id": product["_id"],
            "name": product["name"],
            "price": product["price"],
            "quantity": quantity_to_add,
            "image_url": product["image_url"],
            "category": product.get("category", "Uncategorized")
        })

    try:
        carts_collection.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": cart_items, "updated_at": datetime.utcnow()}}
        )
        flash(f"{quantity_to_add}x '{product['name']}' added to cart!", "success")
    except Exception as e:
        flash(f"Error adding to cart: {e}", "error")
        print(f"MongoDB Update Error in add_to_cart: {e}")

    return redirect(request.referrer or url_for('home'))


@app.route('/update_cart_quantity/<product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    """Updates the quantity of a specific product in the user's cart."""
    try:
        # Determine the action: 'increase', 'decrease', or direct input
        action = request.form.get('action')
        
        cart = get_or_create_cart()
        if not cart or not cart.get("items"):
            flash("Cart not found or empty.", "error")
            return redirect(url_for('view_cart'))

        cart_items = cart['items']
        product_db = products_collection.find_one({"_id": ObjectId(product_id)})

        if not product_db:
            flash("Product not found in store inventory.", "error")
            return redirect(url_for('view_cart'))
        
        item_found_in_cart = False
        for item in cart_items:
            if str(item['product_id']) == product_id:
                item_found_in_cart = True
                current_quantity = item['quantity']
                
                if action == 'increase':
                    new_quantity = current_quantity + 1
                elif action == 'decrease':
                    new_quantity = current_quantity - 1
                else: # Direct input from quantity field
                    new_quantity = int(request.form.get('quantity'))
                
                if new_quantity <= 0:
                    # If new quantity is 0 or less, remove item from cart
                    cart_items.remove(item)
                    flash(f"'{item['name']}' removed from cart.", "info")
                elif new_quantity > product_db['stock']:
                    # If new quantity exceeds stock, cap it at stock and warn
                    flash(f"Only {product_db['stock']} of '{item['name']}' available. Quantity set to maximum available.", "warning")
                    item['quantity'] = product_db['stock']
                else:
                    # Valid quantity, update it
                    item['quantity'] = new_quantity
                break
        
        if not item_found_in_cart:
            flash("Product not found in your cart to update.", "warning")
            return redirect(url_for('view_cart'))

        carts_collection.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": cart_items, "updated_at": datetime.utcnow()}}
        )
        # Only flash success if item wasn't completely removed (handled by the 'info' flash)
        if item_found_in_cart and new_quantity > 0:
            flash(f"Quantity for '{product_db['name']}' updated to {new_quantity}.", "success")

    except (ValueError, TypeError) as e:
        flash("Invalid quantity provided. Please enter a valid number.", "error")
        print(f"DEBUG: Error updating cart quantity: {e}")
    except Exception as e:
        flash(f"An unexpected error occurred while updating cart: {e}", "error")
        print(f"ERROR: Exception in update_cart_quantity route: {e}")

    return redirect(url_for('view_cart'))


@app.route('/remove_from_cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    """Removes a single unit of a product from the user's shopping cart. (Old, now mostly replaced by update_cart_quantity action='decrease')"""
    flash("This function is deprecated. Please use the +/- buttons or quantity input to adjust.", "warning")
    return redirect(url_for('view_cart'))


@app.route('/remove_all_from_cart/<product_id>', methods=['POST'])
def remove_all_from_cart(product_id):
    """Removes all units of a specific product from the user's shopping cart."""
    cart = get_or_create_cart()
    if not cart or not cart.get("items"):
        flash("Cart not found or empty.", "error")
        return redirect(url_for('view_cart'))

    cart_items = cart['items'] # Direct access after check

    item_removed_name = "Item"
    original_item = next((item for item in cart_items if str(item['product_id']) == product_id), None)
    if original_item:
        item_removed_name = original_item['name']

    # Filter out the item to be removed
    updated_items = [item for item in cart_items if str(item['product_id']) != product_id]

    try:
        carts_collection.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": updated_items, "updated_at": datetime.utcnow()}}
        )
        flash(f"All '{item_removed_name}' removed from cart.", "warning")
    except Exception as e:
        flash(f"Error clearing item from cart: {e}", "error")
        print(f"MongoDB Update Error in remove_all_from_from_cart: {e}")

    return redirect(url_for('view_cart'))


@app.route('/cart')
def view_cart():
    """Displays the contents of the user's shopping cart."""
    try:
        cart = get_or_create_cart()
        if not cart or not cart.get("items"):
            flash("Your cart is currently empty. Start adding some products!", "info")
            return render_template('cart.html', cart={"items": []}, total_price=0)

        total_price = sum(item['price'] * item['quantity'] for item in cart['items'])
        return render_template('cart.html', cart=cart, total_price=total_price)
    except Exception as e:
        print(f"ERROR: Exception in view_cart route: {e}")
        flash("An error occurred while loading your cart. Please try again.", "error")
        return render_template('cart.html', cart={"items": []}, total_price=0)


@app.route('/reset_cart', methods=['POST'])
def reset_cart():
    """Empties the current user's shopping cart."""
    cart = get_or_create_cart() # Get current cart, whether user-specific or anonymous
    if cart and cart.get('_id'):
        try:
            carts_collection.update_one(
                {"_id": cart["_id"]},
                {"$set": {"items": [], "updated_at": datetime.utcnow()}}
            )
            flash("Your cart has been reset!", "success")
        except Exception as e:
            flash(f"Error resetting cart: {e}", "error")
            print(f"MongoDB Error in reset_cart: {e}")
    else:
        flash("No cart found to reset.", "info")

    return redirect(url_for('view_cart'))

@app.route('/checkout')
@login_required # Users must be logged in to checkout
def checkout():
    """Displays the order summary/bill page based on the current cart."""
    try:
        cart = get_or_create_cart()
        if not cart or not cart.get("items"):
            flash("Your cart is empty or could not be loaded for checkout.", "error")
            return redirect(url_for('view_cart'))

        items_in_cart = cart['items']

        for item in items_in_cart:
            item['subtotal'] = item['price'] * item['quantity']

        overall_total = sum(item['subtotal'] for item in items_in_cart)

        current_time_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S IST')

        return render_template('checkout.html',
                               cart_items=items_in_cart,
                               overall_total=overall_total,
                               now=current_time_str)
    except Exception as e:
        print(f"ERROR: Exception in checkout route: {e}")
        flash("An error occurred during checkout. Please try again.", "error")
        return redirect(url_for('view_cart'))

@app.route('/order_confirmation', methods=['POST'])
@login_required # Only logged-in users can place orders
def order_confirmation():
    """Simulates placing an order, saves it to database, and clears the cart."""
    cart = get_or_create_cart()
    if not cart or not cart.get('items'):
        flash("Your cart is empty. Nothing to order.", "error")
        return redirect(url_for('home'))

    user_id = session.get('user_id')
    if not user_id: # Should not happen with @login_required, but as a safeguard
        flash("User not logged in. Cannot place order.", "error")
        return redirect(url_for('login'))

    items_ordered = cart['items']
    order_total = sum(item['price'] * item['quantity'] for item in items_ordered)
    current_time_utc = datetime.utcnow() # Use UTC for consistent database timestamps

    # Generate a random 4-digit number for the order ID suffix
    random_suffix = random.randint(1000, 9999) # This is the new line

    # Create the order document
    order_document = {
        "user_id": ObjectId(user_id),
        # Store a deep copy of the items to ensure the order snapshot is immutable
        "order_items": [item.copy() for item in items_ordered],
        "total_amount": order_total,
        "order_date": current_time_utc,
        "status": "Pending", # Initial status (e.g., 'Pending', 'Processing', 'Shipped', 'Delivered')
        "shipping_address": "Simulated Address", # Placeholder for real address
        "payment_info": "Simulated Payment Success" # Placeholder for masked payment details
    }

    try:
        # Step 1: Save the order to the orders_collection
        inserted_order = orders_collection.insert_one(order_document)
        print(f"DEBUG: Order saved to DB with ID: {inserted_order.inserted_id}")

        # Step 2: Deduct stock from products collection
        for cart_item in items_ordered:
            # It's good practice to ensure stock doesn't go negative in a real app (transactions, lock)
            products_collection.update_one(
                {"_id": cart_item['product_id']},
                {"$inc": {"stock": -cart_item['quantity']}}
            )

        # Step 3: Clear the user's cart after successful order
        carts_collection.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": [], "updated_at": datetime.utcnow()}} # Clear the cart
        )

        flash("Your order has been placed successfully!", "success")
        return render_template('order_confirmation.html',
                               order_id=str(inserted_order.inserted_id), # Pass actual order ID
                               items_ordered=items_ordered,
                               order_total=order_total,
                               order_time=current_time_utc.strftime('%Y-%m-%d %H:%M:%S IST'), # Display IST time for report
                               random_suffix=random_suffix) # Pass the generated random suffix
    except Exception as e:
        flash(f"Error processing order: {e}", "error")
        print(f"MongoDB Order Processing Error: {e}")
        return redirect(url_for('checkout'))


@app.route('/profile')
@login_required
def profile():
    """Displays a simple user profile page and their past orders."""
    user_id = session.get('user_id')
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('logout'))

    # Fetch user's past orders, sorted by most recent first
    user_orders = orders_collection.find({"user_id": ObjectId(user_id)}).sort("order_date", -1)

    return render_template('profile.html', user=user, user_orders=user_orders)


@app.route('/about')
def about():
    """Displays the About Us page."""
    # User status is implicitly passed via setup_globals
    return render_template('about.html')

@app.route('/contact')
def contact():
    """Displays the Contact Us page."""
    # User status is implicitly passed via setup_globals
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Basic validation
        if not username or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template('register.html', form_data=request.form)

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('register.html', form_data=request.form)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template('register.html', form_data=request.form)

        # Check if username or email already exists
        if users_collection.find_one({"username": username}):
            flash("Username already taken. Please choose another.", "warning")
            return render_template('register.html', form_data=request.form)
        if users_collection.find_one({"email": email}):
            flash("Email already registered. Please use another or login.", "warning")
            return render_template('register.html', form_data=request.form)

        hashed_password = generate_password_hash(password)

        new_user = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "is_admin": False, # New users are not admins by default
            "created_at": datetime.utcnow()
        }

        try:
            users_collection.insert_one(new_user)
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Registration failed: {e}", "error")
            return render_template('register.html', form_data=request.form)

    return render_template('register.html', form_data={})


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if 'user_id' in session:
        flash("You are already logged in.", "info")
        return redirect(url_for('home')) # Redirect if already logged in

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template('login.html', form_data=request.form)

        user = users_collection.find_one({"username": username})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id']) # Store user_id in session
            # session['username'] and session['is_admin'] are set by setup_globals @app.before_request

            # --- Cart Migration Logic ---
            # If there was an anonymous cart, merge or transfer its items to the user's cart
            anon_cart_id = session.pop('cart_id', None)
            if anon_cart_id:
                anon_cart = carts_collection.find_one({"_id": ObjectId(anon_cart_id), "user_id": None})
                if anon_cart and anon_cart.get('items'):
                    user_cart = get_or_create_cart() # This will get or create the logged-in user's cart
                    # Create a dictionary to easily manage existing items by product_id
                    current_user_items_map = {str(item['product_id']): item for item in user_cart.get('items', [])}

                    for anon_item in anon_cart['items']:
                        anon_product_id_str = str(anon_item['product_id'])
                        if anon_product_id_str in current_user_items_map:
                            # If product already in user's cart, add quantities (check stock in a real app)
                            current_user_items_map[anon_product_id_str]['quantity'] += anon_item['quantity']
                        else:
                            # Add new item from anonymous cart to user's cart
                            current_user_items_map[anon_product_id_str] = anon_item

                    # Convert map back to list of items
                    user_cart['items'] = list(current_user_items_map.values())
                    carts_collection.update_one(
                        {"_id": user_cart["_id"]},
                        {"$set": {"items": user_cart['items'], "updated_at": datetime.utcnow()}}
                    )
                    carts_collection.delete_one({"_id": ObjectId(anon_cart_id)}) # Delete the now-merged anonymous cart
                    flash("Your anonymous cart items have been added to your account!", "info")


            flash(f"Welcome, {session.get('username', user['username'])}!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "error")
            return render_template('login.html', form_data=request.form)

    return render_template('login.html', form_data={})

@app.route('/logout')
def logout():
    """Handles user logout."""
    # When a user logs out, we clear their user_id from the session.
    # The anonymous cart ID (if any) is *not* popped here, allowing it to persist,
    # so users can continue shopping as guests if they were doing so before logging in.
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None) # is_admin is derived from user_id, so it automatically gets cleared.

    flash("You have been logged out.", "info")
    return redirect(url_for('home'))


if __name__ == '__main__':
    # When running with 'flask run' from the command line, Flask defaults to debug mode based on FLASK_DEBUG env var
    # If running directly (python app.py), this ensures debug mode is on.
    app.run(debug=True)