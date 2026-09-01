
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from analytics import normalize_columns,add_positive_size_column,build_safety_scores,build_menu_allergen_summary,build_workflow_summary

st.set_page_config(page_title="School Meal Allergen Safety Monitor",page_icon="🥗",layout="wide",initial_sidebar_state="expanded")
ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"

REQUIRED_COLUMNS={
"ingredients":["ingredient_id","ingredient_name","form","declared_allergen","supplier_verification","storage_profile","handling_steps","storage_area"],
"menus":["menu_id","school","menu_name","meal_period","primary_allergen","secondary_allergen","servings_planned","menu_status"],
"storage":["storage_id","kitchen_id","storage_area","storage_status","separation_method","segregation_index","labeling_readiness_index","cleaning_readiness_index","open_container_count","spill_events_30d","inspection_frequency"],
"workflows":["workflow_id","kitchen_id","workflow_step","task_intensity","cross_contact_control_index","sanitation_readiness_index","utensil_separation_index","surface_separation_index","changeover_discipline_index","verification_status","deviations_30d"]}

st.markdown("""<style>
.stApp{background:linear-gradient(180deg,#fbfdff,#f3fbf7 55%,#fff7ec);color:#203b43}
.block-container{max-width:1650px;padding-top:1rem}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid #dce9e5}
[data-testid="stSidebar"] *{color:#28444c!important}
.hero{background:linear-gradient(135deg,#edf8ff,#effbf5 52%,#fff0dc);border:1px solid #d9e8e3;border-radius:30px;padding:30px 34px;margin-bottom:20px;box-shadow:0 16px 40px rgba(35,67,73,.06)}
.eyebrow{font-size:.72rem;font-weight:900;letter-spacing:.16em;color:#2c7b6b;text-transform:uppercase}
.hero h1{font-size:2.46rem;color:#203b43!important;margin:.4rem 0 .6rem}
.hero p{color:#61777d;max-width:1350px}.pill{display:inline-block;background:#fff;border:1px solid #d7e5df;border-radius:999px;padding:7px 12px;margin:10px 6px 0 0;font-size:.82rem;font-weight:800}
.card{background:#fff;border:1px solid #dfeae6;border-radius:18px;padding:16px;box-shadow:0 10px 28px rgba(31,63,68,.045)}
.label{font-size:.71rem;text-transform:uppercase;letter-spacing:.07em;font-weight:850;color:#7b9197}.value{font-size:1.82rem;font-weight:900;color:#233f47}.sub{font-size:.77rem;color:#7b8f95}
.section{font-size:1.2rem;font-weight:900;color:#294850;margin:24px 0 11px}.note{background:#f5fafc;border:1px solid #dce8ee;border-radius:15px;padding:14px 16px;color:#566c73}.footer{text-align:center;color:#82939a;font-size:.75rem;margin-top:22px}
</style>""",unsafe_allow_html=True)

st.sidebar.markdown("## 🥗 AllergenSafe Local")
st.sidebar.caption("Inspect • Compare • Prioritize")
page=st.sidebar.radio("Workspace",["Dashboard","Ingredient Safety","Menu Allergen Map","Storage Controls","Preparation Workflows","Kitchen Comparison","Priority Queue","Trend & Signals","Scenario Lab","Reports & Export"],label_visibility="collapsed")
st.sidebar.divider()

uploads=[
("ingredients","Upload authorized ingredients CSV","sample_ingredients.csv"),
("menus","Upload school-meal menus CSV","sample_menus.csv"),
("storage","Upload storage-controls CSV","sample_storage.csv"),
("workflows","Upload preparation-workflows CSV","sample_preparation_workflows.csv"),
]
frames={}
for key,label,default_file in uploads:
    uploaded=st.sidebar.file_uploader(label,type=["csv"],key=f"upload_{key}")
    try:
        frames[key]=normalize_columns(pd.read_csv(uploaded) if uploaded is not None else pd.read_csv(DATA/default_file))
    except Exception as exc:
        st.error(f"Could not read {key} CSV: {exc}")
        st.stop()

errors=[]
for dataset,required in REQUIRED_COLUMNS.items():
    missing=[c for c in required if c not in frames[dataset].columns]
    if missing: errors.append(f"{dataset}: missing {', '.join(missing)}")
if errors:
    st.error("Input validation failed.")
    for e in errors: st.write("• "+e)
    st.stop()

