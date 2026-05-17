import requests
import os
import math
from dotenv import load_dotenv

load_dotenv()

CFBD_KEY = os.getenv("CFBD_API_KEY")


# ── COLLEGE PASSING STATS (MOST RECENT SEASON ONLY) ───────────

def get_college_passing_stats(player_name: str, college: str) -> dict:
    """
    Pulls the most recent college passing season for a QB from CFBD.
    Only uses the most recent season to account for transfer portal.
    Requires minimum 100 attempts to filter out garbage time QBs.
    Returns a single dict with passing stats for that season.
    """
    headers = {"Authorization": f"Bearer {CFBD_KEY}"}
    stats_url = "https://api.collegefootballdata.com/stats/player/season"

    for year in range(2024, 2018, -1):
        r = requests.get(stats_url, headers=headers, params={
            "year": year,
            "team": college,
            "category": "passing"
        })

        results = r.json()

        att = 0
        completions = 0
        yds = 0
        tds = 0
        ints = 0
        pct = 0
        ypa = 0
        found = False

        for s in results:
            name = s.get("player", "")
            stat_type = s.get("statType")
            val = float(s.get("stat", 0))

            if player_name.lower() not in name.lower():
                continue

            found = True

            if stat_type == "ATT":
                att = val
            elif stat_type == "COMPLETIONS":
                completions = val
            elif stat_type == "YDS":
                yds = val
            elif stat_type == "TD":
                tds = val
            elif stat_type == "INT":
                ints = val
            elif stat_type == "PCT":
                pct = val
            elif stat_type == "YPA":
                ypa = val

        if found and att >= 100:
            return {
                "year": year,
                "attempts": att,
                "completions": completions,
                "yards": yds,
                "tds": tds,
                "ints": ints,
                "completion_pct": pct,
                "ypa": ypa,
                "td_int_ratio": round(tds / ints, 4) if ints > 0 else tds
            }

    return {}


# ── S-CURVE HELPER ────────────────────────────────────────────

def sigmoid(value: float, midpoint: float, steepness: float = 10) -> float:
    """
    Applies an S-curve to a raw value.
    Midpoint is the value that maps to 0.5.
    Steepness controls how sharply the curve rises.
    Returns a 0-1 score.
    """
    exponent = -steepness * (value - midpoint)
    return round(1 / (1 + math.exp(exponent)), 4)


# ── QB PRODUCTION COMPOSITE ───────────────────────────────────

def score_qb_production(stats: dict) -> float:
    """
    Composite QB production score from three components.
    Each component scored 0-1 using S-curve anchored to historical averages.
    Components averaged equally into one final production score.

    Historical college averages used as S-curve midpoints:
    - YPA midpoint: 7.5
    - TD:INT ratio midpoint: 2.5
    - Completion % midpoint: 0.62
    """
    if not stats:
        return 0

    ypa_score = sigmoid(stats.get("ypa", 0), midpoint=7.5, steepness=0.8)
    td_int_score = sigmoid(stats.get("td_int_ratio", 0), midpoint=2.5, steepness=0.5)
    comp_pct_score = sigmoid(stats.get("completion_pct", 0), midpoint=0.62, steepness=15)

    composite = round((ypa_score + td_int_score + comp_pct_score) / 3, 4)
    return composite


# ── AGE AT ENTRY ──────────────────────────────────────────────

def score_age_qb(age: int) -> float:
    """
    Scores age on a 0-1 scale based on QB dynasty age curves.
    QBs peak later than skill positions so the curve is wider.
    Age 21 or younger = 1.0, age 27 or older = 0.0.
    Linear scale between 21 and 27.
    """
    if age <= 21:
        return 1.0
    elif age >= 27:
        return 0.0
    else:
        return round((27 - age) / (27 - 21), 4)


# ── COLLEGE DOMINATOR (QB) ────────────────────────────────────

