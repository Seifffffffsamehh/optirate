import requests
from bs4 import BeautifulSoup
url = "https://www.cbe.org.eg/ar/economic-research/statistics/cbe-exchange-rates/historical-data"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
with open("cbe_dump.txt", "w", encoding="utf-8") as f:
    f.write(resp.text)
