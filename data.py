import requests


def get_nfl_player(name: str) -> dict:
    """
    Pulls player info from Sleeper API by full name.
    Returns player dict with age, position, team, college.
    Uses legal full name for matching.
    """
    url = "https://api.sleeper.app/v1/players/nfl"
    r = requests.get(url)
    players = r.json()
    name_lower = name.lower()
    for pid, p in players.items():
        full = f"{p.get('first_name','')} {p.get('last_name','')}".lower()
        if full == name_lower:
            return p
    return {}


def get_nfl_team_abbreviations() -> list:
    """
    Returns a list of all current NFL team abbreviations from ESPN.
    Useful for validating user input in the Streamlit UI.
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
    r = requests.get(url)
    teams = r.json()["sports"][0]["leagues"][0]["teams"]
    return [t["team"]["abbreviation"] for t in teams]