def score_qb_dominator(stats: dict) -> float:
    """
    Measures how much of the team offense ran through this QB.
    Uses passing yards as a proxy for offensive involvement.
    S-curve anchored at 4000 yards (strong college starter).
    Returns a 0-1 score.
    """
    if not stats:
        return 0

    passing_yards = stats.get("yards", 0)
    if passing_yards == 0:
        return 0

    return sigmoid(passing_yards / 4000, midpoint=1.0, steepness=3)


# ── LANDING SPOT (QB) ─────────────────────────────────────────

def get_espn_team_id_map() -> dict:
    """
    Pulls all NFL teams from ESPN API.
    Returns dict of abbreviation -> team ID.
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
    r = requests.get(url)
    teams = r.json()["sports"][0]["leagues"][0]["teams"]
    return {t["team"]["abbreviation"]: t["team"]["id"] for t in teams}


def get_team_points_per_game(team_id: int, season: int = 2024) -> float:
    """
    Pulls total points per game for a team from ESPN API.
    Used for QB landing spot since scoring offense reflects
    real support around a QB, not just raw passing volume.
    Returns points per game as float, or 0 if not found.
    Note: landing spot weight is intentionally low (15%) because
    situational context is handled by the LLM analysis layer.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/statistics"
    r = requests.get(url, params={"season": season})
    categories = r.json()["results"]["stats"]["categories"]
    for category in categories:
        if category["name"] == "passing":
            for stat in category["stats"]:
                if stat["name"] == "totalPointsPerGame":
                    return stat["value"]
    return 0


def score_landing_spot_qb(nfl_team: str) -> float:
    """
    Scores QB landing spot based on 2024 team points per game from ESPN.
    Points per game reflects real offensive support around a QB.
    Weight intentionally reduced to 15% since depth chart situation
    and starter competition are handled by the LLM analysis layer.
    Returns 0.5 if team not found.
    """
    team_id_map = get_espn_team_id_map()

    if nfl_team not in team_id_map:
        return 0.5

    team_ppg = {}
    for abbr, tid in team_id_map.items():
        ppg = get_team_points_per_game(tid)
        if ppg > 0:
            team_ppg[abbr] = ppg

    if nfl_team not in team_ppg:
        return 0.5

    sorted_teams = sorted(team_ppg.items(), key=lambda x: x[1], reverse=True)
    rank = next((i for i, (t, _) in enumerate(sorted_teams) if t == nfl_team), 16)

    return round(1 - (rank / 31), 4)


# ── FINAL SCORE ───────────────────────────────────────────────

def score_qb(name: str, college: str, age: int, nfl_team: str) -> dict:
    """
    Combines all four factors into a final weighted dynasty score for 2QB TEP QB rookie draft.
    Weights: production 45%, age 25%, dominator 15%, landing spot 15%.
    Landing spot weight reduced because situational context is handled by LLM layer.
    """
    stats = get_college_passing_stats(name, college)

    production = score_qb_production(stats)
    age_score = score_age_qb(age)
    dominator = score_qb_dominator(stats)
    landing = score_landing_spot_qb(nfl_team)

    final_score = round(
        (production * 0.45) +
        (age_score * 0.25) +
        (dominator * 0.15) +
        (landing * 0.15),
        4
    )

    return {
        "name": name,
        "final_score": final_score,
        "production": production,
        "age_score": age_score,
        "dominator": dominator,
        "landing_spot": landing,
        "season_used": stats.get("year"),
        "ypa": stats.get("ypa"),
        "completion_pct": stats.get("completion_pct"),
        "td_int_ratio": stats.get("td_int_ratio")
    }


# ── TEST ──────────────────────────────────────────────────────

result = score_qb(
    name="Shedeur Sanders",
    college="Colorado",
    age=23,
    nfl_team="CLE"
)

for k, v in result.items():
    print(f"{k}: {v}")

print("\n")

result2 = score_qb(
    name="Cameron Ward",
    college="Miami",
    age=23,
    nfl_team="TEN"
)

for k, v in result2.items():
    print(f"{k}: {v}")