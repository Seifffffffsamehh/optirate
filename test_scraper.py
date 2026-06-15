import re
from bs4 import BeautifulSoup
from datetime import datetime

CURRENCY_NAME_MAP = {
    "دولار أمريكى": "USD", "دولار أمريكي": "USD",
    "يورو": "EUR",
    "جنيــه إسترليـنى": "GBP", "جنيه إسترلينى": "GBP", "جنيه إسترليني": "GBP",
    "ريال سعودي": "SAR", "ريال سعودى": "SAR",
    "درهم إماراتى": "AED", "درهم إماراتي": "AED",
    "دينار كويتي": "KWD", "دينار كويتى": "KWD",
    "ريال قطري": "QAR", "ريال قطرى": "QAR",
    "ريال عماني": "OMR", "ريال عمانى": "OMR",
    "ين ياباني": "JPY", "ين يابانى": "JPY", "١٠٠ ين يابانى": "JPY", "١٠٠ ين ياباني": "JPY",
    "دولار كندي": "CAD", "دولار كنـدى": "CAD", "دولار كندى": "CAD",
    "دولار أسترالي": "AUD", "دولار اســـترالى": "AUD", "دولار أسترالى": "AUD",
    "اليوان الصينى": "CNY", "يوان صيني": "CNY", "اليوان الصيني": "CNY"
}

def clean_currency_name(text):
    # Remove some common zero-width chars or multiple spaces and tatweel
    text = re.sub(r'[\u0640]', '', text)  # remove tatweel
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def test_parse(html_file):
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    table = soup.find("table")
    results = []
    today = datetime.now().date()
    for row in table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue
        c_name = clean_currency_name(cells[0].get_text(strip=True))
        buy = cells[1].get_text(strip=True)
        sell = cells[2].get_text(strip=True)
        code = CURRENCY_NAME_MAP.get(c_name)
        if not code:
            print(f"Unknown currency: {c_name} (original: {cells[0].get_text(strip=True)})")
            continue
        try:
            rate = float(sell)
        except:
            continue
        results.append({
            "currency": code,
            "rate": rate,
            "date": today.isoformat(),
            "source": "CBE"
        })
    return results

if __name__ == "__main__":
    import requests
    url = "https://www.cbe.org.eg/ar/economic-research/statistics/cbe-exchange-rates"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html",
    }
    res = requests.get(url, headers=headers, timeout=10)
    with open("cbe_main.html", "w", encoding="utf-8") as f:
        f.write(res.text)
    print(test_parse("cbe_main.html"))
