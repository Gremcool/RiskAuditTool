"""ia_export.py - Excel export of the whole tracker (summary, per-report action registers, KPIs, history, comments)."""
import io
import json

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import ia_core as core
import ia_seed_data as seed

NAVY = "1E3C72"


def _style(ws, widths=None, wrap_cols=(), freeze="A2"):
    hdr_fill = PatternFill("solid", fgColor=NAVY)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = hdr_fill
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 28
    for i, col in enumerate(ws.columns, start=1):
        letter = get_column_letter(i)
        header = str(col[0].value or "")
        w = (widths or {}).get(header)
        if w is None:
            longest = max((len(str(c.value)) for c in col[:200] if c.value is not None), default=8)
            w = min(max(10, longest + 2), 60)
        ws.column_dimensions[letter].width = w
        if header in wrap_cols:
            for c in col[1:]:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        else:
            for c in col[1:]:
                c.alignment = Alignment(vertical="top")
    ws.freeze_panes = freeze
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions


def build_workbook(findings, actions, kpis, history_fn, comments_by_finding, fy_label=""):
    ref_today = core.today()
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        # ---- Summary -------------------------------------------------------------------------------
        rows = []
        for rkey, rep in seed.REPORTS.items():
            a = actions[actions["report"] == rkey]
            f = findings[findings["report"] == rkey]
            live = a[a["status"] != core.NA]
            overdue = sum(1 for _, r in a.iterrows() if core.action_state(r["status"], r["due_date"], ref_today) == "overdue")
            rows.append({
                "Report": rep["name"], "Issued": rep["issued"], "Audit period": rep["period"],
                "Overall rating": rep["rating"], "Findings": len(f), "High priority": int((f["priority"] == "High").sum()),
                "Actions": len(a), "Closed – verified": int((a["status"] == core.CL).sum()),
                "Implemented – pending verification": int((a["status"] == core.IPV).sum()),
                "In progress": int((a["status"] == core.IP).sum()), "Not started": int((a["status"] == core.NS).sum()),
                "Disputed": int((a["status"] == core.DI).sum()), "Overdue": overdue,
                "Actions without target date": int(((live["due_date"] == "") & (~live["status"].isin(core.DONE_STATUSES))).sum()),
                "Average % complete": round(live["pct"].mean(), 1) if len(live) else 0,
            })
        pd.DataFrame(rows).to_excel(xw, sheet_name="Summary", index=False)
        ws = xw.sheets["Summary"]
        _style(ws, wrap_cols=("Audit period", "Report", "Overall rating"))
        ws.cell(row=len(rows) + 3, column=1, value=f"{fy_label} · exported {ref_today.strftime('%d %b %Y')}")

        # ---- Per-report action registers -----------------------------------------------------------
        for rkey, rep in seed.REPORTS.items():
            a = actions[actions["report"] == rkey].copy()
            recs = []
            for _, r in a.iterrows():
                dl = core.days_left(r["due_date"], ref_today)
                recs.append({
                    "Ref": f"{r['ref']}.{int(r['seq'])}", "Finding": r["finding_title"], "Area": r["area"], "Priority": r["priority"],
                    "Recommended action": core.plain(r["text"]), "Owner": r["owner"], "Owner confirmed": "Yes" if r["owner_confirmed"] else "Proposed",
                    "Target date": core.fmt_date(r["due_date"], ""), "Status": r["status"], "% complete": r["pct"],
                    "Days overdue": (-dl if (dl is not None and dl < 0 and r["status"] in core.OPEN_STATUSES) else ""),
                    "Closed on": core.fmt_date(r["closed_date"], ""), "Update / evidence": core.plain(r["note"]), "Last updated": r["updated_at"],
                })
            name = f"{'Regional' if rkey == 'regional' else 'Central'} actions"
            pd.DataFrame(recs).to_excel(xw, sheet_name=name, index=False)
            _style(xw.sheets[name], widths={"Finding": 40, "Recommended action": 70, "Update / evidence": 45, "Owner": 30},
                   wrap_cols=("Finding", "Recommended action", "Update / evidence", "Owner", "Area"), freeze="C2")

        # ---- Findings --------------------------------------------------------------------------------
        fr = findings.copy()
        fr["Report"] = fr["report"].map(lambda x: seed.REPORTS[x]["name"])
        fr = fr[["Report", "ref", "src_ref", "area", "title", "priority", "mgmt_position", "flagged_label", "timeline",
                 "observation", "criteria", "risk", "mgmt_comment", "notes"]]
        for _c in ("title", "observation", "criteria", "risk", "mgmt_comment", "notes"):
            fr[_c] = fr[_c].map(core.plain)
        fr.columns = ["Report", "Ref", "Report ref", "Area", "Finding", "Priority", "Management position", "Value flagged",
                      "Management timeline", "Observation", "Criteria", "Risk", "Management comment", "Notes"]
        fr.to_excel(xw, sheet_name="Findings", index=False)
        _style(xw.sheets["Findings"], widths={"Finding": 45, "Observation": 70, "Criteria": 40, "Risk": 55, "Management comment": 60, "Value flagged": 32},
               wrap_cols=("Finding", "Observation", "Criteria", "Risk", "Management comment", "Notes", "Value flagged", "Area"), freeze="C2")

        # ---- KPIs ------------------------------------------------------------------------------------
        kr = []
        for k in kpis:
            pct = core.kpi_pct(k["baseline"], k["current"], k["target"])
            bd = "; ".join(f"{b['label']}: {core.fmt_value(b['baseline'], k['unit'], True)} → {core.fmt_value(b['current'], k['unit'], True)}"
                           for b in (k["breakdown"] or []))
            kr.append({"Report": seed.REPORTS[k["report"]]["name"], "Ref": k["ref"], "Finding": k["finding_title"], "KPI": k["name"],
                       "Unit": k["unit"], "Baseline": k["baseline"], "Current": k["current"], "Target": k["target"],
                       "Progress %": pct if pct is not None else "", "Trend": core.TREND_LABEL[core.kpi_trend(k["baseline"], k["current"], k["target"])][0],
                       "As of": core.fmt_date(k["as_of"], ""), "Target basis": k["basis"], "Breakdown (baseline → current)": bd, "Note": k["note"]})
        pd.DataFrame(kr).to_excel(xw, sheet_name="KPIs", index=False)
        _style(xw.sheets["KPIs"], widths={"Finding": 40, "KPI": 45, "Breakdown (baseline → current)": 70, "Target basis": 35, "Note": 40},
               wrap_cols=("Finding", "KPI", "Breakdown (baseline → current)", "Target basis", "Note"), freeze="E2")
        ws = xw.sheets["KPIs"]
        for col in ("F", "G", "H"):
            for c in ws[col][1:]:
                c.number_format = "#,##0.00"

        # ---- KPI history ---------------------------------------------------------------------------
        hr = []
        for k in kpis:
            for h in history_fn(k["id"]):
                hr.append({"Ref": k["ref"], "KPI": k["name"], "Unit": k["unit"], "As of": h["as_of"], "Value": h["value"],
                           "Note": h["note"], "Recorded by": h["author"], "Recorded at": h["created_at"]})
        pd.DataFrame(hr).to_excel(xw, sheet_name="KPI history", index=False)
        _style(xw.sheets["KPI history"], widths={"KPI": 50, "Note": 40})

        # ---- Comments ------------------------------------------------------------------------------
        cr = []
        for _, f in findings.iterrows():
            for author, body, ts in comments_by_finding.get(int(f["id"]), []):
                cr.append({"Ref": f["ref"], "Finding": f["title"], "Author": author, "Comment": body, "Posted": ts})
        pd.DataFrame(cr, columns=["Ref", "Finding", "Author", "Comment", "Posted"]).to_excel(xw, sheet_name="Comments", index=False)
        _style(xw.sheets["Comments"], widths={"Finding": 45, "Comment": 80}, wrap_cols=("Finding", "Comment"))
    out.seek(0)
    return out.getvalue()
