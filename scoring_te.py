import requests
import os
import math
from dotenv import load_dotenv

load_dotenv()

CFBD_KEY = os.getenv("CFBD_API_KEY")


# ── CONFERENCE TIER ───────────────────────────────────────────

def get_conference_multiplier(conference: str) -> float:
    """
    Returns a multiplier based on conference strength.
    Applied to raw dominator rating before S-curve scaling.
    Elite conferences get a boost since production against better
    competition is more predictive of NFL success.
    """
    if not conference:
        return 1.0

    conf = conference.lower()

    elite = ["sec", "big ten"]
    strong = ["big 12", "acc"]
    mid = ["pac-12", "pac 12", "american athletic", "aac"]

    if any(e in conf for e in elite):
        return 1.20
    elif any(s in conf for s in strong):
        return 1.10
    elif any(m in conf for m in mid):
        return 1.00
    else:
        return 0.90


# ── COLLEGE STATS ─────────────────────────────────────────────

def get_college_te_stats(player_name: str, college: str) -> list:
    """
    Pulls all available college receiving seasons for a TE from CFBD.
    Calculates target share as player receptions / team total receptions.
    Dominator rating calculated against all receivers on team.
    Conference captured for dominator rating adjustment.
    Returns a list of dicts, one per season.
    """
    headers = {"Authorization": f"Bearer {CFBD_KEY}"}
    stats_url = "https://api.collegefootballdata.com/stats/player/season"

    seasons_data = []

    for year in range(2019, 2025):
        stats_r = requests.get(stats_url, headers=headers, params={
            "year": year,
            "team": college,
            "category": "receiving"
        })

        stats_results = stats_r.json()

        player_yards = 0
        player_tds = 0
        player_rec = 0
        team_yards = 0
        team_tds = 0
        team_rec = 0
        conference = ""
        found = False

        for s in stats_results:
            stat_type = s.get("statType")
            val = float(s.get("stat", 0))
            name = s.get("player", "")
            position = s.get("position", "")

            if player_name.lower() in name.lower():
                conference = s.get("conference", "")

            # Team totals include all positions
            if stat_type == "YDS":
                team_yards += val
                if player_name.lower() in name.lower():
                    player_yards = val
                    found = True
            elif stat_type == "TD":
                team_tds += val
                if player_name.lower() in name.lower():
                    player_tds = val
            elif stat_type == "REC":
                team_rec += val
                if player_name.lower() in name.lower():
                    player_rec = val

        if found:
            target_share = round(player_rec / team_rec, 4) if team_rec > 0 else 0

            seasons_data.append({
                "year": year,
                "yards": player_yards,
                "tds": player_tds,
                "receptions": player_rec,
                "team_yards": team_yards,
                "team_tds": team_tds,
                "team_rec": team_rec,
                "target_share": target_share,
                "conference": conference
            })

    return seasons_data


# ── WEIGHTED AVERAGE HELPER ───────────────────────────────────

def weighted_average(values: list) -> float:
    """
    Applies dynasty weighting to a list of seasonal values.
    Most recent season = weight 3, second most recent = weight 2, rest = weight 1.
    """
    if not values:
        return 0

    weights = []
    for i in range(len(values)):
        if i == 0:
            weights.append(3)
        elif i == 1:
            weights.append(2)
        else:
            weights.append(1)

    weighted_sum = sum(v * w for v, w in zip(values, weights))
    total_weight = sum(weights)

    return weighted_sum / total_weight


# ── DOMINATOR RATING ──────────────────────────────────────────

def score_dominator_rating(seasons: list) -> float:
    """
    Weighted average dominator rating across all college seasons.
    Dominator rating = 50% yard share + 50% TD share.
    Compared against all skill position receivers on the team.
    S-curve anchored at 11% = 0.5 (historical average first round TE).
    Conference multiplier applied before S-curve.
    Returns a 0-1 score.
    """
    if not seasons:
        return 0

    seasons_sorted = sorted(seasons, key=lambda x: x["year"], reverse=True)
    dominators = []

    for s in seasons_sorted:
        team_yards = s.get("team_yards", 0)
        team_tds = s.get("team_tds", 0)
        player_yards = s.get("yards", 0)
        player_tds = s.get("tds", 0)
        conference = s.get("conference", "")

        if team_yards > 0 and team_tds > 0:
            yard_share = player_yards / team_yards
            td_share = player_tds / team_tds
            raw_dominator = (yard_share * 0.5) + (td_share * 0.5)

            multiplier = get_conference_multiplier(conference)
            adjusted_dominator = raw_dominator * multiplier
            dominators.append(adjusted_dominator)
        else:
            dominators.append(0)

    raw = weighted_average(dominators)
    exponent = -15 * (raw - 0.11)
    normalized = round(1 / (1 + math.exp(exponent)), 4)
    return normalized


