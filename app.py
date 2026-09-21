import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)  # Frontend connection ke liye CORS enable kar diya hai

# Common Request Headers (Anti-blocking/Bot prevention ke liye)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive'
}

def clean_price(price_str):
    """ Price string (e.g. '₹14,999') ko integer/float me convert karta hai """
    if not price_str:
        return None
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None

# ==================== SCRAPERS ====================

def scrape_amazon(query):
    try:
        url = f"https://www.amazon.in/s?k={requests.utils.quote(query)}"
        response = requests.get(url, headers=HEADERS, timeout=7)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('.s-result-item[data-component-type="s-search-result"]')
        
        for item in items:
            title_el = item.select_one('h2 a span')
            price_el = item.select_one('.a-price-whole')
            link_el = item.select_one('h2 a')
            img_el = item.select_one('img.s-image')

            if title_el and price_el and link_el:
                price_val = clean_price(price_el.text)
                if price_val:
                    href = link_el.get('href', '')
                    full_url = f"https://www.amazon.in{href}" if href.startswith('/') else href
                    return {
                        'site': 'Amazon',
                        'title': title_el.text.strip(),
                        'price': price_val,
                        'display_price': f"₹{price_val:,.0f}",
                        'url': full_url,
                        'image': img_el.get('src') if img_el else ''
                    }
    except Exception as e:
        print(f"Amazon Scrape Error: {e}")
    return None


def scrape_flipkart(query):
    try:
        url = f"https://www.flipkart.com/search?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=HEADERS, timeout=7)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Flipkart layout 1 (Mobiles/Laptops) & layout 2 (General products)
        products = soup.select('div._1AtVbE, div._75Wvvf, div.cPHRSc')
        
        for prod in products:
            title_el = prod.select_one('div._4rR01T, a.IRw96b, a.wU2fTh, div.Kz_R1r')
            price_el = prod.select_one('div._30jeq3, div._31q2y9, div.Nx9bqj')
            link_el = prod.select_one('a._1fQ331, a._2rp35f, a')
            img_el = prod.select_one('img._396cs4, img._2r_T1I, img.DA155')

            if title_el and price_el:
                price_val = clean_price(price_el.text)
                if price_val:
                    href = link_el.get('href', '') if link_el else ''
                    full_url = f"https://www.flipkart.com{href}" if href.startswith('/') else href
                    return {
                        'site': 'Flipkart',
                        'title': title_el.text.strip(),
                        'price': price_val,
                        'display_price': f"₹{price_val:,.0f}",
                        'url': full_url,
                        'image': img_el.get('src') if img_el else ''
                    }
    except Exception as e:
        print(f"Flipkart Scrape Error: {e}")
    return None


def scrape_croma(query):
    try:
        url = f"https://www.croma.com/searchB?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=HEADERS, timeout=7)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        product = soup.select_one('li.product-item, div.product-item')
        if product:
            title_el = product.select_one('h3, .product-title')
            price_el = product.select_one('.amount, .new-price, .pdpPrice')
            link_el = product.select_one('a')
            img_el = product.select_one('img')

            if title_el and price_el:
                price_val = clean_price(price_el.text)
                if price_val:
                    href = link_el.get('href', '') if link_el else ''
                    full_url = f"https://www.croma.com{href}" if href.startswith('/') else href
                    return {
                        'site': 'Croma',
                        'title': title_el.text.strip(),
                        'price': price_val,
                        'display_price': f"₹{price_val:,.0f}",
                        'url': full_url,
                        'image': img_el.get('src') if img_el else ''
                    }
    except Exception as e:
        print(f"Croma Scrape Error: {e}")
    return None


def scrape_reliance(query):
    try:
        url = f"https://www.reliancedigital.in/search?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=HEADERS, timeout=7)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        product = soup.select_one('div.sp, div.product-card')
        if product:
            title_el = product.select_one('p.sp__name, .product-title')
            price_el = product.select_one('span.gspPrice, .text-price')
            link_el = product.select_one('a')
            img_el = product.select_one('img')

            if title_el and price_el:
                price_val = clean_price(price_el.text)
                if price_val:
                    href = link_el.get('href', '') if link_el else ''
                    full_url = f"https://www.reliancedigital.in{href}" if href.startswith('/') else href
                    return {
                        'site': 'Reliance Digital',
                        'title': title_el.text.strip(),
                        'price': price_val,
                        'display_price': f"₹{price_val:,.0f}",
                        'url': full_url,
                        'image': img_el.get('src') if img_el else ''
                    }
    except Exception as e:
        print(f"Reliance Scrape Error: {e}")
    return None

# ==================== MAIN API ROUTE ====================

@app.route('/api/compare', methods=['GET', 'POST'])
def compare_prices():
    query = ""
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        query = data.get('query', '')
    else:
        query = request.args.get('query', '')

    query = query.strip()
    if not query:
        return jsonify({'status': 'error', 'message': 'Product name or URL is required!'}), 400

    # ThreadPoolExecutor se sabhi websites ko parallelly scrape karenge (fast response)
    scrapers = [scrape_amazon, scrape_flipkart, scrape_croma, scrape_reliance]
    results = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_scraper = {executor.submit(scraper, query): scraper for scraper in scrapers}
        for future in as_completed(future_to_scraper):
            try:
                res = future.result()
                if res:
                    results.append(res)
            except Exception as exc:
                print(f"Scraper error: {exc}")

    # Aggressive / Incremental Sorting (Lowest price top par aayega)
    results.sort(key=lambda x: x['price'])

    # Top product par "Lowest Price / Best Deal" tag set kar dein
    if results:
        results[0]['is_best_deal'] = True

    return jsonify({
        'status': 'success',
        'query': query,
        'count': len(results),
        'results': results
    })

@app.route('/')
def home():
    return jsonify({'status': 'online', 'message': 'PriceMint API Server is Running!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
