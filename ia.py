"""
ia.py - RMS Internal Audit Action Tracker (Streamlit UI).

Entry point used by app.py:   render_page()

Layout
------
Hero  →  one tab per audit report (Regional Warehouses · Central Warehouse)  →  Export & Settings  →  Activity log
Each report tab:  report card · KPI cards · [ Findings & actions | Dashboard | KPI scoreboard | Action register ]
"""
import base64
import html as _html
import inspect
import os
import zlib
from collections import defaultdict
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode, JsCode
from streamlit_quill import st_quill

import ia_core as core
import ia_db
import ia_export
import ia_seed_data as seed

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(HERE, "logo.jpg")


def _stretch(fn):
    """Streamlit renamed use_container_width -> width='stretch'; support both."""
    return {"width": "stretch"} if "width" in inspect.signature(fn).parameters else {"use_container_width": True}


S_BTN = _stretch(st.button)
S_DF = _stretch(st.dataframe)
S_ED = _stretch(st.data_editor)
S_CH = _stretch(st.altair_chart)
S_DL = _stretch(st.download_button)

esc = lambda s: _html.escape("" if s is None else str(s), quote=True)  # noqa: E731

# ---------------------------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------------------------
PAGE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.ia{font-size:15px;line-height:1.55;}
.ia, .ia *{font-family:'Inter','Segoe UI','Source Sans Pro',system-ui,-apple-system,sans-serif;}
header{visibility:hidden;} #MainMenu{visibility:hidden;}
.block-container,[data-testid="stMainBlockContainer"]{padding-top:.2rem!important;padding-left:.9rem!important;padding-right:.9rem!important;max-width:100%!important;}

