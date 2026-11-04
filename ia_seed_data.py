"""
ia_seed_data.py
---------------
Baseline data for the RMS Internal Audit Action Tracker, extracted from the two internal audit reports:

  * Q3 - Internal Audit Report on Eight (8) RMS Regional Warehouses   (March 2026)
  * Q4 - Internal Audit Report on Central Warehouse Operations         (July 2026)

Everything here is loaded ONCE, on first run (see ia_db.seed_if_needed). After that the database is the
source of truth, so editing this file never overwrites updates people have made in the tracker.

Conventions
-----------
* Action status / % complete and owners are STARTING POINTS taken from the "Management comment" sections of
  the reports. Owners are *proposed* (the reports name units, not people) and show a "proposed" tag until
  someone confirms them in the tracker.
* KPI "baseline" is the figure the auditors reported. "current" starts equal to the baseline (nothing is
  assumed to be fixed until Internal Audit verifies it) except where the report itself shows later data.
* KPI "target" is None when the report gives no target - management/Internal Audit should then set one.
"""

WH = ["Rubavu", "Kayonza", "Nyagatare", "Gakenke", "Musanze", "Nyaruguru", "Huye", "Gisagara"]

REPORTS = {
    "regional": {
        "key": "regional",
        "prefix": "R",
        "tab": "🗺️ Regional Warehouses · Q3",
        "name": "Regional Warehouses Audit Report",
        "title": "Internal Audit Report on Eight (8) RMS Regional Warehouses",
        "scope": "Rubavu, Kayonza, Nyagatare, Gakenke, Musanze, Nyaruguru, Huye, Gisagara",
        "period": "1 July 2025 – 31 December 2025 (field visits Jan–Mar 2026)",
        "issued": "March 2026",
        "baseline_date": "2026-03-31",
        "rating": "Some improvement opportunity",
        "rating_level": 3,   # 1 unacceptable · 2 major improvement · 3 some improvement · 4 satisfactory · 5 well managed
        "conclusion": ("Internal controls designed and implemented across the eight regional warehouses are "
                       "not fully adequate; improvements are required to strengthen risk management."),
        "signed": "Faustin Karangwa, Ag. Director of Audit, Risk and Compliance",
        "file": "Q3-REPORT ON REGIONAL WAREHOUSES OPERATIONS.pdf",
        "notes": ("The report's contents page lists 34 findings but the body contains 23; findings are numbered "
                  "R01–R23 here in the order they appear, and the report's own number is kept in 'Report ref'."),
    },
    "central": {
        "key": "central",
        "prefix": "C",
        "tab": "🏭 Central Warehouse · Q4",
        "name": "Central Warehouse Audit Report",
        "title": "Internal Audit Report on Central Warehouse Operations",
        "scope": "RMS Central Warehouse – inventory management, sales and distribution",
        "period": "1 July 2025 – 31 March 2026 (selected items to 30 June 2026)",
        "issued": "July 2026",
        "baseline_date": "2026-07-17",
        "rating": "Not stated in report",
        "rating_level": 0,
        "conclusion": "The report does not include an overall rating or opinion paragraph.",
        "signed": "",
        "file": "Q4 CENTRAL WAREHOUSE AUDIT REPORT.pdf",
        "notes": "",
    },
}

# --- default % complete for each status when the seed does not give one --------------------------
_PCT = {"Not Started": 0, "In Progress": 50, "Implemented – Pending Verification": 90,
        "Closed – Verified": 100, "Disputed": 0, "Not Applicable": 0}
NS, IP, IPV, CL, DI = "Not Started", "In Progress", "Implemented – Pending Verification", "Closed – Verified", "Disputed"


def A(text, owner, status=NS, due=None, pct=None, note=""):
    return {"text": text, "owner": owner, "status": status, "due": due,
            "pct": _PCT[status] if pct is None else pct, "note": note}


def K(name, unit, baseline=None, target=None, breakdown=None, agg="sum", current=None,
      basis="", note="", series=None):
    """unit: Rwf | % | count | days | units | flag.  breakdown: [(label, baseline_value), ...]"""
    bd = None
    if breakdown:
        bd = [{"label": l, "baseline": v, "current": v} for l, v in breakdown]
        vals = [b["baseline"] for b in bd]
        baseline = round(sum(vals) / len(vals), 4) if agg == "mean" else round(sum(vals), 2)
    if unit == "flag":
        baseline, target = 0, 1
    return {"name": name, "unit": unit, "baseline": baseline, "target": target, "breakdown": bd,
            "agg": agg, "current": baseline if current is None else current, "basis": basis,
            "note": note, "series": series or []}


# Owner names (units named in the reports - proposed, to be confirmed)
SAP = "SAP / Strategic Information (DSI)"
QA = "QA & QC"
FIN = "Finance"
REC = "Finance – Recovery"
SALES = "Sales, Marketing & Distribution"
QDV = "Quantification & Data Visibility"
LOG = "Logistics & Asset Management"
PROC = "Procurement"
WHI = "Warehouse & Inventory Management"
BM = "Regional Branch Managers"
EXEC = "Executive Management"

ZERO = "Implied target: no exceptions remaining"

