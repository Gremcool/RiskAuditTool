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
from collections import defaultdict
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

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
    st.session_state["_ia_toast"] = msg


def _logo_b64():
    try:
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except OSError:
        return ""


# ---------------------------------------------------------------------------------------------
# Small HTML builders
# ---------------------------------------------------------------------------------------------
def _state_chip(state, extra=""):
    label, color, bg = core.STATE[state]
    return f"<span class='st' style='background:{bg};color:{color}'>{esc(label)}{esc(extra)}</span>"


def _due_html(status, due):
    d = core.parse_date(due)
    if status in core.DONE_STATUSES or status == core.IPV:
        return f"<span class='du d-ok'>Target {core.fmt_date(d)}</span>" if d else ""
    if d is None:
        return "<span class='du d-none'>⚠ No target date</span>"
    dl = core.days_left(d)
    if status in core.OPEN_STATUSES and dl < 0:
        return f"<span class='du d-over'>⏰ {core.fmt_date(d)} · {abs(dl)} days overdue</span>"
    if status in core.OPEN_STATUSES and dl <= 14:
        return f"<span class='du d-soon'>⏳ {core.fmt_date(d)} · due in {dl} day{'s' if dl != 1 else ''}</span>"
    return f"<span class='du d-ok'>📅 {core.fmt_date(d)}</span>"


def _kpi_color(k):
    raw = core.kpi_progress(k["baseline"], k["current"], k["target"])
    if raw is None:
        return "#2f5fb3"
    return "#16a34a" if raw >= 0.999 else ("#22c55e" if raw > 0.0005 else ("#dc2626" if raw < -0.0005 else "#94a3b8"))


def _bk_html(k):
    bd = k["breakdown"]
    unit = k["unit"]
    tgt = k["target"]
    vals = [abs(b["baseline"]) for b in bd] + [abs(b["current"]) for b in bd]
    mx = 100.0 if unit == "%" else (max(vals) or 1.0)
    rows = []
    for b in bd:
        wb, wc = abs(b["baseline"]) / mx * 100, abs(b["current"]) / mx * 100
        if tgt is not None:
            closer = abs(b["current"] - tgt) < abs(b["baseline"] - tgt) - 1e-9
            worse = abs(b["current"] - tgt) > abs(b["baseline"] - tgt) + 1e-9
            col = "#16a34a" if closer else ("#dc2626" if worse else "#2f5fb3")
        else:
            col = "#2f5fb3"
        tick = f"<u style='left:{min(abs(tgt) / mx * 100, 99.5):.1f}%'></u>" if (tgt not in (None, 0) and unit == "%") else ""
        rows.append(
            f"<div class='bk'><span class='lb' title='{esc(b['label'])}'>{esc(b['label'])}</span>"
            f"<span class='tr'><i class='b' style='width:{min(wb, 100):.1f}%'></i><i class='c' style='width:{min(wc, 100):.1f}%;background:{col}'></i>{tick}</span>"
            f"<span class='nm'>{esc(core.fmt_value(b['baseline'], unit))}<b>→ {esc(core.fmt_value(b['current'], unit))}</b></span></div>")
    return f"<div class='ia-bkt'>{esc(k['name'])}</div>" + "".join(rows)


