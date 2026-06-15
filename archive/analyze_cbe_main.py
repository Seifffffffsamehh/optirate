import requests
from bs4 import BeautifulSoup
import json

url = "https://www.cbe.org.eg/ar/economic-research/statistics/cbe-exchange-rates"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

res = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(res.text, "html.parser")

tables = soup.find_all("table")
if tables:
    for table in tables:
        rows = table.find_all("tr")
        if rows:
            print("Table found. First few rows:")
            for row in rows[:5]:
                print([cell.get_text(strip=True) for cell in row.find_all(["td", "th"])])
else:
    print("No tables.")
