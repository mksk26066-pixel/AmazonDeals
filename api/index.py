from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_price(price_str):
    if not price_str: return 0
    # Remove non-numeric characters except dot
    clean = re.sub(r'[^\d.]', '', str(price_str))
    try:
        return float(clean)
    except:
        return 0

@app.get("/api/check")
def check_price(url: str, tag: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        # 1. Open URL (Handle Short Links)
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code != 200: 
            return {"error": "Link Blocked or Invalid"}

        final_url = response.url

        # 2. Extract ASIN
        match = re.search(r'/dp/([A-Z0-9]{10})', final_url)
        if not match: match = re.search(r'/gp/product/([A-Z0-9]{10})', final_url)
        if not match: match = re.search(r'/([A-Z0-9]{10})', final_url)

        if not match: return {"error": "Product ID Not Found"}
        asin = match.group(1)
        
        # Affiliate Link
        affiliate_link = f"https://www.amazon.in/dp/{asin}?tag={tag}"

        # 3. Parse HTML
        soup = BeautifulSoup(response.content, "lxml")

        # --- Title ---
        title_elem = soup.find("span", attrs={"id": "productTitle"})
        title = title_elem.get_text().strip()[:65] + "..." if title_elem else "Amazon Deal"

        # --- Image ---
        image = "https://placehold.co/200?text=No+Image"
        img_div = soup.find("div", attrs={"id": "imgTagWrapperId"})
        if img_div and img_div.find("img"): 
            image = img_div.find("img")["src"]
        else:
            landing_img = soup.find("img", attrs={"id": "landingImage"})
            if landing_img: image = landing_img["src"]

        # --- Price Logic ---
        price_tag = soup.find("span", attrs={"class": "a-price-whole"})
        if not price_tag: price_tag = soup.find("span", attrs={"class": "a-offscreen"})
        
        selling_price_str = "Check"
        selling_price_val = 0
        
        if price_tag:
            raw_price = price_tag.get_text().strip().replace('.', '')
            selling_price_str = "₹" + raw_price if "₹" not in raw_price else raw_price
            selling_price_val = clean_price(selling_price_str)

        # --- MRP & Discount Logic ---
        mrp_str = ""
        discount_str = ""
        
        mrp_tag = soup.find("span", attrs={"class": "a-text-price"})
        if mrp_tag:
            mrp_inner = mrp_tag.find("span", attrs={"class": "a-offscreen"})
            if mrp_inner:
                mrp_str = mrp_inner.get_text().strip()
                mrp_val = clean_price(mrp_str)
                
                # Calculate % Off
                if mrp_val > selling_price_val and mrp_val > 0:
                    off = int(((mrp_val - selling_price_val) / mrp_val) * 100)
                    if off > 0:
                        discount_str = f"-{off}%"

        # --- COUPON CHECK (Important) ---
        coupon_text = ""
        # Amazon pe coupon ka text alag-alag jagah hota hai
        coupon_elem = soup.find("label", string=re.compile(r"Apply .* coupon"))
        if not coupon_elem:
            coupon_elem = soup.find("span", class_="promoPriceBlockMessage")
        
        if coupon_elem:
            full_text = coupon_elem.get_text().strip()
            # Extract Amount (e.g. ₹50 or 5%)
            amount_match = re.search(r'(₹\d+|SAVE \d+|\d+%)', full_text)
            if amount_match:
                coupon_text = f"Apply {amount_match.group(0)} Coupon"
            else:
                coupon_text = "Coupon Available"

        # --- BANK OFFER CHECK ---
        bank_offer = False
        # Page text me 'Bank Offer' dhoondo
        page_text = soup.get_text()
        if "Bank Offer" in page_text or "Partner Offers" in page_text:
            bank_offer = True

        return {
            "title": title,
            "price": selling_price_str,
            "mrp": mrp_str,
            "discount": discount_str,
            "coupon": coupon_text,    # Frontend uses this
            "bank_offer": bank_offer, # Frontend uses this
            "image": image,
            "link": affiliate_link
        }

    except Exception as e:
        return {"error": str(e)}