# ======================================================================================================
#  REGIONAL WAREHOUSES (Q3)  ·  23 findings
# ======================================================================================================
REGIONAL = [
    dict(src_ref="Finding 1", area="Inventory Management", priority="High",
         title="Lack of automatic status update for expired items in SAP",
         observation=("Expired items do not move automatically from 'Unrestricted' to 'Blocked' in SAP; a designated "
                      "staff member does it manually. Counts in Jan–Mar 2026 found expired stock worth Rwf 329.1M "
                      "across 7 warehouses affected by the manual process (narrative says Rwf 328.8M, table total "
                      "Rwf 329.1M)."),
         criteria="Product-safety and regulatory standards; SAP stock-status control",
         risk=("Manual monitoring invites oversight and error; expired items could remain issuable, creating "
               "product-safety and regulatory non-compliance."),
         mgmt_position="Reported as implemented",
         mgmt_comment=("DSI created location 9900 (owned by QC/QA) for unfit items. Other unfit products (damaged, "
                       "recalled) are still moved to blocked status manually before transfer."),
         timeline="Reported as already addressed",
         flagged_value=329110874, flagged_label="Rwf 329.1M expired stock exposed",
         actions=[
             A("Configure SAP to change item status automatically from 'Unrestricted' to 'Blocked' at expiry date.",
               SAP, IPV, note="Management cites an alternative control (location 9900) – IA to confirm it meets the recommendation."),
             A("Set up automatic notifications / dashboards in SAP for items approaching expiry.", SAP),
             A("Until automation exists, introduce an independent review of the manual blocking process.", QA),
         ],
         kpis=[
             K("Expired stock exposed by manual blocking", "Rwf", target=0, basis=ZERO,
               breakdown=[("Rubavu", 71721049), ("Kayonza", 4371640.6), ("Nyagatare", 55655073),
                          ("Gakenke", 19717365), ("Nyaruguru", 719334), ("Huye", 176592887), ("Gisagara", 333525)]),
             K("SAP auto-blocking of expired items configured", "flag", basis="Recommendation 1"),
         ]),

    dict(src_ref="Finding 2", area="Inventory Management", priority="Low",
         title="Weak SAP controls over stock held in Quality Inspection status",
         observation=("SAP does not move stock from 'Quality Inspection' to 'Unrestricted' when inspection ends; it "
                      "needs manual intervention. Rwf 6.4M sat in QI status at four warehouses (Jul 2025 – Feb 2026)."),
         criteria="Quality inspection process; SAP stock status",
         risk="Inaccurate inventory records and misstated stock balances.",
         mgmt_position="Agreed",
         mgmt_comment=("Corrected, but some items needed a consultant and were still unfixed during the audit. Branch "
                       "managers committed to timely updates and escalation."),
         timeline="Immediate action",
         flagged_value=6375083, flagged_label="Rwf 6.4M in QI status",
         actions=[A("Strengthen controls so QI status is updated promptly and accurately once inspection is complete "
                    "(including the SAP fix for items that needed a consultant).", f"{QA}; {SAP}", IP, pct=50)],
         kpis=[K("Stock stuck in Quality Inspection status", "Rwf", target=0, basis=ZERO,
                 breakdown=[("Nyagatare", 2746873.62), ("Gakenke", 904000), ("Nyaruguru", 606609), ("Huye", 2117600)])]),

    dict(src_ref="Finding 3", area="Inventory Management", priority="High",
         title="Inventory accuracy outside the approved tolerance",
         observation=("At end-Dec 2025 five warehouses were below the ≥99.5% accuracy required by SOP 4.09.01 "
                      "(variance tolerance 0.5%). Total variance Rwf 84.8M on Rwf 3.35B inventory (2.72%). "
                      "Rubavu, Kayonza and Nyagatare are not in the report's table."),
         criteria="SOP 4.09.01 – accuracy ≥ 99.5% (variance ≤ 0.5%)",
         risk="Accuracy below tolerance indicates poor performance in inventory valuation.",
         mgmt_position="Agreed",
         mgmt_comment=("Strengthening cycle counts, follow-up recounts with the variance committee, closer supervision "
                       "of reconciliations and SOP adherence."),
         timeline="End May 2026",
         flagged_value=84828775, flagged_label="Rwf 84.8M variance · 5 warehouses below tolerance",
         actions=[
             A("Investigate, analyse and reconcile variances to reach the acceptable accuracy threshold.", BM, IP, "2026-05-31"),
             A("Huye: minimise system, picking and checking errors to reach the tolerance level.", "Huye Branch Manager", IP, "2026-05-31"),
         ],
         kpis=[
             K("Inventory accuracy (average of warehouses reported)", "%", target=99.5, agg="mean",
               basis="SOP 4.09.01: ≥ 99.5%",
               breakdown=[("Gakenke", 95.76), ("Musanze", 97.10), ("Nyaruguru", 96.46), ("Huye", 97.73), ("Gisagara", 99.35)]),
             K("Inventory variance value", "Rwf", target=0, basis="SOP 4.09.01: variance ≤ 0.5% of inventory",
               breakdown=[("Gakenke", 18781101), ("Musanze", 18609244), ("Nyaruguru", 14936028.7),
                          ("Huye", 28630971), ("Gisagara", 3871431)]),
         ]),

    dict(src_ref="Finding 4", area="Inventory Management", priority="High",
         title="Unresolved variances between SAP quantity and stock-count quantity",
         observation=("Variances found in the June and December 2025 counts were still unexplained at audit (Mar 2026): "
                      "Rwf 198.7M, of which Musanze's June 2025 count accounts for Rwf 131.6M."),
         criteria="SOP 4.2.13 – variances must be investigated before the next stock take",
         risk=("Errors in stock management are hard to prevent or detect; unreconciled variances can mislead users "
               "of the financial statements."),
         mgmt_position="Agreed",
         mgmt_comment="Same response as Finding 3 – cycle counts, recounts with the variance committee, supervision and SOP adherence.",
         timeline="31 May 2026",
         flagged_value=198697635, flagged_label="Rwf 198.7M unexplained variance",
         actions=[
             A("Investigate the causes of the count variances and take corrective action so every item is accounted for.", f"{BM}; {WHI}", IP, "2026-05-31"),
             A("Update SAP stock balances to remove the variances.", SAP, IP, "2026-05-31"),
         ],
         kpis=[K("Uninvestigated count variance", "Rwf", target=0, basis=ZERO,
                 breakdown=[("Gakenke", 18781101), ("Musanze", 132478010), ("Nyaruguru", 14936122),
                            ("Huye", 28630971), ("Gisagara", 3871431)])]),

    dict(src_ref="Finding 5", area="Inventory Management", priority="High",
         title="Unsupported stock adjustments in SAP",
         observation=("Between Jul 2025 and Mar 2026 the warehouses posted negative adjustments of Rwf 953.2M and positive "
                      "adjustments of Rwf 583.0M with no supporting documents. Rubavu (−391.4M) and Huye (+305.3M) are largest."),
         criteria="SOP 4.2.21 – Goods and stock valuation",
         risk="Completeness and accuracy of reported inventory cannot be confirmed; warehouse reports may be materially misstated.",
         mgmt_position="Agreed",
         mgmt_comment=("A committee was set up to investigate variances and guide stock alignment. Many end-June 2025 "
                       "alignments are complete; the remainder will be done after the release."),
         timeline="End May 2026",
         flagged_value=953177030, flagged_label="Rwf 953.2M negative / 583.0M positive",
         actions=[
             A("Ensure sufficient, relevant supporting documents exist for every SAP adjustment.", f"{FIN}; {WHI}", IP, "2026-05-31"),
             A("Retrieve the documentation behind the unsupported adjustments for future reference.", BM, IP, "2026-05-31"),
         ],
         kpis=[
             K("Unsupported negative adjustments", "Rwf", target=0, basis=ZERO,
               breakdown=[("Rubavu", 391365054), ("Kayonza", 93506059), ("Nyagatare", 11194401), ("Gakenke", 110573668),
                          ("Musanze", 45240389), ("Nyaruguru", 102430913), ("Huye", 183437852), ("Gisagara", 15428695)]),
             K("Unsupported positive adjustments", "Rwf", target=0, basis=ZERO,
               breakdown=[("Rubavu", 83885752.52), ("Kayonza", 4572992.11), ("Nyagatare", 2007180), ("Gakenke", 108343700),
                          ("Musanze", 11016669), ("Nyaruguru", 61360156), ("Huye", 305331406), ("Gisagara", 6475943)]),
         ]),

    dict(src_ref="Finding 6", area="Inventory Management", priority="Medium",
         title="Idle medical equipment not delivered or used",
         observation=("Two centrifuges (Rwf 31.4M) returned by Kabere and Nyange Health Centers for missing rotors sat as "
                      "non-moving stock at Musanze; at Huye an examination couch (Rwf 1.2M) was not delivered to a Health Post."),
         criteria="Pre-distribution inspection; value for money",
         risk="Idle or deteriorating assets, wastage of public resources, and service-delivery gaps in laboratory diagnostics.",
         mgmt_position="Agreed",
         mgmt_comment=("Musanze started reverse logistics and told the SD&D directorate by email; Huye items are no "
                       "longer in use by the client and donation was recommended."),
         timeline="End April 2026",
         flagged_value=32560359, flagged_label="Rwf 32.6M idle equipment",
         actions=[
             A("Engage the supplier or HQ to supply the missing components, or start replacement.", SALES, IP, "2026-04-30"),
             A("Agree an action plan with deadlines for repair, redistribution or disposal.", f"{LOG}; {SALES}", IP, "2026-04-30"),
             A("Strengthen pre-distribution inspection so equipment is complete before dispatch.", WHI, due="2026-04-30"),
         ],
         kpis=[K("Idle medical equipment value", "Rwf", target=0, basis=ZERO,
                 breakdown=[("Musanze", 31388858.6), ("Huye", 1171500)])]),

    dict(src_ref="Finding 9 (first)", area="Inventory Management", priority="High",
         title="High proportion of expired medical products",
         observation=("Strategic Plan 2024–26 targets expiries of 0.42% by June 2026. In three sampled warehouses expiries "
                      "ran at 0.57%–4.77% (Rwf 212.4M over Jul 2025 – Feb 2026). SAP blocked-expiry values also differed "
                      "from disposal reports by Rwf 32.6M."),
         criteria="Strategic Plan 2024–2026: expiry proportion ≤ 0.42% by June 2026",
         risk="Loss to RMS and failure to meet expected consumption of medical products; inaccurate records hinder tracking of expiries.",
         mgmt_position="Agreed",
         mgmt_comment=("Strengthen branch managers' accountability for monitoring items nearing expiry and improve demand "
                       "forecasting. NOTE: the comment is cut off mid-sentence in the report."),
         timeline="Not stated – management comment is truncated in the report",
         flagged_value=212408144, flagged_label="Rwf 212.4M expired · 0.57%–4.77% vs 0.42% target",
         actions=[
             A("Improve stock-management controls to reduce or avoid expiries.", f"{BM}; {QDV}",
               note="Obtain the full management comment and a timeline – both are missing from the report."),
             A("Run regular stock counts and periodic reviews of expiry reports; record all movements in SAP.", WHI),
         ],
         kpis=[
             K("Expired products as % of inventory held (3 warehouses)", "%", target=0.42, agg="mean",
               basis="Strategic Plan 2024–26: 0.42% by June 2026",
               breakdown=[("Gakenke", 0.57), ("Nyaruguru", 2.02), ("Huye", 4.77)]),
             K("Value of expired products", "Rwf", target=None, basis="Not set in report – derive from the 0.42% target",
               breakdown=[("Gakenke", 13923605), ("Nyaruguru", 18894609.57), ("Huye", 179589929)]),
             K("Unexplained gap: SAP blocked expiries vs disposal reports", "Rwf", target=0, basis=ZERO,
               breakdown=[("Rubavu", 20208494), ("Kayonza", 2083988), ("Nyagatare", 1555247), ("Gakenke", 5793760), ("Huye", 2997042)]),
         ]),

    dict(src_ref="Finding 9 (second)", area="Inventory Management", priority="Medium",
         title="Unexplained differences in stock movements and delivery values",
         observation=("Physical count differed from SAP by Rwf 15.1M (Nyaruguru Rwf 10.6M), and goods received from Mediasol "
                      "and Bufmar showed a Rwf 25.2M difference between delivery-note and SAP values (Huye Rwf 16.2M)."),
         criteria="Regular reconciliation of physical quantities to SAP; FEFO and batch picking",
         risk="Completeness of the inventory balance cannot be confirmed; weakened controls over goods receipt and recording.",
         mgmt_position="Agreed",
         mgmt_comment=("Items were not always picked by batch and SAP did not allow batch splitting/FEFO. Spot-checks now "
                       "run; SAP training given; Huye's case referred to the Strategic Information directorate."),
         timeline="Immediate",
         flagged_value=40247451, flagged_label="Rwf 15.1M count diff · Rwf 25.2M delivery-note diff",
         actions=[
             A("Investigate the physical-vs-SAP difference, take corrective action and reconcile regularly.", BM, IP),
             A("Investigate and reconcile the delivery-note vs SAP variance.", f"{BM}; {SAP}", IP),
         ],
         kpis=[
             K("Unexplained physical vs SAP difference", "Rwf", target=0, basis=ZERO,
               breakdown=[("Rubavu", 53718), ("Nyagatare", 1138191), ("Gakenke", 1663205), ("Musanze", 836448),
                          ("Nyaruguru", 10598521), ("Huye", 796904)]),
             K("Delivery-note vs SAP value variance", "Rwf", target=0, basis=ZERO,
               breakdown=[("Nyagatare", 1241865), ("Gakenke", 5269690), ("Nyaruguru", 886400), ("Huye", 16170700), ("Gisagara", 1591809)]),
         ]),

    dict(src_ref="Finding 10", area="Inventory Management", priority="Medium",
         title="Items physically present but missing from SAP",
         observation="Medical items worth Rwf 19.1M were found in warehouses but were not recorded in SAP (see Annex one of the report).",
         criteria="Inventory records must reflect physical stock",
         risk="Unrecorded items cannot be monitored or traced and may lead to overstock.",
         mgmt_position="Agreed",
         mgmt_comment="Same as the previous finding – spot-check strategies in place, FEFO/batch issuing being enforced.",
         timeline="Immediately",
         flagged_value=19080489, flagged_label="Rwf 19.1M not in SAP",
         actions=[A("Update SAP to include all missing items and reconcile physical balances with system records.", f"{SAP}; {BM}", IP)],
         kpis=[K("Value of items missing from SAP", "Rwf", 19080489, 0, basis=ZERO)]),

    dict(src_ref="Finding 11", area="Inventory Management", priority="High",
         title="Recurrent stock-outs of medical products",
         observation=("At Jan–Mar 2026 audits, 129 products were out of stock (95 RMS-scope, 17 Mediasol, 17 Bufmar) for "
                      "between 1 and 398 days."),
         criteria="RMS mandate – availability of quality, affordable medical products",
         risk="RMS may fail its mandate to ensure availability of pharmaceutical products, equipment and consumables.",
         mgmt_position="Agreed",
         mgmt_comment=("Causes: partner funding, non-moving items with alternatives, supplier low fill rate. Some vertical-"
                       "programme products moved into RMS scope (magnesium sulfate, Hemocue microcuvette); redistribution reinforced."),
         timeline="Immediate",
         flagged_value=None, flagged_label="129 products stocked out (1–398 days)",
         actions=[A("With partners, procure the quantities needed to raise the order fill rate and reduce stock-outs.",
                    f"{PROC}; {QDV}", IP)],
         kpis=[
             K("Products out of stock", "count", target=0, basis=ZERO,
               breakdown=[("Rubavu", 22), ("Kayonza", 9), ("Nyagatare", 23), ("Gakenke", 18), ("Musanze", 13),
                          ("Nyaruguru", 11), ("Huye", 17), ("Gisagara", 16)]),
             K("Longest stock-out", "days", 398, None, basis="Not set in report – management to define"),
         ]),

    dict(src_ref="Finding 12", area="Sales & Receivables", priority="High",
         title="Manual sales invoices issued outside SAP (Huye – CHUB)",
         observation=("Despite the CEO's 7 Mar 2025 ban on manual transactions, Huye invoiced CHUB Rwf 217.5M outside SAP "
                      "after unit-price adjustments; the manual invoices exceed the SAP equivalents by Rwf 163.3M. A Rwf 699 "
                      "unit-price variance against purchase orders was also noted."),
         criteria="CEO letter Ref 1102/RMS/CEO/2025 – immediate cessation of manual transactions",
         risk="Sales and receivables may be over/understated; SAP sales reports can mislead; accuracy cannot be confirmed.",
         mgmt_position="Agreed",
         mgmt_comment=("CHUB orders against earlier quotations whose prices have since changed and SAP cannot edit prices after "
                       "order processing, so Excel adjustments were used. All affected invoices reconciled and documented; "
                       "SAP enhancement to hold quotation prices being explored."),
         timeline="End May 2026",
         flagged_value=217476556, flagged_label="Rwf 217.5M manual invoices · Rwf 163.3M variance",
         actions=[
             A("Ensure all customers (incl. CHUB) can order, be served and be invoiced through SAP.", f"{SALES}; {SAP}", IP, "2026-05-31"),
             A("Investigate differences; adjust and reconcile sales and receivables; run regular SAP reconciliations.", FIN, IPV, "2026-05-31",
               note="Management states all affected invoices were reconciled – IA to verify."),
         ],
         kpis=[
             K("Sales invoiced outside SAP", "Rwf", 217476556, 0, basis=ZERO),
             K("Variance: manual invoices vs SAP invoices", "Rwf", 163260344, 0, basis=ZERO),
         ]),

    dict(src_ref="Finding 13", area="Sales & Receivables", priority="High",
         title="Delay in submitting sales invoices to customers",
         observation=("Huye invoices to CHUB (Rwf 293.2M) were transmitted 28–208 days after delivery. Cobas products "
                      "delivered to Gahini (Kayonza) and Kabutare (Huye) hospitals were not invoiced for 119 and 42 days (Rwf 35.1M)."),
         criteria="SOP 4.2.12 – delivery notes and invoices distributed promptly through SAP",
         risk="Incomplete sales and receivables, cut-off breaches and slower debt recovery.",
         mgmt_position="Agreed",
         mgmt_comment=("CHUB delays came from partial deliveries (storage limits) and late purchase orders. The Cobas issue is "
                       "fixed – products are now delivered and invoiced immediately. Management asks for leadership support."),
         timeline="End May 2026",
         flagged_value=293249345, flagged_label="Rwf 293.2M invoiced 28–208 days late",
         actions=[
             A("Invoice every delivery promptly and send invoices to customers (CHUB delays of 28–208 days).", SALES, IP, "2026-05-31"),
             A("Cobas hospital deliveries to be invoiced at delivery (Kayonza–Gahini, Huye–Kabutare).", SALES, IPV, "2026-05-31",
               note="Management states the concern is fixed – IA to verify."),
         ],
         kpis=[
             K("Cobas deliveries not yet invoiced", "Rwf", target=0, basis=ZERO,
               breakdown=[("Kayonza (Gahini)", 5740775), ("Huye (Kabutare)", 29392800)]),
             K("Longest delay from delivery to invoice", "days", 208, None, basis="Not set in report – SOP says 'promptly'"),
         ]),

    dict(src_ref="Finding 14", area="Sales & Receivables", priority="Medium",
         title="Gaps in the receivables ageing report (Huye)",
         observation=("Huye's ageing report at 31 Dec 2025 combined invoices, so unpaid invoices per customer and how long they "
                      "are overdue could not be identified (Rwf 40.3M across five CHUB lines)."),
         criteria="Receivables & Collections Policy – ageing report shows invoice date, reference and balance",
         risk="Inaccurate allowance for doubtful accounts; delinquent accounts can become uncollectible.",
         mgmt_position="Reported as implemented",
         mgmt_comment=("Rectified – a detailed, compliant ageing report was prepared and submitted. System-generated reports, "
                       "stronger review and regular reconciliations will prevent recurrence."),
         timeline="June 2026",
         flagged_value=40282480, flagged_label="Rwf 40.3M invoices combined",
         actions=[A("Enter all invoices individually (customer, date, amount) and categorise by age in the ageing report.", FIN, IPV, "2026-06-30",
                    note="Management states the corrected report was submitted – IA to verify.")],
         kpis=[K("Invoices combined in ageing report", "Rwf", 40282480, 0, basis=ZERO),
               K("Detailed system-generated ageing report used every period", "flag", basis="Management commitment")]),

    dict(src_ref="Finding 15", area="Sales & Receivables", priority="High",
         title="Unsupported receivables at 31 December 2025",
         observation=("No verifiable documents supported Rwf 741.9M of the Rwf 6.86B receivables (10.8%); many invoices were "
                      "not signed or stamped by the branch manager or received by customers. Nyaruguru, Huye and Nyagatare hold most."),
         criteria="Ministerial Order 001/16/10/TC (2016), Art. 103 – keep records and attachments ≥ 10 years",
         risk="Debtors may be unrecoverable and the receivable balance misstated; existence of debtors cannot be confirmed.",
         mgmt_position="Agreed",
         mgmt_comment=("Reconciliations with health facilities were ongoing; clients reject Zipline invoices. Special reconciliations "
                       "with Zipline and between regional warehouses and HQ are needed."),
         timeline="By 30 May 2026",
         flagged_value=741853723, flagged_label="Rwf 741.9M unsupported (10.8% of receivables)",
         actions=[
             A("Support every receivable entry with POs, invoices, signed delivery notes and proof of payment.", REC, IP, "2026-05-30"),
             A("Complete reconciliations with health facilities, Zipline and RMS HQ (per management comment).", REC, IP, "2026-05-30"),
         ],
         kpis=[K("Unsupported receivables", "Rwf", target=0, basis=ZERO,
                 breakdown=[("Rubavu", 48724538), ("Kayonza", 19821979), ("Nyagatare", 128285020), ("Gakenke", 42693263),
                            ("Nyaruguru", 242938811), ("Huye", 256687780), ("Gisagara", 2702332)])]),

    dict(src_ref="Finding 16", area="Sales & Receivables", priority="High",
         title="Unexplained differences between SAP receivables and customer reconciliations",
         observation=("At 31 Dec 2025 the SAP receivables balance exceeded signed health-centre reconciliations by Rwf 2.0B "
                      "(Huye Rwf 1.23B, Kayonza Rwf 0.61B) because reconciliations were not done regularly."),
         criteria="Regular accounts-receivable reconciliation",
         risk="Completeness and accuracy of receivables in the financial statements cannot be confirmed.",
         mgmt_position="Agreed",
         mgmt_comment=("Reconciliations were ongoing; ZDON invoices carried amounts instead of zero price; positive credit notes in "
                       "SAP; Zipline invoices. Special reconciliation with Zipline and with HQ is needed."),
         timeline="End May 2026",
         flagged_value=2002480902, flagged_label="Rwf 2.00B unreconciled",
         actions=[A("Investigate the differences, reconcile receivables, and reconcile regularly going forward.", REC, IP, "2026-05-31")],
         kpis=[K("Unreconciled receivables difference (SAP – customer; net)", "Rwf", target=0, basis=ZERO,
                 breakdown=[("Rubavu", 73553293), ("Kayonza", 611624731), ("Nyagatare", 7327165), ("Gakenke", 22073692),
                            ("Musanze", 61742420), ("Nyaruguru", 1026258), ("Huye", 1231175338), ("Gisagara", -6041995)])]),

    dict(src_ref="Finding 17", area="Sales & Receivables", priority="High",
         title="Overstatement of sales on zero-value CP programme invoices",
         observation=("Invoices with values were issued for CP programme products that should be zero-value, equal to Rwf 154.8M "
                      "over six months; no evidence of adjustment was provided. Musanze accounts for Rwf 81.8M."),
         criteria="SOP 4.12.2 §3.2 – one zero-value invoice for internal archiving",
         risk="Sales (and cost of sales) in the financial statements may be overstated.",
         mgmt_position="Agreed",
         mgmt_comment=("Caused by SAP configuration and automatic invoice-generation errors; escalated to Sales, Finance and IT. "
                       "System configuration being adjusted; reconciliation of sales and cost accounts ongoing."),
         timeline="End June 2026",
         flagged_value=154825015, flagged_label="Rwf 154.8M overstated",
         actions=[A("Investigate the overstated sales and cost-of-sales values and correct them (enforce zero-value invoicing in SAP).",
                    f"{FIN}; {SAP}", IP, "2026-06-30")],
         kpis=[K("Overstated sales on CP programme invoices", "Rwf", target=0, basis=ZERO,
                 breakdown=[("Rubavu", 17101328), ("Kayonza", 3617185), ("Nyagatare", 396960), ("Gakenke", 13061604),
                            ("Musanze", 81845193), ("Huye", 38802745)])]),

    dict(src_ref="Finding 18", area="Sales & Receivables", priority="High",
         title="No standing orders or recovery action on long-outstanding receivables",
         observation=("Receivables over 270 days (Rwf 1.01B across five warehouses, Nyagatare Rwf 458.5M) had no correspondence "
                      "and no standing orders. Opening receivables at 1 Jul 2025 also differed from 30 Jun 2025 closing balances "
                      "by a net Rwf 72.7M (Musanze Rwf −81.4M)."),
         criteria="Receivables & Collections Policy, Art. 6.0 – dunning letters, standing orders, legal escalation",
         risk="Higher debtor balances and weaker cash flow if recovery procedures are not applied.",
         mgmt_position="Agreed",
         mgmt_comment=("Will enforce standing orders and dunning letters, improve monitoring and coordination, and reconcile accurately. "
                       "Drivers: weak solvency of health facilities, Zipline-related receivables, timing differences."),
         timeline="Starting May 2026",
         flagged_value=1010646424, flagged_label="Rwf 1.01B > 270 days · Rwf 72.7M open/close diff",
         actions=[
             A("Put in place debt-recovery mechanisms – standing orders and dunning letters – for invoices unpaid > 270 days.", REC, NS, "2026-05-31"),
             A("Explain and resolve the differences between 30 Jun 2025 closing and 1 Jul 2025 opening receivables.", FIN, NS,
               note="Derived from the observation – the report gives no explicit recommendation for this point."),
         ],
         kpis=[
             K("Receivables outstanding > 270 days with no recovery action", "Rwf", target=0, basis=ZERO,
               breakdown=[("Kayonza", 48268291), ("Nyagatare", 458538850), ("Gakenke", 104197824), ("Musanze", 119044390), ("Huye", 280597069)]),
             K("Opening vs closing receivables difference (net)", "Rwf", target=0, basis=ZERO,
               breakdown=[("Kayonza", -1101550), ("Nyagatare", -1623825), ("Gakenke", 12172104), ("Musanze", -81448225), ("Huye", -657772)]),
         ]),

    dict(src_ref="Finding 19", area="Asset Management", priority="Low",
         title="Asset Register in SAP not updated for assets returned to HQ",
         observation=("83 damaged or idle assets returned or donated to HQ on 2 Oct 2025 were still in the regional asset registers "
                      "(Musanze 20, Gisagara 12, Huye 11). The report lists this section under 'Unresolved issues of previous audit recommendations'."),
         criteria="SOP 06.03 §5.12 – Fixed asset coding and tagging",
         risk="Assets are hard to monitor or identify if lost or stolen; non-compliance with SOPs and regulations.",
         mgmt_position="Agreed",
         mgmt_comment=("Delays in processing asset movements, reliance on Excel records and limited SAP skills. The register is being "
                       "updated; IT/SAP and asset-management engagement ongoing."),
         timeline="June 2026",
         flagged_value=None, flagged_label="83 returned assets still on regional registers",
         actions=[A("Update the Asset Register after each physical count of assets in the 8 regional warehouses; hold staff accountable for assets.",
                    LOG, IP, "2026-06-30")],
         kpis=[K("Returned assets still in regional asset registers", "count", target=0, basis=ZERO,
                 breakdown=[("Rubavu", 4), ("Kayonza", 10), ("Nyagatare", 10), ("Gakenke", 10), ("Musanze", 20),
                            ("Nyaruguru", 6), ("Huye", 11), ("Gisagara", 12)])]),

    dict(src_ref="Finding 20", area="Asset Management", priority="Low",
         title="Idle assets held at regional warehouses",
         observation="12 idle assets (printers, scanners, racks, safes, laptop, router, etc.) were kept without action at five warehouses between 27 Jan and 20 Mar 2026.",
         criteria="SOP 06.03 §5.6 – asset disposal, transfer and donation",
         risk="No value for money from idle assets; growing risk of obsolescence.",
         mgmt_position="Reported as implemented",
         mgmt_comment="All idle assets at Huye have been returned to HQ on recommendation. Other warehouses are not addressed in the comment.",
         timeline="Reported as already implemented (Huye only)",
         flagged_value=None, flagged_label="12 idle assets",
         actions=[A("Put idle assets to use (or return, redistribute or dispose of them) before they deteriorate.", LOG, IP,
                    note="Huye reported returned to HQ; no response yet for Kayonza, Gakenke, Musanze, Gisagara.")],
         kpis=[K("Idle assets with no action", "count", target=0, basis=ZERO,
                 breakdown=[("Kayonza", 4), ("Gakenke", 1), ("Musanze", 1), ("Huye", 5), ("Gisagara", 1)])]),

    dict(src_ref="Finding 21", area="Asset Management", priority="Low",
         title="Damaged equipment not repaired and no maintenance plan",
         observation="At Nyagatare and Huye (Mar 2026) damaged assets (e.g. three metallic chairs at Huye) had no repair or disposal plan.",
         criteria="SOP 06.03 §5.15 – repair and improvement of fixed assets",
         risk="Damaged assets risk theft and further damage; RMS may recover nothing on sale if kept too long.",
         mgmt_position="Agreed",
         mgmt_comment="Damaged assets should be repaired or properly disposed of; unused assets are being transferred to HQ asset management for safe disposal.",
         timeline="April 2026",
         flagged_value=None, flagged_label="Damaged assets without plan",
         actions=[A("Repair or dispose of damaged assets (Huye); redistribute assets that are no longer needed.", LOG, IP, "2026-04-30")],
         kpis=[K("Damaged assets awaiting repair / disposal (sample listed)", "count", 3, 0, basis=ZERO)]),

    dict(src_ref="Finding 22", area="Asset Management", priority="High",
         title="Nyagatare: electrical circuit and generator not repaired",
         observation=("Repair of the electrical installation was requested on 26 Aug 2025; the technical team visited on 14 Nov 2025 yet nothing "
                      "changed. The generator has not worked properly since 24 Oct 2025, parts of the site have no power or night lighting."),
         criteria="SOP 4.2.20 – Cold chain maintenance",
         risk="Loss or poor quality of cold-chain products and a high risk of fire.",
         mgmt_position="Agreed",
         mgmt_comment="Escalated to the logistics unit, which plans to correct all electrical-power issues at Nyagatare.",
         timeline="Follow-up until end May 2026",
         flagged_value=None, flagged_label="Cold-chain and fire risk",
         actions=[A("Repair the electrical installation and restore the backup generator at Nyagatare immediately.", LOG, IP, "2026-05-31")],
         kpis=[K("Electrical circuit repaired", "flag", basis="Recommendation"), K("Backup generator operational", "flag", basis="Recommendation")]),

    dict(src_ref="Finding 23", area="Asset Management", priority="Low",
         title="Assets that have lost their tags (Gisagara)",
         observation="A laptop and a chair at Gisagara had lost their asset tags (visit of 18 Mar 2026).",
         criteria="SOP 06.03 §5.12 – assets tagged and recorded",
         risk="Assets are harder to track and identify in case of loss or theft.",
         mgmt_position="Agreed",
         mgmt_comment="The items exist; Gisagara will ask HQ asset management for replacement tags.",
         timeline="Until end April 2026",
         flagged_value=None, flagged_label="2 assets without tags",
         actions=[A("Re-tag the affected assets and strengthen asset controls at Gisagara.", LOG, IP, "2026-04-30")],
         kpis=[K("Assets without tags", "count", 2, 0, basis=ZERO)]),

    dict(src_ref="Finding 24", area="Asset Management", priority="Medium",
         title="Early deterioration of building walls (Gisagara, Nyaruguru)",
         observation=("Walls deteriorated from humidity about 18 months after maintenance works (contract with Gitisi Construction, "
                      "Rwf 55.4M for FY 2024-25). No inspection or progress reports were available for the works."),
         criteria="Maintenance services contract – supervision and inspection of works",
         risk="Payment for substandard works and extra repair costs.",
         mgmt_position="Agreed",
         mgmt_comment=("Contractor engaged to rectify under warranty; RMS engineers asked to assess the root cause. Contract supervision "
                       "and regular inspections will be strengthened."),
         timeline="End June 2026 (follow-up)",
         flagged_value=55434860, flagged_label="Rwf 55.4M maintenance contract",
         actions=[
             A("Carry out a technical evaluation of the deteriorated walls to establish the root cause.", "RMS Engineers / " + LOG, IP, "2026-06-30"),
             A("Have the contractor rectify the defects under warranty provisions.", LOG, IP, "2026-06-30"),
             A("Subject all maintenance works to regular inspection during execution, as the contract requires.", f"{LOG}; {PROC}", NS, "2026-06-30"),
         ],
         kpis=[K("Technical assessment of walls completed", "flag", basis="Recommendation 2"),
               K("Contractor rectification completed", "flag", basis="Recommendation 2")]),
]

