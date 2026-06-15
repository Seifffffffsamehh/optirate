import requests
import time
import subprocess

def test_endpoints():
    endpoints = [
        "http://localhost:5000/api/v2/currency/history/USD",
        "http://localhost:5000/api/v2/currency/predict/USD",
        "http://localhost:5000/api/v2/currency/rates",
        "http://localhost:5000/api/health",
        "http://localhost:5000/api/v3/dashboard/overview"
    ]
    
    for url in endpoints:
        try:
            res = requests.get(url, timeout=5)
            print(f"[{res.status_code}] {url}")
            if res.status_code == 500:
                print(res.text)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

if __name__ == "__main__":
    # start server
    proc = subprocess.Popen(["venv/Scripts/python.exe", "app.py"])
    time.sleep(3)
    test_endpoints()
    proc.terminate()
