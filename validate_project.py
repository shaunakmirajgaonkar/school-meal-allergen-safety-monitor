
from pathlib import Path
import pandas as pd
from analytics import normalize_columns, build_safety_scores, build_menu_allergen_summary, build_workflow_summary

ROOT=Path(__file__).resolve().parent
i=normalize_columns(pd.read_csv(ROOT/"data/sample_ingredients.csv"))
m=normalize_columns(pd.read_csv(ROOT/"data/sample_menus.csv"))
s=normalize_columns(pd.read_csv(ROOT/"data/sample_storage.csv"))
w=normalize_columns(pd.read_csv(ROOT/"data/sample_preparation_workflows.csv"))

out=build_safety_scores(i,m,s,w)
ms=build_menu_allergen_summary(m)
ws=build_workflow_summary(w)

assert len(out)==6
assert out["allergen_safety_gap_score"].between(0,100).all()
assert out["risk_band"].notna().all()
assert out["primary_driver"].notna().all()
assert out["review_priority_rank"].ge(1).all()
assert out["suggested_review_actions"].ge(0).all()
assert len(ms)>0 and len(ws)>0
assert len(set(out.columns))==len(out.columns)

print("PASS: school meal allergen-safety screening")
print("Kitchens:",len(out))
print("Score range:",float(out["allergen_safety_gap_score"].min()),"-",float(out["allergen_safety_gap_score"].max()))
print("Allergen groups:",len(ms))
print("Workflow rows:",len(ws))
