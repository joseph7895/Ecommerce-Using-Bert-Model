from flask import Flask, render_template, request, redirect, session
import pandas as pd
import sqlite3
import os
import requests

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")
app.secret_key = "secret123"

# ---------------- LOAD DATA ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, "Dataset", "amazon.csv")
if not os.path.exists(csv_path):
    csv_path = os.path.join(BASE_DIR, "dataset", "amazon.csv")
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip().str.lower()

products = df.to_dict(orient="records")

# ---------------- CLEAN DATA ----------------
def clean_price(val):
    try:
        val = str(val)
        val = val.replace('₹', '').replace(',', '').strip()
        return float(val) if val else 0
    except:
        return 0

for p in products:
    p['img_link'] = str(p.get('img_link') or "").strip()

    if not p['img_link'].startswith("http"):
        p['img_link'] = "https://via.placeholder.com/150"

    p['reviews'] = p.get('review_content') or ""

    try:
        p['rating'] = float(p.get('rating', 4))
    except:
        p['rating'] = 4.0

    try:
        p['rating_count'] = int(p.get('rating_count', 100))
    except:
        p['rating_count'] = 100

    p['discounted_price'] = clean_price(p.get('discounted_price'))
    p['actual_price'] = clean_price(p.get('actual_price'))

# ---------------- HUGGING FACE INFERENCE API ----------------
API_URL = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english"

def query_sentiment(text):
    headers = {}
    token = os.environ.get("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=5)
        result = response.json()
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            sorted_predictions = sorted(result[0], key=lambda x: x['score'], reverse=True)
            return sorted_predictions[0]['label']
    except Exception as e:
        print("HF Inference API error:", e)
    
    # Graceful fallback: Rule-based sentiment analysis
    lower_text = text.lower()
    positive_words = ['good', 'great', 'love', 'perfect', 'awesome', 'nice', 'excellent', 'happy', 'best', 'durable', 'fast']
    pos_count = sum(1 for w in positive_words if w in lower_text)
    negative_words = ['bad', 'hate', 'worst', 'broken', 'defect', 'fail', 'poor', 'slow', 'disappoint', 'return']
    neg_count = sum(1 for w in negative_words if w in lower_text)
    return "POSITIVE" if pos_count >= neg_count else "NEGATIVE"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY, user_id INTEGER, product_index INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, product_name TEXT, price REAL)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_index INTEGER,
            user_id INTEGER,
            review TEXT,
            rating REAL
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route("/")
def home():
    search = request.args.get("search", "")
    category = request.args.get("category", "")

    filtered = products

    if search:
        filtered = [p for p in filtered if search.lower() in str(p.get('product_name', '')).lower()]

    if category:
        filtered = [p for p in filtered if category.lower() in str(p.get('category', '')).lower()]

    return render_template("index.html", products=filtered)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        user = c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p)).fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/")
        else:
            return "Invalid login"

    return render_template("login.html")

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")

# ---------------- PRODUCT ----------------
@app.route("/product/<int:index>", methods=["GET", "POST"])
def product(index):
    if index >= len(products):
        return "Product not found"

    product = products[index]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    sentiment = None

    if request.method == "POST":
        review = request.form.get("review")
        rating = request.form.get("rating")

        if "user_id" not in session:
            return redirect("/login")

        if review and rating:
            rating = float(rating)

            # store review
            c.execute("""
                INSERT INTO reviews (product_index, user_id, review, rating)
                VALUES (?, ?, ?, ?)
            """, (index, session["user_id"], review, rating))

            conn.commit()

            # update rating
            product['rating'] = round((product['rating'] + rating) / 2, 1)
            product['rating_count'] += 1

            # ---------------- DISTILBERT SENTIMENT ----------------
            sentiment = query_sentiment(review)

    # fetch reviews
    db_reviews = c.execute("""
        SELECT review, rating FROM reviews
        WHERE product_index=?
        ORDER BY id DESC
    """, (index,)).fetchall()

    conn.close()

    # recommendations
    recommendations = sorted(
        [(i, p) for i, p in enumerate(products) if i != index],
        key=lambda x: (
            x[1].get('rating', 0),
            x[1].get('rating_count', 0)
        ),
        reverse=True
    )[:12]

    # Split dataset reviews by comma safely
    dataset_reviews = [r.strip() for r in product.get('reviews', '').split(',') if r.strip()]

    return render_template("product.html",
                           product=product,
                           recommendations=recommendations,
                           sentiment=sentiment,
                           index=index,
                           reviews=db_reviews,
                           dataset_reviews=dataset_reviews)

# ---------------- CART ----------------
@app.route("/add_to_cart/<int:index>")
def add_to_cart(index):
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO cart (user_id, product_index) VALUES (?, ?)", (session["user_id"], index))
    conn.commit()
    conn.close()

    return redirect("/cart")

@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    rows = c.execute("SELECT product_index FROM cart WHERE user_id=?", (session["user_id"],)).fetchall()
    conn.close()

    cart_products = []
    for row in rows:
        idx = row[0]
        if idx < len(products):
            p = products[idx].copy()
            p['original_index'] = idx
            cart_products.append(p)
            
    total = sum(float(p.get('discounted_price', 0)) for p in cart_products)

    return render_template("cart.html", cart_products=cart_products, total=total)

# ---------------- BUY ----------------
@app.route("/buy/<int:index>", methods=["GET", "POST"])
def buy(index):
    if "user_id" not in session:
        return redirect("/login")

    if index >= len(products):
        return "Product not found"

    product = products[index]

    if request.method == "POST":
        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("INSERT INTO orders (user_id, product_name, price) VALUES (?, ?, ?)",
                  (session["user_id"], product['product_name'], product['discounted_price']))

        conn.commit()
        conn.close()

        return redirect("/orders")

    return render_template("buy.html", product=product)

# ---------------- ORDERS ----------------
@app.route("/orders")
def orders():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    rows = c.execute("SELECT product_name, price FROM orders WHERE user_id=?", (session["user_id"],)).fetchall()
    conn.close()

    return render_template("orders.html", orders=rows)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)