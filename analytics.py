
from __future__ import annotations
import numpy as np
import pandas as pd

def normalize_columns(df):
    out=df.copy()
    seen={}
    cols=[]
    for raw in out.columns:
        name=str(raw).strip().lower().replace("-","_").replace(" ","_") or "unnamed"
        seen[name]=seen.get(name,0)+1
        cols.append(name if seen[name]==1 else f"{name}__{seen[name]}")
    out.columns=cols
    return out

def numeric(s,default=0.0):
    return pd.to_numeric(s,errors="coerce").fillna(default)

def unit(s):
    return numeric(s).clip(0,1)

def add_positive_size_column(df,source,target="plot_size"):
    out=df.copy()
    vals=numeric(out[source],1).replace([np.inf,-np.inf],np.nan).fillna(1).abs().clip(lower=1)
    out[target]=vals
    return out

def risk_band(score):
    return pd.cut(numeric(score),[-.1,24.9,49.9,74.9,100.1],labels=["Low","Moderate","High","Critical"])

def build_safety_scores(ingredients,menus,storage,workflows):
    ing=normalize_columns(ingredients); men=normalize_columns(menus)
    sto=normalize_columns(storage); wf=normalize_columns(workflows)

    ingredient_allergen_share=float((~ing["declared_allergen"].astype(str).str.lower().isin(["none","nan",""])).mean())
    ingredient_verification_gap=float((1-ing["supplier_verification"].astype(str).str.lower().eq("verified").mean()))
    shared_storage=float(ing["storage_profile"].astype(str).str.lower().eq("shared").mean())

    menu_summary=men.groupby("school",as_index=False).agg(
        menu_count=("menu_id","count"),
        average_servings=("servings_planned","mean"),
        allergen_menus=("primary_allergen",lambda x:(~x.astype(str).str.lower().isin(["none","nan",""])).sum()),
        review_menus=("menu_status",lambda x:x.astype(str).str.lower().eq("review").sum()),
    )
    menu_summary["allergen_menu_share"]=(menu_summary["allergen_menus"]/menu_summary["menu_count"].clip(lower=1)).clip(0,1)
    menu_summary["review_menu_share"]=(menu_summary["review_menus"]/menu_summary["menu_count"].clip(lower=1)).clip(0,1)

    storage_summary=sto.groupby("kitchen_id",as_index=False).agg(
        segregation_index=("segregation_index","mean"),
        labeling_readiness_index=("labeling_readiness_index","mean"),
        cleaning_readiness_index=("cleaning_readiness_index","mean"),
        open_container_count=("open_container_count","sum"),
        spill_events_30d=("spill_events_30d","sum"),
        at_risk_share=("storage_status",lambda x:x.astype(str).str.lower().eq("at risk").mean()),
        mixed_storage_share=("separation_method",lambda x:x.astype(str).str.lower().isin(["mixed shelf","unsealed"]).mean()),
    )
    workflow_summary=wf.groupby("kitchen_id",as_index=False).agg(
        cross_contact_control=("cross_contact_control_index","mean"),
        sanitation_readiness=("sanitation_readiness_index","mean"),
        utensil_separation=("utensil_separation_index","mean"),
        surface_separation=("surface_separation_index","mean"),
        changeover_discipline=("changeover_discipline_index","mean"),
        high_intensity_share=("task_intensity",lambda x:x.astype(str).str.lower().eq("high").mean()),
        failure_share=("verification_status",lambda x:x.astype(str).str.lower().eq("fail").mean()),
        deviations_30d=("deviations_30d","sum"),
    )
    kitchen_school=pd.DataFrame({"kitchen_id":[f"K-0{i}" for i in range(1,7)],"school":["Maple Grove","Riverside","Sunrise","Greenfield","Oak Valley","Lakeside"],"zone":["North","East","Central","West","South","North"]})
    out=kitchen_school.merge(storage_summary,on="kitchen_id",how="left").merge(workflow_summary,on="kitchen_id",how="left").merge(menu_summary,on="school",how="left")
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]): out[col]=out[col].fillna(0)

    allergen_exposure=(.40*ingredient_allergen_share+.20*out["allergen_menu_share"]+.20*out["review_menu_share"]+.20*ingredient_verification_gap).clip(0,1)
    storage_gap=(.35*(1-unit(out["segregation_index"]))+.20*(1-unit(out["labeling_readiness_index"]))+.15*(1-unit(out["cleaning_readiness_index"]))+.15*out["at_risk_share"]+.10*out["mixed_storage_share"]+.05*(numeric(out["spill_events_30d"])/8).clip(0,1)).clip(0,1)
    workflow_gap=(.28*(1-unit(out["cross_contact_control"]))+.18*(1-unit(out["sanitation_readiness"]))+.16*(1-unit(out["utensil_separation"]))+.14*(1-unit(out["surface_separation"]))+.12*(1-unit(out["changeover_discipline"]))+.07*out["high_intensity_share"]+.05*out["failure_share"]).clip(0,1)
    operational=(.25*out["review_menu_share"]+.20*(numeric(out["deviations_30d"])/20).clip(0,1)+.15*(numeric(out["open_container_count"])/15).clip(0,1)+.15*out["high_intensity_share"]+.10*shared_storage+.15*(1-unit(out["cleaning_readiness_index"]))).clip(0,1)

    out["allergen_safety_gap_score"]=(100*(.34*allergen_exposure+.28*storage_gap+.28*workflow_gap+.10*operational)).clip(0,100).round(1)
    out["risk_band"]=risk_band(out["allergen_safety_gap_score"])
    out["primary_driver"]=np.select(
        [workflow_gap>=.70,storage_gap>=.70,allergen_exposure>=.65,operational>=.65],
        ["Preparation and cross-contact controls","Storage separation and labeling controls","Ingredient/menu allergen complexity","Operational deviation pressure"],
        default="Mixed allergen-safety controls")
    out["review_priority_rank"]=out["allergen_safety_gap_score"].rank(method="dense",ascending=False).astype(int)
    out["suggested_review_actions"]=((out["allergen_safety_gap_score"]>=50).astype(int)*2+(storage_gap>=.60).astype(int)+(workflow_gap>=.60).astype(int)+(out["review_menu_share"]>=.15).astype(int)).astype(int)
    return out

def build_menu_allergen_summary(menus):
    m=normalize_columns(menus)
    p=m["primary_allergen"].astype(str).str.lower()
    s=m["secondary_allergen"].astype(str).str.lower()
    pc=p.value_counts().rename_axis("allergen").reset_index(name="primary_menu_count")
    sc=s.value_counts().rename_axis("allergen").reset_index(name="secondary_menu_count")
    out=pc.merge(sc,on="allergen",how="outer").fillna(0)
    out=out[~out["allergen"].isin(["none","nan",""])]
    out["total_menu_mentions"]=(out["primary_menu_count"]+out["secondary_menu_count"]).astype(int)
    return out.sort_values("total_menu_mentions",ascending=False)

def build_workflow_summary(workflows):
    w=normalize_columns(workflows)
    return w.groupby(["kitchen_id","workflow_step"],as_index=False).agg(
        avg_cross_contact_control=("cross_contact_control_index","mean"),
        avg_sanitation_readiness=("sanitation_readiness_index","mean"),
        avg_utensil_separation=("utensil_separation_index","mean"),
        avg_surface_separation=("surface_separation_index","mean"),
        average_deviations=("deviations_30d","mean"),
        fail_share=("verification_status",lambda x:x.astype(str).str.lower().eq("fail").mean()))
