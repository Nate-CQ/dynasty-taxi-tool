import streamlit as st
import time
from scoring_wr import score_wr
from scoring_qb import score_qb
from scoring_te import score_te
from scoring_rb import score_rb
from llm import analyze_player, compare_players, rank_taxi_squad

st.set_page_config(
    page_title="Dynasty Taxi Tool",
    page_icon="🏈",
    layout="wide"
)

st.title("🏈 Dynasty Taxi Tool")
st.caption("TEP · 2QB · Rookie Draft Analytics")

tab1, tab2, tab3 = st.tabs(["Player Scorer", "Head to Head", "Taxi Squad Ranker"])


# ── HELPERS ───────────────────────────────────────────────────

POSITIONS = ["WR", "QB", "TE", "RB"]

NFL_TEAMS = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WSH"
]

def get_score(name, college, age, position, nfl_team):
    if position == "WR":
        return score_wr(name, college, age, nfl_team)
    elif position == "QB":
        return score_qb(name, college, age)
    elif position == "TE":
        return score_te(name, college, age, nfl_team)
    elif position == "RB":
        return score_rb(name, college, age)

def score_color(score):
    if score >= 0.65:
        return "🟢"
    elif score >= 0.40:
        return "🟡"
    else:
        return "🔴"

def display_score_breakdown(result, position):
    st.metric("Final Score", f"{result['final_score']:.3f} / 1.0")
    st.caption(f"NFL Draft: Round {result.get('draft_round', 'N/A')}, Pick {result.get('draft_pick', 'N/A')} — {result.get('nfl_team', 'N/A')}")

    st.subheader("Component Scores")
    cols = st.columns(2)

    if position == "WR":
        with cols[0]:
            st.metric("Dominator Rating", f"{result.get('dominator_rating', 0):.3f}", help="College production share, conference adjusted")
            st.metric("Age Score", f"{result.get('age_score', 0):.3f}", help="Dynasty runway")
            st.metric("Target Share", f"{result.get('target_share', 0):.3f}", help="College reception share")
        with cols[1]:
            st.metric("Landing Spot", f"{result.get('landing_spot', 0):.3f}", help="NFL team passing volume")
            st.metric("Draft Capital", f"{result.get('draft_capital', 0):.3f}", help="NFL draft position")
            st.metric("Seasons Found", result.get('seasons_found', 0), help="College seasons in database")

    elif position == "QB":
        with cols[0]:
            st.metric("Production", f"{result.get('production', 0):.3f}", help="YPA, TD:INT, completion %, rushing")
            st.metric("Age Score", f"{result.get('age_score', 0):.3f}", help="Dynasty runway")
            st.metric("Dominator", f"{result.get('dominator', 0):.3f}", help="College offensive involvement")
        with cols[1]:
            st.metric("Draft Capital", f"{result.get('draft_capital', 0):.3f}", help="NFL draft position")
            st.metric("YPA", result.get('ypa', 'N/A'), help="Yards per attempt")
            st.metric("TD:INT Ratio", result.get('td_int_ratio', 'N/A'), help="Touchdown to interception ratio")

    elif position == "TE":
        with cols[0]:
            st.metric("Age Score", f"{result.get('age_score', 0):.3f}", help="Dynasty runway, critical in TEP")
            st.metric("Dominator Rating", f"{result.get('dominator_rating', 0):.3f}", help="College production share, conference adjusted")
            st.metric("Target Share", f"{result.get('target_share', 0):.3f}", help="College reception share")
        with cols[1]:
            st.metric("Landing Spot", f"{result.get('landing_spot', 0):.3f}", help="NFL team passing volume")
            st.metric("Draft Capital", f"{result.get('draft_capital', 0):.3f}", help="NFL draft position")
            st.metric("Seasons Found", result.get('seasons_found', 0), help="College seasons in database")

    elif position == "RB":
        with cols[0]:
            st.metric("Age Score", f"{result.get('age_score', 0):.3f}", help="Dynasty runway")
            st.metric("Dominator Rating", f"{result.get('dominator_rating', 0):.3f}", help="College rushing share")
        with cols[1]:
            st.metric("Receiving Role", f"{result.get('receiving_role', 0):.3f}", help="Pass catching ability")
            st.metric("Draft Capital", f"{result.get('draft_capital', 0):.3f}", help="NFL draft position")


# ── TAB 1: PLAYER SCORER ──────────────────────────────────────

with tab1:
    st.header("Player Scorer")
    st.caption("Score any rookie prospect and get an AI-powered dynasty analysis.")

    with st.form("player_form"):
        cols = st.columns(2)
        with cols[0]:
            name = st.text_input("Player Name", placeholder="e.g. Jeremiyah Love")
            college = st.text_input("College", placeholder="e.g. Notre Dame")
        with cols[1]:
            position = st.selectbox("Position", POSITIONS)
            age = st.number_input("Age", min_value=18, max_value=30, value=21)
            nfl_team = st.selectbox("NFL Team", NFL_TEAMS) if position in ["WR", "TE"] else None

        st.caption("Use full legal names (e.g. Cameron Ward, not Cam Ward)")
        submitted = st.form_submit_button("Score Player", use_container_width=True)

    if submitted and name and college:
        with st.spinner("Pulling college stats and draft data..."):
            try:
                result = get_score(name, college, age, position, nfl_team)

                st.divider()
                st.subheader(f"{score_color(result['final_score'])} {name} — {position}")
                display_score_breakdown(result, position)

                st.divider()
                st.subheader("AI Dynasty Analysis")
                with st.spinner("Searching current NFL rosters and dynasty rankings..."):
                    analysis = analyze_player(result, position)
                    st.markdown(analysis)

            except Exception as e:
                st.error(f"Error scoring player: {e}")


