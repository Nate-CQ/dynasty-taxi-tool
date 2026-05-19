import anthropic
import os
from dotenv import load_dotenv

load_dotenv(override=True)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── SYSTEM PROMPT ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert dynasty fantasy football analyst specializing in TEP (Tight End Premium) 2QB leagues.

You receive a player's statistical scoring profile and provide analysis to help dynasty managers make rookie draft decisions.

You have access to web search. Use it to look up:
- Current NFL roster and depth chart information as of May 2026
- Current dynasty community rookie rankings and consensus values
- The full 2026 rookie class and where players are projected in dynasty rookie drafts
- Any recent news about the player or their NFL team that affects dynasty value

Your analysis should be:
- Specific and data-driven, referencing the actual scores provided
- Grounded in current real-world NFL information from web search
- Aware of the full 2026 rookie class context and how this player compares
- Honest about weaknesses and risks
- Focused on dynasty value, not redraft value
- Aware that this is a TEP 2QB league which affects positional values
- Actionable, giving the manager a clear draft decision

Key positional context for TEP 2QB leagues:
- QBs carry premium value due to 2QB scarcity, but elite RB prospects with generational profiles can still go 1.01
- TEs carry premium value due to TEP scoring, especially young TEs with long development runways
- RBs have the shortest dynasty windows but top prospects with elite situations are still valuable early picks
- WRs are the deepest position and generally should not be reached for over elite prospects at other positions
- Always evaluate the specific player and situation rather than defaulting to positional rules

Never frame recommendations as trades. This tool is purely for rookie draft decisions.
When comparing players, always frame draft recommendations as relative decisions
(draft X before Y, or prefer X over Y) not as absolute pick numbers like 1.01 or 1.02,
since the user's actual draft position is unknown.
When analyzing a single player, give a general tier recommendation such as
early first round, mid first round, late first round, early second round, etc."""


# ── SINGLE PLAYER ANALYSIS ────────────────────────────────────

def analyze_player(player_profile: dict, position: str) -> str:
    """
    Takes a player's scoring profile and returns a plain-language
    dynasty analysis from Claude with web search for current context.
    Position must be one of: WR, QB, TE, RB.
    """
    nfl_team = player_profile.get("nfl_team", "Unknown")

    prompt = f"""Analyze this {position} prospect for a TEP 2QB dynasty rookie draft.
This is the 2026 rookie class.

First, search the web for:
1. Current {nfl_team} NFL roster and depth chart as of May 2026
2. Current dynasty community rankings for {player_profile['name']} in 2026 rookie drafts
3. 2026 dynasty rookie draft rankings and where {player_profile['name']} is projected to go overall
4. The full 2026 NFL rookie class skill position players and their dynasty values
5. Any recent news about {player_profile['name']} and the {nfl_team}

Then provide your analysis using both the scoring data below and what you find online.

Player: {player_profile['name']}
NFL Team: {nfl_team}
Final Score: {player_profile['final_score']} / 1.0
NFL Draft: Round {player_profile.get('draft_round', 'N/A')}, Pick {player_profile.get('draft_pick', 'N/A')} overall

Component Scores (each out of 1.0):"""

    if position == "WR":
        prompt += f"""
- Dominator Rating: {player_profile.get('dominator_rating')} (college production share, conference adjusted)
- Age Score: {player_profile.get('age_score')} (dynasty runway)
- Target Share: {player_profile.get('target_share')} (college reception share)
- Landing Spot: {player_profile.get('landing_spot')} (NFL team passing volume, 2025 data)
- Draft Capital: {player_profile.get('draft_capital')} (NFL draft position)"""

    elif position == "QB":
        prompt += f"""
- Production: {player_profile.get('production')} (YPA, TD:INT, completion %, rushing)
- Age Score: {player_profile.get('age_score')} (dynasty runway)
- Dominator: {player_profile.get('dominator')} (college offensive involvement)
- Draft Capital: {player_profile.get('draft_capital')} (NFL draft position)
- YPA: {player_profile.get('ypa')}
- Completion %: {player_profile.get('completion_pct')}
- TD:INT Ratio: {player_profile.get('td_int_ratio')}
- Rush Yards: {player_profile.get('rush_yards')}
- Rush TDs: {player_profile.get('rush_tds')}"""

    elif position == "TE":
        prompt += f"""
- Age Score: {player_profile.get('age_score')} (dynasty runway, critical in TEP)
- Dominator Rating: {player_profile.get('dominator_rating')} (college production share, conference adjusted)
- Target Share: {player_profile.get('target_share')} (college reception share)
- Landing Spot: {player_profile.get('landing_spot')} (NFL team passing volume, 2025 data)
- Draft Capital: {player_profile.get('draft_capital')} (NFL draft position)"""

    elif position == "RB":
        prompt += f"""
