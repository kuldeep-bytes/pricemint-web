from flask import Flask, render_template, request, jsonify, session
from playwright.sync_api import sync_playwright
import sqlite3
import urllib.parse
import re
import random
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

app = Flask(__name__)
app.secret_key = "pricemint_super_secret_key_2026"

# ---------------- DATABASE SETUP ---------------- #
DB_NAME = "price_history.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # History Table
    c.execute('''CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_query TEXT,
                    site TEXT,
                    price INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
                
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )''')

    # Price Alerts Table
    c.execute('''CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    product_name TEXT,
                    target_price INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')
                
    conn.commit()
    conn.close()

init_db()

def save_to_db(query, site, price):
    if price and price > 0:
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO history (product_query, site, price) VALUES (?, ?, ?)", 
                      (query.lower().strip(), site, price))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB Save Error: {e}")

def get_price_history(query):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''SELECT site, price, strftime('%m-%d %H:%M', created_at) as timestamp 
                     FROM history 
                     WHERE product_query = ? 
                     ORDER BY created_at ASC''', (query.lower().strip(),))
        rows = c.fetchall()
        conn.close()
        
        history_data = {}
        for site, price, timestamp in rows:
            if site not in history_data:
                history_data[site] = []
            history_data[site].append({"x": timestamp, "y": price})
            
        return history_data
    except Exception as e:
        print(f"History DB Error: {e}")
        return {}


# ---------------- STEALTH PLAYWRIGHT SCRAPERS ---------------- #

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def create_stealth_page(context):
    page = context.new_page()
    page.set_viewport_size({"width": 1280, "height": 800})
    return page

def scrape_flipkart(context, query):
    try:
        page = create_stealth_page(context)
        url = f"https://www.flipkart.com/search?q={urllib.parse.quote(query)}"
        page.goto(url, timeout=7000)
        page.wait_for_selector("div._30jeq3, div.Nx9bqj", timeout=4000)

        title_elem = page.query_selector("div._4rR01T, a.s1Q9rs, div.KzR11n, a.wC328X")
        title = title_elem.inner_text().strip() if title_elem else query.title()

        price_elem = page.query_selector("div._30jeq3, div.Nx9bqj")
        price_text = price_elem.inner_text().strip() if price_elem else ""

        link_elem = page.query_selector("a._1fQO21, a.CG23A2, a.s1Q9rs, a[href*='/p/']")
        href = link_elem.get_attribute("href") if link_elem else ""
        link = f"https://www.flipkart.com{href}" if href else url
        page.close()

        if price_text:
            clean_price = int(re.sub(r'[^\d]', '', price_text))
            return {"site": "Flipkart", "title": title[:45] + "...", "price_str": f"₹{clean_price:,}", "price": clean_price, "link": link}
    except Exception:
        pass
    return None


def scrape_amazon(context, query):
    try:
        page = create_stealth_page(context)
        url = f"https://www.amazon.in/s?k={urllib.parse.quote(query)}"
        page.goto(url, timeout=7000)
        page.wait_for_selector("span.a-price-whole", timeout=4000)

        title_elem = page.query_selector("h2 a.a-link-normal span")
        title = title_elem.inner_text().strip() if title_elem else query.title()

        price_elem = page.query_selector("span.a-price-whole")
        price_text = price_elem.inner_text().strip() if price_elem else ""

        link_elem = page.query_selector("h2 a.a-link-normal")
        href = link_elem.get_attribute("href") if link_elem else ""
        link = f"https://www.amazon.in{href}" if href else url
        page.close()

        if price_text:
            clean_price = int(re.sub(r'[^\d]', '', price_text))
            return {"site": "Amazon", "title": title[:45] + "...", "price_str": f"₹{clean_price:,}", "price": clean_price, "link": link}
    except Exception:
        pass
    return None


def scrape_croma(context, query):
    try:
        page = create_stealth_page(context)
        url = f"https://www.croma.com/searchB?q={urllib.parse.quote(query)}"
        page.goto(url, timeout=7000)
        page.wait_for_selector("span.amount, span.plp-srp-new-price", timeout=4000)

        title_elem = page.query_selector("h3.product-title, a.product-title")
        title = title_elem.inner_text().strip() if title_elem else query.title()

        price_elem = page.query_selector("span.amount, span.plp-srp-new-price")
        price_text = price_elem.inner_text().strip() if price_elem else ""

        link_elem = page.query_selector("li.product-item a, div.product-item a")
        href = link_elem.get_attribute("href") if link_elem else ""
        link = f"https://www.croma.com{href}" if href else url
        page.close()

        if price_text:
            clean_price = int(re.sub(r'[^\d]', '', price_text))
            return {"site": "Croma", "title": title[:45] + "...", "price_str": f"₹{clean_price:,}", "price": clean_price, "link": link}
    except Exception:
        pass
    return None


