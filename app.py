from flask import Flask, render_template, request, redirect, session
import pandas as pd
import sqlite3
from transformers import pipeline

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")
app.secret_key = "secret123"

# ---------------- LOAD DATA ----------------
df = pd.read_csv("dataset/amazon.csv")
df.columns = df.columns.str.strip().str.lower()
products = df.to_dict(orient="records")

# ---------------- CLEAN FUNCTIONS ----------------
def clean_price(val):
    try:
        val = str(val).replace("₹", "").replace(",", "").strip()
        return float(val)
    except:
        return 0.0

def clean_float(val, default=4.0):
    try:
        val = str(val).replace(",", "").strip()
        if val in ["", "None", "nan", "|"]:
            return default
        return float(val)
    except:
        return default

def clean_int(val, default=0):
    try:
        val = str(val).replace(",", "").strip()
        if val in ["", "None", "nan", "|"]:
            return default
        return int(float(val))
    except:
        return default

# ---------------- CLEAN PRODUCTS ----------------
for p in products:
    p["product_name"] = str(p.get("product_name", "Unknown"))
    p["category"] = str(p.get("category", "other"))

    p["rating"] = clean_float(p.get("rating", 4))
    p["rating_count"] = clean_int(p.get("rating_count", 100))

    p["discounted_price"] = clean_price(p.get("discounted_price"))
    p["actual_price"] = clean_price(p.get("actual_price"))

    img = p.get("img_link") or p.get("image_link")
    if not img or not str(img).startswith("http"):
        img = "https://via.placeholder.com/300"

    p["img_link"] = img
    p["review_content"] = p.get("review_content") or ""

# ---------------- AI MODEL ----------------
classifier = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment"
)

# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_index INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_name TEXT,
        price REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_index INTEGER,
        user_id INTEGER,
        review TEXT,
        rating REAL
    )""")

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route("/")
def home():
    search = request.args.get("search", "").lower()

    filtered = products

    if search:
        filtered = [
            p for p in products
            if search in p["product_name"].lower()
            or search in p["category"].lower()
        ]

    return render_template("index.html", products=filtered)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        user = c.execute(
            "SELECT id FROM users WHERE username=? AND password=?",
            (u, p)
        ).fetchone()

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
        u = request.form.get("username")
        p = request.form.get("password")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")

# ---------------- PRODUCT PAGE ----------------
@app.route("/product/<int:index>", methods=["GET", "POST"])
def product(index):
    if index >= len(products):
        return "Product not found"

    product = products[index]
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    sentiment = None

    if request.method == "POST":
        if "user_id" not in session:
            return redirect("/login")

        review = request.form.get("review")
        rating = float(request.form.get("rating"))

        c.execute("""
            INSERT INTO reviews (product_index, user_id, review, rating)
            VALUES (?, ?, ?, ?)
        """, (index, session["user_id"], review, rating))

        conn.commit()

        product["rating"] = round((product["rating"] + rating) / 2, 1)
        product["rating_count"] += 1

        sentiment = classifier(review)[0]["label"]

    db_reviews = c.execute("""
        SELECT review, rating FROM reviews
        WHERE product_index=?
        ORDER BY id DESC
    """, (index,)).fetchall()

    conn.close()

    recommendations = sorted(
        [(i, p) for i, p in enumerate(products) if i != index],
        key=lambda x: (x[1]["rating"], x[1]["rating_count"]),
        reverse=True
    )[:12]

    reviews_list = product.get("review_content", "").split("|")

    return render_template(
        "product.html",
        product=product,
        index=index,
        reviews=db_reviews,
        dataset_reviews=reviews_list,
        recommendations=recommendations,
        sentiment=sentiment
    )

# ---------------- CART ----------------
@app.route("/add_to_cart/<int:index>")
def add_to_cart(index):
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("INSERT INTO cart (user_id, product_index) VALUES (?, ?)",
              (session["user_id"], index))

    conn.commit()
    conn.close()

    return redirect("/cart")

@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    rows = c.execute(
        "SELECT product_index FROM cart WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    cart_products = []
    for r in rows:
        i = r[0]
        if 0 <= i < len(products):
            cart_products.append(products[i])

    total = sum(p["discounted_price"] for p in cart_products)

    return render_template("cart.html", cart_products=cart_products, total=total)

# ---------------- BUY ----------------
@app.route("/buy/<int:index>", methods=["GET", "POST"])
def buy(index):
    if "user_id" not in session:
        return redirect("/login")

    product = products[index]

    if request.method == "POST":
        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("""
            INSERT INTO orders (user_id, product_name, price)
            VALUES (?, ?, ?)
        """, (session["user_id"], product["product_name"], product["discounted_price"]))

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

    rows = c.execute(
        "SELECT product_name, price FROM orders WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template("orders.html", orders=rows)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)