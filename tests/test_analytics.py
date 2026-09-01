
from pathlib import Path
import sys, pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analytics import normalize_columns, add_positive_size_column, build_safety_scores

def test_duplicate_header_normalization():
    df=pd.DataFrame([[1,2]],columns=["Zone","Zone"])
    assert list(normalize_columns(df).columns)==["zone","zone__2"]

def test_plot_size_safe():
    df=pd.DataFrame({"x":[0,None,-3,4]})
    out=add_positive_size_column(df,"x")
    assert (out["plot_size"]>=1).all()

def test_scores():
    i=pd.read_csv(ROOT/"data/sample_ingredients.csv")
    m=pd.read_csv(ROOT/"data/sample_menus.csv")
    s=pd.read_csv(ROOT/"data/sample_storage.csv")
    w=pd.read_csv(ROOT/"data/sample_preparation_workflows.csv")
    out=build_safety_scores(i,m,s,w)
    assert len(out)==6
    assert out["allergen_safety_gap_score"].between(0,100).all()
    assert out["risk_band"].notna().all()
    assert out["review_priority_rank"].ge(1).all()
