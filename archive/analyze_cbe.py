from bs4 import BeautifulSoup

with open("cbe_dump.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

tables = soup.find_all("table")
print(f"Found {len(tables)} tables")
for i, table in enumerate(tables):
    print(f"Table {i}:")
    for tr in table.find_all("tr")[:2]:
        print(tr.get_text(strip=True, separator=" | "))
    print("-" * 40)