# ======================================================================================================
#  CENTRAL WAREHOUSE (Q4)  ·  25 findings
# ======================================================================================================
_ORD = [("Dec 2025", 63, 6), ("Jan 2026", 47, 34), ("Feb 2026", 39, 26), ("Mar 2026", 58, 8),
        ("Apr 2026", 62, 8), ("May 2026", 64, 11), ("Jun 2026", 55, 14), ("17 Jul 2026", 62, 16)]
_ORD_DATES = ["2025-12-31", "2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31", "2026-06-30", "2026-07-17"]

CENTRAL = [
    dict(src_ref="Finding 1", area="Inventory & Expiry Management", priority="Medium",
         title="Medical equipment expired while in stock",
         observation=("Equipment worth Rwf 30.0M (trolleys, titanium screws, digital BP monitors) expired in May and July 2026 without "
                      "being distributed to regional warehouses or donated."),
         criteria="Timely distribution and monitoring of equipment approaching expiry",
         risk="Weak inventory planning and distribution; expiry and wastage of medical commodities.",
         mgmt_position="Agreed",
         mgmt_comment=("QA&QC asked RSB to recalibrate and extend shelf life and is awaiting the report; the titanium screws are being "
                       "replaced by the suppliers."),
         timeline="Not stated",
         flagged_value=30027915, flagged_label="Rwf 30.0M expired equipment",
         actions=[A("Establish a timely distribution and monitoring mechanism for equipment nearing expiry (transfer to regional warehouses or donate).",
                    f"{WHI}; {QA}", IP)],
         kpis=[K("Value of expired medical equipment in stock", "Rwf", target=0, basis=ZERO,
                 breakdown=[("BP monitors (small, upper arm)", 28769866.08), ("Trolley", 910469.04), ("Titanium interference screws", 347579.7)])]),

    dict(src_ref="Finding 2", area="Inventory & Expiry Management", priority="High",
         title="Non-moving and slow-moving medical products",
         observation=("The March 2026 inventory report shows slow-moving stock of Rwf 4.13B and non-moving stock of Rwf 529.0M with no "
                      "adequate action plan for timely intervention."),
         criteria="Stock-management practice – periodic review, redistribution and donation",
         risk="Expiry, obsolescence, wasted resources, higher storage cost and less space for fast-moving products.",
         mgmt_position="Agreed",
         mgmt_comment=("Items categorised and a memorandum proposing interventions (faster distribution, donation, disposal) submitted to "
                       "management; escalated to Risk & Compliance."),
         timeline="Not stated",
         flagged_value=4659079096, flagged_label="Rwf 4.13B slow-moving · Rwf 529.0M non-moving",
         actions=[A("Establish and implement a formal action plan for slow- and non-moving products: periodic review, redistribution to facilities with demand, donation.",
                    f"{WHI}; {QDV}", IP, note="Memorandum submitted to management – approval and implementation pending.")],
         kpis=[K("Non-moving stock value", "Rwf", 529042001, None, basis="Not set in report – management to define reduction target"),
               K("Slow-moving stock value", "Rwf", 4130037095, None, basis="Not set in report – management to define reduction target"),
               K("Formal action plan approved and implemented", "flag", basis="Recommendation")]),

    dict(src_ref="Finding 3", area="SAP Controls & Inventory Records", priority="High",
         title="Unsupported stock adjustments in SAP",
         observation=("Net adjustments of Rwf 15.02B (negative Rwf 77.08B, positive Rwf 92.10B) were posted Jul 2025 – Mar 2026; Rwf 299.8M "
                      "was not justified with adequate supporting documents."),
         criteria="SOP 4.2.21 – Goods and stock valuation",
         risk="Validity and authorisation of adjustments cannot be verified; the warehouse report may be materially misstated.",
         mgmt_position="Disagreed",
         mgmt_comment=("Adjustments came from the SAP S/4HANA migration, stock reconciliation and data correction and are supported by variance "
                       "reports, approvals and correspondence. Management does not concur."),
         timeline="Not stated",
         flagged_value=299812061, flagged_label="Rwf 299.8M unjustified (of Rwf 15.02B net)",
         actions=[A("Ensure sufficient supporting documents exist for any SAP adjustment; retrieve the documents for the unsupported ones.",
                    f"{FIN}; {WHI}", DI, note="Management disagrees – IA and management to agree the evidence to be provided.")],
         kpis=[K("Adjustments not justified", "Rwf", 299812060.74, 0, basis=ZERO),
               K("Share of net adjustments justified", "%", 98.0, 100, basis="Implied target: 100% supported",
                 note="14.72bn of 15.02bn net adjustments justified (98.0%).")]),

    dict(src_ref="Finding 4", area="Order Fulfilment & Distribution", priority="High",
         title="Gaps in order fulfilment",
         observation=("Strategic Plan Activity 2.2.3 targets a 95% order fill rate by June 2026; June 2026 data show 55% fully delivered, 31% partial, "
                      "14% open (62% fully delivered at 17 Jul 2026). The order fill rate was not prepared for all special customers."),
         criteria="Strategic Plan Activity 2.2.3 – order fill rate 95% by June 2026",
         risk="Stock-outs at health facilities, delayed treatment, emergency procurement costs and missed strategic objectives.",
         mgmt_position="Partially agreed",
         mgmt_comment=("Distribution cycles do not match calendar month-end, and one order can be served through several outbound deliveries, so "
                       "fulfilment should be assessed across all related deliveries."),
         timeline="Not stated",
         flagged_value=None, flagged_label="55% fully delivered vs 95% target",
         actions=[
             A("Strengthen supply and distribution – inventory management, regular monitoring of fulfilment, address partial/open orders – to reach the target fill rate.",
               f"{SALES}; {WHI}"),
             A("Prepare the order fill-rate report for all special customers and share it with the relevant authorities.", SALES),
         ],
         kpis=[
             K("Orders fully delivered", "%", 55, 95, current=62, basis="Strategic Plan 2.2.3: 95% by June 2026",
               series=[(d, o[1]) for d, o in zip(_ORD_DATES, _ORD)], note="Baseline = June 2026 (55%). History from the report's monthly table."),
             K("Orders still open", "%", 14, None, current=16, basis="Not set in report",
               series=[(d, o[2]) for d, o in zip(_ORD_DATES, _ORD)]),
         ]),

    dict(src_ref="Finding 5", area="SAP Controls & Inventory Records", priority="Medium",
         title="Unfit products held with 'Unrestricted' status in the quarantine location",
         observation=("Products classified as unfit by Quality, held in quarantine location 9900, still carried 'Unrestricted' status in SAP "
                      "(Rwf 2.7M)."),
         criteria="SOP 6.07.03 – Quarantine management",
         risk="Accidental issue of unsafe products; misstated inventory records.",
         mgmt_position="Partially agreed",
         mgmt_comment=("Plant 9900 is not mapped to any customer or distribution process, so the products could not be issued. Status changes via an "
                       "automated background job; management will review its timing with SAP support."),
         timeline="Not stated",
         flagged_value=2666645, flagged_label="Rwf 2.7M unfit stock marked Unrestricted",
         actions=[A("Assign restricted/blocked status immediately to all unfit, quarantined, expired or pending-disposal products in SAP.",
                    f"{SAP}; {QA}", IP)],
         kpis=[K("Unfit stock with Unrestricted status", "Rwf", 2666645, 0, basis=ZERO)]),

    dict(src_ref="Finding 6", area="SAP Controls & Inventory Records", priority="Medium",
         title="Expired products still shown as Unrestricted stock",
         observation="At 1 Jun 2026 expired items worth Rwf 15.4M were still 'Unrestricted' (available for delivery) instead of blocked or quarantined.",
         criteria="SOP 6.07.03 – Quarantine management",
         risk="System stock does not reflect physical stock; expired items could be treated as available.",
         mgmt_position="Disagreed",
         mgmt_comment=("Items were physically removed from shelves on expiry; the temporary Unrestricted status is a system requirement to create the "
                       "transfer order to the quarantine plant. Management does not concur but will explore automating the status transition."),
         timeline="Not stated",
         flagged_value=15439330, flagged_label="Rwf 15.4M expired but 'Unrestricted'",
         actions=[A("Update SAP stock regularly so expired items are removed from available stock (explore automating the status transition).",
                    f"{SAP}; {WHI}", DI, note="Management disagrees with the conclusion but will explore automation.")],
         kpis=[K("Expired stock shown as Unrestricted", "Rwf", 15439330.26, 0, basis=ZERO)]),

    dict(src_ref="Finding 7", area="Inventory & Expiry Management", priority="High",
         title="Increasing value of expired medical products",
         observation=("Expired products reached 1.60% of inventory held at 30 Jun 2026 (Rwf 4.08B) against a strategic target of 0.42% and a risk-appetite "
                      "tolerance of 0.5% (April 2026)."),
         criteria="Strategic Plan 2024–26 (0.42% by June 2026); Risk Appetite & Tolerance Framework (0.5%)",
         risk="Loss of funds that could be used elsewhere; failure to achieve the strategic target.",
         mgmt_position="Agreed",
         mgmt_comment=("Causes: slow-moving stock, overstocking from inaccurate forecasting, unsold seasonal products, and damage/quality issues."),
         timeline="Not stated",
         flagged_value=4084542339, flagged_label="Rwf 4.08B expired · 1.60% vs 0.42% target",
         actions=[A("Strengthen inventory management to bring the expired-product proportion down to an acceptable level.", f"{WHI}; {QDV}")],
         kpis=[K("Expired products as % of inventory held", "%", 1.6, 0.42, basis="Strategic Plan 2024–26: 0.42% (tolerance ≤ 0.5%)"),
               K("Value of expired products", "Rwf", 4084542339, None, basis="Not set in report – derive from the 0.42% target")]),

    dict(src_ref="Finding 8", area="Quality, Returns & Recalls", priority="High",
         title="Delays in obtaining replacements for products returned for poor quality",
         observation=("Defective products worth Rwf 211.9M (perforated adhesive tape from Abacus; short IV catheters from Zhejiang Lidesen) returned since Sep 2025 "
                      "were still not replaced by June 2026 – delays of 278 and 118 days."),
         criteria="SOP 6.7.2 – Quarantine management",
         risk="Financial loss from non-replacement or no refund; stock shortages and service disruption.",
         mgmt_position="Agreed",
         mgmt_comment="Replacement requests have been issued and feedback is awaited; the local supplier delayed collecting returned quantities.",
         timeline="Not stated",
         flagged_value=211914600, flagged_label="Rwf 211.9M awaiting replacement / refund",
         actions=[A("Communicate with suppliers with clear expectations to replace the substandard products or refund the payments.", f"{PROC}; {QA}", IP)],
         kpis=[K("Defective products awaiting replacement or refund", "Rwf", target=0, basis=ZERO,
                 breakdown=[("Abacus Ltd (adhesive tape)", 203950800), ("Zhejiang Lidesen (IV catheter)", 7963800)]),
               K("Longest replacement delay", "days", 278, None, basis="Not set in report")]),

    dict(src_ref="Finding 9", area="Quality, Returns & Recalls", priority="Medium",
         title="Differences between reported and actual quantities of recalled products",
         observation=("For recalled perforated adhesive tape, 22,038 units were reported in quarantine but only 18,002 found – 4,036 units (Rwf 14.5M) unexplained."),
         criteria="Recall reconciliation: distributed, returned, quarantined, incinerated",
         risk="Weak tracking of recalled products and loss of stock accountability.",
         mgmt_position="Partially agreed",
         mgmt_comment=("Data were split across Sage, SAP pre-production and SAP production; the integrated system now allows reliable tracing. The gap is "
                       "likely a data-migration effect."),
         timeline="Not stated",
         flagged_value=14529600, flagged_label="Rwf 14.5M · 4,036 units unexplained",
         actions=[A("Strengthen recall and reconciliation – document, track and reconcile distributed, returned, quarantined and incinerated quantities.",
                    f"{QA}; {WHI}", IPV, note="Management says the integrated system now supports this – IA to verify.")],
         kpis=[K("Unexplained recalled-product variance (units)", "units", 4036, 0, basis=ZERO),
               K("Unexplained recalled-product variance (value)", "Rwf", 14529600, 0, basis=ZERO)]),

    dict(src_ref="Finding 10", area="Order Fulfilment & Distribution", priority="High",
         title="Delay in clearing stock-in-transit from HQ to regional warehouses",
         observation="Stock worth Rwf 485.8M stayed 'in transit' for 13–305 days before being received by regional warehouses.",
         criteria="Stock transfer, receipt confirmation and reconciliation",
         risk="Stock shortages at regional warehouses, damage, expiry or loss, and inaccurate inventory records.",
         mgmt_position="Reported as implemented",
         mgmt_comment=("Caused by limited system knowledge. During preparation for the June 2026 stock take all in-transit items were identified, cleared and "
                       "received; monitoring has been strengthened and few items remain."),
         timeline="Reported as resolved (June 2026 stock take)",
         flagged_value=485835503, flagged_label="Rwf 485.8M in transit 13–305 days",
         actions=[A("Strengthen stock-in-transit monitoring: transfer timelines, follow-up of pending deliveries, receipt confirmation by regional warehouses, tracking and periodic review.",
                    f"{WHI}; {BM}", IPV, note="Management says all items were cleared at the June 2026 stock take – IA to verify.")],
         kpis=[K("Stock-in-transit value", "Rwf", 485835503, 0, basis=ZERO),
               K("Longest time in transit", "days", 305, None, basis="Not set in report")]),

    dict(src_ref="Finding 11", area="Sales & Receivables", priority="High",
         title="Delay in sending delivery notes and invoices to special customers",
         observation="For CHUK and Kanombe Military Hospital, delivery notes and invoices (Rwf 234.5M) were sent 4–55 days after delivery.",
         criteria="SOP 4.2.12 – delivery notes and invoices transmitted promptly through SAP",
         risk="Delayed confirmation and payment, disputes, inaccurate receivables and weaker cash flow.",
         mgmt_position="Partially agreed",
         mgmt_comment=("Delays were due to missing documents on urgent deliveries (deliveries are now halted until documents are complete) and to the multi-stage "
                       "invoice approval process at Kanombe Military Hospital."),
         timeline="Not stated",
         flagged_value=234459682, flagged_label="Rwf 234.5M invoiced 4–55 days late",
         actions=[A("Strengthen control over the delivery-note and invoice cycle, monitor delays, and set accountability for non-compliance.", SALES, IP)],
         kpis=[K("Value of invoices sent late", "Rwf", 234459682, 0, basis=ZERO),
               K("Longest delay to invoice transmission", "days", 55, None, basis="Not set in report – SOP says 'promptly'")]),

    dict(src_ref="Finding 12", area="Planning & Governance", priority="Medium",
         title="Deficiencies in managing and monitoring cross-subsidised commodities",
         observation=("No quarterly reports, revenue-trend analyses or executive reports on cross-subsidised commodities existed for Jul 2025 – Mar 2026, and the SOP "
                      "names no single process owner across Quantification, Finance and Sales."),
         criteria="SOP 5.02.01 – Cross-subsidisation (quarterly monitoring and reporting)",
         risk="Weak oversight, unclear accountability and risks to financial sustainability and equitable access.",
         mgmt_position="Agreed",
         mgmt_comment="Governance, monitoring and reporting will be strengthened and a structured collaboration mechanism established.",
         timeline="Not stated",
         flagged_value=None, flagged_label="0 quarterly reports in 3 quarters",
         actions=[
             A("Prepare, review and submit quarterly cross-subsidisation reports (revenue trends, uptake, cost recovery, access) to Senior Management.", f"{FIN}; {SALES}"),
             A("Establish a formal cross-functional governance mechanism (Quantification, Finance, Sales).", EXEC),
             A("Designate a single process owner for the cross-subsidisation framework.", EXEC),
             A("Conduct periodic joint reviews of the strategy's effectiveness and recommend pricing or operational adjustments.", f"{FIN}; {QDV}"),
             A("Finance to archive all proposals, approvals, monitoring reports and supporting documents.", FIN),
         ],
         kpis=[K("Quarterly cross-subsidisation reports submitted (per year)", "count", 0, 4, basis="SOP 5.02.01: quarterly"),
               K("Single process owner designated", "flag", basis="Recommendation"),
               K("Cross-functional governance mechanism established", "flag", basis="Recommendation")]),

    dict(src_ref="Finding 13", area="Procurement, Donations & Suppliers", priority="High",
         title="Delays in recording donated products and in receiving ordered products",
         observation=("Donated products were recorded in SAP 69–325 days after arrival. 89 purchase orders were not received within the agreed delivery period, "
                      "overdue by 141–309 days (Appendix Two)."),
         criteria="Inventory procedures – prompt SAP recording; supply contracts – delivery within agreed time",
         risk="Poor performance against supply plans, higher cost and time, and stock-outs.",
         mgmt_position="Agreed",
         mgmt_comment=("Some purchase orders were created though not needed because the same items arrived on other POs; these should have been deleted. "
                       "Outstanding POs will keep being monitored until fulfilled."),
         timeline="Not stated",
         flagged_value=None, flagged_label="89 overdue POs · donations recorded 69–325 days late",
         actions=[
             A("Record and receive donated medical products in SAP promptly.", f"{WHI}; {SAP}"),
             A("Strengthen supervision and monitoring of purchase orders outstanding beyond the agreed delivery date; close or delete POs that are no longer needed.",
               PROC, IP),
         ],
         kpis=[K("Purchase orders overdue (not received)", "count", 89, 0, basis=ZERO),
               K("Longest delay recording donations in SAP", "days", 325, None, basis="Not set in report"),
               K("Longest overdue purchase order", "days", 309, None, basis="Not set in report")]),

    dict(src_ref="Finding 14", area="Planning & Governance", priority="High",
         title="No stock-level parameters (min / max / re-order) in SAP",
         observation="Minimum, maximum and re-order levels were not established or maintained in SAP, so there are no alerts when stock reaches the re-order point.",
         criteria="SOP 2.5.2 – Quantification and Data Visibility (Min/Max stock monitoring)",
         risk="Stock-outs from late replenishment, overstocking and expiry, and ineffective forecasting.",
         mgmt_position="Agreed",
         mgmt_comment="Material Requirements Planning (MRP) is being deployed and analytics dashboards are being built in the ROC.",
         timeline="Not stated",
         flagged_value=None, flagged_label="No min/max levels configured",
         actions=[A("Configure and maintain Min, Max and Re-order levels in SAP for all items based on consumption, lead times and programme needs; review regularly.",
                    f"{QDV}; {SAP}", IP)],
         kpis=[K("Items with min/max/re-order levels configured", "%", 0, 100, basis="Implied target: all items")]),

    dict(src_ref="Finding 15", area="Planning & Governance", priority="Medium",
         title="Ineffective inventory management – unclear roles for stock monitoring",
         observation=("The Inventory Section does not do regular stock analysis or monitor min/max levels, saying it is outside its KPIs, and assigns it to Quantification "
                      "and Data Visibility; no coordinated process was evidenced."),
         criteria="Clear roles and responsibilities for inventory monitoring",
         risk="Overstocking, stock-outs, expiry and weak procurement planning from unclear accountability.",
         mgmt_position="Agreed",
         mgmt_comment="Responsibilities between Quantification and Inventory Management are under review; roles will be allocated on completion.",
         timeline="Not stated",
         flagged_value=None, flagged_label="Roles not assigned",
         actions=[
             A("Document and assign clear roles for stock analysis, min/max monitoring and parameter review; include them in departmental KPIs.", EXEC, IP),
             A("Implement a coordinated inventory-monitoring framework between the Inventory Section and Quantification & Data Visibility.", f"{WHI}; {QDV}"),
         ],
         kpis=[K("Roles for inventory monitoring documented and assigned", "flag", basis="Recommendation 1"),
               K("Coordinated monitoring framework in place", "flag", basis="Recommendation 2")]),

    dict(src_ref="Finding 16", area="SAP Controls & Inventory Records", priority="Medium",
         title="Variance between physical stock count and SAP records",
         observation="The 2–4 Jun 2026 count showed physical stock Rwf 906.8M against SAP Rwf 865.5M – an unexplained variance of Rwf 41.3M that had not been investigated or adjusted.",
         criteria="Reconciliation of the physical count report to SAP",
         risk="Completeness of the disclosed inventory balance cannot be confirmed.",
         mgmt_position="Partially agreed",
         mgmt_comment=("The count ran during live operations; some items missing from bins had already been picked against outbound deliveries awaiting goods issue and "
                       "still showed in SAP."),
         timeline="Not stated",
         flagged_value=41259217, flagged_label="Rwf 41.3M variance",
         actions=[A("Investigate the cause of the difference, take corrective action, and reconcile physical quantities with SAP regularly.", f"{WHI}; {SAP}")],
         kpis=[K("Unexplained physical vs SAP variance", "Rwf", 41259217, 0, basis=ZERO)]),

    dict(src_ref="Finding 17", area="SAP Controls & Inventory Records", priority="Medium",
         title="Incorrect expiry dates recorded in SAP",
         observation="At the 3–4 Jun 2026 count, expiry dates in SAP differed from those on the physical products for items worth Rwf 18.4M.",
         criteria="SOP 4.01.05 – Quality inspection and receiving",
         risk="Poor shelf-life monitoring, expired stock kept or issued, and unreliable data for planning.",
         mgmt_position="Reported as implemented",
         mgmt_comment=("Spot checks on newly received products increased; receiving and QA teams made accountable; authority to amend batch/expiry data restricted to the "
                       "Warehouse Manager."),
         timeline="Not stated",
         flagged_value=18361770, flagged_label="Rwf 18.4M with wrong expiry date",
         actions=[
             A("Review all inventory records and reconcile SAP expiry dates to the physical products; correct discrepancies promptly.", f"{WHI}; {QA}", IP),
             A("Introduce independent verification and supervisory review of batch numbers and expiry dates before they are entered in SAP.", WHI, IPV,
               note="Management says authority to amend is restricted to the Warehouse Manager – IA to verify."),
             A("Run periodic data-quality reviews and reconciliations of SAP inventory records.", WHI),
             A("Train warehouse and inventory staff on accurate data entry and procedures.", WHI),
         ],
         kpis=[K("Stock with incorrect expiry date in SAP", "Rwf", 18361770, 0, basis=ZERO)]),

    dict(src_ref="Finding 18", area="Order Fulfilment & Distribution", priority="Medium",
         title="Unjustified delays against the Active Distribution Calendar",
         observation="Actual deliveries ran 1–12 days behind the Active Distribution Calendar (Jul 2025 – Apr 2026), and monthly implementation reports were not prepared for every cycle.",
         criteria="RMS Service Charter (March 2025) – orders processed in 2–3 days; approved Active Distribution Calendar",
         risk="Stock-outs at health facilities and non-achievement of the RMS mandate.",
         mgmt_position="Partially agreed",
         mgmt_comment="Delays arise from several factors; monitoring will increase and the calendar readjusted when needed. Monthly reports were prepared for some cycles, not all.",
         timeline="Not stated",
         flagged_value=None, flagged_label="Deliveries 1–12 days late",
         actions=[
             A("Enforce adherence to the approved distribution schedule through supervision and accountability.", SALES),
             A("Identify and address bottlenecks (stock availability, transport, etc.) causing delays.", f"{SALES}; {WHI}"),
             A("Introduce performance indicators and regular reporting on distribution timelines, with corrective actions; prepare a monthly implementation report for every cycle.", SALES, IP),
         ],
         kpis=[K("Longest delay against planned distribution date", "days", 12, 0, basis="Implied target: delivery on the planned date"),
               K("Monthly calendar implementation report prepared for every cycle", "flag", basis="Recommendation 3")]),

    dict(src_ref="Finding 19", area="SAP Controls & Inventory Records", priority="Medium",
         title="Items delivered directly to health facilities without SAP updates",
         observation=("Products worth Rwf 12.8M were distributed to health facilities with no SAP transaction, so stock stayed overstated. Corn Soya delivered directly by the "
                      "supplier accounts for 5,296 units."),
         criteria="SOP 4.13.2 – Stock take and inventory count; stock movements recorded in SAP",
         risk="Cost of sales, closing inventory and sales cannot be confirmed.",
         mgmt_position="Partially agreed",
         mgmt_comment=("Corn Soya is supplied under a DDP end-user contract with direct distribution by the supplier. Documents for 4,176 of 5,296 units were found and regularised; "
                       "the rest to be closed by end August 2026."),
         timeline="End August 2026",
         flagged_value=12848096, flagged_label="Rwf 12.8M delivered without SAP update",
         actions=[A("Distribute through the normal SAP process; regularise all past direct deliveries (Corn Soya) by end August 2026.", f"{SALES}; {WHI}", IP, "2026-08-31")],
         kpis=[K("Value delivered without SAP update", "Rwf", 12848096, 0, basis=ZERO),
               K("Corn Soya units not yet regularised", "units", 5296, 0, basis=ZERO,
                 note="Management reports 4,176 of 5,296 regularised (evidence sent to the auditor) – verify, then record 1,120.")]),

    dict(src_ref="Finding 20", area="Sales & Receivables", priority="High",
         title="Unsupported sales invoices and credit notes",
         observation="For the year to 31 Mar 2026, sales invoices of Rwf 851.0M and credit notes of Rwf 117.4M lacked verifiable supporting documents (Appendix 3).",
         criteria="RMS financial procedures – approved delivery notes, customer acknowledgements, credit-note approvals",
         risk="Existence and validity of sales cannot be verified; misstated financial statements; weak control against fraud or error.",
         mgmt_position="Partially agreed",
         mgmt_comment=("The documents span a long period and are split between Kigali Hub and HQ files, some very old. Most support was found; the rest will be provided by end August 2026."),
         timeline="End August 2026",
         flagged_value=968381024, flagged_label="Rwf 851.0M invoices · Rwf 117.4M credit notes",
         actions=[
             A("Ensure all sales invoices and credit notes are supported by verifiable documents before they are recorded.", f"{FIN}; {SALES}", IP, "2026-08-31"),
             A("Strengthen document retention and filing controls; review supporting documentation periodically.", FIN, NS, "2026-08-31"),
         ],
         kpis=[K("Unsupported sales invoices", "Rwf", 851019620, 0, basis=ZERO),
               K("Unsupported credit notes", "Rwf", 117361404, 0, basis=ZERO)]),

    dict(src_ref="Finding 21", area="Order Fulfilment & Distribution", priority="High",
         title="No distribution plan for COBAS products",
         observation="A large quantity of short-shelf-life COBAS products (Rwf 922.8M) stayed in RMS warehouses long after receipt and no documented distribution plan existed.",
         criteria="Demand-driven inventory control and prompt distribution of laboratory products",
         risk="Expiry and disposal costs, hospitals not receiving products, and reduced shelf life before use.",
         mgmt_position="Partially agreed",
         mgmt_comment=("Products are procured on confirmed demand but sometimes refused on arrival because customers require quotations or second confirmations. The unit will work "
                       "with Quantification to monitor slow-moving COBAS stock."),
         timeline="Not stated",
         flagged_value=922827359, flagged_label="Rwf 922.8M COBAS stock without a plan",
         actions=[
             A("Procure on confirmed demand and deliver to requesting hospitals within an appropriate timeframe.", f"{PROC}; {SALES}"),
             A("Monitor slow-moving stock regularly and redistribute it in time.", f"{SALES}; {QDV}", IP),
             A("Develop and implement a distribution plan for all COBAS products on receipt (beneficiaries, quantities, schedules, responsible persons).", SALES),
         ],
         kpis=[K("COBAS stock without a distribution plan", "Rwf", 922827359, 0, basis=ZERO),
               K("Distribution plan documented for all COBAS products", "flag", basis="Recommendation 3")]),

    dict(src_ref="Finding 22", area="Sales & Receivables", priority="High",
         title="Unsupported receivables at 30 April 2026",
         observation=("Receivables of Rwf 1.72B were not supported by verifiable documents, and official invoices for Inkurunziza Orthopedic Hospital (Rwf 33.1M) had not been sent."),
         criteria="SOP on Sales – Recovery Officer responsibilities",
         risk="Debtors may be unrecoverable; the receivable balance may be misstated.",
         mgmt_position="Agreed",
         mgmt_comment=("Customers moved from Kigali Hub and recovery moved from Sales to Finance only in Feb 2026; archived files at Kicukiro are being retrieved. A full customer "
                       "reconciliation is expected to finish by end August 2026."),
         timeline="End August 2026",
         flagged_value=1715230287, flagged_label="Rwf 1.72B unsupported",
         actions=[
             A("Support every receivable entry with POs, invoices, signed delivery notes and proof of payment.", REC, IP, "2026-08-31"),
             A("Complete the customer reconciliation exercise and submit signed statements with supporting documents.", REC, IP, "2026-08-31"),
             A("Transmit the official sales invoices to Inkurunziza Orthopedic Hospital.", REC, NS, note="Derived from the observation."),
         ],
         kpis=[K("Unsupported receivables", "Rwf", 1715230287, 0, basis=ZERO),
               K("Invoices not yet transmitted to customer (Inkurunziza)", "Rwf", 33063666, 0, basis=ZERO)]),

    dict(src_ref="Finding 23", area="Sales & Receivables", priority="Medium",
         title="Manual sales invoices issued outside SAP (CHUK)",
         observation="Sales of Rwf 94.1M to CHUK were processed outside SAP despite the CEO's instruction to stop manual transactions.",
         criteria="CEO letter Ref 1102/RMS/CEO/2025 – cessation of manual transactions",
         risk="Inaccurate financial records and revenue reporting.",
         mgmt_position="Partially agreed",
         mgmt_comment=("Urgent specialised equipment and lab consumables were quoted on supplier pro-formas and delivered directly in an emergency, then regularised. Sales and the SAP consultants "
                       "are designing a process to quote and invoice non-warehoused items in SAP."),
         timeline="Not stated",
         flagged_value=94135515, flagged_label="Rwf 94.1M invoiced outside SAP",
         actions=[A("Process all sales through SAP; any exception must be justified and approved by the CEO beforehand.", f"{SALES}; {SAP}", IP)],
         kpis=[K("Sales invoiced outside SAP", "Rwf", 94135515, 0, basis=ZERO)]),

    dict(src_ref="Finding 24", area="Procurement, Donations & Suppliers", priority="High",
         title="Delay in paying suppliers' invoices",
         observation=("Supplier bills of EUR 75,985, USD 3,653,673 and Rwf 926.9M for the year to 31 Mar 2026 were paid 4–127 days late against 45-day terms; acknowledgements to "
                      "suppliers were sent 16–65 days late."),
         criteria="Supplier contracts – pay within 45 days; SOP 4.2.1 – supplier notification and acceptance timelines",
         risk="Reputational damage, penalties or interest, supplier disputes and disruption to supply of medical products.",
         mgmt_position="Agreed",
         mgmt_comment=("Delays came from late funding of programme stock by RBC (advance funding under the MoU is being explored) and administrative/documentation delays. Finance attached comments "
                       "for each PO."),
         timeline="Not stated",
         flagged_value=926942315, flagged_label="Rwf 926.9M + USD 3.65M + EUR 76K paid late",
         actions=[
             A("Establish clear timelines and responsibilities for sending acknowledgements and supporting documents to suppliers.", f"{PROC}; {FIN}"),
             A("Implement a tracking mechanism for outstanding acknowledgements so invoices are processed promptly.", FIN),
             A("Reconcile supplier documentation and invoice status regularly.", FIN),
             A("Strengthen coordination between warehouse, procurement, finance and supplier management (incl. RBC advance funding under the MoU).", f"{FIN}; {PROC}", IP),
         ],
         kpis=[K("Value of supplier bills paid late (Rwf portion)", "Rwf", 926942315, 0, basis=ZERO,
                 note="Excludes USD 3,653,673 and EUR 75,985 of late-paid bills."),
               K("Longest delay in paying a supplier invoice", "days", 127, 0, basis="Contract terms: 45 days"),
               K("Longest delay sending acknowledgement to supplier", "days", 65, 0, basis="SOP 4.2.1 timelines")]),

    dict(src_ref="Finding 25", area="Sales & Receivables", priority="Medium",
         title="Gaps in the receivables ageing report",
         observation="The 31 Mar 2026 ageing report omitted invoices totalling Rwf 239.0M, so outstanding invoices per customer and their age could not be determined.",
         criteria="Receivables & Collections Policy §9.1 – ageing report",
         risk="Inaccurate allowance for doubtful accounts; delinquent accounts can become uncollectible.",
         mgmt_position="Partially agreed",
         mgmt_comment=("Some invoices were fully settled, some migrated to SAP under new references (originals kept in the assignment field), and some belong to Kanombe MH's second account. "
                       "Proof of payment will be sent to the auditors by 17 July 2026."),
         timeline="17 July 2026",
         flagged_value=239043400, flagged_label="Rwf 239.0M missing from ageing report",
         actions=[A("Record all invoices promptly and accurately (customer, date, amount) and categorise them correctly in the ageing report; supply proof of payment for settled invoices.",
                    FIN, IP, "2026-07-17")],
         kpis=[K("Invoices missing from ageing report", "Rwf", 239043400, 0, basis=ZERO)]),
]

FINDINGS = {"regional": REGIONAL, "central": CENTRAL}