# ── TARGET SHARE ──────────────────────────────────────────────

def score_target_share(seasons: list) -> float:
    """
    Weighted average reception share across all college seasons.
    Calculated as player receptions / team total receptions.
    Confirms TE was a real pass catcher not just a blocker.
    Returns a 0-1 score.
    """
    if not seasons:
        return 0

    seasons_sorted = sorted(seasons, key=lambda x: x["year"], reverse=True)
    shares = [s.get("target_share", 0) for s in seasons_sorted]

    return round(weighted_average(shares), 4)


# ── AGE AT ENTRY ──────────────────────────────────────────────

def score_age_te(age: int) -> float:
    """
    Scores age on a 0-1 scale based on TE dynasty age curves.
    TEs develop slowest of all positions, age runway is critical in TEP.
    Age 21 or younger = 1.0, age 27 or older = 0.0.
    Linear scale between 21 and 27.
    """
    if age <= 21:
        return 1.0
    elif age >= 27:
        return 0.0
    else:
        return round((27 - age) / (27 - 21), 4)


# ── LANDING SPOT ──────────────────────────────────────────────

def get_espn_team_id_map() -> dict:
    """
    Pulls all NFL teams from ESPN API.
    Returns dict of abbreviation -> team ID.
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
    r = requests.get(url)
    teams = r.json()["sports"][0]["leagues"][0]["teams"]
    return {t["team"]["abbreviation"]: t["team"]["id"] for t in teams}


def get_team_passing_attempts(team_id: int, season: int = 2024) -> float:
    """
    Pulls total passing attempts for a team from ESPN API.
    Returns passing attempts as float, or 0 if not found.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/statistics"
    r = requests.get(url, params={"season": season})
    categories = r.json()["results"]["stats"]["categories"]
    for category in categories:
        if category["name"] == "passing":
            for stat in category["stats"]:
                if stat["name"] == "passingAttempts":
                    return stat["value"]
    return 0


def score_landing_spot(nfl_team: str) -> float:
    """
    Scores landing spot based on 2024 team passing attempts from ESPN.
    Weight intentionally reduced to 15% since depth chart situation
    and target share opportunity are handled by the LLM analysis layer.
    Returns 0.5 if team not found.
    """
    team_id_map = get_espn_team_id_map()

    if nfl_team not in team_id_map:
        return 0.5

    team_attempts = {}
    for abbr, tid in team_id_map.items():
        attempts = get_team_passing_attempts(tid)
        if attempts > 0:
            team_attempts[abbr] = attempts

    if nfl_team not in team_attempts:
        return 0.5

    sorted_teams = sorted(team_attempts.items(), key=lambda x: x[1], reverse=True)
    rank = next((i for i, (t, _) in enumerate(sorted_teams) if t == nfl_team), 16)

    return round(1 - (rank / 31), 4)


# ── FINAL SCORE ───────────────────────────────────────────────

def score_te(name: str, college: str, age: int, nfl_team: str) -> dict:
    """
    Combines all four factors into a final weighted dynasty score for TEP TE rookie draft.
    Weights: age 35%, dominator rating 30%, target share 20%, landing spot 15%.
    Age weighted highest because TEs develop slowest and TEP amplifies age runway.
    Landing spot weight reduced because situational context handled by LLM layer.
    """
    seasons = get_college_te_stats(name, college)

    age_score = score_age_te(age)
    dominator = score_dominator_rating(seasons)
    target = score_target_share(seasons)
    landing = score_landing_spot(nfl_team)

    final_score = round(
        (age_score * 0.35) +
        (dominator * 0.30) +
        (target * 0.20) +
        (landing * 0.15),
        4
    )

    return {
        "name": name,
        "final_score": final_score,
        "age_score": age_score,
        "dominator_rating": dominator,
        "target_share": target,
        "landing_spot": landing,
        "seasons_found": len(seasons)
    }


# ── TEST ──────────────────────────────────────────────────────

result = score_te(
    name="Tyler Warren",
    college="Penn State",
    age=23,
    nfl_team="IND"
)

for k, v in result.items():
    print(f"{k}: {v}")

print("\n")

result2 = score_te(
    name="Colston Loveland",
    college="Michigan",
    age=21,
    nfl_team="CHI"
)

for k, v in result2.items():
    print(f"{k}: {v}")