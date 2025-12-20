from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

# Browser ko allow karo baat karne ke liye
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/check")
def check_price(url: str, tag: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        # ASIN Nikalo
        match = re.search(r'/([A-Z0-9]{10})', url)
        if not match: return {"error": "Invalid Link"}
        asin = match.group(1)
        
        # Affiliate Link
        affiliate_link = f"https://www.amazon.in/dp/{asin}?tag={tag}"

        # Request bhejo
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200: 
            return {"error": "Amazon Blocked"}

        soup = BeautifulSoup(response.content, "lxml")

        # 1. Title
        title = soup.find("span", attrs={"id": "productTitle"})
        title = title.get_text().strip()[:50] + "..." if title else "Amazon Product"

        # 2. Price
        price = "See Price"
        price_tag = soup.find("span", attrs={"class": "a-price-whole"})
        if price_tag:
            price = "₹" + price_tag.get_text().strip().replace('.', '')

        # 3. Image
        image = "https://placehold.co/200?text=No+Image"
        img_div = soup.find("div", attrs={"id": "imgTagWrapperId"})
        if img_div and img_div.find("img"):
            image = img_div.find("img")["src"]

        return {
            "title": title,
            "price": price,
            "image": image,
            "link": affiliate_link
        }

    except Exception as e:
        return {"error": str(e)}