try:
    scored=build_safety_scores(frames["ingredients"],frames["menus"],frames["storage"],frames["workflows"])
    menu_summary=build_menu_allergen_summary(frames["menus"])
    workflow_summary=build_workflow_summary(frames["workflows"])
except Exception as exc:
    st.error("The supplied records could not be processed safely.")
    st.exception(exc); st.stop()

zones=sorted(scored["zone"].astype(str).unique())
bands=["All","Low","Moderate","High","Critical"]
selected_zone=st.sidebar.selectbox("Zone",["All"]+zones)
selected_band=st.sidebar.selectbox("Risk band",bands)
minimum_score=st.sidebar.slider("Minimum safety-gap score",0,100,0)

view=scored.copy()
if selected_zone!="All": view=view[view["zone"].astype(str)==selected_zone]
if selected_band!="All": view=view[view["risk_band"].astype(str)==selected_band]
view=view[view["allergen_safety_gap_score"]>=minimum_score]
if view.empty:
    st.warning("No records match the current filters."); st.stop()

st.markdown("""<div class="hero"><div class="eyebrow">SCHOOL FOOD SAFETY • ALLERGEN CONTROLS • LOCAL-FIRST • EXPLAINABLE</div><h1>Monitor potential allergen cross-contact pressure across ingredients, menus, storage and preparation workflows.</h1><p>Surface operational conditions that may warrant qualified school-food-safety review using transparent, locally processed signals.</p><span class="pill">🥜 Allergen Context</span><span class="pill">🍽️ Menu Analysis</span><span class="pill">📦 Storage Controls</span><span class="pill">🧤 Preparation Workflow</span><span class="pill">🏫 Kitchen Comparison</span><span class="pill">📋 Review Queue</span><span class="pill">🔒 Local Processing</span></div>""",unsafe_allow_html=True)

