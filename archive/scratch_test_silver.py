import requests
from bs4 import BeautifulSoup
import re

url = "https://dahabmasr.com/silver-price-today-ar"
resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
print("Status Code:", resp.status_code)
print("Length of HTML:", len(resp.text))

soup = BeautifulSoup(resp.text, 'html.parser')

# Let's try to print parts of the page that contain silver prices
# Usually it's in a table or some specific div
tables = soup.find_all('table')
for i, t in enumerate(tables):
    print(f"Table {i}:", t.text.strip()[:200])

# Just dump all text with numbers to see what we're working with
print("Looking for prices in raw text...")
text = soup.get_text(separator=' ')
matches = re.findall(r"([\d,]+\.?\d*)\s*(?:جنيه|ج\.م|EGP)?", text)
print("Raw matches found:", matches[:20])

# What about divs with specific classes?
# Print the first few hundred chars of the body
print("Body start:", str(soup.body)[:500])
