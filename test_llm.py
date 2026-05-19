import time
from scoring_wr import score_wr
from scoring_qb import score_qb
from scoring_te import score_te
from scoring_rb import score_rb
from llm import analyze_player, compare_players, rank_taxi_squad

qb = score_qb("Fernando Mendoza", "Indiana", 23)
wr = score_wr("Carnell Tate", "Ohio State", 21, "TEN")
te = score_te("Will Kacmereck", "Ohio State", 23, "MIA")
rb = score_rb("Jeremiyah Love", "Notre Dame", 21)

output = ""

output += "=== SINGLE PLAYER ANALYSIS: Jeremiyah Love ===\n\n"
output += analyze_player(rb, "RB")

time.sleep(30)

output += "\n\n=== HEAD TO HEAD: Carnell Tate vs Fernando Mendoza ===\n\n"
output += compare_players(wr, "WR", qb, "QB")

time.sleep(30)

output += "\n\n=== TAXI SQUAD RANKER ===\n\n"
taxi_players = [
    {**rb, "position": "RB"},
    {**qb, "position": "QB"},
    {**wr, "position": "WR"},
    {**te, "position": "TE"}
]
output += rank_taxi_squad(taxi_players)

with open("llm_test_output.txt", "w", encoding="utf-8") as f:
    f.write(output)

print("Done. Output written to llm_test_output.txt")