kpis=[("Kitchens",int(view.kitchen_id.nunique()),"Operational kitchens"),("High / Critical",int((view.allergen_safety_gap_score>=50).sum()),"Review-priority kitchens"),("Critical",int((view.allergen_safety_gap_score>=75).sum()),"Highest screening band"),("Avg gap score",f"{view.allergen_safety_gap_score.mean():.1f}","Mean safety-gap score"),("Review actions",int(view.suggested_review_actions.sum()),"Suggested review actions")]
cols=st.columns(5)
for col,(label,value,sub) in zip(cols,kpis):
    col.markdown(f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div><div class="sub">{sub}</div></div>',unsafe_allow_html=True)

if page=="Dashboard":
    st.markdown('<div class="section">Allergen-safety command view</div>',unsafe_allow_html=True)
    a,b,c=st.columns([1,1.25,1])
    dist=view.risk_band.astype(str).value_counts().rename_axis("band").reset_index(name="count")
    a.plotly_chart(px.pie(dist,names="band",values="count",hole=.62,title="Safety-gap distribution",template="plotly_white"),width="stretch")
    sp=add_positive_size_column(view,"suggested_review_actions")
    b.plotly_chart(px.scatter(sp,x="segregation_index",y="allergen_safety_gap_score",size="plot_size",color="zone",hover_name="kitchen_id",range_x=[0,1],range_y=[0,100],title="Storage segregation × safety gap",template="plotly_white"),width="stretch")
    top=view.nlargest(8,"allergen_safety_gap_score").sort_values("allergen_safety_gap_score")
    c.plotly_chart(px.bar(top,x="allergen_safety_gap_score",y="kitchen_id",orientation="h",color="primary_driver",text_auto=".0f",range_x=[0,100],title="Top review priorities",template="plotly_white"),width="stretch")
    d,e=st.columns(2)
    wp=add_positive_size_column(view,"deviations_30d")
    d.plotly_chart(px.scatter(wp,x="cross_contact_control",y="allergen_safety_gap_score",size="plot_size",color="zone",range_x=[0,1],range_y=[0,100],title="Cross-contact controls × safety gap",template="plotly_white"),width="stretch")
    mp=add_positive_size_column(view,"average_servings")
    e.plotly_chart(px.scatter(mp,x="allergen_menu_share",y="allergen_safety_gap_score",size="plot_size",color="zone",range_x=[0,1],range_y=[0,100],title="Allergen-menu share × safety gap",template="plotly_white"),width="stretch")
    st.dataframe(view.sort_values("allergen_safety_gap_score",ascending=False),width="stretch",hide_index=True)
    visual=ROOT/"assets/allergensafe_dashboard_visual.svg"
    if visual.exists(): st.image(str(visual),width="stretch")

elif page=="Ingredient Safety":
    st.markdown('<div class="section">Ingredient safety context</div>',unsafe_allow_html=True)
    ing=frames["ingredients"]
    a,b=st.columns(2)
    verify=ing.supplier_verification.astype(str).value_counts().rename_axis("status").reset_index(name="count")
    a.plotly_chart(px.pie(verify,names="status",values="count",hole=.55,title="Supplier-verification status",template="plotly_white"),width="stretch")
    al=ing.declared_allergen.astype(str).str.title().value_counts().rename_axis("allergen").reset_index(name="ingredient_count")
    al=al[~al.allergen.str.lower().eq("None")]
    b.plotly_chart(px.bar(al,x="allergen",y="ingredient_count",color="allergen",title="Declared allergen presence",template="plotly_white"),width="stretch")
    st.dataframe(ing,width="stretch",hide_index=True)

elif page=="Menu Allergen Map":
    st.markdown('<div class="section">Menu allergen profile</div>',unsafe_allow_html=True)
    st.plotly_chart(px.bar(menu_summary,x="allergen",y="total_menu_mentions",color="allergen",text_auto=True,title="Allergen mentions across menus",template="plotly_white"),width="stretch")
    st.dataframe(menu_summary,width="stretch",hide_index=True)

elif page=="Storage Controls":
    st.markdown('<div class="section">Storage-control readiness</div>',unsafe_allow_html=True)
    s=frames["storage"]; a,b=st.columns(2)
    a.plotly_chart(px.scatter(s,x="segregation_index",y="labeling_readiness_index",size="open_container_count",color="storage_status",range_x=[0,1],range_y=[0,1],title="Segregation × labeling readiness",template="plotly_white"),width="stretch")
    b.plotly_chart(px.scatter(s,x="cleaning_readiness_index",y="spill_events_30d",size="open_container_count",color="separation_method",range_x=[0,1],title="Cleaning readiness × spill events",template="plotly_white"),width="stretch")
    st.dataframe(s,width="stretch",hide_index=True)

elif page=="Preparation Workflows":
    st.markdown('<div class="section">Preparation workflow controls</div>',unsafe_allow_html=True)
    a,b=st.columns(2)
    a.plotly_chart(px.scatter(workflow_summary,x="avg_cross_contact_control",y="avg_sanitation_readiness",size="average_deviations",color="workflow_step",range_x=[0,1],range_y=[0,1],title="Cross-contact control × sanitation readiness",template="plotly_white"),width="stretch")
    step=workflow_summary.groupby("workflow_step",as_index=False)["fail_share"].mean().sort_values("fail_share",ascending=False)
    b.plotly_chart(px.bar(step,x="workflow_step",y="fail_share",color="workflow_step",range_y=[0,1],title="Failure share by workflow step",template="plotly_white"),width="stretch")
    st.dataframe(workflow_summary,width="stretch",hide_index=True)

elif page=="Kitchen Comparison":
    st.markdown('<div class="section">Kitchen-level comparison</div>',unsafe_allow_html=True)
    comp=view[["kitchen_id","school","zone","allergen_safety_gap_score","risk_band","segregation_index","labeling_readiness_index","cross_contact_control","sanitation_readiness","allergen_menu_share","review_menu_share","deviations_30d","primary_driver"]]
    st.plotly_chart(px.scatter(comp,x="cross_contact_control",y="allergen_safety_gap_score",size="deviations_30d",color="risk_band",hover_name="kitchen_id",range_x=[0,1],range_y=[0,100],title="Kitchen workflow control × gap",template="plotly_white"),width="stretch")
    st.dataframe(comp.sort_values("allergen_safety_gap_score",ascending=False),width="stretch",hide_index=True)

elif page=="Priority Queue":
    st.markdown('<div class="section">Safety review priority queue</div>',unsafe_allow_html=True)
    q=view.sort_values(["allergen_safety_gap_score","suggested_review_actions"],ascending=False)
    st.dataframe(q,width="stretch",hide_index=True)
    st.download_button("⬇️ Download priority queue",q.to_csv(index=False).encode("utf-8"),file_name="school_meal_allergen_safety_priority_queue.csv",mime="text/csv")

elif page=="Trend & Signals":
    st.markdown('<div class="section">Operational signals</div>',unsafe_allow_html=True)
    tr=frames["workflows"].groupby("workflow_step",as_index=False).agg(avg_control=("cross_contact_control_index","mean"),deviations=("deviations_30d","sum"),failures=("verification_status",lambda x:x.astype(str).str.lower().eq("fail").sum()))
    a,b=st.columns(2)
    a.plotly_chart(px.bar(tr,x="workflow_step",y="deviations",color="workflow_step",title="Workflow deviations",template="plotly_white"),width="stretch")
    b.plotly_chart(px.scatter(tr,x="avg_control",y="failures",size="deviations",color="workflow_step",range_x=[0,1],title="Control level × failures",template="plotly_white"),width="stretch")
    st.dataframe(tr,width="stretch",hide_index=True)

elif page=="Scenario Lab":
    st.markdown('<div class="section">Allergen Safety Scenario Lab</div>',unsafe_allow_html=True)
    st.caption("Scenario weights change planning emphasis only; they do not certify food safety, establish compliance, or replace qualified review.")
    a,b,c,d=st.columns(4)
    with a: wa=st.slider("Allergen complexity",10,50,34)
    with b: ws=st.slider("Storage controls",10,45,28)
    with c: ww=st.slider("Preparation controls",10,45,28)
    with d: wo=st.slider("Operational pressure",5,25,10)
    w=np.array([wa,ws,ww,wo],dtype=float); w/=w.sum(); sc=view.copy()
    # Allergen complexity uses stable portfolio-level signal.
    ing_allergen=(~frames["ingredients"]["declared_allergen"].astype(str).str.lower().isin(["none","nan",""])).mean()
    ing_ver_gap=1-frames["ingredients"]["supplier_verification"].astype(str).str.lower().eq("verified").mean()
    allergen_component=(.55*ing_allergen+.25*sc.allergen_menu_share+.20*ing_ver_gap).clip(0,1)
    storage_component=(.50*(1-sc.segregation_index)+.25*(1-sc.labeling_readiness_index)+.15*sc.at_risk_share+.10*(sc.open_container_count/15).clip(0,1)).clip(0,1)
    workflow_component=(.38*(1-sc.cross_contact_control)+.22*(1-sc.utensil_separation)+.18*(1-sc.surface_separation)+.14*(1-sc.changeover_discipline)+.08*sc.failure_share).clip(0,1)
    operations_component=(.40*sc.review_menu_share+.30*(sc.deviations_30d/20).clip(0,1)+.30*sc.high_intensity_share).clip(0,1)
    sc["scenario_score"]=(100*(w[0]*allergen_component+w[1]*storage_component+w[2]*workflow_component+w[3]*operations_component)).clip(0,100).round(1)
    sc["scenario_change"]=(sc.scenario_score-sc.allergen_safety_gap_score).round(1)
    st.dataframe(sc[["kitchen_id","school","zone","allergen_safety_gap_score","scenario_score","scenario_change","primary_driver"]].sort_values("scenario_score",ascending=False),width="stretch",hide_index=True)
    st.download_button("⬇️ Download scenario CSV",sc.to_csv(index=False).encode("utf-8"),file_name="school_meal_allergen_safety_scenario.csv",mime="text/csv")

else:
    st.markdown('<div class="section">Reports & export</div>',unsafe_allow_html=True)
    exports=[("Scored kitchens",scored,"scored_kitchen_allergen_safety.csv"),("Ingredients",frames["ingredients"],"ingredients.csv"),("Menus",frames["menus"],"menus.csv"),("Storage",frames["storage"],"storage_controls.csv"),("Preparation workflows",frames["workflows"],"preparation_workflows.csv"),("Menu allergen summary",menu_summary,"menu_allergen_summary.csv"),("Workflow summary",workflow_summary,"workflow_summary.csv")]
    for label,data,filename in exports:
        st.download_button(f"⬇️ Download {label}",data.to_csv(index=False).encode("utf-8"),file_name=filename,mime="text/csv")

st.markdown("""<div class="note"><b>Important:</b> Screening signals are planning aids. They do not certify allergen safety, establish regulatory compliance, diagnose individual medical risk, or replace school food-service procedures, qualified food-safety professionals, allergen-control plans, or applicable standards.</div><div class="footer">100% local CSV processing • No external APIs • Explainable heuristics • Human-in-the-loop review • Synthetic demonstration data</div>""",unsafe_allow_html=True)