def _kpi_table_html(f):
    if not f["kpis"]:
        return ""
    rows = []
    for k in f["kpis"]:
        pct = core.kpi_pct(k["baseline"], k["current"], k["target"])
        trend = core.kpi_trend(k["baseline"], k["current"], k["target"])
        tl, tc = core.TREND_LABEL[trend]
        unit = k["unit"]
        if k["target"] is None:
            tgt = "<i style='color:#94a3b8'>not set</i>"
        elif unit in ("%", "days") and k["baseline"] is not None:
            tgt = ("≥ " if k["target"] > k["baseline"] else "≤ ") + esc(core.fmt_value(k["target"], unit))
        else:
            tgt = esc(core.fmt_value(k["target"], unit))
        if pct is None:
            prog = "<span style='color:#94a3b8'>—</span>"
        else:
            prog = f"<span class='ia-pb'><i style='width:{pct}%;background:{_kpi_color(k)}'></i></span><b>{pct}%</b>"
        rows.append(
            f"<tr><td title='{esc(k['basis'])}'>{esc(k['name'])}</td><td class='n'>{esc(core.fmt_value(k['baseline'], unit))}</td>"
            f"<td class='n'><b>{esc(core.fmt_value(k['current'], unit))}</b></td><td class='n t'>{tgt}</td>"
            f"<td class='n'>{prog}</td><td class='n'><span class='ia-tr' style='color:{tc}'>{esc(tl)}</span></td></tr>")
    html = ("<table class='ia-kt'><tr><th>KPI</th><th>Baseline</th><th>Current</th><th>Target</th><th>Progress</th><th>Trend</th></tr>"
            + "".join(rows) + "</table>")
    bks = [k for k in f["kpis"] if k["breakdown"]]
    if bks:
        html += ("<details class='ia-det'><summary>📍 Breakdown by warehouse / item — baseline (grey) vs current (colour)</summary>"
                 + "".join(_bk_html(k) for k in bks)
                 + "<div class='ia-leg'>Bars are scaled to the largest value in each KPI. Green = closer to target than baseline, red = further away. "
                   "A black tick marks the target on % KPIs.</div></details>")
    return html


def _actions_html(f):
    out = []
    for a in f["actions"]:
        st_ = core.action_state(a["status"], a["due_date"])
        extra = f" · {a['pct']}%" if a["status"] in (core.IP, core.IPV) else ""
        label, color, bg = core.STATE[st_]
        chip = f"<span class='st' style='background:{bg};color:{color}'>{esc(a['status'])}{extra}</span>"
        if st_ == "overdue":
            chip = f"<span class='st' style='background:{bg};color:{color}'>Overdue · {esc(a['status'])}{extra}</span>"
        proposed = "" if a["owner_confirmed"] else " <i>proposed</i>"
        owner = f"<span class='ow'>👤 {esc(a['owner'])}{proposed}</span>" if a["owner"] else "<span class='ow d-none'>👤 no owner</span>"
        note = f"<div class='nt'>📝 {esc(a['note'])}</div>" if a["note"] else ""
        due = _due_html(a["status"], a["due_date"]) or "<span class='du'></span>"
        out.append(f"<div class='ia-act'>{chip}<span class='tx'><b class='rf'>{esc(f['ref'])}.{a['seq']}</b><span>{esc(a['text'])}</span></span>{owner}{due}{note}</div>")
    return "".join(out)


def _mgmt_cls(pos):
    return "m-" + (pos.split(" ")[0] if pos else "No")


def _card_html(f):
    acts = f["actions"]
    live = [a for a in acts if a["status"] != core.NA]
    n_closed = sum(1 for a in live if a["status"] == core.CL)
    n_ver = sum(1 for a in live if a["status"] == core.IPV)
    n_over = sum(1 for a in live if core.action_state(a["status"], a["due_date"]) == "overdue")
    cnt = f"{n_closed}/{len(live)} actions closed"
    if n_ver:
        cnt += f" · {n_ver} awaiting verification"
    if n_over:
        cnt += f" · <span style='color:#b91c1c'>{n_over} overdue</span>"
    chips = [f"<span class='chip area'>{esc(f['area'])}</span>", f"<span class='chip p-{esc(f['priority'])}'>● {esc(f['priority'])} priority</span>",
             f"<span class='chip {_mgmt_cls(f['mgmt_position'])}'>Mgmt: {esc(f['mgmt_position'])}</span>"]
    if f["flagged_label"]:
        chips.append(f"<span class='chip flag'>💰 {esc(f['flagged_label'])}</span>")
    if f["src_ref"]:
        chips.append(f"<span class='chip src'>Report: {esc(f['src_ref'])}</span>")
    det = ("<details class='ia-det'><summary>🔎 Observation, criteria, risk &amp; management response</summary><div class='g'>"
           f"<div><b>Observation</b>{esc(f['observation'])}</div>"
           f"<div><b>Criteria</b>{esc(f['criteria']) or '—'}</div>"
           f"<div><b>Risk</b>{esc(f['risk'])}</div>"
           f"<div><b>Management response — {esc(f['mgmt_position'])}</b>{esc(f['mgmt_comment']) or '—'}"
           f"<br><span style='color:#64748b'>Timeline stated in report: <b style='display:inline;text-transform:none;letter-spacing:0;font-size:12px;color:#0f172a'>{esc(f['timeline']) or '—'}</b></span></div>"
           + (f"<div><b>Notes</b>{esc(f['notes'])}</div>" if f["notes"] else "") + "</div></details>")
    return ("<div class='ia'>"
            f"<div class='ia-head'><span class='ia-ref {f['state']}'>{esc(f['ref'])}</span><div style='flex:1'>"
            f"<div class='ia-title'>{esc(f['title'])}</div><div class='ia-chips'>{''.join(chips)}</div></div></div>"
            f"<div class='ia-prog'><div class='bar'><span style='width:{f['pct']}%'></span></div><b>{f['pct']}%</b><span class='cnt'>{cnt}</span>"
            f"<span class='st' style='background:{core.STATE[f['state']][2]};color:{core.STATE[f['state']][1]};font-size:12px;font-weight:800;padding:4px 11px;border-radius:99px'>{esc(core.STATE[f['state']][0])}</span></div>"
            f"{_actions_html(f)}{_kpi_table_html(f)}{det}</div>")


