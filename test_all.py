from scoring_wr import score_wr
from scoring_qb import score_qb
from scoring_te import score_te
from scoring_rb import score_rb

results = []

results.append({**score_wr("Malik Nabers", "LSU", 22, "NYG"), "position": "WR"})
results.append({**score_wr("Tetairoa McMillan", "Arizona", 21, "CAR"), "position": "WR"})
results.append({**score_qb("Shedeur Sanders", "Colorado", 23), "position": "QB"})
results.append({**score_qb("Cameron Ward", "Miami", 23), "position": "QB"})
results.append({**score_te("Tyler Warren", "Penn State", 23, "IND"), "position": "TE"})
results.append({**score_te("Colston Loveland", "Michigan", 21, "CHI"), "position": "TE"})
results.append({**score_rb("Ashton Jeanty", "Boise State", 21), "position": "RB"})
results.append({**score_rb("Omarion Hampton", "North Carolina", 21), "position": "RB"})

results.sort(key=lambda x: x["final_score"], reverse=True)

print(f"{'Rank':<5} {'Name':<25} {'Pos':<5} {'Score':<8}")
print("-" * 50)

for i, r in enumerate(results, 1):
    print(f"{i:<5} {r['name']:<25} {r['position']:<5} {r['final_score']:<8}")