# ── TAB 2: HEAD TO HEAD ───────────────────────────────────────

with tab2:
    st.header("Head to Head")
    st.caption("Compare two players and get a clear draft order recommendation.")

    with st.form("h2h_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Player 1")
            p1_name = st.text_input("Name", placeholder="e.g. Carnell Tate", key="p1_name")
            p1_college = st.text_input("College", placeholder="e.g. Ohio State", key="p1_college")
            p1_position = st.selectbox("Position", POSITIONS, key="p1_pos")
            p1_age = st.number_input("Age", min_value=18, max_value=30, value=21, key="p1_age")
            p1_team = st.selectbox("NFL Team", NFL_TEAMS, key="p1_team")

        with col2:
            st.subheader("Player 2")
            p2_name = st.text_input("Name", placeholder="e.g. Fernando Mendoza", key="p2_name")
            p2_college = st.text_input("College", placeholder="e.g. Indiana", key="p2_college")
            p2_position = st.selectbox("Position", POSITIONS, key="p2_pos")
            p2_age = st.number_input("Age", min_value=18, max_value=30, value=21, key="p2_age")
            p2_team = st.selectbox("NFL Team", NFL_TEAMS, key="p2_team")

        st.caption("Use full legal names (e.g. Cameron Ward, not Cam Ward). NFL Team is only used for WR and TE.")
        compare_submitted = st.form_submit_button("Compare Players", use_container_width=True)

    if compare_submitted and p1_name and p1_college and p2_name and p2_college:
        with st.spinner("Scoring both players..."):
            try:
                p1_team_val = p1_team if p1_position in ["WR", "TE"] else None
                p2_team_val = p2_team if p2_position in ["WR", "TE"] else None

                p1_result = get_score(p1_name, p1_college, p1_age, p1_position, p1_team_val)
                p2_result = get_score(p2_name, p2_college, p2_age, p2_position, p2_team_val)

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(
                        f"{score_color(p1_result['final_score'])} {p1_result['name']} ({p1_position})",
                        f"{p1_result['final_score']:.3f}",
                        help=f"Pick {p1_result.get('draft_pick', 'N/A')}, {p1_result.get('nfl_team', 'N/A')}"
                    )
                with c2:
                    st.metric(
                        f"{score_color(p2_result['final_score'])} {p2_result['name']} ({p2_position})",
                        f"{p2_result['final_score']:.3f}",
                        help=f"Pick {p2_result.get('draft_pick', 'N/A')}, {p2_result.get('nfl_team', 'N/A')}"
                    )

                st.divider()
                st.subheader("AI Comparison")
                with st.spinner("Searching dynasty rankings and NFL situations..."):
                    comparison = compare_players(p1_result, p1_position, p2_result, p2_position)
                    st.markdown(comparison)

            except Exception as e:
                st.error(f"Error: {e}")


# ── TAB 3: TAXI SQUAD RANKER ──────────────────────────────────

with tab3:
    st.header("Taxi Squad Ranker")
    st.caption("Enter up to 4 taxi squad candidates then rank them all at once.")

    if "taxi_players" not in st.session_state:
        st.session_state.taxi_players = []
    if "taxi_inputs" not in st.session_state:
        st.session_state.taxi_inputs = []

    with st.form("taxi_form"):
        st.subheader("Enter Your Taxi Squad")
        st.caption("Use full legal names (e.g. Cameron Ward, not Cam Ward). NFL Team only required for WR and TE.")

        rows = []
        for i in range(4):
            st.markdown(f"**Player {i+1}**")
            cols = st.columns([2, 2, 1, 1, 1])
            with cols[0]:
                name = st.text_input("Name", key=f"t_name_{i}", placeholder="Full legal name")
            with cols[1]:
                college = st.text_input("College", key=f"t_college_{i}")
            with cols[2]:
                position = st.selectbox("Position", POSITIONS, key=f"t_pos_{i}")
            with cols[3]:
                age = st.number_input("Age", min_value=18, max_value=30, value=21, key=f"t_age_{i}")
            with cols[4]:
                team = st.selectbox("NFL Team", [""] + NFL_TEAMS, key=f"t_team_{i}")
            rows.append((name, college, position, age, team))

        rank_submitted = st.form_submit_button("Score and Rank Taxi Squad", use_container_width=True)

    if rank_submitted:
        valid_players = [(n, c, p, a, t) for n, c, p, a, t in rows if n and c]

        if len(valid_players) < 2:
            st.warning("Please enter at least 2 players to rank.")
        else:
            scored_players = []
            with st.spinner("Scoring all players..."):
                for name, college, position, age, team in valid_players:
                    try:
                        team_val = team if position in ["WR", "TE"] and team else None
                        result = get_score(name, college, age, position, team_val)
                        result["position"] = position
                        scored_players.append(result)
                    except Exception as e:
                        st.error(f"Error scoring {name}: {e}")

            if scored_players:
                st.divider()
                st.subheader("Model Scores")
                for p in sorted(scored_players, key=lambda x: x["final_score"], reverse=True):
                    st.write(f"{score_color(p['final_score'])} **{p['name']}** ({p['position']}) — {p.get('nfl_team', 'N/A')} — Pick {p.get('draft_pick', 'N/A')} — Score: **{p['final_score']:.3f}**")

                st.divider()
                st.subheader("AI Taxi Squad Analysis")
                with st.spinner("Searching dynasty rankings and NFL depth charts..."):
                    try:
                        ranking = rank_taxi_squad(scored_players)
                        st.markdown(ranking)
                    except Exception as e:
                        st.error(f"Error: {e}")