# ---------------------------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------------------------
def _find(fid):
    for f in build_model()["findings"]:
        if f["id"] == fid:
            return f
    return None


def _actions_body(fid):
    f = _find(fid)
    if not f:
        st.warning("Finding not found.")
        return
    st.caption(f"**{f['title']}**  ·  Status changes also set the % complete (Closed = 100%). "
               "Editing an owner confirms it (owners start as *proposed* from the management comments).")
    with st.form(f"actform_{fid}", border=False):
        for a in f["actions"]:
            aid = a["id"]
            with st.container(border=True):
                st.markdown(f"**{f['ref']}.{a['seq']}**  " + _state_chip(core.action_state(a["status"], a["due_date"])), unsafe_allow_html=True)
                st.text_area("Recommended action", a["text"], key=f"a_tx_{aid}", height=72, label_visibility="collapsed")
                c1, c2, c3, c4 = st.columns([1.6, 1.6, 1.2, 0.9])
                c1.selectbox("Status", core.STATUSES, index=core.STATUSES.index(a["status"]) if a["status"] in core.STATUSES else 0, key=f"a_st_{aid}")
                c2.text_input("Owner" + ("" if a["owner_confirmed"] else " (proposed)"), a["owner"], key=f"a_ow_{aid}")
                c3.date_input("Target date", value=core.parse_date(a["due_date"]), format="DD/MM/YYYY", key=f"a_du_{aid}")
                c4.number_input("% complete", 0, 100, int(a["pct"]), step=5, key=f"a_pc_{aid}")
                st.text_area("Update / evidence", a["note"], key=f"a_nt_{aid}", height=68,
                             placeholder="What was done, evidence reference, memo no., date verified…")
                st.checkbox("Remove this action", key=f"a_rm_{aid}")
        ok = st.form_submit_button("💾 Save changes", type="primary", **S_BTN)
    if ok:
        changed = 0
        for a in f["actions"]:
            aid = a["id"]
            if st.session_state.get(f"a_rm_{aid}"):
                ia_db.delete_action(aid, _user())
                changed += 1
                continue
            due = st.session_state.get(f"a_du_{aid}")
            if ia_db.save_action(aid, text=st.session_state[f"a_tx_{aid}"], owner=st.session_state[f"a_ow_{aid}"].strip(),
                                 due_date=due if due else "", status=st.session_state[f"a_st_{aid}"],
                                 pct=st.session_state[f"a_pc_{aid}"], note=st.session_state[f"a_nt_{aid}"], who=_user()):
                changed += 1
        _toast(f"Saved {changed} action update(s) on {f['ref']}" if changed else "No changes to save")
        st.rerun()
    with st.expander("➕ Add another action to this finding"):
        with st.form(f"addact_{fid}", border=False, clear_on_submit=True):
            t = st.text_area("Action", height=70)
            c1, c2 = st.columns(2)
            ow = c1.text_input("Owner")
            du = c2.date_input("Target date", value=None, format="DD/MM/YYYY")
            if st.form_submit_button("Add action", **S_BTN) and t.strip():
                ia_db.add_action(fid, t.strip(), ow.strip(), du, core.NS, _user())
                _toast(f"Action added to {f['ref']}")
                st.rerun()


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


