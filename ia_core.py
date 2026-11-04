"""
ia_core.py - pure helpers (no database, no Streamlit): statuses, dates, KPI maths, number formatting.
"""
from datetime import date, datetime, timedelta, timezone

KIGALI = timezone(timedelta(hours=2))  # Rwanda: UTC+2, no daylight saving

# ---------------------------------------------------------------------------------------------
# Action statuses
# ---------------------------------------------------------------------------------------------
NS = "Not Started"
IP = "In Progress"
IPV = "Implemented – Pending Verification"
CL = "Closed – Verified"
DI = "Disputed"
NA = "Not Applicable"
STATUSES = [NS, IP, IPV, CL, DI, NA]
OPEN_STATUSES = (NS, IP)          # these can become overdue
DONE_STATUSES = (CL, NA)

# state slug -> (label, colour, soft background)
STATE = {
    "closed":   ("Closed – verified",          "#15803d", "#dcfce7"),
    "verify":   ("Awaiting IA verification",   "#6d28d9", "#ede9fe"),
    "progress": ("In progress",                "#ca8a04", "#fef3c7"),
    "pending":  ("Not started",                "#475569", "#e2e8f0"),
    "overdue":  ("Overdue",                    "#b91c1c", "#fee2e2"),
    "disputed": ("Disputed",                   "#c2410c", "#ffedd5"),
    "na":       ("Not applicable",             "#94a3b8", "#f1f5f9"),
}
STATUS_TO_STATE = {NS: "pending", IP: "progress", IPV: "verify", CL: "closed", DI: "disputed", NA: "na"}

PRIORITIES = ["High", "Medium", "Low"]
MGMT_POSITIONS = ["Agreed", "Partially agreed", "Disagreed", "Reported as implemented", "No response"]
UNITS = ["Rwf", "%", "count", "units", "days", "flag"]


def today():
    return datetime.now(KIGALI).date()


def parse_date(s):
    if s is None or s == "":
        return None
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def iso(d):
    d = parse_date(d)
    return d.isoformat() if d else ""


def fmt_date(d, empty="—"):
    d = parse_date(d)
    return d.strftime("%d %b %Y") if d else empty


def days_left(due, ref=None):
    d = parse_date(due)
    return None if d is None else (d - (ref or today())).days


def action_state(status, due, ref=None):
    """Slug used for colours. 'overdue' only applies to actions that are not yet implemented."""
    if status in OPEN_STATUSES:
        dl = days_left(due, ref)
        if dl is not None and dl < 0:
            return "overdue"
    return STATUS_TO_STATE.get(status, "pending")


def normalise_pct(status, pct):
    """Keep the % complete consistent with the status."""
    try:
        pct = int(pct or 0)
    except (TypeError, ValueError):
        pct = 0
    pct = max(0, min(100, pct))
    if status == NS:
        return 0
    if status == IP:
        return max(1, min(89, pct)) if pct else 25
    if status == IPV:
        return max(90, min(99, pct)) if pct else 90
    if status == CL:
        return 100
    return pct


def finding_state(actions):
    """Roll the actions of one finding up to one state slug.  `actions` = list of dicts with status/due_date."""
    live = [a for a in actions if a["status"] != NA]
    if not live:
        return "na"
    states = [action_state(a["status"], a["due_date"]) for a in live]
    if all(s == "closed" for s in states):
        return "closed"
    if "overdue" in states:
        return "overdue"
    if "disputed" in states:
        return "disputed"
    if all(s in ("closed", "verify") for s in states):
        return "verify"
    if any(s in ("closed", "verify", "progress") for s in states):
        return "progress"
    return "pending"


def finding_pct(actions):
    live = [a for a in actions if a["status"] != NA]
    return round(sum(a["pct"] for a in live) / len(live)) if live else 0


# ---------------------------------------------------------------------------------------------
# KPI maths
# ---------------------------------------------------------------------------------------------
def aggregate(values, how="sum"):
    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 4) if how == "mean" else round(sum(vals), 2)


def kpi_progress(baseline, current, target):
    """Raw progress from baseline towards target (1.0 = target reached, <0 = worse than baseline).
    Works for 'lower is better' and 'higher is better' alike. None when no target / nothing to measure."""
    if target is None or baseline is None or current is None:
        return None
    span = float(target) - float(baseline)
    if abs(span) < 1e-9:
        return 1.0 if abs(float(current) - float(target)) < 1e-9 else None
    return (float(current) - float(baseline)) / span


def kpi_pct(baseline, current, target):
    raw = kpi_progress(baseline, current, target)
    return None if raw is None else int(round(max(0.0, min(1.0, raw)) * 100))


def kpi_trend(baseline, current, target):
    raw = kpi_progress(baseline, current, target)
    if raw is None:
        if target is None and baseline is not None and current is not None:
            if abs(float(current) - float(baseline)) < 1e-9:
                return "unchanged"
            return "changed"
        return "unchanged"
    if raw >= 0.999:
        return "achieved"
    if raw > 0.0005:
        return "improving"
    if raw < -0.0005:
        return "worse"
    return "unchanged"


TREND_LABEL = {"achieved": ("🎯 Target met", "#15803d"), "improving": ("▲ Improving", "#15803d"),
               "unchanged": ("● No change", "#64748b"), "worse": ("▼ Worse than baseline", "#b91c1c"),
               "changed": ("↕ Changed (no target set)", "#475569")}


# ---------------------------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------------------------
def _trim(x, nd):
    s = f"{x:.{nd}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def fmt_value(v, unit, full=False):
    if v is None or v == "":
        return "—"
    v = float(v)
    if unit == "flag":
        return "Done" if v >= 1 else "Not yet"
    if unit == "%":
        return _trim(v, 2) + "%"
    if unit == "days":
        return f"{v:,.0f} day" + ("" if abs(v) == 1 else "s")
    if unit in ("count", "units"):
        return f"{v:,.0f}"
    if unit in ("Rwf", "Frw"):
        sign = "−" if v < 0 else ""
        a = abs(v)
        if full:
            return f"{sign}Rwf {a:,.0f}"
        if a >= 1_000_000_000:
            return f"{sign}Rwf {_trim(a / 1e9, 2)}B"
        if a >= 1_000_000:
            return f"{sign}Rwf {_trim(a / 1e6, 1)}M"
        if a >= 1_000:
            return f"{sign}Rwf {_trim(a / 1e3, 1)}K"
        return f"{sign}Rwf {a:,.0f}"
    return _trim(v, 2)


def fmt_frw(v):
    return fmt_value(v, "Rwf")