- Age Score: {player_profile.get('age_score')} (dynasty runway)
- Dominator Rating: {player_profile.get('dominator_rating')} (college rushing share)
- Receiving Role: {player_profile.get('receiving_role')} (pass catching ability)
- Draft Capital: {player_profile.get('draft_capital')} (NFL draft position)"""

    prompt += f"""

Please provide:
1. A 2-3 sentence summary of this player's dynasty profile
2. Their current NFL situation with {nfl_team} including accurate depth chart and path to playing time based on your web search
3. What the dynasty community currently thinks about this player and where they rank him in the 2026 rookie class
4. One historical comparable player
5. A rookie draft recommendation expressed as a tier (early first round, mid first round,
   late first round, early second round, etc.) and whether to place them on the active
   roster or taxi squad immediately after drafting, with clear reasoning for both decisions"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}]
    )

    full_text = " ".join(
        block.text for block in message.content
        if hasattr(block, "text") and block.text
    )
    return full_text


# ── HEAD TO HEAD COMPARISON ───────────────────────────────────

def compare_players(player1: dict, pos1: str, player2: dict, pos2: str) -> str:
    """
    Compares two players head to head and recommends who to draft first.
    Uses web search for current dynasty community context.
    Players can be different positions.
    """
    prompt = f"""You are helping a dynasty manager decide who to draft first in a TEP 2QB rookie draft.
This is the 2026 rookie class.

First, search the web for:
1. 2026 dynasty rookie draft overall rankings and tier list
2. Current dynasty community rankings comparing {player1['name']} and {player2['name']}
3. Current NFL situations for both players as of May 2026
4. Any recent news affecting either player's dynasty value

Then compare these two prospects using both the scoring data and what you find online:

PLAYER 1: {player1['name']} ({pos1})
NFL Team: {player1.get('nfl_team', 'Unknown')}
Final Score: {player1['final_score']} / 1.0
Draft: Round {player1.get('draft_round', 'N/A')}, Pick {player1.get('draft_pick', 'N/A')} overall

PLAYER 2: {player2['name']} ({pos2})
NFL Team: {player2.get('nfl_team', 'Unknown')}
Final Score: {player2['final_score']} / 1.0
Draft: Round {player2.get('draft_round', 'N/A')}, Pick {player2.get('draft_pick', 'N/A')} overall

Please provide:
1. Who you draft first and why, considering TEP 2QB positional value and current dynasty consensus
2. What each player's dynasty ceiling and floor looks like
3. What situations would make you change your pick order
4. A relative draft recommendation expressed as "draft X before Y" or "prefer X over Y"
   with an indication of how large the gap is between them (close call, moderate gap, clear preference).
   Do not use absolute pick numbers like 1.01 or 1.02 since the manager's actual draft position is unknown.
5. Active roster vs taxi squad recommendation for each player independently

Keep it to 200-250 words. Be direct and opinionated."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}]
    )

    full_text = " ".join(
        block.text for block in message.content
        if hasattr(block, "text") and block.text
    )
    return full_text


# ── TAXI SQUAD RANKER ─────────────────────────────────────────

def rank_taxi_squad(players: list) -> str:
    """
    Takes a list of player profile dicts with position included.
    Returns a ranked analysis of who to keep on the taxi squad.
    Uses web search for current dynasty context and NFL situations.
    Each dict must have a 'position' key and 'nfl_team' key.
    """
    player_summaries = ""
    for p in players:
        player_summaries += f"""
{p['name']} ({p['position']}) — NFL Team: {p.get('nfl_team', 'Unknown')}
- Model Score: {p['final_score']} / 1.0
- Draft: Round {p.get('draft_round', 'N/A')}, Pick {p.get('draft_pick', 'N/A')} overall
"""

    names = ", ".join([p['name'] for p in players])

    prompt = f"""Rank these players for a dynasty taxi squad in a TEP 2QB league.
This is the 2026 rookie class.

First, search the web for:
1. 2026 dynasty rookie draft overall rankings and tier list
2. Current dynasty community rookie rankings for {names}
3. Current NFL depth charts and situations for each player as of May 2026
4. Any recent news affecting any of these players

Then rank them using both the model scores and what you find online.
The model has assigned scores but you should use your own dynasty reasoning to rerank them.
Scores are one input, not the final answer. Consider positional value in TEP 2QB,
development timelines, NFL situations, and long term dynasty ceiling.

Important: if any player listed is not actually a 2026 rookie, flag this clearly
and note they are ineligible for a 2026 rookie taxi squad.

Players to evaluate:
{player_summaries}

Please provide:
1. Your reranked list from best to worst taxi squad candidate with 1-2 sentence
   reasoning for each. Reference current dynasty consensus where relevant.
   Be explicit if your ranking differs from the model scores and why.
2. Which players should be promoted to the active roster immediately
3. Which players are most at risk of being cut if roster space is needed
4. One key insight about this specific taxi squad composition

Keep it to 250-300 words. Use your dynasty expertise and current information."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}]
    )

    full_text = " ".join(
        block.text for block in message.content
        if hasattr(block, "text") and block.text
    )
    return full_text