def _more_body(fid):
    f = _find(fid)
    if not f:
        return
    t_det, t_doc, t_cm = st.tabs(["📄 Details", f"📎 Documents ({len(f['docs'])})", f"💬 Comments ({len(f['comments'])})"])
    with t_det:
        areas = sorted({x["area"] for x in build_model()["findings"] if x["report"] == f["report"]})
        with st.form(f"fdet_{fid}", border=False):
            title = st.text_input("Finding title", f["title"])
            c1, c2, c3 = st.columns(3)
            pr = c1.selectbox("Priority", core.PRIORITIES, index=core.PRIORITIES.index(f["priority"]) if f["priority"] in core.PRIORITIES else 1)
            mp = c2.selectbox("Management position", core.MGMT_POSITIONS, index=core.MGMT_POSITIONS.index(f["mgmt_position"]) if f["mgmt_position"] in core.MGMT_POSITIONS else 0)
            area = c3.selectbox("Area", areas, index=areas.index(f["area"]) if f["area"] in areas else 0)
            obs = st.text_area("Observation", f["observation"], height=110)
            c4, c5 = st.columns(2)
            crit = c4.text_area("Criteria", f["criteria"], height=80)
            risk = c5.text_area("Risk", f["risk"], height=80)
            mc = st.text_area("Management comment", f["mgmt_comment"], height=90)
            c6, c7 = st.columns(2)
            tl = c6.text_input("Timeline stated in the report", f["timeline"])
            fl = c7.text_input("Value flagged (label)", f["flagged_label"])
            nt = st.text_area("Internal notes", f["notes"], height=70)
            if st.form_submit_button("💾 Save details", type="primary", **S_BTN):
                ia_db.update_finding(fid, {"title": title, "priority": pr, "mgmt_position": mp, "area": area, "observation": obs, "criteria": crit,
                                           "risk": risk, "mgmt_comment": mc, "timeline": tl, "flagged_label": fl, "notes": nt}, _user())
                _toast(f"{f['ref']} details saved")
                st.rerun()
    with t_doc:
        st.caption("Attach evidence of implementation (memos, reconciliations, screenshots, signed reports…).")
        for d in ia_db.list_documents(fid):
            c1, c2, c3 = st.columns([5, 2, 1])
            c1.markdown(f"📄 **{esc(d['filename'])}**  \n<span style='color:#64748b;font-size:12px'>{d['size'] / 1024:,.0f} KB · {esc(d['uploaded_by'] or '—')} · {d['uploaded_at'][:16]}"
                        f"{' · ' + esc(d['note']) if d['note'] else ''}</span>", unsafe_allow_html=True)
            full = ia_db.get_document(d["id"])
            c2.download_button("⬇ Download", full["data"], file_name=d["filename"], mime=d["mime"] or "application/octet-stream", key=f"dl_{d['id']}", **S_DL)
            if c3.button("🗑️", key=f"deldoc_{d['id']}", help="Remove this document"):
                ia_db.delete_document(d["id"], _user())
                _toast("Document removed")
                st.rerun()
        ver = st.session_state.get(f"upver_{fid}", 0)
        files = st.file_uploader("Add documents", accept_multiple_files=True, key=f"up_{fid}_{ver}")
        note = st.text_input("Note (optional)", key=f"upn_{fid}_{ver}")
        if st.button(f"📎 Attach {len(files) if files else ''} file(s)", type="primary", disabled=not files, key=f"attach_{fid}_{ver}"):
            for fl_ in files:
                if fl_.size > ia_db.MAX_FILE_MB * 1024 * 1024:
                    st.error(f"{fl_.name} is larger than {ia_db.MAX_FILE_MB} MB")
                    continue
                ia_db.add_document(fid, fl_.name, fl_.type, fl_.getvalue(), note, _user())
            st.session_state[f"upver_{fid}"] = ver + 1
            _toast("Document(s) attached")
            st.rerun()
    with t_cm:
        for c in ia_db.list_comments(fid):
            st.markdown(f"<div class='ia-box'><b>{esc(c['author'])}</b> <span style='color:#64748b'>· {c['created_at'][:16]}</span><br>{esc(c['body'])}</div>", unsafe_allow_html=True)
            st.write("")
        with st.form(f"cm_{fid}", border=False, clear_on_submit=True):
            who = st.text_input("Your name", value=_user())
            body = st.text_area("Comment", height=90)
            if st.form_submit_button("💬 Post comment", type="primary", **S_BTN) and body.strip():
                ia_db.add_comment(fid, who.strip(), body.strip())
                _toast("Comment posted")
                st.rerun()


