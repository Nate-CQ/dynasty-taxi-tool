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
        "year": 2023,
        "team": "Notre Dame",
        "category": "receiving"
    }
)

for item in r.json():
    print(item["player"], item["position"], item["statType"], item["stat"])