/* hero */
.ia-hero{display:flex;align-items:center;gap:16px;flex-wrap:wrap;background:linear-gradient(120deg,#12294f 0%,#1e3c72 42%,#2f5fb3 100%);
  color:#fff;border-radius:20px;padding:16px 26px;margin:8px 0 12px;box-shadow:0 6px 16px rgba(30,60,114,.22);}
.ia-logo{width:42px;height:42px;border-radius:10px;background:#fff;display:flex;align-items:center;justify-content:center;overflow:hidden;flex:0 0 auto;}
.ia-logo img{width:100%;height:100%;object-fit:contain;}
.ia-hero-text{flex:1 1 300px;min-width:240px;}
.ia-eyebrow{font-size:11px;letter-spacing:.12em;font-weight:700;opacity:.7;text-transform:uppercase;}
.ia-h1{font-size:22px;font-weight:800;line-height:1.2;margin:1px 0;color:#fff;}
.ia-sub{font-size:13px;opacity:.85;color:#fff;}
.ia-hero-right{display:flex;align-items:center;gap:10px;}
.ia-ring{--p:0;width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  background:conic-gradient(#4ade80 calc(var(--p)*1%),rgba(255,255,255,.22) 0);}
.ia-ring>div{width:41px;height:41px;border-radius:50%;background:#1b3868;display:flex;align-items:center;justify-content:center;}
.ia-ring b{font-size:12px;font-weight:800;color:#fff;}
.ia-pill{background:rgba(255,255,255,.14);border:2px solid rgba(255,255,255,.35);border-radius:14px;padding:8px 14px;text-align:center;line-height:1.15;color:#fff;}
.ia-pill b{display:block;font-size:19px;font-weight:800;color:#fff;}
.ia-pill span{font-size:10.5px;opacity:.85;text-transform:uppercase;letter-spacing:.05em;color:#fff;}
.ia-pill.bad{background:rgba(239,68,68,.30);border-color:rgba(254,202,202,.6);}

/* report card */
.ia-rep{display:flex;gap:18px;flex-wrap:wrap;align-items:stretch;background:#fff;border:2px solid #1e3c72;border-radius:20px;padding:18px 24px;margin:6px 0 16px;box-shadow:0 4px 16px rgba(30,60,114,.10);}
.ia-rep .l{flex:2 1 420px;min-width:300px;}
.ia-rep .r{flex:1 1 320px;min-width:280px;}
.ia-rep h3{margin:0 0 6px;font-size:19px;font-weight:800;color:#12294f;}
.ia-rep .meta{font-size:13.5px;color:#475569;line-height:1.7;}
.ia-rep .meta b{color:#0f172a;}
.ia-rep .concl{margin-top:10px;font-size:13.5px;color:#334155;background:#f6f9ff;border:1.5px solid #c7d6f0;padding:10px 14px;border-radius:12px;}
.ia-scale{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:8px;align-items:center;}
.ia-scale span{font-size:11.5px;text-align:center;padding:11px 6px;border-radius:10px;background:#eef2f8;color:#6b7a92;font-weight:600;line-height:1.25;border:2px solid transparent;}
.ia-scale span.on{color:#fff;font-weight:700;font-size:12px;padding:11px 6px;border:2px solid var(--rc);box-shadow:0 3px 8px color-mix(in srgb,var(--rc) 28%,transparent);}
.ia-scale span.on.l1{--rc:#b91c1c;background:#b91c1c;} .ia-scale span.on.l2{--rc:#ea580c;background:#ea580c;} .ia-scale span.on.l3{--rc:#ca8a04;background:#ca8a04;}
.ia-scale span.on.l4{--rc:#16a34a;background:#16a34a;} .ia-scale span.on.l5{--rc:#15803d;background:#15803d;}
.ia-rating-head{display:inline-flex;align-items:center;gap:6px;margin-top:6px;padding:3px 12px;border-radius:99px;font-size:12.5px;font-weight:700;color:var(--rc);background:color-mix(in srgb,var(--rc) 12%,#fff);border:1.5px solid color-mix(in srgb,var(--rc) 45%,#fff);}
.ia-rep .lbl{font-size:11.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#64748b;}
.ia-note{font-size:12.5px;color:#64748b;margin-top:8px;}

/* KPI cards */
.ia-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:14px;margin:6px 0 14px;}
@media (max-width:1150px){.ia-kpis{grid-template-columns:repeat(3,minmax(0,1fr));}}
@media (max-width:640px){.ia-kpis{grid-template-columns:repeat(2,minmax(0,1fr));}}
.ia-kpi{background:color-mix(in srgb,var(--c) 7%,#fff);border:2px solid var(--c);border-radius:20px;padding:14px 20px;position:relative;overflow:hidden;box-shadow:0 4px 14px color-mix(in srgb,var(--c) 14%,transparent);}
.ia-kpi .ic{position:absolute;right:14px;top:12px;font-size:20px;}
.ia-kpi .lb{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#64748b;}
.ia-kpi .vl{font-size:30px;font-weight:800;color:#0f172a;line-height:1.15;margin-top:4px;}
.ia-kpi .sb{font-size:12.5px;color:#64748b;font-weight:600;}

/* area header */
.ia-sec{display:flex;align-items:center;gap:16px;margin:26px 0 14px;padding:12px 20px;border-radius:18px;background:linear-gradient(90deg,#eaf0fa,#f8faff);border:2px solid #2f5fb3;}
.ia-sec .num{min-width:44px;height:44px;border-radius:14px;background:linear-gradient(135deg,#1e3c72,#2f5fb3);color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:16px;padding:0 6px;}
.ia-sec .tt{font-size:19px;font-weight:800;color:#12294f;flex:1;}
.ia-sec .mt{font-size:13.5px;color:#475569;font-weight:600;text-align:right;white-space:nowrap;}
.ia-sec .bar{width:150px;height:10px;border-radius:99px;background:#d6e0f2;overflow:hidden;flex:0 0 auto;}
.ia-sec .bar span{display:block;height:100%;background:linear-gradient(90deg,#34d399,#22c55e);border-radius:99px;}

/* finding cards */
div[class*="st-key-iacard-"]{--bc:#94a3b8;background:color-mix(in srgb,var(--bc) 4%,#fff);border:2px solid var(--bc);border-radius:20px;padding:22px 26px 18px;margin-bottom:18px;box-shadow:0 3px 12px color-mix(in srgb,var(--bc) 12%,transparent);}
div[class*="st-key-iacard-"]:hover{box-shadow:0 10px 28px color-mix(in srgb,var(--bc) 24%,transparent);}
div[class*="st-key-iacard-closed-"]{--bc:#16a34a;}
div[class*="st-key-iacard-verify-"]{--bc:#7c3aed;}
div[class*="st-key-iacard-progress-"]{--bc:#f59e0b;}
div[class*="st-key-iacard-overdue-"]{--bc:#dc2626;}
div[class*="st-key-iacard-disputed-"]{--bc:#ea580c;}
div[class*="st-key-iacard-pending-"]{--bc:#94a3b8;}
div[class*="st-key-iacard-"] button{min-height:2.5rem;padding:.3rem .9rem;font-size:14px;border-radius:12px;}
.ia-head{display:flex;gap:16px;align-items:flex-start;}
.ia-ref{min-width:54px;height:36px;padding:0 10px;border-radius:12px;color:#fff;font-weight:800;font-size:15px;display:flex;align-items:center;justify-content:center;background:#64748b;flex:0 0 auto;margin-top:1px;}
.ia-ref.closed{background:#16a34a;} .ia-ref.verify{background:#7c3aed;} .ia-ref.progress{background:#ca8a04;}
.ia-ref.overdue{background:#dc2626;} .ia-ref.disputed{background:#ea580c;} .ia-ref.pending{background:#64748b;}
.ia-title{font-size:18px;font-weight:800;color:#0f172a;line-height:1.35;}
.ia-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px;}
.chip{display:inline-block;font-size:12.5px;font-weight:700;padding:4px 12px;border-radius:99px;background:#eef2f8;color:#334155;white-space:nowrap;}
.chip.area{background:#e0e9fb;color:#1e3c72;} .chip.src{background:#f1f5f9;color:#64748b;font-weight:600;}
.chip.p-High{background:#fee2e2;color:#991b1b;} .chip.p-Medium{background:#fef3c7;color:#92400e;} .chip.p-Low{background:#e2e8f0;color:#475569;}
.chip.m-Agreed{background:#dcfce7;color:#166534;} .chip.m-Partially{background:#fef3c7;color:#92400e;}
.chip.m-Disagreed{background:#ffedd5;color:#9a3412;} .chip.m-Reported{background:#ede9fe;color:#5b21b6;} .chip.m-No{background:#e2e8f0;color:#475569;}
.chip.flag{background:#fff7ed;color:#9a3412;border:1px solid #fed7aa;}
.ia-prog{display:flex;align-items:center;gap:14px;margin:16px 0 12px;flex-wrap:wrap;}
.ia-prog .bar{width:240px;height:11px;border-radius:99px;background:#e2e8f0;overflow:hidden;}
.ia-prog .bar span{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#34d399,#16a34a);}
.ia-prog b{font-size:15px;color:#0f172a;} .ia-prog .cnt{font-size:13px;color:#64748b;font-weight:600;}
.ia-act{display:grid;grid-template-columns:290px minmax(0,1fr) 280px 210px;column-gap:16px;row-gap:4px;align-items:start;padding:11px 0;border-top:1px dashed #d8e0ee;font-size:14.5px;color:#1e293b;}
.ia-act .st{justify-self:start;white-space:nowrap;font-size:12px;font-weight:800;padding:5px 12px;border-radius:99px;line-height:1.3;text-align:left;}
.ia-act .tx{display:flex;gap:10px;line-height:1.55;min-width:0;}
.ia-act .tx .rf{flex:0 0 auto;min-width:50px;color:#0f172a;}
.ia-act .ow{font-size:13px;color:#475569;line-height:1.45;padding-top:3px;} .ia-act .ow i{color:#b45309;font-style:normal;font-size:10px;font-weight:700;}
.ia-act .du{font-size:13px;font-weight:700;line-height:1.45;padding-top:3px;}
.ia-act .nt{grid-column:2 / -1;font-size:13px;color:#64748b;}
@media (max-width:1300px){.ia-act{grid-template-columns:250px minmax(0,1fr);}.ia-act .ow,.ia-act .du{grid-column:2;padding-top:0;}}
.d-over{color:#b91c1c;} .d-soon{color:#b45309;} .d-ok{color:#475569;} .d-none{color:#94a3b8;font-weight:600;}
.ia-kt{width:100%;border-collapse:separate;border-spacing:0;margin-top:14px;font-size:14px;border:1.5px solid #d8e0ee;border-radius:14px;overflow:hidden;background:#fff;}
.ia-kt th{text-align:left;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:#475569;padding:10px 14px;background:#f3f6fb;border-bottom:1.5px solid #d8e0ee;font-weight:700;}
.ia-kt td{padding:11px 14px;border-bottom:1px solid #eef2f8;vertical-align:middle;color:#0f172a;}
.ia-kt td.n{white-space:nowrap;font-variant-numeric:tabular-nums;}
.ia-kt td.t{color:#475569;}
.ia-pb{display:inline-block;width:110px;height:10px;border-radius:99px;background:#e2e8f0;overflow:hidden;vertical-align:middle;margin-right:6px;}
.ia-pb i{display:block;height:100%;border-radius:99px;}
.ia-tr{font-size:12px;font-weight:700;}
.ia-det{margin-top:14px;font-size:14px;} .ia-det summary{cursor:pointer;font-weight:700;color:#1e3c72;font-size:14px;padding:3px 0;}
.ia-det .g{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:10px;}
.ia-det .g>div{background:#f8fafc;border:1.5px solid #e2e8f2;border-radius:14px;padding:12px 16px;color:#334155;line-height:1.6;}
.ia-det .g b{display:block;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:#64748b;margin-bottom:2px;}
.ia-bkt{font-size:13.5px;font-weight:800;color:#12294f;margin:14px 0 6px;}
.bk{display:flex;align-items:center;gap:12px;margin:5px 0;font-size:13px;}
.bk .lb{width:170px;color:#334155;font-weight:600;flex:0 0 auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.bk .tr{position:relative;flex:1 1 200px;height:16px;background:#f1f5f9;border-radius:8px;overflow:hidden;min-width:120px;}
.bk .tr i{position:absolute;left:0;top:0;bottom:0;border-radius:8px;display:block;}
.bk .tr i.b{background:#cbd5e1;} .bk .tr i.c{top:4px;bottom:4px;}
.bk .tr u{position:absolute;top:0;bottom:0;width:2px;background:#0f172a;opacity:.7;}
.bk .nm{width:300px;color:#475569;font-variant-numeric:tabular-nums;flex:0 0 auto;text-align:right;white-space:nowrap;}
.bk .nm b{color:#0f172a;margin-left:4px;}
.ia-leg{font-size:12px;color:#64748b;margin:2px 0 0 0;}
.ia-empty{text-align:center;padding:30px;color:#64748b;background:#fff;border:1px dashed #cbd5e1;border-radius:14px;}
.ia-box{background:#f6f9ff;border:1.5px solid #c7d6f0;border-radius:14px;padding:12px 16px;font-size:14px;color:#334155;}

/* ===== highlighted buttons (every button is clearly clickable) ===== */
[data-testid^="stBaseButton-secondary"],[data-testid^="stBaseButton-primary"]{
  background:linear-gradient(135deg,#3b6fd0,#1e3c72)!important;color:#fff!important;border:2px solid #1e3c72!important;border-radius:14px!important;
  font-weight:800!important;min-height:2.8rem!important;padding:.4rem 1.2rem!important;box-shadow:0 5px 14px rgba(30,60,114,.38)!important;
  transition:transform .12s ease,box-shadow .12s ease,filter .12s ease;}
[data-testid^="stBaseButton-secondary"] *,[data-testid^="stBaseButton-primary"] *{color:#fff!important;font-weight:800!important;font-size:15px!important;}
[data-testid^="stBaseButton-secondary"]:hover,[data-testid^="stBaseButton-primary"]:hover{transform:translateY(-2px);filter:brightness(1.14);box-shadow:0 10px 22px rgba(30,60,114,.5)!important;}
[data-testid^="stBaseButton-secondary"]:active,[data-testid^="stBaseButton-primary"]:active{transform:translateY(0);}
[data-testid^="stBaseButton-primary"]{background:linear-gradient(135deg,#22c55e,#15803d)!important;border-color:#15803d!important;box-shadow:0 5px 14px rgba(21,128,61,.42)!important;}
[data-testid^="stBaseButton-primary"]:hover{box-shadow:0 10px 22px rgba(21,128,61,.55)!important;}
[class*="st-key-del"] [data-testid^="stBaseButton"]{background:linear-gradient(135deg,#ef4444,#b91c1c)!important;border-color:#b91c1c!important;box-shadow:0 5px 14px rgba(185,28,28,.4)!important;}
[data-testid^="stBaseButton-secondary"]:disabled,[data-testid^="stBaseButton-primary"]:disabled{background:#cbd5e1!important;border-color:#94a3b8!important;box-shadow:none!important;opacity:.7;}
[data-testid="stFileUploaderDropzone"]{border:2px dashed #2f5fb3!important;background:#f3f7ff!important;border-radius:16px!important;}
/* section switcher inside the popup */
[data-testid="stButtonGroup"] button{font-weight:800!important;font-size:14.5px!important;padding:.55rem 1.1rem!important;border:2px solid #c7d6f0!important;border-radius:12px!important;background:#fff!important;color:#1e3c72!important;}
[data-testid="stButtonGroup"] button *{color:inherit!important;font-weight:800!important;}
[data-testid="stButtonGroup"] button[aria-checked="true"],[data-testid="stBaseButton-segmented_controlActive"]{background:linear-gradient(135deg,#3b6fd0,#1e3c72)!important;color:#fff!important;border-color:#1e3c72!important;box-shadow:0 4px 12px rgba(30,60,114,.35)!important;}
/* ===== clickable KPI cards (same look; an invisible button sits on top) ===== */
[class*="st-key-kpi-"]{position:relative;}
[class*="st-key-kpib-"]{position:absolute!important;inset:0;z-index:6;margin:0!important;}
[class*="st-key-kpib-"] [data-testid="stElementContainer"],[class*="st-key-kpib-"] .stButton{width:100%!important;height:100%!important;}
[class*="st-key-kpib-"] [data-testid^="stBaseButton"]{opacity:0!important;background:transparent!important;border:0!important;box-shadow:none!important;width:100%!important;height:100%!important;min-height:100px!important;padding:0!important;cursor:pointer!important;}
[class*="st-key-kpi-"]:hover .ia-kpi{transform:translateY(-3px);box-shadow:0 12px 26px color-mix(in srgb,var(--c) 30%,transparent);}
.ia-kpi{min-height:118px;transition:transform .12s ease,box-shadow .12s ease;}
.ia-kpi.on{box-shadow:0 0 0 5px color-mix(in srgb,var(--c) 28%,transparent),0 10px 24px color-mix(in srgb,var(--c) 32%,transparent);}
.ia-kpi .tag{position:absolute;right:14px;bottom:10px;font-size:10.5px;font-weight:800;letter-spacing:.08em;color:var(--c);}
.ia-notice{display:flex;align-items:center;gap:12px;background:#fff7e6;border:2px solid #f59e0b;border-radius:16px;padding:12px 20px;font-size:15px;color:#7c2d12;font-weight:600;min-height:2.8rem;}
.ia-hint{font-size:13px;color:#64748b;margin:2px 0 10px;}
.ia-sel{display:flex;align-items:center;gap:10px;background:#f3f7ff;border:2px dashed #2f5fb3;border-radius:14px;padding:12px 18px;font-size:14.5px;color:#1e3c72;font-weight:700;min-height:2.8rem;}

/* ===== home cards ===== */
.ia-home-h{font-size:26px;font-weight:800;color:#12294f;margin:10px 0 2px;}
.ia-home-s{font-size:15px;color:#64748b;margin-bottom:16px;}
[class*="st-key-home-"]{position:relative;}
[class*="st-key-homeb-"]{position:absolute!important;inset:0;z-index:6;margin:0!important;}
[class*="st-key-homeb-"] [data-testid="stElementContainer"],[class*="st-key-homeb-"] .stButton{width:100%!important;height:100%!important;}
[class*="st-key-homeb-"] [data-testid^="stBaseButton"]{opacity:0!important;background:transparent!important;border:0!important;box-shadow:none!important;width:100%!important;height:100%!important;min-height:200px!important;padding:0!important;cursor:pointer!important;}
.ia-home{background:linear-gradient(135deg,var(--g1),var(--g2));border:3px solid var(--bd);border-radius:28px;padding:34px 28px;text-align:center;box-shadow:0 8px 22px color-mix(in srgb,var(--bd) 35%,transparent);transition:transform .14s ease,box-shadow .14s ease;}
[class*="st-key-home-"]:hover .ia-home{transform:translateY(-5px);box-shadow:0 16px 34px color-mix(in srgb,var(--bd) 55%,transparent);}
.ia-home .ico{width:104px;height:104px;border-radius:26px;background:#fff;display:flex;align-items:center;justify-content:center;margin:0 auto 18px;font-size:54px;box-shadow:0 6px 16px rgba(0,0,0,.08);}
.ia-home .t{font-size:26px;font-weight:800;color:var(--tt);}
.ia-home .s{font-size:16px;color:var(--st);margin-top:6px;font-weight:600;}
.ia-home .n{font-size:14px;color:var(--tt);margin-top:14px;font-weight:700;opacity:.85;}
.ia-home .go{display:inline-block;margin-top:16px;padding:8px 22px;border-radius:99px;background:var(--tt);color:#fff;font-weight:800;font-size:14px;}
/* ===== find-your-items filter bar ===== */
[class*="st-key-ia-filterbar-"]{background:#f6f9ff;border:2px solid #c7d6f0;border-radius:20px;padding:14px 20px 8px;margin:6px 0 12px;}
.ia-fb-t{font-size:18px;font-weight:800;color:#12294f;} .ia-fb-s{font-size:14px;color:#475569;margin:2px 0 8px;}
[class*="st-key-ownfilter-"]{background:#fff7e6;border:3px solid #f59e0b;border-radius:16px;padding:8px 14px 4px;box-shadow:0 0 0 5px rgba(245,158,11,.20);}
[class*="st-key-ownfilter-"] label p{font-weight:800!important;color:#92400e!important;font-size:14.5px!important;}
.ia-steps{display:flex;flex-wrap:wrap;gap:10px;margin:4px 0 10px;}
.ia-steps span{background:#fff;border:2px solid #c7d6f0;border-radius:14px;padding:8px 14px;font-size:14px;font-weight:700;color:#1e3c72;}
.ia-steps b{color:#fff;background:#1e3c72;border-radius:99px;padding:1px 9px;margin-right:6px;}

.ia-slim{display:flex;align-items:center;gap:26px;flex-wrap:wrap;background:#fff;border:2px solid #1e3c72;border-radius:18px;padding:10px 22px;margin:2px 0 12px;box-shadow:0 3px 10px rgba(30,60,114,.08);}
.ia-slim .tt{flex:1 1 300px;min-width:240px;} .ia-slim .t{font-size:19px;font-weight:800;color:#12294f;line-height:1.25;} .ia-slim .m{font-size:13px;color:#64748b;margin-top:1px;}
.ia-slim .rt{flex:1.4 1 420px;min-width:320px;} .ia-slim .pg{flex:0 1 270px;}
.ia-slim .lbl{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#64748b;}
.ia-slim .ia-scale{margin:3px 0 0!important;} .ia-scale.sm span{font-size:11px;padding:7px 4px;} .ia-scale.sm span.on{font-size:11.5px;padding:7px 4px;}
</style>
"""

# ---------------------------------------------------------------------------------------------
# Data model for one run
# ---------------------------------------------------------------------------------------------
def build_model():
    findings = ia_db.load_findings().to_dict("records")
    actions = ia_db.load_actions().to_dict("records")
    kpis = ia_db.load_kpis()
    docs = ia_db.docs_summary()
    comments = ia_db.comments_all()
    by_a, by_k = defaultdict(list), defaultdict(list)
    for a in actions:
        by_a[a["finding_id"]].append(a)
    for k in kpis:
        by_k[k["finding_id"]].append(k)
    for f in findings:
        f["actions"] = by_a[f["id"]]
        f["kpis"] = by_k[f["id"]]
        f["state"] = core.finding_state(f["actions"])
        f["pct"] = core.finding_pct(f["actions"])
        f["docs"] = docs.get(f["id"], [])
        f["comments"] = comments.get(f["id"], [])
        fv = f["flagged_value"]
        f["flagged_value"] = None if fv is None or pd.isna(fv) else float(fv)
    return {"findings": findings, "actions": actions, "kpis": kpis, "docs": docs, "comments": comments}


def _user():
    return (st.session_state.get("ia_user") or "").strip()


def _toast(msg):
    """Show a message after the next full rerun and force the table to reload from the database."""
    st.session_state["_ia_toast"] = msg
    st.session_state["ia_ver"] = st.session_state.get("ia_ver", 0) + 1


def _logo_b64():
    try:
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except OSError:
        return ""


# ---------------------------------------------------------------------------------------------
# Small HTML builders
# ---------------------------------------------------------------------------------------------
_PRI = {"High": ("#fee2e2", "#991b1b"), "Medium": ("#fef3c7", "#92400e"), "Low": ("#e2e8f0", "#475569")}
_MG = {"Agreed": ("#dcfce7", "#166534"), "Partially": ("#fef3c7", "#92400e"), "Disagreed": ("#ffedd5", "#9a3412"),
       "Reported": ("#ede9fe", "#5b21b6"), "No": ("#e2e8f0", "#475569")}


def _ichip(text, bg, fg, border=""):
    b = f"border:1.5px solid {border};" if border else ""
    return (f"<span style='display:inline-block;font-size:12px;font-weight:700;padding:3px 11px;border-radius:99px;background:{bg};"
            f"color:{fg};white-space:nowrap;margin:3px 6px 3px 0;{b}'>{esc(text)}</span>")


def _kpi_color(k):
    raw = core.kpi_progress(k["baseline"], k["current"], k["target"])
    if raw is None:
        return "#2f5fb3"
    return "#16a34a" if raw >= 0.999 else ("#22c55e" if raw > 0.0005 else ("#dc2626" if raw < -0.0005 else "#94a3b8"))


def _finding_cell(f):
    """Findings column (shown on the first row of each finding)."""
    label, col, soft = core.STATE[f["state"]]
    live = [a for a in f["actions"] if a["status"] != core.NA]
    n_closed = sum(1 for a in live if a["status"] == core.CL)
    chips = _ichip(f["area"], "#e0e9fb", "#1e3c72") + _ichip(f"● {f['priority']} priority", *_PRI.get(f["priority"], _PRI["Medium"]))
    if f["flagged_label"]:
        chips += _ichip("💰 " + f["flagged_label"], "#fff7ed", "#9a3412", "#fed7aa")
    return (f"<div style='font-family:Inter,Segoe UI,sans-serif;padding:2px 0'>"
            f"<div style='display:flex;gap:8px;align-items:flex-start'><span style='flex:0 0 auto;background:{col};color:#fff;font-weight:800;font-size:13px;padding:3px 9px;border-radius:9px'>{esc(f['ref'])}</span>"
            f"<span style='font-weight:800;font-size:14.5px;line-height:1.35;color:#0f172a'>{esc(core.plain(f['title']))}</span></div>"
            f"<div style='display:flex;flex-wrap:wrap;margin-top:6px'>{chips}</div>"
            f"<div style='display:flex;align-items:center;gap:8px;margin-top:4px'><div style='width:120px;height:9px;border-radius:99px;background:#e2e8f0;overflow:hidden'>"
            f"<div style='width:{f['pct']}%;height:100%;background:linear-gradient(90deg,#34d399,#16a34a)'></div></div><b style='font-size:13px'>{f['pct']}%</b>"
            f"<span style='font-size:12px;color:#64748b;font-weight:600'>{n_closed}/{len(live)} closed</span></div></div>")


def _kpi_cell(f):
    """KPIs column: each KPI as name, now -> target and a progress bar."""
    if not f["kpis"]:
        return "<span style='color:#94a3b8'>No KPIs</span>"
    out = []
    for k in f["kpis"]:
        pct = core.kpi_pct(k["baseline"], k["current"], k["target"])
        unit = k["unit"]
        tgt = "target not set" if k["target"] is None else ("target " + ("≥ " if (unit in ("%", "days") and k["baseline"] is not None and k["target"] > k["baseline"]) else ("≤ " if unit in ("%", "days") else "")) + core.fmt_value(k["target"], unit))
        bar = ("" if pct is None else
               f"<div style='display:flex;align-items:center;gap:6px;margin-top:3px'><div style='flex:1;height:8px;border-radius:99px;background:#e2e8f0;overflow:hidden'>"
               f"<div style='width:{pct}%;height:100%;background:{_kpi_color(k)}'></div></div><b style='font-size:12px'>{pct}%</b></div>")
        out.append(f"<div style='margin:0 0 9px 0;font-family:Inter,Segoe UI,sans-serif'><div style='font-size:12.5px;font-weight:700;color:#0f172a;line-height:1.3'>{esc(k['name'])}</div>"
                   f"<div style='font-size:12.5px;color:#475569'>Now <b style='color:#0f172a'>{esc(core.fmt_value(k['current'], unit))}</b> · {esc(tgt)}</div>{bar}</div>")
    return "".join(out)


def _timing(a):
    st_ = core.action_state(a["status"], a["due_date"])
    d = core.parse_date(a["due_date"])
    if a["status"] == core.CL:
        return "✔ Closed " + core.fmt_date(a["closed_date"]) if a["closed_date"] else "✔ Closed"
    if a["status"] == core.NA:
        return "—"
    if a["status"] == core.IPV:
        return "🔎 Awaiting IA verification"
    if d is None:
        return "⚠ No target date"
    dl = core.days_left(d)
    if st_ == "overdue":
        return f"⏰ {abs(dl)} days overdue"
    if a["status"] in core.OPEN_STATUSES and dl <= 14:
        return f"⏳ Due in {dl} day{'s' if dl != 1 else ''}"
    return "📅 " + core.fmt_date(d)


# ---------------------------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------------------------
def _find(fid):
    for f in build_model()["findings"]:
        if f["id"] == fid:
            return f
    return None


def _ulabel(u):
    return "Rwf" if u in ("Rwf", "Frw") else u


def _axis(unit, **kw):
    """Axis whose tick labels read 200K / 5M / 1.2B for Rwf values."""
    if unit in ("Rwf", "Frw"):
        return alt.Axis(labelExpr="replace(replace(format(datum.value,'~s'),'G','B'),'k','K')", **kw)
    return alt.Axis(**kw)


def _trend_chart(k, hist, by_item):
    unit = k["unit"]
    pts = []
    for h in hist:
        if by_item and h["detail"]:
            for lbl, v in h["detail"].items():
                pts.append({"date": pd.to_datetime(h["as_of"]), "value": v, "series": lbl})
        else:
            pts.append({"date": pd.to_datetime(h["as_of"]), "value": h["value"], "series": "Total" if unit != "%" or not k["breakdown"] else "Average"})
    df = pd.DataFrame(pts)
    if df.empty:
        return None
    df["text"] = df["value"].map(lambda v: core.fmt_value(v, unit))
    ytitle = _ulabel(unit) if unit != "flag" else "0 = not done · 1 = done"
    base = alt.Chart(df).encode(x=alt.X("date:T", title=None, axis=alt.Axis(format="%d %b %Y", labelFontSize=12)),
                                y=alt.Y("value:Q", title=ytitle, axis=_axis(unit, labelFontSize=12, titleFontSize=12), scale=alt.Scale(zero=False if unit == "%" else True, nice=True)),
                                tooltip=[alt.Tooltip("date:T", title="As of", format="%d %b %Y"), alt.Tooltip("series:N", title="Series"), alt.Tooltip("text:N", title="Value")])
    line = base.mark_line(point=alt.OverlayMarkDef(size=80, filled=True), strokeWidth=3).encode(color=alt.Color("series:N", legend=alt.Legend(title=None, orient="bottom", labelFontSize=12)))
    labels = base.mark_text(dy=-14, fontSize=12, fontWeight="bold").encode(text="text:N", color=alt.Color("series:N", legend=None))
    layers = [line, labels]
    rules = pd.DataFrame([{"y": k["baseline"], "label": "Baseline", "text": core.fmt_value(k["baseline"], unit)}]
                         + ([{"y": k["target"], "label": "Target", "text": core.fmt_value(k["target"], unit)}] if k["target"] is not None else []))
    if not by_item or not k["breakdown"]:
        r = alt.Chart(rules).mark_rule(strokeDash=[6, 4], strokeWidth=2).encode(
            y="y:Q", color=alt.Color("label:N", scale=alt.Scale(domain=["Baseline", "Target"], range=["#94a3b8", "#16a34a"]), legend=alt.Legend(title=None, orient="bottom", labelFontSize=12)),
            tooltip=[alt.Tooltip("label:N", title="Line"), alt.Tooltip("text:N", title="Value")])
        layers.append(r)
    return alt.layer(*layers).properties(height=300, padding={"top": 18, "right": 30}).resolve_scale(color="independent")


def _breakdown_chart(k):
    unit = k["unit"]
    rows = []
    for b in k["breakdown"]:
        rows.append({"item": b["label"], "series": "Baseline", "value": b["baseline"], "text": core.fmt_value(b["baseline"], unit)})
        rows.append({"item": b["label"], "series": "Current", "value": b["current"], "text": core.fmt_value(b["current"], unit)})
    df = pd.DataFrame(rows)
    order = [b["label"] for b in k["breakdown"]]
    enc = dict(x=alt.X("item:N", title=None, sort=order, axis=alt.Axis(labelAngle=-30, labelFontSize=12, labelLimit=200)), xOffset="series:N")
    y = alt.Y("value:Q", title=_ulabel(unit), axis=_axis(unit, labelFontSize=12, titleFontSize=12))
    col = alt.Color("series:N", scale=alt.Scale(domain=["Baseline", "Current"], range=["#cbd5e1", "#2f5fb3"]), legend=alt.Legend(title=None, orient="bottom", labelFontSize=12))
    tip = [alt.Tooltip("item:N", title="Item"), alt.Tooltip("series:N", title="Series"), alt.Tooltip("text:N", title="Value")]
    bars = alt.Chart(df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(y=y, color=col, tooltip=tip, **enc)
    labels = alt.Chart(df).mark_text(dy=-7, fontSize=11, fontWeight="bold", color="#334155").encode(y=alt.Y("value:Q"), text="text:N", **enc)
    ch = bars + labels
    if k["target"] not in (None, 0):
        ch = ch + alt.Chart(pd.DataFrame({"y": [k["target"]], "text": [core.fmt_value(k["target"], unit)]})).mark_rule(color="#16a34a", strokeDash=[6, 4], strokeWidth=2).encode(y="y:Q", tooltip=[alt.Tooltip("text:N", title="Target")])
    return ch.properties(height=320, padding={"top": 22})


def _kpis_body(fid):
    f = _find(fid)
    if not f or not f["kpis"]:
        st.info("This finding has no KPIs yet.")
        return
    st.caption(f"**{f['title']}**")
    df = pd.DataFrame([{"KPI": k["name"], "Baseline": core.fmt_value(k["baseline"], k["unit"]), "Current": core.fmt_value(k["current"], k["unit"]),
                        "Target": core.fmt_value(k["target"], k["unit"]) if k["target"] is not None else "not set",
                        "Progress": core.kpi_pct(k["baseline"], k["current"], k["target"]),
                        "Trend": core.TREND_LABEL[core.kpi_trend(k["baseline"], k["current"], k["target"])][0]} for k in f["kpis"]])
    st.dataframe(df, hide_index=True, column_config={"Progress": st.column_config.ProgressColumn("Progress", min_value=0, max_value=100, format="%d%%")}, **S_DF)
    names = {k["id"]: k["name"] for k in f["kpis"]}
    kid = st.selectbox("KPI", list(names), format_func=lambda i: names[i], key=f"kpisel_{fid}") if len(names) > 1 else list(names)[0]
    k = next(x for x in f["kpis"] if x["id"] == kid)
    unit = k["unit"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Baseline", core.fmt_value(k["baseline"], unit))
    m2.metric("Current", core.fmt_value(k["current"], unit), delta=None)
    m3.metric("Target", core.fmt_value(k["target"], unit) if k["target"] is not None else "not set")
    pct = core.kpi_pct(k["baseline"], k["current"], k["target"])
    m4.metric("Progress", f"{pct}%" if pct is not None else "—")
    if k["basis"]:
        st.caption(f"Target basis: {k['basis']}" + (f"  ·  {k['note']}" if k["note"] else ""))
    elif k["note"]:
        st.caption(k["note"])
    hist = ia_db.kpi_history(kid)
    tabs = st.tabs(["📈 Trend", "📍 Breakdown", "✍️ Record measurement", "🗒️ History", "⚙️ Definition"])
    with tabs[0]:
        by_item = False
        if k["breakdown"]:
            by_item = st.toggle("Show each warehouse / item separately", key=f"byitem_{kid}")
        ch = _trend_chart(k, hist, by_item)
        if ch is not None and len(hist) >= 1:
            st.altair_chart(ch, **S_CH)
            if len(hist) == 1:
                st.caption("Only the baseline is recorded so far — record a measurement to start the trend line.")
    with tabs[1]:
        if k["breakdown"]:
            st.altair_chart(_breakdown_chart(k), **S_CH)
            bdf = pd.DataFrame([{"Item": b["label"], "Baseline": core.fmt_value(b["baseline"], unit, True), "Current": core.fmt_value(b["current"], unit, True),
                                 "Change": core.fmt_value(b["current"] - b["baseline"], unit, True)} for b in k["breakdown"]])
            st.dataframe(bdf, hide_index=True, **S_DF)
        else:
            st.info("This KPI has a single figure (no breakdown). See the Trend tab.")
    with tabs[2]:
        with st.form(f"kpirec_{kid}", border=False):
            d = st.date_input("Measurement date", value=core.today(), format="DD/MM/YYYY", key=f"kd_{kid}")
            vals, single = {}, None
            if k["breakdown"]:
                st.caption("Enter the latest figure for each item" + (" (the KPI shows their average)." if k["agg"] == "mean" else " (the KPI shows their total)."))
                cols = st.columns(2)
                for i, b in enumerate(k["breakdown"]):
                    vals[b["label"]] = cols[i % 2].number_input(b["label"], value=float(b["current"]), step=1.0, format="%.2f" if unit == "%" else "%.0f", key=f"kb_{kid}_{i}")
            elif unit == "flag":
                single = 1.0 if st.checkbox("Done / in place", value=bool(k["current"] >= 1), key=f"kf_{kid}") else 0.0
            else:
                single = st.number_input("Current value", value=float(k["current"]), step=1.0, format="%.2f" if unit == "%" else "%.0f", key=f"kv_{kid}")
            note = st.text_input("Note / evidence", placeholder="e.g. Verified by IA on site visit, SAP report 12-Nov-2026", key=f"kn_{kid}")
            if st.form_submit_button("💾 Save measurement", type="primary", **S_BTN):
                ia_db.record_kpi(kid, current=single, breakdown_current=vals if k["breakdown"] else None, as_of=d, note=note, who=_user())
                _toast("Measurement saved — progress updated")
                st.rerun()
    with tabs[3]:
        if hist:
            hdf = pd.DataFrame([{"ID": h["id"], "As of": core.fmt_date(h["as_of"]), "Value": core.fmt_value(h["value"], unit, True), "Note": h["note"], "By": h["author"]} for h in reversed(hist)])
            st.dataframe(hdf.drop(columns="ID"), hide_index=True, **S_DF)
            if len(hist) > 1:
                opts = {h["id"]: f"{core.fmt_date(h['as_of'])} · {core.fmt_value(h['value'], unit, True)}" for h in reversed(hist)}
                rid = st.selectbox("Remove a mistaken measurement", list(opts), format_func=lambda i: opts[i], key=f"krm_{kid}")
                if st.button("🗑️ Remove selected measurement", key=f"krmb_{kid}"):
                    ia_db.delete_kpi_measurement(rid, _user())
                    _toast("Measurement removed")
                    st.rerun()
    with tabs[4]:
        with st.form(f"kpidef_{kid}", border=False):
            nm = st.text_input("KPI name", k["name"])
            has_t = st.checkbox("This KPI has a target", value=k["target"] is not None, disabled=(unit == "flag"))
            tv = st.number_input("Target value", value=float(k["target"]) if k["target"] is not None else 0.0, step=1.0, format="%.2f", disabled=(unit == "flag"))
            bs = st.text_input("Target basis (where the target comes from)", k["basis"])
            if st.form_submit_button("Save definition", **S_BTN):
                ia_db.update_kpi_definition(kid, target=(tv if has_t else None) if unit != "flag" else 1, name=nm, basis=bs, who=_user())
                _toast("KPI definition updated")
                st.rerun()


_SECTIONS = ["✅ Action", "🎯 KPIs & charts", "📄 Finding details", "📎 Documents", "💬 Comments"]


def _mgmt_cls(pos):
    return "m-" + (pos.split(" ")[0] if pos else "No")


def _workspace(rkey, fid, aid=None, section=None):
    """ONE popup for everything: edit an action, record KPI figures, edit finding text, upload evidence, comment."""
    if not fid:
        _ws_new_finding(rkey)
        return
    f = _find(fid)
    if not f:
        st.warning("This item no longer exists.")
        return
    chips = (f"<span class='chip area'>{esc(f['area'])}</span><span class='chip p-{esc(f['priority'])}'>● {esc(f['priority'])} priority</span>"
             f"<span class='chip {_mgmt_cls(f['mgmt_position'])}'>Mgmt: {esc(f['mgmt_position'])}</span>"
             f"<span class='chip src'>📎 {len(f['docs'])} document(s) · 💬 {len(f['comments'])} comment(s)</span>")
    st.markdown(f"<div class='ia'><div class='ia-head' style='margin-bottom:8px'><span class='ia-ref {f['state']}'>{esc(f['ref'])}</span><div style='flex:1'>"
                f"<div class='ia-title' style='font-size:16.5px'>{esc(core.plain(f['title']))}</div><div class='ia-chips'>{chips}</div></div></div></div>", unsafe_allow_html=True)
    sec = st.segmented_control("Section", _SECTIONS, default=section if section in _SECTIONS else _SECTIONS[0], key=f"ws_sec_{fid}", label_visibility="collapsed") or _SECTIONS[0]
    if sec == _SECTIONS[0]:
        _ws_action(f, aid)
    elif sec == _SECTIONS[1]:
        _kpis_body(fid)
    elif sec == _SECTIONS[2]:
        _ws_details(f)
    elif sec == _SECTIONS[3]:
        _ws_docs(f)
    else:
        _ws_comments(f)


def _ws_add_action(f):
    with st.expander("➕ Add another action to this finding", expanded=not f["actions"]):
        t = st.text_area("New action", height=90, key=f"na_t_{f['id']}")
        c1, c2 = st.columns(2)
        ow = c1.text_input("Owner", key=f"na_o_{f['id']}")
        du = c2.date_input("Target date", value=None, format="DD/MM/YYYY", key=f"na_d_{f['id']}")
        if st.button("➕ Add action", key=f"na_b_{f['id']}", **S_BTN) and t.strip():
            ia_db.add_action(f["id"], core.to_html(t.strip()), ow.strip(), du, core.NS, _user())
            _toast(f"Action added to {f['ref']}")
            st.rerun()


def _ws_action(f, aid):
    acts = f["actions"]
    if not acts:
        st.info("This finding has no actions yet.")
        _ws_add_action(f)
        return
    ids = [a["id"] for a in acts]
    labels = {a["id"]: f"{f['ref']}.{a['seq']} · {core.plain(a['text'])[:85]}" for a in acts}
    sel = st.selectbox("Action to update (every action of this finding is listed)", ids, index=ids.index(aid) if aid in ids else 0,
                       format_func=lambda i: labels[i], key=f"ws_act_{f['id']}")
    a = next(x for x in acts if x["id"] == sel)
    k = a["id"]
    st.markdown("#### 📋 Recommendations")
    q_tx = st_quill(value=core.to_html(a["text"]), html=True, key=f"q_tx_{k}", placeholder="Describe the recommended action…")
    c1, c2, c3, c4 = st.columns([1.7, 1.7, 1.2, 0.9])
    c1.selectbox("Status", core.STATUSES, index=core.STATUSES.index(a["status"]) if a["status"] in core.STATUSES else 0, key=f"ws_st_{k}")
    c2.text_input("Owner" + ("" if a["owner_confirmed"] else " (proposed)"), a["owner"], key=f"ws_ow_{k}")
    c3.date_input("Target date", value=core.parse_date(a["due_date"]), format="DD/MM/YYYY", key=f"ws_du_{k}")
    c4.number_input("% complete", 0, 100, int(a["pct"]), step=5, key=f"ws_pc_{k}")
    st.markdown("#### 📝 Update / evidence")
    q_nt = st_quill(value=core.to_html(a["note"]), html=True, key=f"q_nt_{k}", placeholder="What was done, evidence reference, memo no., date verified…")
    rm = st.checkbox("🗑️ Remove this action from the finding", key=f"ws_rm_{k}")
    if st.button("💾 Save action", type="primary", key=f"ws_save_{k}", **S_BTN):
        if rm:
            ia_db.delete_action(k, _user())
            _toast(f"Action removed from {f['ref']}")
            st.rerun()
        new_tx = core.clean_rich(q_tx) if q_tx is not None else ""
        tx_arg = new_tx if (new_tx and core.plain(new_tx) != core.plain(a["text"])) else None
        nt_arg = None
        if q_nt is not None:
            new_nt = core.clean_rich(q_nt)
            if core.plain(new_nt) != core.plain(a["note"]):
                nt_arg = new_nt
        due = st.session_state.get(f"ws_du_{k}")
        changed = ia_db.save_action(k, text=tx_arg, owner=st.session_state[f"ws_ow_{k}"].strip(), due_date=due if due else "",
                                    status=st.session_state[f"ws_st_{k}"], pct=st.session_state[f"ws_pc_{k}"], note=nt_arg, who=_user())
        _toast(f"{f['ref']}.{a['seq']} saved" if changed else "No changes to save")
        st.rerun()
    _ws_add_action(f)


def _ws_details(f):
    fid = f["id"]
    areas = sorted({x["area"] for x in build_model()["findings"] if x["report"] == f["report"]})
    st.caption("Edit the auditors' wording or add context. Use the editor toolbar for bold, lists and links.")
    title = st.text_input("Finding title", core.plain(f["title"]), key=f"fd_t_{fid}")
    c1, c2, c3 = st.columns(3)
    pr = c1.selectbox("Priority", core.PRIORITIES, index=core.PRIORITIES.index(f["priority"]) if f["priority"] in core.PRIORITIES else 1, key=f"fd_p_{fid}")
    mp = c2.selectbox("Management position", core.MGMT_POSITIONS, index=core.MGMT_POSITIONS.index(f["mgmt_position"]) if f["mgmt_position"] in core.MGMT_POSITIONS else 0, key=f"fd_m_{fid}")
    area = c3.selectbox("Area", areas, index=areas.index(f["area"]) if f["area"] in areas else 0, key=f"fd_a_{fid}")
    st.markdown("#### 🔎 Observation")
    q_obs = st_quill(value=core.to_html(f["observation"]), html=True, key=f"q_obs_{fid}", placeholder="Observation…")
    st.markdown("#### 📏 Criteria")
    q_crit = st_quill(value=core.to_html(f["criteria"]), html=True, key=f"q_crit_{fid}", placeholder="Criteria…")
    st.markdown("#### ⚠️ Risk")
    q_risk = st_quill(value=core.to_html(f["risk"]), html=True, key=f"q_risk_{fid}", placeholder="Risk…")
    st.markdown("#### 🗣️ Management comment")
    q_mc = st_quill(value=core.to_html(f["mgmt_comment"]), html=True, key=f"q_mc_{fid}", placeholder="Management comment…")
    c4, c5 = st.columns(2)
    tl = c4.text_input("Timeline stated in the report", f["timeline"], key=f"fd_tl_{fid}")
    fl = c5.text_input("Value flagged (label)", f["flagged_label"], key=f"fd_fl_{fid}")
    st.markdown("#### 🗒️ Internal notes")
    q_nt = st_quill(value=core.to_html(f["notes"]), html=True, key=f"q_fnt_{fid}", placeholder="Your own working notes (kept separate from the auditors' wording)…")
    if st.button("💾 Save finding details", type="primary", key=f"fd_save_{fid}", **S_BTN):
        def pick(new, old):
            return old if new is None else core.clean_rich(new)
        ia_db.update_finding(fid, {"title": title, "priority": pr, "mgmt_position": mp, "area": area, "observation": pick(q_obs, f["observation"]),
                                   "criteria": pick(q_crit, f["criteria"]), "risk": pick(q_risk, f["risk"]), "mgmt_comment": pick(q_mc, f["mgmt_comment"]),
                                   "timeline": tl, "flagged_label": fl, "notes": pick(q_nt, f["notes"])}, _user())
        _toast(f"{f['ref']} details saved")
        st.rerun()


def _ws_docs(f):
    fid = f["id"]
    st.caption("Attach evidence of implementation: memos, reconciliations, screenshots, signed reports…")
    docs = ia_db.list_documents(fid)
    if not docs:
        st.markdown("<div class='ia'><div class='ia-box'>No documents attached yet.</div></div>", unsafe_allow_html=True)
    for d in docs:
        c1, c2, c3 = st.columns([5, 2, 1])
        c1.markdown(f"📄 **{esc(d['filename'])}**  \n<span style='color:#64748b;font-size:13px'>{d['size'] / 1024:,.0f} KB · {esc(d['uploaded_by'] or '—')} · {d['uploaded_at'][:16]}"
                    f"{' · ' + esc(d['note']) if d['note'] else ''}</span>", unsafe_allow_html=True)
        full = ia_db.get_document(d["id"])
        c2.download_button("⬇ Download", full["data"], file_name=d["filename"], mime=d["mime"] or "application/octet-stream", key=f"dl_{d['id']}", **S_DL)
        if c3.button("🗑️", key=f"deldoc_{d['id']}", help="Remove this document"):
            ia_db.delete_document(d["id"], _user())
            st.toast("Document removed")
            st.rerun(scope="fragment")
    ver = st.session_state.get(f"upver_{fid}", 0)
    files = st.file_uploader("📎 Add documents", accept_multiple_files=True, key=f"up_{fid}_{ver}")
    note = st.text_input("Note (optional)", key=f"upn_{fid}_{ver}")
    if st.button(f"📎 Attach {len(files) if files else ''} file(s)", type="primary", disabled=not files, key=f"attach_{fid}_{ver}", **S_BTN):
        for fl_ in files:
            if fl_.size > ia_db.MAX_FILE_MB * 1024 * 1024:
                st.error(f"{fl_.name} is larger than {ia_db.MAX_FILE_MB} MB")
                continue
            ia_db.add_document(fid, fl_.name, fl_.type, fl_.getvalue(), note, _user())
        st.session_state[f"upver_{fid}"] = ver + 1
        st.session_state["ia_ver"] = st.session_state.get("ia_ver", 0) + 1
        st.toast("Document(s) attached")
        st.rerun(scope="fragment")


def _ws_comments(f):
    fid = f["id"]
    cms = ia_db.list_comments(fid)
    if not cms:
        st.markdown("<div class='ia'><div class='ia-box'>No comments yet. Start the conversation below.</div></div>", unsafe_allow_html=True)
    for c in cms:
        st.markdown(f"<div class='ia'><div class='ia-box'><b>{esc(c['author'])}</b> <span style='color:#64748b'>· {c['created_at'][:16]}</span><br>{esc(c['body'])}</div></div>", unsafe_allow_html=True)
    who = st.text_input("Your name", value=_user(), key=f"cm_who_{fid}")
    body = st.text_area("Comment", height=100, key=f"cm_body_{fid}")
    if st.button("💬 Post comment", type="primary", key=f"cm_post_{fid}", **S_BTN) and body.strip():
        ia_db.add_comment(fid, who.strip(), body.strip())
        st.session_state["ia_ver"] = st.session_state.get("ia_ver", 0) + 1
        st.toast("Comment posted")
        for kk in (f"cm_body_{fid}",):
            st.session_state.pop(kk, None)
        st.rerun(scope="fragment")


def _ws_new_finding(rkey):
    rep = seed.REPORTS[rkey]
    areas = sorted({x["area"] for x in build_model()["findings"] if x["report"] == rkey})
    st.caption(f"Adds a finding to the **{rep['name']}** table (for example one raised in a follow-up review).")
    title = st.text_input("Finding title *", key=f"nf_t_{rkey}")
    c1, c2, c3 = st.columns(3)
    area_sel = c1.selectbox("Area", areas + ["➕ New area…"], key=f"nf_a_{rkey}")
    pr = c2.selectbox("Priority", core.PRIORITIES, index=1, key=f"nf_p_{rkey}")
    mp = c3.selectbox("Management position", core.MGMT_POSITIONS, index=4, key=f"nf_m_{rkey}")
    new_area = st.text_input("New area name (only if you chose ‘New area…’)", key=f"nf_na_{rkey}")
    st.markdown("#### 🔎 Observation")
    q_obs = st_quill(value="", html=True, key=f"nf_obs_{rkey}", placeholder="Observation…")
    st.markdown("#### ⚠️ Risk")
    q_risk = st_quill(value="", html=True, key=f"nf_risk_{rkey}", placeholder="Risk…")
    st.markdown("#### 📋 First recommended action")
    q_act = st_quill(value="", html=True, key=f"nf_act_{rkey}", placeholder="Recommended action…")
    c4, c5 = st.columns(2)
    ow = c4.text_input("Action owner", key=f"nf_o_{rkey}")
    du = c5.date_input("Action target date", value=None, format="DD/MM/YYYY", key=f"nf_d_{rkey}")
    if st.button("➕ Add finding", type="primary", key=f"nf_go_{rkey}", **S_BTN):
        area = new_area.strip() if area_sel.startswith("➕") else area_sel
        if not title.strip() or not area:
            st.error("Please give a title and an area.")
        else:
            fid = ia_db.add_finding(rkey, {"title": title.strip(), "area": area, "priority": pr, "mgmt_position": mp,
                                           "observation": core.clean_rich(q_obs), "risk": core.clean_rich(q_risk)}, _user())
            if core.clean_rich(q_act):
                ia_db.add_action(fid, core.clean_rich(q_act), ow.strip(), du, core.NS, _user())
            _toast("Finding added")
            st.rerun()


def _open(title, body, *args, width="large"):
    st.dialog(title, width=width)(body)(*args)


def _open_workspace(rkey, fid, aid=None, section=None, title=None):
    _open(title or "✏️ Update / Upload", _workspace, rkey, fid, aid, section)


# ---------------------------------------------------------------------------------------------
# Report tab pieces
# ---------------------------------------------------------------------------------------------
def _stats(fl):
    acts = [a for f in fl for a in f["actions"]]
    live = [a for a in acts if a["status"] != core.NA]
    st_ = [core.action_state(a["status"], a["due_date"]) for a in live]
    return {
        "findings": len(fl), "high": sum(1 for f in fl if f["priority"] == "High"), "actions": len(live),
        "closed": st_.count("closed"), "verify": st_.count("verify"), "overdue": st_.count("overdue"),
        "disputed": st_.count("disputed"), "progress": st_.count("progress"), "pending": st_.count("pending"),
        "nodate": sum(1 for a in live if a["status"] in core.OPEN_STATUSES and not a["due_date"]),
        "avg": round(sum(a["pct"] for a in live) / len(live)) if live else 0,
    }


def _hero(M, fy):
    stats = {k: _stats([f for f in M["findings"] if f["report"] == k]) for k in seed.REPORTS}
    all_a = [a for f in M["findings"] for a in f["actions"] if a["status"] != core.NA]
    avg = round(sum(a["pct"] for a in all_a) / len(all_a)) if all_a else 0
    over = sum(s["overdue"] for s in stats.values())
    logo = _logo_b64()
    logo_html = f"<div class='ia-logo'><img src='data:image/jpeg;base64,{logo}'/></div>" if logo else "<div class='ia-logo'>🏥</div>"
    pills = "".join(f"<div class='ia-pill'><b>{stats[k]['avg']}%</b><span>{'Regional' if k == 'regional' else 'Central'}</span></div>" for k in ("regional", "central"))
    over_pill = f"<div class='ia-pill bad'><b>{over}</b><span>overdue</span></div>" if over else ""
    st.markdown(
        "<div class='ia'><div class='ia-hero'>" + logo_html +
        "<div class='ia-hero-text'><div class='ia-eyebrow'>Rwanda Medical Supply Ltd · Audit, Risk &amp; Compliance Directorate</div>"
        "<div class='ia-h1'>Internal Audit Action Tracker</div>"
        f"<div class='ia-sub'>Action plan on audit recommendations · {esc(fy)} · {len(M['findings'])} findings · {len(all_a)} actions · 2 audit reports</div></div>"
        f"<div class='ia-hero-right'>{over_pill}{pills}<div class='ia-ring' style='--p:{avg}'><div><b>{avg}%</b></div></div></div></div></div>",
        unsafe_allow_html=True)


def _report_card(rep, fl):
    """One slim banner: report title, rating and progress on a single row (keeps the KPI cards high on the page)."""
    s = _stats(fl)
    labels = ["Unacceptable", "Major improvement", "Some improvement", "Satisfactory", "Well managed"]
    if rep["rating_level"]:
        scale = ("<div class='ia-scale sm'>" + "".join(f"<span class='{'on l' + str(i + 1) if i + 1 == rep['rating_level'] else ''}'>{esc(l)}</span>" for i, l in enumerate(labels)) + "</div>")
    else:
        scale = "<div class='ia-scale sm' style='grid-template-columns:1fr'><span>Overall rating not stated in the report</span></div>"
    st.markdown(
        "<div class='ia'><div class='ia-slim'>"
        f"<div class='tt'><div class='t'>{esc(rep['title'])}</div><div class='m'>Issued {esc(rep['issued'])}</div></div>"
        f"<div class='rt'><div class='lbl'>Auditors' rating</div>{scale}</div>"
        f"<div class='pg'><div class='lbl'>Implementation progress</div><div class='ia-prog' style='margin:2px 0'><div class='bar' style='width:100%;max-width:240px;height:12px'><span style='width:{s['avg']}%'></span></div><b>{s['avg']}%</b></div></div>"
        "</div></div>", unsafe_allow_html=True)


def _set_kpi(rkey, mode):
    st.session_state[f"{rkey}_kpi"] = mode


def _clear_kpi(rkey):
    st.session_state.pop(f"{rkey}_kpi", None)


_KPI_NAMES = {"findings": "findings only (one row per finding, recommendations stacked)", "actions": "all recommended actions",
              "closed": "Closed – verified actions", "verify": "actions Awaiting verification", "overdue": "Overdue actions",
              "nodate": "open actions with No target date"}


def _kpi_match(mode, a):
    stt = core.action_state(a["status"], a["due_date"])
    if mode == "closed":
        return stt == "closed"
    if mode == "verify":
        return stt == "verify"
    if mode == "overdue":
        return stt == "overdue"
    if mode == "nodate":
        return a["status"] in core.OPEN_STATUSES and not a["due_date"]
    return True


def _kpi_cards(rkey, fl):
    s = _stats(fl)
    base = max(s["actions"], 1)
    mode = st.session_state.get(f"{rkey}_kpi")
    defs = [("findings", "Findings", s["findings"], f"{s['high']} high priority", "#1e3c72", "📋"),
            ("actions", "Actions", s["actions"], f"{s['disputed']} disputed by management", "#2f5fb3", "✅"),
            ("closed", "Closed · verified", s["closed"], f"{s['closed'] / base * 100:.0f}% of actions", "#15803d", "🔒"),
            ("verify", "Awaiting verification", s["verify"], "management says done", "#6d28d9", "🔎"),
            ("overdue", "Overdue", s["overdue"], "past target date", "#b91c1c", "🚨"),
            ("nodate", "No target date", s["nodate"], "open actions need a date", "#64748b", "📅")]
    for col, (m, lb, vl, sb, color, icon) in zip(st.columns(6), defs):
        with col:
            with st.container(key=f"kpi-{rkey}-{m}"):
                on = mode == m
                tag = "<span class='tag'>● FILTER ON</span>" if on else ""
                st.markdown(f"<div class='ia'><div class='ia-kpi{' on' if on else ''}' style='--c:{color}'><span class='ic'>{icon}</span><div class='lb'>{lb}</div>"
                            f"<div class='vl'>{vl}</div><div class='sb'>{sb}</div>{tag}</div></div>", unsafe_allow_html=True)
                with st.container(key=f"kpib-{rkey}-{m}"):
                    st.button("filter", key=f"kpibtn-{rkey}-{m}", on_click=_set_kpi, args=(rkey, m), help="Click to show only these items · double-click to undo")
    if mode:
        all_a = [a for f in fl for a in f["actions"] if a["status"] != core.NA]
        n = len(fl) if mode == "findings" else sum(1 for a in all_a if _kpi_match(mode, a))
        unit = "findings" if mode == "findings" else "actions"
        total = len(fl) if mode == "findings" else len(all_a)
        c1, c2 = st.columns([8, 1.7])
        c1.markdown(f"<div class='ia'><div class='ia-notice'>🔎 <span>Only <b>{esc(_KPI_NAMES[mode])}</b> are being displayed — {n} of {total} {unit}. "
                    f"<b>Double-click</b> the card (or press Undo) to show everything.</span></div></div>", unsafe_allow_html=True)
        c2.button("↩ Undo filter", key=f"kpiundo-{rkey}", on_click=_clear_kpi, args=(rkey,), **S_BTN)
    else:
        st.markdown("<div class='ia'><div class='ia-hint'>💡 Click any card to show only those items in the table · double-click the card to undo.</div></div>", unsafe_allow_html=True)


_RICH = JsCode(r"""
class RichRenderer { init(p){ this.e=document.createElement('div'); this.e.style.cssText='white-space:normal;word-break:break-word;line-height:1.5';
  this.e.innerHTML = p.value ? p.value : ''; this.e.querySelectorAll('p').forEach(function(x){x.style.margin='0 0 4px 0';x.style.padding='0';}); }
  getGui(){ return this.e; } }
""")
_OWNER = JsCode(r"""
class OwnerRenderer { init(p){ this.e=document.createElement('div'); var v=p.value||'';
  var t=String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;');
  this.e.innerHTML = v ? ('👤 '+t+((p.data&&p.data.Proposed)?' <span style="color:#b45309;font-size:10px;font-weight:800">PROPOSED</span>':'')) : '<span style="color:#94a3b8">— click to add owner —</span>'; }
  getGui(){ return this.e; } }
""")
_PCT = JsCode(r"""
class PctRenderer { init(p){ var v=Number(p.value||0); this.e=document.createElement('div');
  this.e.innerHTML='<div style="display:flex;align-items:center;gap:8px"><div style="flex:1;height:10px;border-radius:99px;background:#e2e8f0;overflow:hidden"><div style="width:'+v+'%;height:100%;background:linear-gradient(90deg,#34d399,#16a34a)"></div></div><b>'+v+'%</b></div>'; }
  getGui(){ return this.e; } }
""")
_REF = JsCode(r"""
class RefRenderer { init(p){ this.e=document.createElement('div'); this.e.style.cssText='display:flex;align-items:center;gap:8px';
  var t=document.createElement('span'); t.textContent=p.value||''; t.style.cssText='font-weight:800;color:#1e3c72;font-size:14px';
  var b=document.createElement('button'); b.className='ia-edit'; b.textContent='✏️ Edit'; b.title='Open the update window for this row';
  b.addEventListener('click', function(ev){ ev.stopPropagation(); p.node.setSelected(true); p.node.setDataValue('Open', Math.floor(Date.now()/1000)); });
  this.e.appendChild(t); this.e.appendChild(b); }
  getGui(){ return this.e; } }
""")
_ROW_STYLE = JsCode("function(p){ if(p.data && Number(p.data._first)===1){ return {borderTop:'3px solid #1e3c72'}; } return null; }")
_TINT = JsCode("function(p){ var c=p.data&&p.data.FC; return c?{backgroundColor:c}:null; }")
_ROW_ID = JsCode("function(p){ return p.data._type + '-' + p.data.FID + '-' + p.data.ID; }")
_DATE_FMT = JsCode("function(p){ if(!p.value) return ''; var d=new Date(p.value+'T00:00:00'); return isNaN(d)? p.value : d.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'}); }")
_TIMING_STYLE = JsCode("function(p){ var v=p.value||''; if(v.indexOf('⏰')===0) return {color:'#b91c1c',fontWeight:'700'}; if(v.indexOf('⏳')===0) return {color:'#b45309',fontWeight:'700'}; if(v.indexOf('🔎')===0) return {color:'#6d28d9',fontWeight:'700'}; if(v.indexOf('✔')===0) return {color:'#15803d',fontWeight:'700'}; if(v.indexOf('⚠')===0) return {color:'#64748b',fontWeight:'600'}; return {color:'#334155'}; }")
_STATUS_STYLE = JsCode(r"""
function(p){ var c=(p.data&&p.data.SC)||'#64748b';
  return {backgroundColor:c,fontWeight:'800',color:'white',textAlign:'center',display:'flex',alignItems:'center',justifyContent:'center',whiteSpace:'normal',lineHeight:'1.3'}; }
""")
_SC = {core.CL: "#15803d", core.IPV: "#6d28d9", core.IP: "#ca8a04", core.NS: "#64748b", core.DI: "#ea580c", core.NA: "#94a3b8"}
_COLS = ["Findings", "Ref", "Recommendations", "Owner", "Target date", "Timing", "% complete", "KPIs", "Update / evidence", "Status",
         "_type", "ID", "FID", "Proposed", "SC", "FC", "_first", "Open"]
_HIDDEN = ("_type", "ID", "FID", "Proposed", "SC", "FC", "_first", "Open")


def _blank(**kw):
    r = {"Ref": "", "Findings": "", "Recommendations": "", "Owner": "", "Target date": "", "Timing": "", "% complete": 0, "KPIs": "", "Update / evidence": "",
         "Status": "", "_type": "action", "ID": 0, "FID": 0, "Proposed": 0, "SC": "", "FC": "", "_first": 0, "Open": 0, "eh": 0}
    r.update(kw)
    return r


def _lines(txt, per):
    t = core.plain(txt)
    return max(1, sum(-(-len(p) // per) for p in t.split("\n"))) if t else 1


def _row_h(r, f=None):
    h = 21 * max(_lines(r["Recommendations"], 40), _lines(r["Update / evidence"], 34), _lines(r["Owner"], 22), 2) + 20
    if r["_first"] and f is not None:
        left = 20 * max(1, -(-len(core.plain(f["title"])) // 28)) + 74
        right = sum(18 * max(1, -(-len(k["name"]) // 34)) + 44 for k in f["kpis"]) + 8
        h = max(h, left, right)
    return h


def _grid(rkey, df, height):
    # a new key whenever the visible rows change, so the grid remounts and every cell colour is recomputed
    sig = zlib.crc32("|".join(df["Ref"].astype(str) + df["Status"].astype(str) + df["SC"].astype(str) + df["Timing"].astype(str)).encode())
    gb = GridOptionsBuilder.from_dataframe(df[_COLS])
    gb.configure_default_column(wrapText=True, autoHeight=True, editable=False, sortable=False, filter=False, resizable=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    for c in _HIDDEN:
        gb.configure_column(c, hide=True)
    gb.configure_column("Ref", header_name="Ref", width=235, minWidth=225, wrapText=False, checkboxSelection=True, cellRenderer=_REF)
    gb.configure_column("Findings", header_name="Findings", width=340, minWidth=280, cellRenderer=_RICH, cellStyle=_TINT)
    gb.configure_column("Recommendations", header_name="Recommendations", width=380, minWidth=300, cellRenderer=_RICH)
    gb.configure_column("Owner", header_name="👤 Owner ✏️", width=230, minWidth=200, editable=True, cellRenderer=_OWNER, cellClass="ia-ed")
    gb.configure_column("Target date", header_name="📅 Target date ✏️", width=170, minWidth=150, editable=True, wrapText=False, cellEditor="agDateStringCellEditor", valueFormatter=_DATE_FMT, cellClass="ia-ed")
    gb.configure_column("Timing", header_name="Timing", width=170, minWidth=150, cellStyle=_TIMING_STYLE)
    gb.configure_column("% complete", header_name="% complete ✏️", width=160, minWidth=140, editable=True, cellEditor="agNumberCellEditor", cellEditorParams={"min": 0, "max": 100, "precision": 0}, cellRenderer=_PCT, cellClass="ia-ed")
    gb.configure_column("KPIs", header_name="🎯 KPIs (now → target)", width=340, minWidth=280, cellRenderer=_RICH, cellStyle=_TINT)
    gb.configure_column("Update / evidence", header_name="Update / evidence", width=290, minWidth=240, cellRenderer=_RICH)
    gb.configure_column("Status", header_name="Status ✏️", pinned="right", width=215, minWidth=190, editable=True, wrapText=True, cellStyle=_STATUS_STYLE,
                        cellEditor="agSelectCellEditor", cellEditorParams={"values": core.STATUSES})
    gb.configure_grid_options(getRowStyle=_ROW_STYLE, getRowId=_ROW_ID, singleClickEdit=True, alwaysShowVerticalScroll=False,
                              rowHeight=48, headerHeight=54, suppressMovableColumns=True)
    css = {".ag-header": {"background-color": "#1e3c72 !important"},
           ".ag-header-cell-label": {"font-weight": "800 !important", "color": "white !important", "font-size": "14px !important"},
           ".ag-cell": {"font-size": "14px !important", "padding-top": "6px !important", "padding-bottom": "6px !important"},
           ".ag-row-selected": {"background-color": "#e8f0ff !important"},
           ".ia-ed": {"background-color": "#fffbea", "border-bottom": "1px dashed #e0c46c !important", "cursor": "text"},
           ".ia-edit": {"display": "none", "background": "linear-gradient(135deg,#22c55e,#15803d)", "color": "#fff", "border": "0", "border-radius": "99px",
                        "padding": "5px 14px", "font-weight": "800", "font-size": "12.5px", "cursor": "pointer", "box-shadow": "0 3px 8px rgba(21,128,61,.45)"},
           ".ag-row-selected .ia-edit": {"display": "inline-block !important"}}
    return AgGrid(df[_COLS], gridOptions=gb.build(), update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,
                  data_return_mode=DataReturnMode.AS_INPUT, fit_columns_on_grid_load=False, height=height, theme="streamlit",
                  allow_unsafe_jscode=True, custom_css=css, key=f"{rkey}_grid_{st.session_state.get('ia_ver', 0)}_{sig}")


def _sync_grid_edits(orig, edited, who=""):
    """Save inline edits (owner, target date, status, % complete) made directly in the table. Returns how many actions changed."""
    base = {int(r["ID"]): r for _, r in orig.iterrows() if r["_type"] == "action" and int(r["ID"])}
    n = 0
    for _, e in edited.iterrows():
        if e.get("_type") != "action":
            continue
        try:
            aid = int(float(e["ID"]))
        except (TypeError, ValueError):
            continue
        o = base.get(aid)
        if o is None:
            continue
        owner_new = (e["Owner"] or "").strip() if isinstance(e["Owner"], str) else ""
        due_new = core.iso(core.parse_date(e["Target date"])) if isinstance(e["Target date"], str) else ""
        try:
            pct_new = int(float(e["% complete"]))
        except (TypeError, ValueError):
            pct_new = int(o["% complete"])
        if (owner_new == (o["Owner"] or "") and due_new == (o["Target date"] or "") and e["Status"] == o["Status"] and pct_new == int(o["% complete"])):
            continue
        if ia_db.save_action(aid, owner=owner_new, due_date=due_new, status=e["Status"], pct=pct_new if pct_new != int(o["% complete"]) else None, who=who):
            n += 1
    return n


def _units(owner):
    return [u.strip() for u in (owner or "").split(";") if u.strip()]


def _findings_view(rkey, fl):
    areas = list(dict.fromkeys(f["area"] for f in fl))
    owners = sorted({u for f in fl for a in f["actions"] for u in _units(a["owner"])})
    status_opts = ["Any status", "Open (not closed)", "Overdue", "Awaiting verification", "In progress", "Not started", "Disputed", "Closed – verified"]
    with st.container(key=f"ia-filterbar-{rkey}"):
        st.markdown("<div class='ia'><div class='ia-fb-t'>🔎 Find your items</div><div class='ia-fb-s'>Choose <b>your department</b> in the highlighted box to see only the issues you must attend to.</div></div>", unsafe_allow_html=True)
        c0, c1, c2, c3, c4 = st.columns([2.7, 1.8, 1.9, 1.4, 2.2])
        with c0:
            with st.container(key=f"ownfilter-{rkey}"):
                own_sel = st.selectbox("👤 My department / owner  ·  start here", ["All departments"] + owners, key=f"{rkey}_ow")
        st_sel = c1.selectbox("📌 Status", status_opts, key=f"{rkey}_st")
        area_sel = c2.selectbox("📂 Area", ["All areas"] + areas, key=f"{rkey}_area")
        pr_sel = c3.selectbox("⭐ Priority", ["Any priority"] + core.PRIORITIES, key=f"{rkey}_pr")
        q = c4.text_input("🔍 Search", placeholder="ref, wording, owner…", key=f"{rkey}_q")
        t1, t2, t3, _sp = st.columns([1.5, 1.7, 1.9, 3.5])
        hide_closed = t1.toggle("🙈 Hide closed", key=f"{rkey}_hide")
        nodate = t2.toggle("📅 Missing a date", key=f"{rkey}_nodate")
        high = t3.toggle("🔥 High priority only", key=f"{rkey}_high")
    mode = st.session_state.get(f"{rkey}_kpi")
    smap = {"Overdue": "overdue", "Awaiting verification": "verify", "In progress": "progress", "Not started": "pending", "Disputed": "disputed", "Closed – verified": "closed"}

    rows, heights, n_act, n_find = [], [], 0, 0
    for f in fl:
        if area_sel != "All areas" and f["area"] != area_sel:
            continue
        if pr_sel != "Any priority" and f["priority"] != pr_sel:
            continue
        if high and f["priority"] != "High":
            continue
        if q.strip():
            blob = " ".join([f["ref"], core.plain(f["title"]), core.plain(f["observation"]), core.plain(f["risk"]), f["area"], f["src_ref"]]
                            + [core.plain(a["text"]) + " " + a["owner"] + " " + core.plain(a["note"]) for a in f["actions"]] + [k["name"] for k in f["kpis"]]).lower()
            if q.strip().lower() not in blob:
                continue
        soft = core.STATE[f["state"]][2]
        fcell, kcell = _finding_cell(f), _kpi_cell(f)
        live = [a for a in f["actions"] if a["status"] != core.NA]
        if mode == "findings":
            if own_sel != "All departments" and not any(own_sel in _units(a["owner"]) for a in live):
                continue
            stack = "".join(f"<div style='margin-bottom:6px'><b style='color:#1e3c72'>{esc(f['ref'])}.{a['seq']}</b> {core.plain(a['text'])[:160]}</div>" for a in live)
            r = _blank(Ref=f["ref"], Findings=fcell, Recommendations=stack, KPIs=kcell, Owner="; ".join(dict.fromkeys(u for a in live for u in _units(a["owner"]))),
                       **{"% complete": f["pct"], "Status": core.STATE[f["state"]][0], "Timing": f"{sum(1 for a in live if core.action_state(a['status'], a['due_date']) == 'overdue')} overdue",
                          "_type": "findingrow", "FID": f["id"], "SC": core.STATE[f["state"]][1], "FC": soft, "_first": 1})
            r["Recommendations"] = stack
            rows.append(r)
            heights.append(max(_row_h(r, f), 24 * len(live) + 20))
            n_find += 1
            continue
        acts = []
        for a in f["actions"]:
            if a["status"] == core.NA:
                continue
            stt = core.action_state(a["status"], a["due_date"])
            if st_sel == "Open (not closed)" and stt == "closed":
                continue
            if st_sel in smap and stt != smap[st_sel]:
                continue
            if own_sel != "All departments" and own_sel not in _units(a["owner"]):
                continue
            if hide_closed and stt == "closed":
                continue
            if nodate and not (a["status"] in core.OPEN_STATUSES and not a["due_date"]):
                continue
            if not _kpi_match(mode, a):
                continue
            acts.append(a)
        if not acts:
            continue
        n_find += 1
        for i, a in enumerate(acts):
            n_act += 1
            first = i == 0
            r = _blank(Ref=f"{f['ref']}.{a['seq']}", Findings=fcell if first else "", KPIs=kcell if first else "", Recommendations=core.to_html(a["text"]), Owner=a["owner"],
                       **{"Target date": a["due_date"] or "", "Timing": _timing(a), "% complete": int(a["pct"]), "Update / evidence": core.to_html(a["note"]), "Status": a["status"],
                          "_type": "action", "ID": int(a["id"]), "FID": f["id"], "Proposed": 0 if a["owner_confirmed"] else 1, "FC": soft, "_first": 1 if first else 0,
                          "SC": "#b91c1c" if stt_overdue(a) else _SC.get(a["status"], "#64748b")})
            rows.append(r)
            heights.append(_row_h(r, f if first else None))
    st.markdown("<div class='ia'><div class='ia-steps'><span><b>1</b>Pick your department above</span><span><b>2</b>Tick the box next to the <u>Ref</u> of your row — a green <u>✏️ Edit</u> button appears beside it</span>"
                "<span><b>3</b>Update everything in the popup — or just click the <u>✏️ yellow cells</u> to edit them in place</span></div></div>", unsafe_allow_html=True)
    st.caption(f"Showing **{n_act}** recommendations across **{n_find}** findings" if mode != "findings" else f"Showing **{n_find}** findings")
    toolbar = st.empty()
    if not rows:
        st.markdown("<div class='ia'><div class='ia-empty'><div style='font-size:28px'>🔎</div><b>Nothing matches these filters.</b></div></div>", unsafe_allow_html=True)
        with toolbar.container():
            if st.button("➕ New finding", type="primary", key=f"{rkey}_newf0"):
                _open_workspace(rkey, None, title=f"➕ New finding · {seed.REPORTS[rkey]['name']}")
        return
    df = pd.DataFrame(rows)
    est = 54 + sum(heights) + 6
    # short list: let the grid measure itself (no blank band). long list: fixed height, scrolls inside with the header pinned
    height = None if est <= 1100 else 740
    resp = _grid(rkey, df, height)
    edited = resp["data"]
    opened = None
    if edited is not None and len(edited):
        ed = pd.DataFrame(edited)
        n = _sync_grid_edits(df, ed, _user())
        if n:
            _toast(f"Saved {n} change(s) from the table")
            st.rerun()
        if "Open" in ed.columns:
            hit = ed[pd.to_numeric(ed["Open"], errors="coerce").fillna(0) > 0]
            if len(hit):
                h = hit.iloc[0]
                stamp = (int(float(h["FID"])), int(float(h["ID"])), float(h["Open"]))
                if st.session_state.get(f"{rkey}_lastopen") != stamp:
                    st.session_state[f"{rkey}_lastopen"] = stamp
                    opened = h
    sel = resp.get("selected_rows")
    sel_row = None
    if sel is not None and len(sel) > 0:
        sel_row = sel.iloc[0].to_dict() if isinstance(sel, pd.DataFrame) else sel[0]
    if opened is not None:
        _open_workspace(rkey, int(float(opened["FID"])), int(float(opened["ID"])) or None, _SECTIONS[0], title=f"✏️ {opened['Ref']} · Update / Upload")
    with toolbar.container():
        c1, c2, c3 = st.columns([4.6, 1.8, 2.4])
        if sel_row:
            label = f"✏️ Update / Upload · {sel_row.get('Ref', '')}"
            if c1.button(label, type="primary", key=f"{rkey}_upd", **S_BTN):
                _open_workspace(rkey, int(float(sel_row["FID"])), (int(float(sel_row["ID"])) or None), _SECTIONS[0], title=f"✏️ {sel_row.get('Ref', '')} · Update / Upload")
        else:
            c1.markdown("<div class='ia'><div class='ia-sel'>👇 Tick the box next to a Ref, then press ✏️ Edit</div></div>", unsafe_allow_html=True)
        if c2.button("➕ New finding", key=f"{rkey}_newf", **S_BTN):
            _open_workspace(rkey, None, title=f"➕ New finding · {seed.REPORTS[rkey]['name']}")


def stt_overdue(a):
    return core.action_state(a["status"], a["due_date"]) == "overdue"


# ---------------------------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------------------------
def _stack(d, group, cat, order, val="Actions"):
    """Add start/end/mid columns so stacked bars and their centred labels line up exactly."""
    rank = {c: i for i, c in enumerate(order)}
    d = d.assign(_r=d[cat].map(rank)).sort_values([group, "_r"])
    d["end"] = d.groupby(group)[val].cumsum()
    d["start"] = d["end"] - d[val]
    d["mid"] = (d["start"] + d["end"]) / 2
    return d.drop(columns="_r")


def _dashboard(fl):
    acts = [dict(a, _state=core.action_state(a["status"], a["due_date"]), _f=f) for f in fl for a in f["actions"] if a["status"] != core.NA]
    order = ["closed", "verify", "progress", "pending", "overdue", "disputed"]
    labels = [core.STATE[s][0] for s in order]
    colors = [core.STATE[s][1] for s in order]
    leg = lambda cols: alt.Legend(title=None, orient="bottom", columns=cols, labelFontSize=12, symbolSize=120)  # noqa: E731
    cA, cB = st.columns([1, 1.4])
    with cA:
        st.markdown("#### Recommended actions by status")
        d = pd.DataFrame([{"Status": core.STATE[s][0], "Actions": sum(1 for a in acts if a["_state"] == s)} for s in order])
        d = d[d["Actions"] > 0]
        arc = alt.Chart(d).mark_arc(innerRadius=68, outerRadius=122, stroke="#fff", strokeWidth=2).encode(
            theta=alt.Theta("Actions:Q", stack=True), color=alt.Color("Status:N", scale=alt.Scale(domain=labels, range=colors), legend=alt.Legend(title=None, orient="right", labelFontSize=12, symbolSize=120)),
            tooltip=[alt.Tooltip("Status:N"), alt.Tooltip("Actions:Q", title="Actions")])
        lab = alt.Chart(d).mark_text(radius=95, fontSize=16, fontWeight="bold", color="white").encode(theta=alt.Theta("Actions:Q", stack=True), text="Actions:Q")
        mid = alt.Chart(pd.DataFrame({"t": [int(d["Actions"].sum())]})).mark_text(fontSize=34, fontWeight=800, color="#0f172a", dy=-6).encode(text="t:Q")
        mid2 = alt.Chart(pd.DataFrame({"t": ["actions"]})).mark_text(fontSize=13, color="#64748b", dy=18).encode(text="t:N")
        st.altair_chart((arc + lab + mid + mid2).properties(height=320), **S_CH)
    with cB:
        st.markdown("#### Status of actions by area")
        rows = [{"Area": a["_f"]["area"], "Status": core.STATE[a["_state"]][0], "Actions": 1} for a in acts]
        d = pd.DataFrame(rows).groupby(["Area", "Status"], as_index=False).sum()
        tot = d.groupby("Area")["Actions"].sum().sort_values(ascending=False)
        d = _stack(d, "Area", "Status", labels)
        yenc = alt.Y("Area:N", sort=list(tot.index), title=None, axis=alt.Axis(labelLimit=300, labelFontSize=12))
        bars = alt.Chart(d).mark_bar(stroke="#fff", strokeWidth=1.5).encode(
            y=yenc, x=alt.X("start:Q", title="Actions", axis=alt.Axis(tickMinStep=1)), x2="end:Q",
            color=alt.Color("Status:N", scale=alt.Scale(domain=labels, range=colors), legend=leg(3)),
            tooltip=[alt.Tooltip("Area:N"), alt.Tooltip("Status:N"), alt.Tooltip("Actions:Q")])
        seg = alt.Chart(d).mark_text(color="white", fontWeight="bold", fontSize=13).encode(y=yenc, x=alt.X("mid:Q"), text="Actions:Q")
        tdf = tot.reset_index().rename(columns={"Actions": "Total"})
        tl = alt.Chart(tdf).mark_text(align="left", dx=6, fontSize=13, fontWeight="bold", color="#0f172a").encode(y=yenc, x=alt.X("Total:Q"), text="Total:Q")
        st.altair_chart((bars + seg + tl).properties(height=320, padding={"right": 24}), **S_CH)
    cC, cD = st.columns(2)
    with cC:
        st.markdown("#### When open actions fall due")
        st.caption("Actions not yet implemented, by target month")
        rows = []
        for a in acts:
            if a["status"] in core.OPEN_STATUSES:
                d_ = core.parse_date(a["due_date"])
                rows.append({"Month": d_.strftime("%b %Y") if d_ else "No date", "_s": d_.strftime("%Y-%m") if d_ else "9999",
                             "Type": ("Overdue" if core.action_state(a["status"], a["due_date"]) == "overdue" else ("Not yet due" if d_ else "No date")), "Actions": 1})
        if rows:
            d = pd.DataFrame(rows).groupby(["Month", "_s", "Type"], as_index=False).sum()
            months = list(d.sort_values("_s")["Month"].drop_duplicates())
            types = ["Overdue", "Not yet due", "No date"]
            d = _stack(d, "Month", "Type", types)
            xenc = alt.X("Month:N", sort=months, title=None, axis=alt.Axis(labelAngle=-30, labelFontSize=12))
            cscale = alt.Scale(domain=types, range=["#dc2626", "#2f5fb3", "#94a3b8"])
            bars = alt.Chart(d).mark_bar(stroke="#fff", strokeWidth=1.5).encode(
                x=xenc, y=alt.Y("start:Q", title="Actions", axis=alt.Axis(tickMinStep=1)), y2="end:Q", color=alt.Color("Type:N", scale=cscale, legend=leg(3)),
                tooltip=[alt.Tooltip("Month:N"), alt.Tooltip("Type:N"), alt.Tooltip("Actions:Q")])
            seg = alt.Chart(d).mark_text(color="white", fontWeight="bold", fontSize=13).encode(x=xenc, y=alt.Y("mid:Q"), text="Actions:Q")
            tdf = d.groupby("Month", as_index=False)["Actions"].sum().rename(columns={"Actions": "Total"})
            tl = alt.Chart(tdf).mark_text(dy=-9, fontSize=13, fontWeight="bold", color="#0f172a").encode(x=xenc, y=alt.Y("Total:Q"), text="Total:Q")
            st.altair_chart((bars + seg + tl).properties(height=320, padding={"top": 20}), **S_CH)
        else:
            st.info("No open actions.")
    with cD:
        st.markdown("#### Value flagged by the auditors — top 10")
        st.caption("Rwf millions · amounts overlap between findings, so don't add them up")
        d = pd.DataFrame([{"Finding": f"{f['ref']} · {f['title'][:42]}{'…' if len(f['title']) > 42 else ''}", "M": f["flagged_value"] / 1e6,
                           "Value": core.fmt_value(f["flagged_value"], "Rwf"), "Completion": f"{f['pct']}%"} for f in fl if f["flagged_value"]])
        if not d.empty:
            d = d.sort_values("M", ascending=False).head(10)
            yenc = alt.Y("Finding:N", sort=list(d["Finding"]), title=None, axis=alt.Axis(labelLimit=340, labelFontSize=12))
            tip = [alt.Tooltip("Finding:N"), alt.Tooltip("Value:N", title="Value flagged"), alt.Tooltip("Completion:N", title="% complete")]
            bars = alt.Chart(d).mark_bar(color="#2f5fb3", cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
                y=yenc, x=alt.X("M:Q", title="Rwf millions", axis=alt.Axis(labelExpr="format(datum.value,',.0f') + 'M'", tickCount=5)), tooltip=tip)
            lab = alt.Chart(d).mark_text(align="left", dx=6, fontSize=12, fontWeight="bold", color="#0f172a").encode(y=yenc, x="M:Q", text="Value:N")
            st.altair_chart((bars + lab).properties(height=320, padding={"right": 90}), **S_CH)
    st.markdown("#### Average completion by area")
    d = pd.DataFrame([{"Area": f["area"], "Completion": f["pct"]} for f in fl]).groupby("Area", as_index=False).mean()
    d["Label"] = d["Completion"].map(lambda v: f"{v:.0f}%")
    yenc = alt.Y("Area:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300, labelFontSize=12))
    bars = alt.Chart(d).mark_bar(color="#16a34a", cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
        x=alt.X("Completion:Q", scale=alt.Scale(domain=[0, 100]), title="% complete", axis=alt.Axis(values=[0, 25, 50, 75, 100])), y=yenc, tooltip=[alt.Tooltip("Area:N"), alt.Tooltip("Label:N", title="Average completion")])
    lab = alt.Chart(d).mark_text(align="left", dx=6, fontSize=13, fontWeight="bold", color="#0f172a").encode(x="Completion:Q", y=yenc, text="Label:N")
    st.altair_chart((bars + lab).properties(height=max(150, 44 * len(d)), padding={"right": 40}), **S_CH)


# ---------------------------------------------------------------------------------------------
# KPI scoreboard + action register
# ---------------------------------------------------------------------------------------------
def _kpi_scoreboard(rkey, fl):
    ks = [dict(k, _f=f) for f in fl for k in f["kpis"]]
    withT = [k for k in ks if k["target"] is not None]
    pcts = [core.kpi_pct(k["baseline"], k["current"], k["target"]) for k in withT]
    met = sum(1 for p in pcts if p == 100)
    improving = sum(1 for k in withT if core.kpi_trend(k["baseline"], k["current"], k["target"]) == "improving")
    worse = sum(1 for k in withT if core.kpi_trend(k["baseline"], k["current"], k["target"]) == "worse")
    c = st.columns(5)
    c[0].metric("KPIs tracked", len(ks))
    c[1].metric("With a target", len(withT))
    c[2].metric("Targets met", met)
    c[3].metric("Improving / worse", f"{improving} / {worse}")
    c[4].metric("Average progress", f"{round(sum(pcts) / len(pcts)) if pcts else 0}%")
    f1, f2, f3 = st.columns([2, 2, 1.5])
    areas = list(dict.fromkeys(f["area"] for f in fl))
    a_sel = f1.selectbox("Area", ["All areas"] + areas, key=f"{rkey}_ksa", label_visibility="collapsed")
    q = f2.text_input("Search", placeholder="🔍 Search KPI or finding…", key=f"{rkey}_ksq", label_visibility="collapsed")
    only_t = f3.toggle("Only KPIs with a target", key=f"{rkey}_kst")
    rows = []
    for k in ks:
        if a_sel != "All areas" and k["_f"]["area"] != a_sel:
            continue
        if only_t and k["target"] is None:
            continue
        if q.strip() and q.strip().lower() not in (k["name"] + " " + k["_f"]["title"] + " " + k["ref"]).lower():
            continue
        tl = core.TREND_LABEL[core.kpi_trend(k["baseline"], k["current"], k["target"])][0]
        rows.append({"Ref": k["ref"], "Finding": k["_f"]["title"], "KPI": k["name"], "Baseline": core.fmt_value(k["baseline"], k["unit"]),
                     "Current": core.fmt_value(k["current"], k["unit"]), "Target": core.fmt_value(k["target"], k["unit"]) if k["target"] is not None else "not set",
                     "Progress": core.kpi_pct(k["baseline"], k["current"], k["target"]), "Trend": tl, "As of": core.fmt_date(k["as_of"]), "Target basis": k["basis"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, height=min(720, 40 + 35 * max(len(rows), 1)),
                 column_config={"Progress": st.column_config.ProgressColumn("Progress to target", min_value=0, max_value=100, format="%d%%"),
                                "Finding": st.column_config.TextColumn(width="large"), "KPI": st.column_config.TextColumn(width="large")}, **S_DF)
    st.caption("Update a KPI from its finding card → **🎯 KPIs & charts → Record measurement**. Progress = how far the current value has moved from the baseline toward the target.")


def _report_tab(rkey, M):
    rep = seed.REPORTS[rkey]
    fl = [f for f in M["findings"] if f["report"] == rkey]
    _report_card(rep, fl)
    _kpi_cards(rkey, fl)
    t1, t2, t3 = st.tabs(["📋 Findings & actions (table)", "📊 Dashboard", "🎯 KPI scoreboard"])
    with t1:
        _findings_view(rkey, fl)
    with t2:
        _dashboard(fl)
    with t3:
        _kpi_scoreboard(rkey, fl)


# ---------------------------------------------------------------------------------------------
# Export / settings / log
# ---------------------------------------------------------------------------------------------
def _export_tab(M):
    t = ia_db.totals()
    st.markdown(f"Your tracker holds **{t['findings']} findings**, **{t['actions']} actions**, **{t['kpis']} KPIs** ({t['measurements']} measurements), "
                f"**{t['documents']} documents** and **{t['comments']} comments**.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📊 Excel export")
        st.caption("Summary · Regional actions · Central actions · Findings · KPIs · KPI history · Comments")
        if st.button("Prepare Excel workbook", key="ia_prep_x", **S_BTN):
            st.session_state["_ia_xlsx"] = ia_export.build_workbook(ia_db.load_findings(), ia_db.load_actions(), ia_db.load_kpis(), ia_db.kpi_history,
                                                                    ia_db.comments_all(), ia_db.get_meta("fy_label", ""))
        if st.session_state.get("_ia_xlsx"):
            st.download_button("⬇ Download Excel workbook", st.session_state["_ia_xlsx"], file_name=f"RMS_Internal_Audit_Action_Tracker_{core.today().isoformat()}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", **S_DL)
    with c2:
        st.subheader("🗄️ Full backup")
        st.caption("The whole tracker (including documents) is one SQLite file. Keep a copy somewhere safe.")
        if st.button("Prepare database backup", key="ia_prep_db", **S_BTN):
            st.session_state["_ia_db"] = ia_db.read_db_bytes()
        if st.session_state.get("_ia_db"):
            st.download_button("⬇ Download backup (.db)", st.session_state["_ia_db"], file_name=f"ia_tracker_backup_{core.today().isoformat()}.db",
                               mime="application/octet-stream", type="primary", **S_DL)
    st.divider()
    st.subheader("⚙️ Settings")
    fy = st.text_input("Financial-year label shown in the header", ia_db.get_meta("fy_label", "FY 2024–2025"), key="ia_fy_in")
    if st.button("Save label", key="ia_fy_save"):
        ia_db.set_meta("fy_label", fy.strip())
        _toast("Label saved")
        st.rerun()
    st.divider()
    st.subheader("ℹ️ How progress is measured")
    st.markdown(
        "- **Action status** → *Not Started* 0% · *In Progress* 1–89% · *Implemented – Pending Verification* ≥90% (management says it is done; Internal Audit has not yet confirmed) · "
        "*Closed – Verified* 100% · *Disputed* (management disagrees with the finding) · *Not Applicable* (ignored in the maths).\n"
        "- **Overdue** = an action that is *Not Started* or *In Progress* and whose target date has passed.\n"
        "- **Finding completion** = average % complete of its actions. **Area completion** = average of its findings.\n"
        "- **KPI progress** = (current − baseline) ÷ (target − baseline), capped 0–100%, so it works whether *lower* (e.g. unsupported Rwf) or *higher* (e.g. accuracy %) is better. "
        "KPIs without a target in the report show no progress until one is set.\n"
        "- **Baselines** are the figures in the audit reports. *Current* starts equal to the baseline: nothing is counted as fixed until a measurement is recorded.")


def _log_tab():
    df = ia_db.get_logs()
    if df.empty:
        st.info("No activity yet.")
    else:
        df.columns = ["When", "What happened"]
        st.dataframe(df, hide_index=True, height=620, **S_DF)


# ---------------------------------------------------------------------------------------------
def _go(page):
    st.session_state["ia_page"] = page


def _nav(current):
    items = [("home", "🏠 Home"), ("regional", "🏬 Regional Warehouses"), ("central", "🏭 Central Warehouse"), ("export", "💾 Export & Settings"), ("log", "🕘 Activity log")]
    cols = st.columns([1, 1.6, 1.5, 1.5, 1.3, 2.2])
    for col, (k, lb) in zip(cols, items):
        col.button(lb, key=f"nav-{k}", type="primary" if k == current else "secondary", on_click=_go, args=(k,), **S_BTN)
    cols[5].text_input("Your name", key="ia_user", placeholder="👤 Your name (saved in the activity log)", label_visibility="collapsed")


_HOME = [("regional", "🏬", "Regional Warehouses", "8 branches · Q3 audit report", "--g1:#fff3c4;--g2:#ffe083;--bd:#f5c542;--tt:#5a2a00;--st:#b45309"),
         ("central", "🏭", "Central Warehouse", "Central Warehouse · Q4 audit report", "--g1:#e6fff4;--g2:#cdf7e2;--bd:#6ee7b7;--tt:#064e3b;--st:#0f766e")]


def _home(M):
    st.markdown("<div class='ia'><div class='ia-home-h'>Where do you want to work?</div><div class='ia-home-s'>Choose a module — the two audit reports are kept apart.</div></div>", unsafe_allow_html=True)
    for col, (k, icon, title, sub_, theme) in zip(st.columns(2, gap="large"), _HOME):
        fl = [f for f in M["findings"] if f["report"] == k]
        s_ = _stats(fl)
        with col:
            with st.container(key=f"home-{k}"):
                st.markdown(f"<div class='ia'><div class='ia-home' style='{theme}'><div class='ico'>{icon}</div><div class='t'>{esc(title)}</div><div class='s'>{esc(sub_)}</div>"
                            f"<div class='n'>{s_['findings']} findings · {s_['actions']} recommendations · {s_['overdue']} overdue · {s_['avg']}% complete</div><span class='go'>Open →</span></div></div>", unsafe_allow_html=True)
                with st.container(key=f"homeb-{k}"):
                    st.button("open", key=f"homebtn-{k}", on_click=_go, args=(k,))
    st.write("")
    c1, c2, _x = st.columns([1.4, 1.2, 4])
    c1.button("💾 Export & Settings", key="home-export", on_click=_go, args=("export",), **S_BTN)
    c2.button("🕘 Activity log", key="home-log", on_click=_go, args=("log",), **S_BTN)


_DBLCLICK_JS = """
<script>
(function(){
  var d = window.parent.document;
  function wire(){
    d.querySelectorAll('[class*="st-key-kpi-"]').forEach(function(el){
      if (el.dataset.iaDbl) return; el.dataset.iaDbl = '1';
      el.addEventListener('dblclick', function(){
        var m = (el.className.match(/st-key-kpi-([a-z]+)-/) || [])[1];
        if (!m) return;
        var u = d.querySelector('[class*="st-key-kpiundo-' + m + '"] button');
        if (u) u.click();
      });
    });
  }
  wire(); setInterval(wire, 700);
})();
</script>
"""


def _inject_js(js):
    """Run a tiny script in a hidden iframe (st.components.v1.html is being retired; st.iframe replaces it)."""
    if hasattr(st, "iframe"):
        st.iframe(js, height=1)
    else:
        components.html(js, height=0)


def render_page():
    ia_db.init()
    ia_db.seed_if_needed()
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    toast = st.session_state.pop("_ia_toast", None)
    if toast:
        st.toast(toast)
    M = build_model()
    page = st.session_state.get("ia_page", "home")
    _hero(M, ia_db.get_meta("fy_label", "FY 2024–2025"))
    _nav(page)
    if page == "regional":
        _report_tab("regional", M)
    elif page == "central":
        _report_tab("central", M)
    elif page == "export":
        _export_tab(M)
    elif page == "log":
        _log_tab()
    else:
        _home(M)
    _inject_js(_DBLCLICK_JS)
