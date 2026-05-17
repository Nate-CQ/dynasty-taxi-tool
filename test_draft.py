import requests

r = requests.get(
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/draft",
    params={"season": 2025}
)

data = r.json()
picks = data["picks"]
print(f"Total picks: {len(picks)}")
print("\nFirst 3 picks:")
for pick in picks[:3]:
    print(pick)