import requests
url = "https://www.cbe.org.eg/ar/economic-research/statistics/cbe-exchange-rates/historical-data"
res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
with open("cbe_dump.html", "w", encoding="utf-8") as f:
    f.write(res.text)
