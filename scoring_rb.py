import requests
import os
import math
from dotenv import load_dotenv
from draft import get_player_draft_info, score_draft_capital

load_dotenv()

CFBD_KEY = os.getenv("CFBD_API_KEY")


# ── COLLEGE STATS ─────────────────────────────────────────────

def get_college_rb_stats(player_name: str, college: str) -> list:
    """
    Pulls all available college rushing and receiving seasons for an RB from CFBD.
    Calculates rushing dominator rating against total team rushing production.
    Calculates receiving share against total team receiving production.
    Updated to include 2025 college season.
    Returns a list of dicts, one per season.
    """
    headers = {"Authorization": f"Bearer {CFBD_KEY}"}
    stats_url = "https://api.collegefootballdata.com/stats/player/season"

    seasons_data = []

    for year in range(2019, 2026):

        rush_r = requests.get(stats_url, headers=headers, params={
            "year": year,
            "team": college,
            "category": "rushing"
        })
        rush_results = rush_r.json()

        player_rush_yds = 0
        player_rush_tds = 0
        player_rush_car = 0
        player_rush_ypc = 0
        team_rush_yds = 0
        team_rush_tds = 0
        found = False

        for s in rush_results:
            stat_type = s.get("statType")
            val = float(s.get("stat", 0))
            name = s.get("player", "")

            if stat_type == "YDS":
                team_rush_yds += val
                if player_name.lower() in name.lower():
                    player_rush_yds = val
                    found = True
            elif stat_type == "TD":
                team_rush_tds += val
                if player_name.lower() in name.lower():
                    player_rush_tds = val
            elif stat_type == "CAR":
                if player_name.lower() in name.lower():
                    player_rush_car = val
            elif stat_type == "YPC":
                if player_name.lower() in name.lower():
                    player_rush_ypc = val

        if not found:
            continue

        rec_r = requests.get(stats_url, headers=headers, params={
            "year": year,
            "team": college,
            "category": "receiving"
        })
        rec_results = rec_r.json()

        player_rec_yds = 0
        player_rec_tds = 0
        player_rec = 0
        team_rec_yds = 0
        team_rec = 0

        for s in rec_results:
            stat_type = s.get("statType")
            val = float(s.get("stat", 0))
            name = s.get("player", "")

            if stat_type == "YDS":
                team_rec_yds += val
                if player_name.lower() in name.lower():
                    player_rec_yds = val
            elif stat_type == "TD":
                if player_name.lower() in name.lower():
                    player_rec_tds = val
            elif stat_type == "REC":
                team_rec += val
                if player_name.lower() in name.lower():
                    player_rec = val

        rush_dominator = round(player_rush_yds / team_rush_yds, 4) if team_rush_yds > 0 else 0
        rec_share = round(player_rec / team_rec, 4) if team_rec > 0 else 0

        seasons_data.append({
            "year": year,
            "rush_yards": player_rush_yds,
            "rush_tds": player_rush_tds,
            "rush_carries": player_rush_car,
            "rush_ypc": player_rush_ypc,
            "team_rush_yards": team_rush_yds,
            "team_rush_tds": team_rush_tds,
            "rec_yards": player_rec_yds,
            "rec_tds": player_rec_tds,
            "receptions": player_rec,
            "team_rec": team_rec,
            "rush_dominator": rush_dominator,
            "rec_share": rec_share
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
    Weighted average rushing dominator rating across all college seasons.
    Calculated as player rush yards / total team rush yards.
    No conference multiplier for RBs since committee backs are rare
    regardless of conference and production translates more directly.
    S-curve anchored at 35% = 0.5 (historical average first round RB).
    Returns a 0-1 score.
    """
    if not seasons:
        return 0

    seasons_sorted = sorted(seasons, key=lambda x: x["year"], reverse=True)
    dominators = [s.get("rush_dominator", 0) for s in seasons_sorted]

    raw_avg = weighted_average(dominators)
    exponent = -12 * (raw_avg - 0.35)
    normalized = round(1 / (1 + math.exp(exponent)), 4)
    return normalized


# ── RECEIVING ROLE ────────────────────────────────────────────

def score_receiving_role(seasons: list) -> float:
    """
    Weighted average receiving share across all college seasons.
    Calculated as player receptions / team total receptions.
    S-curve anchored at 8% = 0.5 (average receiving RB).
    Pass catching RBs have longer dynasty value in TEP.
    Returns a 0-1 score.
    """
    if not seasons:
        return 0

    seasons_sorted = sorted(seasons, key=lambda x: x["year"], reverse=True)
    shares = [s.get("rec_share", 0) for s in seasons_sorted]

    raw_avg = weighted_average(shares)
    exponent = -20 * (raw_avg - 0.08)
    normalized = round(1 / (1 + math.exp(exponent)), 4)
    return normalized


# ── AGE AT ENTRY ──────────────────────────────────────────────

def score_age_rb(age: int) -> float:
    """
    Scores age on a 0-1 scale based on RB dynasty age curves.
    RBs have the shortest dynasty windows of all positions.
    Age 21 or younger = 1.0, age 25 or older = 0.0.
    Linear scale between 21 and 25.
    """
    if age <= 21:
        return 1.0
    elif age >= 25:
        return 0.0
    else:
        return round((25 - age) / (25 - 21), 4)


# ── FINAL SCORE ───────────────────────────────────────────────

def score_rb(name: str, college: str, age: int) -> dict:
    """
    Combines four factors into a final weighted dynasty score for TEP RB rookie draft.
    Weights: age 35%, dominator 25%, receiving role 20%, draft capital 20%.
    Draft capital weighted higher for RBs since opportunity is everything.
    Landing spot removed because backfield situation handled by LLM layer.
    NFL team pulled automatically from draft data for LLM context.
    """
    seasons = get_college_rb_stats(name, college)
    draft_info = get_player_draft_info(name)
    draft = score_draft_capital(draft_info["overall"])

    age_score = score_age_rb(age)
    dominator = score_dominator_rating(seasons)
    receiving = score_receiving_role(seasons)

    final_score = round(
        (age_score * 0.35) +
        (dominator * 0.25) +
        (receiving * 0.20) +
        (draft * 0.20),
        4
    )

    return {
        "name": name,
        "nfl_team": draft_info["nfl_team"],
        "final_score": final_score,
        "age_score": age_score,
        "dominator_rating": dominator,
        "receiving_role": receiving,
        "draft_capital": draft,
        "draft_pick": draft_info["overall"],
        "draft_round": draft_info["round"],
        "draft_season": draft_info["season"],
        "seasons_found": len(seasons)
    }