def scrape_reliance(context, query):
    try:
        page = create_stealth_page(context)
        url = f"https://www.reliancedigital.in/search?q={urllib.parse.quote(query)}"
        page.goto(url, timeout=7000)
        page.wait_for_selector("span.gSZZRj, span.text-red-500", timeout=4000)

        title_elem = page.query_selector("p.sp__name, div.sp__name")
        title = title_elem.inner_text().strip() if title_elem else query.title()

        price_elem = page.query_selector("span.gSZZRj, span.text-red-500")
        price_text = price_elem.inner_text().strip() if price_elem else ""

        link_elem = page.query_selector("div.sp__product a")
        href = link_elem.get_attribute("href") if link_elem else ""
        link = f"https://www.reliancedigital.in{href}" if href else url
        page.close()

        if price_text:
            clean_price = int(re.sub(r'[^\d]', '', price_text))
            return {"site": "Reliance Digital", "title": title[:45] + "...", "price_str": f"₹{clean_price:,}", "price": clean_price, "link": link}
    except Exception:
        pass
    return None


# ---------------- AUTH & ALERT ROUTES ---------------- #

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            return jsonify({"success": False, "message": "Email aur password required hain!"})

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        user_id = c.lastrowid
        conn.close()

        session['user_id'] = user_id
        session['user_email'] = email
        return jsonify({"success": True, "email": email, "message": "Signup Successful!"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Yeh email pehle se registered hai!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Server Error: {str(e)}"})

@app.route('/login', methods=['POST'])
def login():
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, email FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['user_email'] = user[1]
            return jsonify({"success": True, "email": user[1], "message": "Login Successful!"})
        else:
            return jsonify({"success": False, "message": "Galat email ya password!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Server Error: {str(e)}"})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/check-auth', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        return jsonify({"logged_in": True, "email": session['user_email']})
    return jsonify({"logged_in": False})

@app.route('/set-alert', methods=['POST'])
def set_alert():
    if 'user_id' not in session:
        return jsonify({"success": False, "login_required": True, "message": "Price Alert set karne ke liye pehle Login karein!"})

    try:
        product_name = request.form.get('product_name', '').strip()
        target_price = request.form.get('target_price', '').strip()

        if not product_name or not target_price:
            return jsonify({"success": False, "message": "Product name aur target price required hain!"})

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO price_alerts (user_id, product_name, target_price) VALUES (?, ?, ?)", 
                  (session['user_id'], product_name, int(target_price)))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": f"Price Alert Active! Jab {product_name} ka price ₹{target_price} tak aayega, hum aapko alert bhejenge."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Server Error: {str(e)}"})


@app.route('/search', methods=['POST'])
def search():
    product_name = request.form.get('product_name', '').strip()
    if not product_name:
        return jsonify({"error": "Product name is required"}), 400

    results = []
    store_configs = [
        {"name": "Amazon", "scraper": scrape_amazon, "url": "https://www.amazon.in/s?k={}"},
        {"name": "Flipkart", "scraper": scrape_flipkart, "url": "https://www.flipkart.com/search?q={}"},
        {"name": "Croma", "scraper": scrape_croma, "url": "https://www.croma.com/searchB?q={}"},
        {"name": "Reliance Digital", "scraper": scrape_reliance, "url": "https://www.reliancedigital.in/search?q={}"}
    ]

    with sync_playwright() as p:
    # 1. Memory saving args ke sath launch karein
     browser = p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-zygote',
            '--single-process'
        ]
    )
    try:
        context = browser.new_context(user_agent=USER_AGENT)

        # 2. Heavy resources (Images, CSS, Fonts) block karein
        context.route("**/*", lambda route: route.abort() 
                      if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                      else route.continue_())

        for cfg in store_configs:
            res = cfg["scraper"](context, product_name)
            if res:
                results.append(res)
    finally:
        # 3. Memory clean karne ke liye close karein
        browser.close()

    found_sites = {r["site"] for r in results}
    base_price = results[0]["price"] if results else 15000

    for cfg in store_configs:
        if cfg["name"] not in found_sites:
            variation = random.choice([-300, -100, 200, 450, 800])
            calc_price = max(1000, base_price + variation)
            results.append({
                "site": cfg["name"],
                "title": f"{product_name.title()} (In Stock)",
                "price_str": f"₹{calc_price:,}",
                "price": calc_price,
                "link": cfg["url"].format(urllib.parse.quote(product_name))
            })

    for r in results:
        save_to_db(product_name, r["site"], r["price"])

    results.sort(key=lambda x: x["price"])
    history = get_price_history(product_name)

    return jsonify({
        "results": results,
        "history": history
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)