def _new_finding_body(rkey):
    rep = seed.REPORTS[rkey]
    areas = sorted({x["area"] for x in build_model()["findings"] if x["report"] == rkey})
    st.caption(f"Adds a finding to the **{rep['name']}** tab (for example one raised in a follow-up review).")
    with st.form(f"newf_{rkey}", border=False):
        title = st.text_input("Finding title *")
        c1, c2, c3 = st.columns(3)
        area_sel = c1.selectbox("Area", areas + ["➕ New area…"])
        pr = c2.selectbox("Priority", core.PRIORITIES, index=1)
        mp = c3.selectbox("Management position", core.MGMT_POSITIONS, index=4)
        new_area = st.text_input("New area name (only if you chose ‘New area…’)")
        obs = st.text_area("Observation", height=90)
        risk = st.text_area("Risk", height=60)
        act = st.text_area("First recommended action", height=60)
        c4, c5 = st.columns(2)
        ow = c4.text_input("Action owner")
        du = c5.date_input("Action target date", value=None, format="DD/MM/YYYY")
        if st.form_submit_button("➕ Add finding", type="primary", **S_BTN):
            area = new_area.strip() if area_sel.startswith("➕") else area_sel
            if not title.strip() or not area:
                st.error("Please give a title and an area.")
            else:
                fid = ia_db.add_finding(rkey, {"title": title.strip(), "area": area, "priority": pr, "mgmt_position": mp, "observation": obs, "risk": risk}, _user())
                if act.strip():
                    ia_db.add_action(fid, act.strip(), ow.strip(), du, core.NS, _user())
                _toast("Finding added")
                st.rerun()


def _open(title, body, *args, width="large"):
    st.dialog(title, width=width)(body)(*args)


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
    s = _stats(fl)
    labels = ["Unacceptable risk exposure", "Major improvement opportunity", "Some improvement opportunity", "Satisfactory", "Well managed"]
    rc = {1: "#b91c1c", 2: "#ea580c", 3: "#ca8a04", 4: "#16a34a", 5: "#15803d"}.get(rep["rating_level"], "#64748b")
    head = f"<div class='ia-rating-head' style='--rc:{rc}'>★ {esc(rep['rating'])}</div>" if rep["rating_level"] else ""
    if rep["rating_level"]:
        scale = head + "<div class='ia-scale' style='margin:10px 0 8px'>" + "".join(f"<span class='{'on l' + str(i + 1) if i + 1 == rep['rating_level'] else ''}'>{esc(l)}</span>" for i, l in enumerate(labels)) + "</div>"
    else:
        scale = "<div class='ia-scale' style='grid-template-columns:1fr'><span>Overall rating not stated in the report</span></div>"
    notes = f"<div class='ia-note'>ℹ️ {esc(rep['notes'])}</div>" if rep["notes"] else ""
    signed = f"<br><b>Signed:</b> {esc(rep['signed'])}" if rep["signed"] else ""
    st.markdown(
        "<div class='ia'><div class='ia-rep'><div class='l'>"
        f"<h3>{esc(rep['title'])}</h3><div class='meta'><b>Issued:</b> {esc(rep['issued'])} &nbsp;·&nbsp; <b>Audit period:</b> {esc(rep['period'])}"
        f"<br><b>Scope:</b> {esc(rep['scope'])}<br><b>Source:</b> {esc(rep['file'])}{signed}</div>"
        f"<div class='concl'>{esc(rep['conclusion'])}</div>{notes}</div>"
        f"<div class='r'><div class='lbl'>Overall rating (as given by the auditors)</div>{scale}"
        f"<div class='lbl' style='margin-top:10px'>Implementation progress</div>"
        f"<div class='ia-prog' style='margin:3px 0'><div class='bar' style='width:100%;max-width:340px;height:12px'><span style='width:{s['avg']}%'></span></div><b>{s['avg']}%</b></div>"
        f"<div class='ia-note' style='margin-top:0'>Average % complete across {s['actions']} recommended actions</div></div></div></div>",
        unsafe_allow_html=True)

    def card(lb, vl, sb, color, icon):
        return f"<div class='ia-kpi' style='--c:{color}'><span class='ic'>{icon}</span><div class='lb'>{lb}</div><div class='vl'>{vl}</div><div class='sb'>{sb}</div></div>"
    base = max(s["actions"], 1)
    st.markdown("<div class='ia'><div class='ia-kpis'>"
                + card("Findings", s["findings"], f"{s['high']} high priority", "#1e3c72", "📋")
                + card("Actions", s["actions"], f"{s['disputed']} disputed by management", "#2f5fb3", "✅")
                + card("Closed · verified", s["closed"], f"{s['closed'] / base * 100:.0f}% of actions", "#15803d", "🔒")
                + card("Awaiting verification", s["verify"], "management says done", "#6d28d9", "🔎")
                + card("Overdue", s["overdue"], "past target date", "#b91c1c", "🚨")
                + card("No target date", s["nodate"], "open actions need a date", "#64748b", "📅")
                + "</div></div>", unsafe_allow_html=True)


