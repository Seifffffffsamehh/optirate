import requests
from bs4 import BeautifulSoup

url = "https://www.cbe.org.eg/ar/economic-research/statistics/cbe-exchange-rates"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html",
}

res = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(res.text, "html.parser")
table = soup.find("table")
for row in table.find_all("tr"):
    print([cell.get_text(strip=True) for cell in row.find_all(["td", "th"])])
