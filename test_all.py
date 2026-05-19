from scoring_wr import score_wr
from scoring_qb import score_qb
from scoring_te import score_te
from scoring_rb import score_rb

results = []

# 2026 NFL Draft class - QBs
results.append({**score_qb("Fernando Mendoza", "Indiana", 23), "position": "QB"})
results.append({**score_qb("Drew Allar", "Penn State", 23), "position": "QB"})

# 2026 NFL Draft class - WRs
results.append({**score_wr("Carnell Tate", "Ohio State", 21, "TEN"), "position": "WR"})
results.append({**score_wr("Makai Lemon", "USC", 21, "PHI"), "position": "WR"})
results.append({**score_wr("Jordyn Tyson", "Arizona State", 22, "NO"), "position": "WR"})

# 2026 NFL Draft class - RBs
results.append({**score_rb("Jeremiyah Love", "Notre Dame", 21), "position": "RB"})
results.append({**score_rb("Jadarian Price", "Notre Dame", 21), "position": "RB"})

# 2026 NFL Draft class - TEs
results.append({**score_te("Will Kacmarek", "Ohio State", 23, "MIA"), "position": "TE"})

results.sort(key=lambda x: x["final_score"], reverse=True)

print(f"{'Rank':<5} {'Name':<25} {'Pos':<5} {'Score':<8} {'Pick':<6} {'Round':<6} {'Team':<6}")
print("-" * 68)

for i, r in enumerate(results, 1):
    print(f"{i:<5} {r['name']:<25} {r['position']:<5} {r['final_score']:<8} {r.get('draft_pick', 'N/A'):<6} {r.get('draft_round', 'N/A'):<6} {r.get('nfl_team', 'N/A'):<6}")