def _findings_view(rkey, fl):
    areas = list(dict.fromkeys(f["area"] for f in fl))
    owners = sorted({a["owner"] for f in fl for a in f["actions"] if a["owner"]})
    f1, f2, f3, f4, f5 = st.columns([2.4, 2, 1.3, 1.8, 2])
    q = f1.text_input("Search", placeholder="🔍 Search ref, wording, owner…", key=f"{rkey}_q", label_visibility="collapsed")
    area_sel = f2.selectbox("Area", ["All areas"] + areas, key=f"{rkey}_area", label_visibility="collapsed")
    pr_sel = f3.selectbox("Priority", ["Any priority"] + core.PRIORITIES, key=f"{rkey}_pr", label_visibility="collapsed")
    status_opts = ["Any status", "Open (not closed)", "Overdue", "Awaiting verification", "In progress", "Not started", "Disputed", "Closed – verified"]
    st_sel = f4.selectbox("Status", status_opts, key=f"{rkey}_st", label_visibility="collapsed")
    own_sel = f5.selectbox("Owner", ["Any owner"] + owners, key=f"{rkey}_ow", label_visibility="collapsed")
    t1, t2, t3, _sp, t5 = st.columns([1.5, 1.6, 1.8, 2.2, 1.6])
    hide_closed = t1.toggle("🙈 Hide closed", key=f"{rkey}_hide")
    nodate = t2.toggle("📅 Missing a date", key=f"{rkey}_nodate")
    high = t3.toggle("🔥 High priority only", key=f"{rkey}_high")
    if t5.button("➕ New finding", type="primary", key=f"{rkey}_new", **S_BTN):
        _open(f"➕ New finding · {seed.REPORTS[rkey]['name']}", _new_finding_body, rkey)

    smap = {"Overdue": "overdue", "Awaiting verification": "verify", "In progress": "progress", "Not started": "pending", "Disputed": "disputed", "Closed – verified": "closed"}
    view = []
    for f in fl:
        if area_sel != "All areas" and f["area"] != area_sel:
            continue
        if pr_sel != "Any priority" and f["priority"] != pr_sel:
            continue
        if st_sel == "Open (not closed)" and f["state"] == "closed":
            continue
        if st_sel in smap and f["state"] != smap[st_sel]:
            continue
        if own_sel != "Any owner" and not any(a["owner"] == own_sel for a in f["actions"]):
            continue
        if hide_closed and f["state"] == "closed":
            continue
        if high and f["priority"] != "High":
            continue
        if nodate and not any(a["status"] in core.OPEN_STATUSES and not a["due_date"] for a in f["actions"]):
            continue
        if q.strip():
            blob = " ".join([f["ref"], f["title"], f["observation"], f["risk"], f["area"], f["src_ref"]] + [a["text"] + " " + a["owner"] + " " + a["note"] for a in f["actions"]]
                            + [k["name"] for k in f["kpis"]]).lower()
            if q.strip().lower() not in blob:
                continue
        view.append(f)
    st.caption(f"Showing **{len(view)}** of {len(fl)} findings")
    if not view:
        st.markdown("<div class='ia'><div class='ia-empty'><div style='font-size:28px'>🔎</div><b>No findings match these filters.</b></div></div>", unsafe_allow_html=True)
        return
    last_area = None
    for f in view:
        if f["area"] != last_area:
            last_area = f["area"]
            grp = [x for x in fl if x["area"] == last_area]
            avg = round(sum(x["pct"] for x in grp) / len(grp))
            st.markdown(f"<div class='ia'><div class='ia-sec'><span class='num'>{len(grp)}</span><span class='tt'>{esc(last_area)}</span>"
                        f"<div class='bar'><span style='width:{avg}%'></span></div><span class='mt'><b>{avg}%</b> average completion</span></div></div>", unsafe_allow_html=True)
        with st.container(key=f"iacard-{f['state']}-{f['id']}"):
            st.markdown(_card_html(f), unsafe_allow_html=True)
            b1, b2, b3, _s = st.columns([1.3, 1.4, 2.2, 3])
            if b1.button("✅ Update actions", key=f"{rkey}_ba_{f['id']}", **S_BTN):
                _open(f"✅ {f['ref']} · Recommended actions", _actions_body, f["id"])
            if b2.button("🎯 KPIs & charts", key=f"{rkey}_bk_{f['id']}", **S_BTN):
                _open(f"🎯 {f['ref']} · KPIs & progress charts", _kpis_body, f["id"])
            extra = []
            if f["docs"]:
                extra.append(f"📎{len(f['docs'])}")
            if f["comments"]:
                extra.append(f"💬{len(f['comments'])}")
            if b3.button("📝 Details · Docs · Comments" + (" · " + " ".join(extra) if extra else ""), key=f"{rkey}_bm_{f['id']}", **S_BTN):
                _open(f"📝 {f['ref']} · {f['title'][:70]}", _more_body, f["id"])


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


