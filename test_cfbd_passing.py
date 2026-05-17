import requests
import os
from dotenv import load_dotenv

load_dotenv()

CFBD_KEY = os.getenv("CFBD_API_KEY")
headers = {"Authorization": f"Bearer {CFBD_KEY}"}

r = requests.get(
    "https://api.collegefootballdata.com/stats/player/season",
    headers=headers,
    params={
        "year": 2024,
        "team": "Colorado",
        "category": "passing"
    }
)

for item in r.json():
    print(item["statType"], item["stat"])
print("\n--- RUSHING STATS ---")

r2 = requests.get(
    "https://api.collegefootballdata.com/stats/player/season",
    headers=headers,
    params={
        "year": 2024,
        "team": "Colorado",
        "category": "rushing"
    }
)

for item in r2.json():
    if "Sanders" in item["player"]:
        print(item["player"], item["statType"], item["stat"])