import requests
import os
import math
from dotenv import load_dotenv

load_dotenv()

CFBD_KEY = os.getenv("CFBD_API_KEY")


# ── COLLEGE STATS ─────────────────────────────────────────────

def get_college_receiving_stats(player_name: str, college: str) -> list:
    """
    Pulls all available college receiving seasons for a player from CFBD.
    Calculates target share as player receptions / team total receptions.
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
        found = False

        for s in stats_results:
            stat_type = s.get("statType")
            val = float(s.get("stat", 0))
            name = s.get("player", "")

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
                "target_share": target_share
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
    Scaled with S-curve anchored at 22% = 0.5 (historical average first round WR).
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

        if team_yards > 0 and team_tds > 0:
            yard_share = player_yards / team_yards
            td_share = player_tds / team_tds
            dominators.append((yard_share * 0.5) + (td_share * 0.5))
        else:
            dominators.append(0)

    raw = weighted_average(dominators)
    exponent = -12 * (raw - 0.22)
    normalized = round(1 / (1 + math.exp(exponent)), 4)
    return normalized


# ── TARGET SHARE ──────────────────────────────────────────────

def score_target_share(seasons: list) -> float:
    """
    Weighted average reception share across all college seasons.
    Calculated as player receptions / team total receptions.
    Used as a proxy for target share since CFBD does not expose raw targets.
    Returns a 0-1 score.
    """
    if not seasons:
        return 0

    seasons_sorted = sorted(seasons, key=lambda x: x["year"], reverse=True)
    shares = [s.get("target_share", 0) for s in seasons_sorted]

    return round(weighted_average(shares), 4)


# ── AGE AT ENTRY ──────────────────────────────────────────────

def score_age(age: int) -> float:
    """
    Scores age on a 0-1 scale based on WR dynasty age curves.
    Age 20 or younger = 1.0, age 26 or older = 0.0.
    Linear scale between 20 and 26.
    """
    if age <= 20:
        return 1.0
    elif age >= 26:
        return 0.0
    else:
        return round((26 - age) / (26 - 20), 4)


# ── LANDING SPOT ──────────────────────────────────────────────

def get_espn_team_id_map() -> dict:
    """
    Pulls all NFL teams from ESPN API and returns a dict of abbreviation -> team ID.
    Used to look up the correct ESPN team ID for passing attempts data.
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
    r = requests.get(url)
    teams = r.json()["sports"][0]["leagues"][0]["teams"]
    return {t["team"]["abbreviation"]: t["team"]["id"] for t in teams}


def get_team_passing_attempts(team_id: int, season: int = 2024) -> float:
    """
    Pulls total passing attempts for a team in a given season from ESPN API.
    Returns passing attempts as a float, or 0 if not found.
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
    Scores landing spot quality based on 2024 team passing attempts from ESPN.
    Pulls all 32 teams dynamically, ranks them, scores player's team 0-1.
    Returns 0.5 if team abbreviation not found.
    """
    team_id_map = get_espn_team_id_map()

    if nfl_team not in team_id_map:
        print(f"Team not found in ESPN data: {nfl_team}")
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

def score_wr(name: str, college: str, age: int, nfl_team: str) -> dict:
    """
    Combines all four factors into a final weighted dynasty score for TEP WR rookie draft.
    Weights: dominator rating 35%, age 25%, target share 20%, landing spot 20%.
    """
    seasons = get_college_receiving_stats(name, college)

    dominator = score_dominator_rating(seasons)
    age_score = score_age(age)
    target = score_target_share(seasons)
    landing = score_landing_spot(nfl_team)

    final_score = round(
        (dominator * 0.35) +
        (age_score * 0.25) +
        (target * 0.20) +
        (landing * 0.20),
        4
    )

    return {
        "name": name,
        "final_score": final_score,
        "dominator_rating": dominator,
        "age_score": age_score,
        "target_share": target,
        "landing_spot": landing,
        "seasons_found": len(seasons)
    }


# ── TEST ──────────────────────────────────────────────────────

seasons = get_college_receiving_stats("Malik Nabers", "LSU")
for s in seasons:
    print(s)

result = score_wr(
    name="Malik Nabers",
    college="LSU",
    age=22,
    nfl_team="NYG"
)

for k, v in result.items():
    print(f"{k}: {v}")

result2 = score_wr(
    name="Tetairoa McMillan",
    college="Arizona",
    age=21,
    nfl_team="CAR"
)

print("\n")
for k, v in result2.items():
    print(f"{k}: {v}")