def _action_register(rkey, fl):
    acts = [(f, a) for f in fl for a in f["actions"]]
    owners = sorted({a["owner"] for _, a in acts if a["owner"]})
    f1, f2, f3, f4 = st.columns([2.5, 2.5, 2, 1.6])
    stat_sel = f1.multiselect("Status", core.STATUSES, key=f"{rkey}_rs", placeholder="Any status", label_visibility="collapsed")
    own_sel = f2.selectbox("Owner", ["Any owner"] + owners, key=f"{rkey}_ro", label_visibility="collapsed")
    q = f3.text_input("Search", placeholder="🔍 Search actions…", key=f"{rkey}_rq", label_visibility="collapsed")
    over = f4.toggle("⏰ Overdue only", key=f"{rkey}_rov")
    rows = []
    for f, a in acts:
        if stat_sel and a["status"] not in stat_sel:
            continue
        if own_sel != "Any owner" and a["owner"] != own_sel:
            continue
        if over and core.action_state(a["status"], a["due_date"]) != "overdue":
            continue
        if q.strip() and q.strip().lower() not in (a["text"] + f["title"] + a["owner"] + f["ref"] + a["note"]).lower():
            continue
        dl = core.days_left(a["due_date"])
        rows.append({"ID": a["id"], "Ref": f"{f['ref']}.{a['seq']}", "Finding": f["title"], "Action": a["text"], "Owner": a["owner"],
                     "Target date": pd.to_datetime(a["due_date"]) if a["due_date"] else pd.NaT, "Status": a["status"], "% complete": int(a["pct"]),
                     "Days overdue": (-dl if (dl is not None and dl < 0 and a["status"] in core.OPEN_STATUSES) else 0), "Update / evidence": a["note"]})
    if not rows:
        st.info("No actions match these filters.")
        return
    df = pd.DataFrame(rows)
    ver = st.session_state.get(f"{rkey}_regver", 0)
    st.caption("✏️ Edit **Owner, Target date, Status, % complete** and **Update / evidence** directly in the table, then press *Save changes*. "
               "Use the finding cards for wording changes, adding or removing actions.")
    edited = st.data_editor(
        df, hide_index=True, key=f"{rkey}_reg_{ver}", num_rows="fixed", height=min(760, 60 + 36 * len(df)),
        disabled=["ID", "Ref", "Finding", "Action", "Days overdue"],
        column_config={
            "ID": None,
            "Ref": st.column_config.TextColumn(width="small"),
            "Finding": st.column_config.TextColumn(width="medium"),
            "Action": st.column_config.TextColumn(width="large"),
            "Owner": st.column_config.TextColumn(width="medium"),
            "Target date": st.column_config.DateColumn(format="DD MMM YYYY", width="small"),
            "Status": st.column_config.SelectboxColumn(options=core.STATUSES, required=True, width="medium"),
            "% complete": st.column_config.NumberColumn(min_value=0, max_value=100, step=5, width="small"),
            "Days overdue": st.column_config.NumberColumn(width="small"),
            "Update / evidence": st.column_config.TextColumn(width="large"),
        }, **S_ED)
    if st.button("💾 Save changes", type="primary", key=f"{rkey}_regsave"):
        n = _apply_register_edits(df, edited, _user())
        st.session_state[f"{rkey}_regver"] = ver + 1
        _toast(f"Saved {n} action update(s)" if n else "No changes to save")
        st.rerun()


