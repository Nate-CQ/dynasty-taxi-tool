import requests
import os
import math
from dotenv import load_dotenv
from draft import get_player_draft_info, score_draft_capital

load_dotenv()

CFBD_KEY = os.getenv("CFBD_API_KEY")


# ── COLLEGE PASSING AND RUSHING STATS (MOST RECENT SEASON ONLY) ───────────

def get_college_qb_stats(player_name: str, college: str) -> dict:
    """
    Pulls the most recent college passing and rushing season for a QB from CFBD.
    Only uses the most recent season to account for transfer portal.
    Requires minimum 100 passing attempts to filter out garbage time QBs.
    Updated to check 2025 season first.
    Returns a single dict with passing and rushing stats for that season.
    """
    headers = {"Authorization": f"Bearer {CFBD_KEY}"}
    stats_url = "https://api.collegefootballdata.com/stats/player/season"

    for year in range(2025, 2018, -1):

        pass_r = requests.get(stats_url, headers=headers, params={
            "year": year,
            "team": college,
            "category": "passing"
        })
        pass_results = pass_r.json()

        att = 0
        completions = 0
        yds = 0
        tds = 0
        ints = 0
        pct = 0
        ypa = 0
        found = False

        for s in pass_results:
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

        if not found or att < 100:
            continue

        rush_r = requests.get(stats_url, headers=headers, params={
            "year": year,
            "team": college,
            "category": "rushing"
        })
        rush_results = rush_r.json()

        rush_yds = 0
        rush_tds = 0
        rush_car = 0
        rush_ypc = 0

        for s in rush_results:
            name = s.get("player", "")
            stat_type = s.get("statType")
            val = float(s.get("stat", 0))

            if player_name.lower() not in name.lower():
                continue

            if stat_type == "YDS":
                rush_yds = val
            elif stat_type == "TD":
                rush_tds = val
            elif stat_type == "CAR":
                rush_car = val
            elif stat_type == "YPC":
                rush_ypc = val

        return {
            "year": year,
            "attempts": att,
            "completions": completions,
            "yards": yds,
            "tds": tds,
            "ints": ints,
            "completion_pct": pct,
            "ypa": ypa,
            "td_int_ratio": round(tds / ints, 4) if ints > 0 else tds,
            "rush_yards": rush_yds,
            "rush_tds": rush_tds,
            "rush_carries": rush_car,
            "rush_ypc": rush_ypc
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
    Composite QB production score from four components.
    Each component scored 0-1 using S-curve anchored to historical averages.

    Component weights:
    - YPA: 30%
    - TD:INT ratio: 30%
    - Completion %: 20%
    - Rushing contribution: 20%

    Rushing S-curve midpoints:
    - YPC midpoint: 4.0 (average mobile college QB)
    - Rushing TDs midpoint: 5 (average mobile college QB)
    Pocket passers with negative YPC correctly score near 0 on rushing.
    """
    if not stats:
        return 0

    ypa_score = sigmoid(stats.get("ypa", 0), midpoint=7.5, steepness=0.8)
    td_int_score = sigmoid(stats.get("td_int_ratio", 0), midpoint=2.5, steepness=0.5)
    comp_pct_score = sigmoid(stats.get("completion_pct", 0), midpoint=0.62, steepness=15)

    rush_ypc = stats.get("rush_ypc", 0)
    rush_tds = stats.get("rush_tds", 0)
    rush_ypc_capped = max(rush_ypc, 0)
    rush_ypc_score = sigmoid(rush_ypc_capped, midpoint=4.0, steepness=0.5)
    rush_td_score = sigmoid(rush_tds, midpoint=5.0, steepness=0.3)
    rushing_score = round((rush_ypc_score + rush_td_score) / 2, 4)

    composite = round(
        (ypa_score * 0.30) +
        (td_int_score * 0.30) +
        (comp_pct_score * 0.20) +
        (rushing_score * 0.20),
        4
    )
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


# ── FINAL SCORE ───────────────────────────────────────────────

def score_qb(name: str, college: str, age: int) -> dict:
    """
    Combines four factors into a final weighted dynasty score for 2QB TEP QB rookie draft.
    Weights: production 45%, age 20%, dominator 10%, draft capital 25%.
    Draft capital weighted higher for QBs since starting opportunity
    is heavily determined by where a QB is drafted.
    Landing spot removed because situational context handled by LLM layer.
    NFL team pulled automatically from draft data for LLM context.
    """
    stats = get_college_qb_stats(name, college)
    draft_info = get_player_draft_info(name)
    draft = score_draft_capital(draft_info["overall"])

    production = score_qb_production(stats)
    age_score = score_age_qb(age)
    dominator = score_qb_dominator(stats)

    final_score = round(
        (production * 0.45) +
        (age_score * 0.20) +
        (dominator * 0.10) +
        (draft * 0.25),
        4
    )

    return {
        "name": name,
        "nfl_team": draft_info["nfl_team"],
        "final_score": final_score,
        "production": production,
        "age_score": age_score,
        "dominator": dominator,
        "draft_capital": draft,
        "draft_pick": draft_info["overall"],
        "draft_round": draft_info["round"],
        "draft_season": draft_info["season"],
        "season_used": stats.get("year"),
        "ypa": stats.get("ypa"),
        "completion_pct": stats.get("completion_pct"),
        "td_int_ratio": stats.get("td_int_ratio"),
        "rush_yards": stats.get("rush_yards"),
        "rush_tds": stats.get("rush_tds"),
        "rush_ypc": stats.get("rush_ypc")
    }