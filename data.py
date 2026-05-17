import requests
import os
from dotenv import load_dotenv

load_dotenv()

CFBD_KEY = os.getenv("CFBD_API_KEY")

def get_nfl_player(name: str) -> dict:
    """Pulls player info from Sleeper API by full name."""
    url = "https://api.sleeper.app/v1/players/nfl"
    r = requests.get(url)
    players = r.json()
    name_lower = name.lower()
    for pid, p in players.items():
        full = f"{p.get('first_name','')} {p.get('last_name','')}".lower()
        if full == name_lower:
            return p
    return {}

def get_college_stats(name: str) -> dict:
    """Pulls college receiving/rushing stats from College Football Data API."""
    url = "https://api.collegefootballdata.com/player/search"
    headers = {"Authorization": f"Bearer {CFBD_KEY}"}
    r = requests.get(url, headers=headers, params={"searchTerm": name})
    results = r.json()
    if results:
        return results[0]
    return {}

def get_dynasty_value(name: str) -> dict:
    """Pulls current dynasty trade value from FantasyCalc."""
    url = "https://api.fantasycalc.com/values/current"
    params = {"isDynasty": "true", "numQbs": "1"}
    r = requests.get(url, params=params)
    players = r.json()
    name_lower = name.lower()
    for p in players:
        if p.get("player", {}).get("name", "").lower() == name_lower:
            return p
    return {}

def get_player_profile(name: str) -> dict:
    """Combines all sources into one player profile."""
    nfl = get_nfl_player(name)
    college = get_college_stats(name)
    dynasty = get_dynasty_value(name)

    return {
        "name": name,
        "age": nfl.get("age"),
        "position": nfl.get("position"),
        "team": nfl.get("team"),
        "college": nfl.get("college"),
        "draft_round": nfl.get("practice_description"),
        "dynasty_value": dynasty.get("value"),
        "college_info": college
    }

# Test it
profile = get_player_profile("Malik Nabers")
print(profile)