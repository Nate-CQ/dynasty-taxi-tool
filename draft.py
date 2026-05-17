import requests
import math


def get_draft_picks(season: int) -> list:
    """
    Pulls all NFL draft picks for a given season from ESPN API.
    Returns a list of dicts with player name and overall pick number.
    """
    r = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/draft",
        params={"season": season}
    )
    data = r.json()
    picks = data.get("picks", [])

    results = []
    for pick in picks:
        athlete = pick.get("athlete", {})
        name = athlete.get("displayName", "")
        overall = pick.get("overall", 0)
        round_num = pick.get("round", 0)
        nfl_team_id = pick.get("teamId", "")
        results.append({
            "name": name,
            "overall": overall,
            "round": round_num,
            "nfl_team_id": nfl_team_id,
            "season": season
        })

    return results


def get_player_draft_info(player_name: str, seasons: list = [2025, 2024, 2023, 2022]) -> dict:
    """
    Looks up a player's draft position by name from ESPN draft data.
    Searches across multiple seasons to handle players from different draft classes.
    Matches on last name plus first name initial to handle nicknames like Cam vs Cameron.
    Returns overall pick number, round, NFL team ID, and draft season.
    Returns overall = 0 if player was undrafted or not found.
    """
    name_lower = player_name.lower()
    name_parts = name_lower.split()

    for season in seasons:
        picks = get_draft_picks(season)
        for pick in picks:
            pick_name_lower = pick["name"].lower()
            pick_parts = pick_name_lower.split()

            # First try exact substring match
            if name_lower in pick_name_lower or pick_name_lower in name_lower:
                return pick

            # Fall back to last name plus first initial match
            if len(name_parts) >= 2 and len(pick_parts) >= 2:
                same_last = name_parts[-1] == pick_parts[-1]
                same_first_initial = name_parts[0][0] == pick_parts[0][0]
                if same_last and same_first_initial:
                    return pick

    return {"name": player_name, "overall": 0, "round": 0, "nfl_team_id": "", "season": None}


def score_draft_capital(overall_pick: int) -> float:
    """
    Scores NFL draft capital using an S-curve anchored at pick 65 = 0.5.
    Pick 1 scores near 1.0, pick 65 (end of round 2) = 0.5, day 3+ near 0.
    Undrafted (overall_pick = 0) returns 0.0.
    Returns a 0-1 score.
    """
    if overall_pick <= 0:
        return 0.0
    exponent = 0.05 * (overall_pick - 65)
    return round(1 / (1 + math.exp(exponent)), 4)


# ── TEST ──────────────────────────────────────────────────────

players = [
    "Cameron Ward",
    "Shedeur Sanders",
    "Ashton Jeanty",
    "Malik Nabers",
    "Tetairoa McMillan",
    "Colston Loveland",
    "Tyler Warren",
    "Omarion Hampton"
]

for name in players:
    info = get_player_draft_info(name)
    draft_score = score_draft_capital(info["overall"])
    season_str = str(info["season"]) if info["season"] else "N/A"
    print(f"{name:<25} Overall: {info['overall']:<5} Round: {info['round']:<3} Season: {season_str:<6} Score: {draft_score}")