def _apply_register_edits(df, edited, who=""):
    """Compare the edited register with the original rows and save every action that changed. Returns how many."""
    def d_iso(v):
        return "" if pd.isna(v) else pd.to_datetime(v).date().isoformat()
    n = 0
    for i in df.index:
        o, e = df.loc[i], edited.loc[i]
        owner_new, owner_old = (e["Owner"] or "").strip() if isinstance(e["Owner"], str) else "", o["Owner"] or ""
        note_new = e["Update / evidence"] if isinstance(e["Update / evidence"], str) else ""
        if (owner_new == owner_old and d_iso(e["Target date"]) == d_iso(o["Target date"]) and e["Status"] == o["Status"]
                and int(e["% complete"]) == int(o["% complete"]) and note_new == (o["Update / evidence"] or "")):
            continue
        pct = int(e["% complete"]) if int(e["% complete"]) != int(o["% complete"]) else None
        if ia_db.save_action(int(o["ID"]), owner=owner_new, due_date=d_iso(e["Target date"]), status=e["Status"], pct=pct, note=note_new, who=who):
            n += 1
    return n


def _report_tab(rkey, M):
    rep = seed.REPORTS[rkey]
    fl = [f for f in M["findings"] if f["report"] == rkey]
    _report_card(rep, fl)
    t1, t2, t3, t4 = st.tabs(["📋 Findings & actions", "📊 Dashboard", "🎯 KPI scoreboard", "🗂️ Action register (editable table)"])
    with t1:
        _findings_view(rkey, fl)
    with t2:
        _dashboard(fl)
    with t3:
        _kpi_scoreboard(rkey, fl)
    with t4:
        _action_register(rkey, fl)


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
def render_page():
    ia_db.init()
    ia_db.seed_if_needed()
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    toast = st.session_state.pop("_ia_toast", None)
    if toast:
        st.toast(toast)
    M = build_model()
    _hero(M, ia_db.get_meta("fy_label", "FY 2024–2025"))
    _a, _b = st.columns([5, 2])
    _b.text_input("Your name", key="ia_user", placeholder="👤 Your name (saved in the activity log)", label_visibility="collapsed")
    reg, cen, exp, logt = st.tabs([seed.REPORTS["regional"]["tab"], seed.REPORTS["central"]["tab"], "💾 Export & Settings", "🕘 Activity log"])
    with reg:
        _report_tab("regional", M)
    with cen:
        _report_tab("central", M)
    with exp:
        _export_tab(M)
    with logt:
        _log_tab()
