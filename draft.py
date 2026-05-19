import requests
import math


def get_draft_picks(season: int) -> list:
    """
    Pulls all NFL draft picks for a given season from ESPN API.
    Returns a list of dicts with player name, overall pick, round, and NFL team.
    """
    r = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/draft",
        params={"season": season}
    )

    if r.status_code != 200:
        return []

    data = r.json()
    picks = data.get("picks", [])

    results = []
    for pick in picks:
        athlete = pick.get("athlete", {})
        name = athlete.get("displayName", "")
        overall = pick.get("overall", 0)
        round_num = pick.get("round", 0)
        team_id = pick.get("teamId", "")
        results.append({
            "name": name,
            "overall": overall,
            "round": round_num,
            "team_id": team_id,
            "season": season
        })

    return results


def get_team_id_to_abbr() -> dict:
    """
    Pulls all NFL teams from ESPN API.
    Returns a dict mapping team ID to team abbreviation.
    Used to convert draft team IDs to readable abbreviations.
    """
    r = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams")
    teams = r.json()["sports"][0]["leagues"][0]["teams"]
    return {t["team"]["id"]: t["team"]["abbreviation"] for t in teams}


def get_player_draft_info(
    player_name: str,
    seasons: list = [2026, 2025, 2024, 2023, 2022, 2021, 2020]
) -> dict:
    """
    Looks up a player's draft position and NFL team from ESPN draft data.
    Searches across multiple seasons to handle players from different draft classes.
    Matches on last name plus first name initial to handle nicknames like Cam vs Cameron.
    Returns overall pick, round, NFL team abbreviation, and draft season.
    Returns overall = 0 and nfl_team = '' if player was undrafted or not found.
    """
    name_lower = player_name.lower()
    name_parts = name_lower.split()
    team_map = get_team_id_to_abbr()

    for season in seasons:
        picks = get_draft_picks(season)
        for pick in picks:
            pick_name_lower = pick["name"].lower()
            pick_parts = pick_name_lower.split()

            matched = False

            if name_lower in pick_name_lower or pick_name_lower in name_lower:
                matched = True

            if not matched and len(name_parts) >= 2 and len(pick_parts) >= 2:
                same_last = name_parts[-1] == pick_parts[-1]
                same_first_initial = name_parts[0][0] == pick_parts[0][0]
                if same_last and same_first_initial:
                    matched = True

            if matched:
                team_abbr = team_map.get(pick["team_id"], "")
                return {
                    "name": pick["name"],
                    "overall": pick["overall"],
                    "round": pick["round"],
                    "nfl_team": team_abbr,
                    "season": pick["season"]
                }

    return {
        "name": player_name,
        "overall": 0,
        "round": 0,
        "nfl_team": "",
        "season": None
    }


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