#!/usr/bin/env python3
"""Build Fortinet (FTNT) Q3 2026 earnings update: charts (matplotlib) + DOCX (python-docx).

All reported figures come from Fortinet 8-K Exhibit 99.1 press releases on SEC EDGAR
(Q4'24 through Q3'26). Forward estimates are our own and labelled "E".
Run:  python3 build_report.py
"""
import csv
import datetime as dt
import os
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.section import WD_ORIENT  # noqa: E402,F401
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.opc.constants import RELATIONSHIP_TYPE as RT  # noqa: E402
from docx.shared import Inches, Pt, RGBColor  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(BASE, "charts")
OUT = os.path.join(BASE, "Fortinet_Q3_2026_Earnings_Update.docx")
os.makedirs(CHART_DIR, exist_ok=True)

# ----------------------------------------------------------------------------
# URLs
# ----------------------------------------------------------------------------
EDGAR = "https://www.sec.gov/Archives/edgar/data/1262039/"
U = {
    "q3_26": "https://www.sec.gov/Archives/edgar/data/0001262039/000126203926000024/ftntq3-2026ex991.htm",
    "q3_26_idx": EDGAR + "000126203926000024/",
    "pr": "https://investor.fortinet.com/news-releases/news-release-details/fortinet-reports-strong-third-quarter-2026-financial-results",
    "q2_26": "https://www.sec.gov/Archives/edgar/data/0001262039/000126203926000018/ftntq2-2026ex991.htm",
    "q1_26": EDGAR + "000126203926000010/ftntq1-2026ex991.htm",
    "q4_25": EDGAR + "000126203926000003/ftntq4-2025ex991.htm",
    "q3_25": EDGAR + "000126203925000036/ftntq3-2025ex991.htm",
    "q2_25": EDGAR + "000126203925000025/ftntq2-2025ex991.htm",
    "q1_25": EDGAR + "000126203925000014/ftntq1-2025ex991.htm",
    "q4_24": EDGAR + "000126203925000007/ftntq4-2024ex991.htm",
    "10q_q2": EDGAR + "000126203926000021/ftnt-20260630.htm",
    "edgar_list": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001262039&type=8-K&dateb=&owner=include&count=40",
    "fool": "https://www.fool.com/earnings/call-transcripts/2026/10/29/fortinet-ftnt-q3-2026-earnings-call-transcript/",
    "inv_tr": "https://www.investing.com/news/transcripts/earnings-call-transcript-fortinet-beats-q3-2026-estimates-but-shares-plunge-93CH-4981034",
    "inv_plunge": "https://www.investing.com/news/stock-market-news/why-is-fortinet-stock-plunging-today-93CH-4980914",
    "sa": "https://www.tradingview.com/news/seekingalpha:853e1b02f094b:0-fortinet-falls-despite-strong-q3-results-and-higher-guidance/",
    "tickeron": "https://tickeron.com/blogs/fortinet-ftnt-delivers-q3-beat-and-raises-guidance-but-shares-drop-more-than-20-23536/",
    "hudson": "https://www.hudson-labs.com/research/fortinet-q3-2026-earnings-preview-ftnt-revenue-and-outlook",
    "arete": "https://www.investing.com/news/stock-market-news/fortinet-stock-falls-as-arete-delivers-rare-double-downgrade-to-sell-4962860",
    "mb_jpm": "https://www.marketbeat.com/instant-alerts/analyst-fortinet-nasdaq-ftnt-stock-price-expected-to-rise-jpmorgan-chase-co-analyst-says-2026-10-23/",
    "yahoo": "https://finance.yahoo.com/quote/FTNT/history/",
}

# ----------------------------------------------------------------------------
# Reported data ($M except per share / %), from 8-K Ex. 99.1 releases
# ----------------------------------------------------------------------------
Q = ["Q4'24", "Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26", "Q3'26"]
QA = [q + "A" for q in Q]
REV = [1660.1, 1539.7, 1630.0, 1724.9, 1905.0, 1849.6, 2047.9, 2078.4]
PROD = [574.0, 459.1, 508.9, 559.3, 691.1, 645.1, 773.0, 765.0]
SERV = [1086.1, 1080.6, 1121.1, 1165.6, 1213.9, 1204.5, 1274.9, 1313.4]
# prior-year quarters for growth (Q4'23..Q3'25)
PROD_PY = [488.1, 408.9, 451.9, 473.9, 574.0, 459.1, 508.9, 559.3]
SERV_PY = [927.0, 944.4, 982.4, 1034.2, 1086.1, 1080.6, 1121.1, 1165.6]
REV_PY = [1415.1, 1353.3, 1434.3, 1508.1, 1660.1, 1539.7, 1630.0, 1724.9]
GP = [1345.6, 1246.6, 1315.1, 1393.2, 1515.8, 1485.1, 1643.2, 1640.9]
PROD_GP = [396.0, 309.2, 343.0, 378.6, 462.2, 436.8, 539.2, 492.4]
SERV_GP = [949.6, 937.4, 972.1, 1014.6, 1053.6, 1048.3, 1104.0, 1148.5]
NG_OM = [39.2, 34.2, 33.1, 36.9, 37.3, 35.8, 38.0, 38.2]
G_OM = [34.6, 29.5, 28.1, 31.7, 32.8, 31.4, 33.7, 33.9]
NG_EPS = [0.74, 0.58, 0.64, 0.74, 0.81, 0.82, 0.90, 0.91]
G_EPS = [0.68, 0.56, 0.57, 0.62, 0.68, 0.72, 0.82, 0.86]
BILL = [2002.5, 1597.2, 1778.4, 1807.7, 2370.4, 2085.3, 2372.1, 2336.3]
BILL_PY = [1864.8, 1407.2, 1540.6, 1582.2, 2002.5, 1597.2, 1778.4, 1807.7]
OCF = [477.6, 863.3, 451.9, 655.2, 620.2, 1077.1, 1043.6, 946.0]
FCF = [380.0, 782.8, 284.1, 567.5, 577.4, 1006.5, 965.6, 864.8]
DR_ST = [3276.2, 3339.4, 3412.5, 3460.5, 3636.0, 3726.3, 3841.8, 3961.0]
DR_LT = [3084.7, 3079.0, 3155.1, 3189.9, 3479.8, 3625.2, 3833.9, 3973.4]
INV = [315.5, 362.7, 405.2, 426.6, 399.5, 369.6, 426.3, 591.2]
# Non-GAAP EPS Q4'23..Q3'26 for trailing-twelve-month P/E
EPS_HIST = {  # report date -> quarterly non-GAAP EPS reported that day
    dt.date(2024, 11, 7): 0.63, dt.date(2025, 2, 6): 0.74, dt.date(2025, 5, 7): 0.58,
    dt.date(2025, 8, 6): 0.64, dt.date(2025, 11, 5): 0.74, dt.date(2026, 2, 5): 0.81,
    dt.date(2026, 5, 6): 0.82, dt.date(2026, 7, 29): 0.90, dt.date(2026, 10, 28): 0.91,
}
EPS_PRE = [0.51, 0.43, 0.57]  # Q4'23, Q1'24, Q2'24 (from Q4'24/Q1'25/Q2'25 releases)

pct = lambda a, b: (a / b - 1) * 100  # noqa: E731
PROD_G = [pct(a, b) for a, b in zip(PROD, PROD_PY)]
SERV_G = [pct(a, b) for a, b in zip(SERV, SERV_PY)]
REV_G = [pct(a, b) for a, b in zip(REV, REV_PY)]
BILL_G = [pct(a, b) for a, b in zip(BILL, BILL_PY)]
GM = [a / b * 100 for a, b in zip(GP, REV)]
PGM = [a / b * 100 for a, b in zip(PROD_GP, PROD)]
SGM = [a / b * 100 for a, b in zip(SERV_GP, SERV)]
FCFM = [a / b * 100 for a, b in zip(FCF, REV)]
DR = [a + b for a, b in zip(DR_ST, DR_LT)]

# Market data
PX_CLOSE = 174.08  # 10/28/26 close (Yahoo Finance)
PX_REF = 129.00  # indicative pre-market 10/29/26 (~$128-131)
SHARES = 742.6  # Q3'26 diluted shares (M)
NET_CASH = 3750.6 + 1048.4 + 519.4 - 497.1  # cash + ST + LT investments - debt, 9/30/26

# Our estimates
EST = {
    #               FY25A    FY26 old  FY26 new  FY27 old  FY27 new
    "Revenue ($M)": (6799.6, 8140, 8191, 9250, 9065),
    "  Service ($M)": (4581.2, 5205, 5160, 5960, 5882),
    "  Product ($M)": (2218.4, 2935, 3031, 3290, 3183),
    "Billings ($M)": (7553.7, 9480, 9664, 10500, 10437),
    "Non-GAAP gross margin (%)": (None, 80.3, 80.0, 80.0, 79.0),
    "Non-GAAP op. margin (%)": (35.5, 36.4, 37.3, 36.5, 36.0),
    "Non-GAAP EPS ($)": (2.76, 3.48, 3.58, 3.95, 3.81),
    "Free cash flow ($M)": (2211.8, 3250, 3437, 3500, 3350),
}
EPS26, EPS27 = 3.58, 3.81
FCF27 = 3350
PT_MULT = 34
PT = 130
BEAR = (3.50, 28)
BULL = (4.10, 40)

# ----------------------------------------------------------------------------
# Chart styling
# ----------------------------------------------------------------------------
NAVY, BLUE, LIGHT, ORANGE, GRAY, GREEN, RED = (
    "#1f3b6f", "#4a78b5", "#a9c1e0", "#d9822b", "#7f7f7f", "#3a8f5c", "#b23a3a")
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "-",
    "legend.frameon": False, "legend.fontsize": 8, "savefig.dpi": 200,
    "text.parse_math": False,
})


def save(fig, name):
    path = os.path.join(CHART_DIR, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def bar_colors(n, base=BLUE, last=NAVY):
    return [base] * (n - 1) + [last]


charts = {}

# Fig 1: revenue mix
fig, ax = plt.subplots(figsize=(6.5, 2.9))
x = range(len(Q))
ax.bar(x, SERV, color=LIGHT, label="Service revenue")
ax.bar(x, PROD, bottom=SERV, color=[BLUE] * 7 + [NAVY], label="Product revenue")
for i in x:
    ax.text(i, REV[i] + 25, f"${REV[i]:,.0f}", ha="center", fontsize=7.5)
ax.set_xticks(list(x)); ax.set_xticklabels(QA)
ax.set_ylabel("$M"); ax.set_ylim(0, 2450)
ax2 = ax.twinx(); ax2.plot(list(x), REV_G, color=ORANGE, marker="o", lw=1.8, label="Total revenue YoY %")
ax2.set_ylim(0, 40); ax2.set_ylabel("YoY growth (%)"); ax2.grid(False)
ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", ncol=3)
charts["rev"] = save(fig, "fig01_revenue_mix.png")

# Fig 2: billings
fig, ax = plt.subplots(figsize=(6.5, 2.7))
ax.bar(x, BILL, color=bar_colors(8))
for i in x:
    ax.text(i, BILL[i] + 30, f"${BILL[i]:,.0f}", ha="center", fontsize=7.5)
ax.set_xticks(list(x)); ax.set_xticklabels(QA); ax.set_ylabel("$M"); ax.set_ylim(0, 2800)
ax2 = ax.twinx(); ax2.plot(list(x), BILL_G, color=ORANGE, marker="o", lw=1.8, label="Billings YoY %")
ax2.set_ylim(0, 40); ax2.set_ylabel("YoY growth (%)"); ax2.grid(False); ax2.spines["right"].set_visible(True)
ax2.legend(loc="upper left")
charts["bill"] = save(fig, "fig02_billings.png")

# Fig 3: product vs service growth
fig, ax = plt.subplots(figsize=(6.5, 2.7))
ax.plot(QA, PROD_G, color=NAVY, marker="o", lw=2, label="Product revenue YoY %")
ax.plot(QA, SERV_G, color=ORANGE, marker="s", lw=2, label="Service revenue YoY %")
for i in x:
    ax.annotate(f"{PROD_G[i]:.0f}%", (i, PROD_G[i]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=7.5, color=NAVY)
    ax.annotate(f"{SERV_G[i]:.1f}%", (i, SERV_G[i]), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=7.5, color=ORANGE)
ax.set_ylabel("YoY growth (%)"); ax.set_ylim(0, 60); ax.legend(loc="upper left")
charts["growth"] = save(fig, "fig03_product_vs_service_growth.png")

# Fig 4: margins
fig, ax = plt.subplots(figsize=(6.5, 2.8))
ax.plot(QA, SGM, color=LIGHT, marker="o", lw=2, label="Service GM (GAAP)")
ax.plot(QA, GM, color=NAVY, marker="o", lw=2, label="Total GM (GAAP)")
ax.plot(QA, PGM, color=RED, marker="o", lw=2, label="Product GM (GAAP)")
ax.plot(QA, NG_OM, color=ORANGE, marker="s", lw=2, label="Non-GAAP op. margin")
for series, col, off in ((PGM, RED, -12), (NG_OM, ORANGE, 6), (GM, NAVY, 6)):
    ax.annotate(f"{series[-1]:.1f}%", (7, series[-1]), textcoords="offset points", xytext=(14, off - 3), fontsize=7.5, color=col)
ax.set_ylabel("%"); ax.set_ylim(25, 95); ax.legend(loc="lower left", ncol=4)
charts["margin"] = save(fig, "fig04_margins.png")

# Fig 5: EPS
fig, ax = plt.subplots(figsize=(6.5, 2.6))
w = 0.38
ax.bar([i - w / 2 for i in x], G_EPS, w, color=LIGHT, label="GAAP diluted EPS")
ax.bar([i + w / 2 for i in x], NG_EPS, w, color=bar_colors(8), label="Non-GAAP diluted EPS")
for i in x:
    ax.text(i + w / 2, NG_EPS[i] + 0.015, f"${NG_EPS[i]:.2f}", ha="center", fontsize=7.2)
ax.set_xticks(list(x)); ax.set_xticklabels(QA); ax.set_ylabel("$ per share"); ax.set_ylim(0, 1.05)
ax.legend(loc="upper left")
charts["eps"] = save(fig, "fig05_eps.png")

# Fig 6: where results landed within the guidance range (Q2'26 vs Q3'26)
metrics = ["Revenue", "Billings", "Non-GAAP GM", "Non-GAAP OM", "Non-GAAP EPS"]
q2pos = [(2047.9 - 1830) / 100, (2372.1 - 2090) / 100, (80.9 - 79.5) / 1.0, (38.0 - 33.0) / 2.0, (0.90 - 0.72) / 0.04]
q3pos = [(2078.4 - 2010) / 90, (2336.3 - 2250) / 100, (79.6 - 79.0) / 2.0, (38.2 - 35.0) / 2.0, (0.91 - 0.83) / 0.04]
q2pos = [v * 100 for v in q2pos]; q3pos = [v * 100 for v in q3pos]
fig, ax = plt.subplots(figsize=(6.5, 2.8))
xm = range(len(metrics))
ax.bar([i - w / 2 for i in xm], q2pos, w, color=LIGHT, label="Q2'26A")
ax.bar([i + w / 2 for i in xm], q3pos, w, color=NAVY, label="Q3'26A")
for i in xm:
    ax.text(i - w / 2, q2pos[i] + 8, f"{q2pos[i]:.0f}%", ha="center", fontsize=7.2)
    ax.text(i + w / 2, q3pos[i] + 8, f"{q3pos[i]:.0f}%", ha="center", fontsize=7.2, color=NAVY)
ax.axhspan(0, 100, color=ORANGE, alpha=0.12, label="Guidance range (low to high end)")
ax.set_xticks(list(xm)); ax.set_xticklabels(metrics); ax.set_ylabel("Position vs. guidance range (%)")
ax.set_ylim(0, 560); ax.legend(loc="upper center", ncol=3)
charts["guidepos"] = save(fig, "fig09_results_vs_guidance_range.png")

# Fig 7: deferred revenue & inventory
fig, ax = plt.subplots(figsize=(6.5, 2.7))
ax.bar(x, DR_ST, color=BLUE, label="Short-term deferred revenue")
ax.bar(x, DR_LT, bottom=DR_ST, color=LIGHT, label="Long-term deferred revenue")
ax.set_xticks(list(x)); ax.set_xticklabels(QA); ax.set_ylabel("$M"); ax.set_ylim(0, 9500)
ax2 = ax.twinx(); ax2.plot(list(x), INV, color=RED, marker="o", lw=2, label="Inventory (rhs)")
for i in (6, 7):
    ax2.annotate(f"${INV[i]:.0f}M", (i, INV[i]), textcoords="offset points", xytext=(-4, 7), ha="center", fontsize=7.5, color=RED)
ax2.set_ylim(0, 700); ax2.set_ylabel("Inventory ($M)"); ax2.grid(False); ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", ncol=3)
charts["dr"] = save(fig, "fig06_deferred_revenue_inventory.png")

# Fig 8: FCF
fig, ax = plt.subplots(figsize=(6.5, 2.6))
ax.bar(x, FCF, color=bar_colors(8, GREEN, NAVY), label="Free cash flow ($M)")
for i in x:
    ax.text(i, FCF[i] + 15, f"${FCF[i]:,.0f}", ha="center", fontsize=7.5)
ax.set_xticks(list(x)); ax.set_xticklabels(QA); ax.set_ylabel("$M"); ax.set_ylim(0, 1300)
ax2 = ax.twinx(); ax2.plot(list(x), FCFM, color=ORANGE, marker="o", lw=1.8, label="FCF margin % (rhs)")
ax2.set_ylim(0, 70); ax2.set_ylabel("%"); ax2.grid(False); ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", ncol=2)
charts["fcf"] = save(fig, "fig07_free_cash_flow.png")

# Fig 9: FY26 guidance evolution
dates = ["Feb-26", "May-26", "Jul-26", "Oct-26"]
guide = {
    "FY26 revenue ($B)": [(7.500, 7.700), (7.710, 7.870), (8.020, 8.180), (8.125, 8.215)],
    "FY26 billings ($B)": [(8.400, 8.600), (8.800, 9.100), (9.350, 9.550), (9.568, 9.718)],
    "FY26 service revenue ($B)": [(5.050, 5.150), (5.090, 5.150), (5.180, 5.220), (5.150, 5.170)],
    "FY26 non-GAAP EPS ($)": [(2.94, 3.00), (3.10, 3.16), (3.41, 3.47), (3.54, 3.58)],
}
fig, axes = plt.subplots(1, 4, figsize=(6.6, 2.4))
for ax, (k, v) in zip(axes, guide.items()):
    mids = [(a + b) / 2 for a, b in v]
    err = [[m - a for (a, b), m in zip(v, mids)], [b - m for (a, b), m in zip(v, mids)]]
    col = RED if "service" in k else NAVY
    ax.errorbar(range(4), mids, yerr=err, fmt="o-", color=col, capsize=3, lw=1.6, ms=4)
    ax.set_xticks(range(4)); ax.set_xticklabels(dates, rotation=45, fontsize=7)
    ax.set_title(k, fontsize=8)
    ax.tick_params(axis="y", labelsize=7)
    fmt = "{:.2f}" if "EPS" in k else "{:.2f}"
    ax.annotate(fmt.format(mids[-1]), (3, mids[-1]), textcoords="offset points", xytext=(-14, 6), fontsize=7, color=col)
charts["guide"] = save(fig, "fig08_fy26_guidance_evolution.png")

# Fig 10: estimate revisions
fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.4))
pairs = [("Revenue ($B)", "Revenue ($M)", 1000), ("Service rev. ($B)", "  Service ($M)", 1000), ("Non-GAAP EPS ($)", "Non-GAAP EPS ($)", 1)]
for ax, (title, key, div) in zip(axes, pairs):
    e = EST[key]
    old = [e[1] / div, e[3] / div]; new = [e[2] / div, e[4] / div]
    ax.bar([-0.2, 0.8], old, 0.4, color=LIGHT, label="Prior est.")
    ax.bar([0.2, 1.2], new, 0.4, color=NAVY, label="New est.")
    for xx, val in zip([-0.2, 0.8, 0.2, 1.2], old + new):
        ax.text(xx, val * 1.01, f"{val:.2f}", ha="center", fontsize=6.8)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["FY26E", "FY27E"])
    lo = min(old + new) * 0.85
    ax.set_ylim(lo, max(old + new) * 1.06)
    ax.set_title(title, fontsize=8.5); ax.tick_params(labelsize=7)
axes[0].legend(loc="upper left", fontsize=7)
charts["revisions"] = save(fig, "fig10_estimate_revisions.png")

# Fig 11: trailing P/E history
prices = []
with open(os.path.join(BASE, "data", "ftnt_daily_close.csv")) as f:
    for row in csv.DictReader(f):
        prices.append((dt.date.fromisoformat(row["date"]), float(row["close"])))
rep_dates = sorted(EPS_HIST)
pe_dates, pe_vals = [], []
for d, p in prices:
    known = [rd for rd in rep_dates if rd < d]  # results known after report date
    if not known:
        continue
    n = len(known)
    seq = EPS_PRE + [EPS_HIST[rd] for rd in rep_dates[:n]]
    ttm = sum(seq[-4:])
    pe_dates.append(d); pe_vals.append(p / ttm)
ttm_now = sum(([EPS_HIST[rd] for rd in rep_dates])[-4:])
pe_ref = PX_REF / ttm_now
pe_mean = statistics.mean(pe_vals); pe_sd = statistics.pstdev(pe_vals)
pe_min, pe_max = min(pe_vals), max(pe_vals)
fig, ax = plt.subplots(figsize=(6.5, 2.7))
ax.plot(pe_dates, pe_vals, color=NAVY, lw=1.4, label="Price / trailing 4Q non-GAAP EPS")
ax.axhline(pe_mean, color=GRAY, ls="--", lw=1, label=f"2-yr average {pe_mean:.1f}x")
ax.axhline(pe_mean + pe_sd, color=GRAY, ls=":", lw=1, label="+/- 1 std. dev.")
ax.axhline(pe_mean - pe_sd, color=GRAY, ls=":", lw=1)
ax.scatter([dt.date(2026, 10, 29)], [pe_ref], color=ORANGE, zorder=5, s=30, label=f"Pre-market 10/29 (~${PX_REF:.0f}): {pe_ref:.1f}x")
ax.set_ylabel("P/E (x)"); ax.legend(loc="upper left", ncol=2)
charts["pe"] = save(fig, "fig11_trailing_pe.png")

# Fig 12: scenario valuation
scen = [("Bear", BEAR[0] * BEAR[1], RED, f"{BEAR[1]}x FY27E EPS ${BEAR[0]:.2f}"),
        ("Base (PT)", PT, NAVY, f"{PT_MULT}x FY27E EPS ${EPS27:.2f}"),
        ("Bull", BULL[0] * BULL[1], GREEN, f"{BULL[1]}x FY27E EPS ${BULL[0]:.2f}")]
fig, ax = plt.subplots(figsize=(6.5, 2.5))
for i, (lbl, val, col, note) in enumerate(scen):
    ax.barh(i, val, color=col, height=0.55)
    ax.text(val + 2, i, f"${val:.0f}  ({note})", va="center", fontsize=8)
ax.axvline(PX_REF, color=ORANGE, ls="--", lw=1.3, label=f"Pre-market ~${PX_REF:.0f}")
ax.axvline(PX_CLOSE, color=GRAY, ls=":", lw=1.3, label=f"10/28 close ${PX_CLOSE:.2f}")
ax.set_yticks(range(3)); ax.set_yticklabels([s[0] for s in scen]); ax.set_xlim(0, 260)
ax.set_xlabel("$ per share"); ax.legend(loc="lower right")
charts["scen"] = save(fig, "fig12_scenario_valuation.png")

# ----------------------------------------------------------------------------
# DOCX helpers
# ----------------------------------------------------------------------------
FONT = "Times New Roman"
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(0.85)
sec.top_margin = Inches(0.7); sec.bottom_margin = Inches(0.7)


def set_run_font(run, size=None, bold=None, italic=None, color=None):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FONT)
    if size: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if color: run.font.color.rgb = RGBColor.from_string(color)


for sname in ("Normal", "Heading 1", "Heading 2", "Heading 3", "Title"):
    st = doc.styles[sname]
    st.font.name = FONT
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
doc.styles["Normal"].font.size = Pt(10.5)
# document defaults: replace theme fonts with Times New Roman
_rpr_def = doc.styles.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
_rf = _rpr_def.find(qn("w:rFonts"))
if _rf is None:
    _rf = OxmlElement("w:rFonts"); _rpr_def.insert(0, _rf)
for _a in list(_rf.attrib):
    del _rf.attrib[_a]
for _a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
    _rf.set(qn(_a), FONT)
pf = doc.styles["Normal"].paragraph_format
pf.space_after = Pt(4); pf.space_before = Pt(0); pf.line_spacing = 1.05


def add_hyperlink(paragraph, text, url, size=None, bold=False):
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement("w:hyperlink"); h.set(qn("r:id"), r_id)
    r = OxmlElement("w:r"); rpr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FONT)
    rpr.append(rf)
    if bold:
        rpr.append(OxmlElement("w:b"))
    c = OxmlElement("w:color"); c.set(qn("w:val"), "0563C1"); rpr.append(c)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rpr.append(u)
    if size:
        sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size * 2))); rpr.append(sz)
    r.append(rpr)
    t = OxmlElement("w:t"); t.text = text; t.set(qn("xml:space"), "preserve"); r.append(t)
    h.append(r); paragraph._p.append(h)
    return h


def para(segments, size=None, bold=False, italic=False, align=None, after=None, before=None, color=None, keep=False):
    """segments: str or list of str / (text, url) / dict(text=, bold=, italic=)."""
    p = doc.add_paragraph()
    if isinstance(segments, str):
        segments = [segments]
    for s in segments:
        if isinstance(s, tuple):
            add_hyperlink(p, s[0], s[1], size=size)
        elif isinstance(s, dict):
            r = p.add_run(s["text"])
            set_run_font(r, size, s.get("bold", bold), s.get("italic", italic), s.get("color", color))
        else:
            r = p.add_run(s)
            set_run_font(r, size, bold, italic, color)
    if align == "center": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if align == "justify": p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None: p.paragraph_format.space_after = Pt(after)
    if before is not None: p.paragraph_format.space_before = Pt(before)
    if keep: p.paragraph_format.keep_with_next = True
    return p


def heading(text, level=1):
    size = {1: 13, 2: 11.5}[level]
    p = para(text, size=size, bold=True, color="1F3B6F", before=8 if level == 1 else 5, after=3, keep=True)
    if level == 1:
        pPr = p._p.get_or_add_pPr(); bdr = OxmlElement("w:pBdr"); b = OxmlElement("w:bottom")
        b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "6"); b.set(qn("w:space"), "1"); b.set(qn("w:color"), "1F3B6F")
        bdr.append(b); pPr.append(bdr)
    return p


def bullet(header, body_segments):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run("■ "); set_run_font(r, 10, True, color="1F3B6F")
    r = p.add_run(header + " "); set_run_font(r, 10.5, True)
    if isinstance(body_segments, str):
        body_segments = [body_segments]
    for s in body_segments:
        if isinstance(s, tuple):
            add_hyperlink(p, s[0], s[1])
        else:
            r = p.add_run(s); set_run_font(r, 10.5)
    return p


fig_no = [0]


def figure(path, title, source_segments, width=6.0):
    fig_no[0] += 1
    # caption and picture share one paragraph so they can never be split across pages
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(f"Figure {fig_no[0]} - {title}"); set_run_font(r, 9.5, True, color="1F3B6F")
    r.add_break(WD_BREAK.LINE)
    p.add_run().add_picture(path, width=Inches(width))
    para(["Source: "] + source_segments, size=8, italic=True, after=6)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor); tcPr.append(shd)


def table(rows, col_widths, header_rows=1, size=8.5, bold_first_col=False, title=None, source=None, keep=False):
    if title:
        para([{"text": title, "bold": True}], size=9.5, after=1, before=4, keep=True, color="1F3B6F")
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    for j, wd in enumerate(col_widths):
        t.columns[j].width = Inches(wd)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.width = Inches(col_widths[j])
            c.text = ""
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val))
            set_run_font(r, size, bold=(i < header_rows) or (bold_first_col and j == 0),
                         color="FFFFFF" if i < header_rows else None)
            if keep and i < len(rows) - 1:
                p.paragraph_format.keep_with_next = True
            if i < header_rows:
                shade(c, "1F3B6F")
            elif i % 2 == 0:
                shade(c, "EEF2F8")
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); trPr.append(cs)
    if source:
        para(["Source: "] + source, size=8, italic=True, after=6, before=2)
    return t


SRC_Q3 = [("Fortinet Q3 2026 8-K Ex. 99.1 (Oct 28, 2026)", U["q3_26"])]
SRC_HIST = [("Q4'24", U["q4_24"]), ", ", ("Q1'25", U["q1_25"]), ", ", ("Q2'25", U["q2_25"]), ", ",
            ("Q3'25", U["q3_25"]), ", ", ("Q4'25", U["q4_25"]), ", ", ("Q1'26", U["q1_26"]), ", ",
            ("Q2'26", U["q2_26"]), " and ", ("Q3'26", U["q3_26"]), " 8-K Ex. 99.1 earnings releases (SEC EDGAR)"]

# ----------------------------------------------------------------------------
# PAGE 1
# ----------------------------------------------------------------------------
para([{"text": "EQUITY RESEARCH  |  EARNINGS UPDATE  |  U.S. CYBERSECURITY", "bold": True}], size=8.5, color="7F7F7F", after=0)
para([{"text": "Fortinet, Inc. (NASDAQ: FTNT)", "bold": True}], size=17, color="1F3B6F", after=0)
para([{"text": "Q3 2026 EARNINGS UPDATE  |  October 29, 2026", "bold": True}], size=10.5, after=4)
para([{"text": "Clean Beat, Messy Mix: Price-Led Product Surge Cannot Offset a 13% Service Line; Maintain HOLD, $130 PT", "bold": True}],
     size=13.5, after=4)
para([{"text": "Rating: ", "bold": True}, "MAINTAIN HOLD    ",
      {"text": "12-month price target: ", "bold": True}, f"${PT} (34x FY27E non-GAAP EPS of ${EPS27:.2f})    ",
      {"text": "Price: ", "bold": True}, f"${PX_CLOSE:.2f} (Oct 28 close); ~${PX_REF:.0f} indicated pre-market Oct 29"],
     size=9.5, after=1)
para([{"text": "52-week range: ", "bold": True}, "$73.55 - $197.13    ",
      {"text": "Diluted shares: ", "bold": True}, f"{SHARES:.1f}M    ",
      {"text": "Mkt cap at ~$129: ", "bold": True}, f"~${PX_REF * SHARES / 1000:.0f}B    ",
      {"text": "Net cash (9/30/26): ", "bold": True}, f"${NET_CASH / 1000:.1f}B    ",
      {"text": "P/E FY26E/FY27E at ~$129: ", "bold": True}, f"{PX_REF / EPS26:.1f}x / {PX_REF / EPS27:.1f}x"],
     size=9.5, after=5)

table([
    ["Q3 2026: BEAT", "Reported", "Consensus", "Variance", "Guidance", "YoY"],
    ["Revenue ($M)", "2,078.4", "~2,060", "+~18 (+0.9%)", "2,010-2,100", "+20.5%"],
    ["  Product revenue ($M)", "765.0", "n/a", "n/a", "n/a", "+36.8%"],
    ["  Service revenue ($M)", "1,313.4", "n/a", "n/a", "n/a", "+12.7%"],
    ["Billings ($M)", "2,336.3", "~2,300", "+~36 (+1.6%)", "2,250-2,350", "+29.2%"],
    ["Non-GAAP gross margin", "79.6%", "n/a", "n/a", "79.0-81.0%", "-200 bps"],
    ["Non-GAAP operating margin", "38.2%", "36.1%", "+210 bps", "35.0-37.0%", "+130 bps"],
    ["Non-GAAP EPS ($)", "0.91", "0.86", "+0.05 (+5.8%)", "0.83-0.87", "+23.0%"],
    ["GAAP EPS ($)", "0.86", "n/a", "n/a", "n/a", "+38.7%"],
    ["Free cash flow ($M)", "864.8", "n/a", "n/a", "n/a", "+52.4%"],
], [2.0, 0.75, 0.75, 1.0, 0.95, 0.7], keep=True, title="Table 1 - Q3 2026 results vs. consensus and guidance",
    source=SRC_Q3 + ["; consensus per ", ("Investing.com", U["inv_tr"]), ", ", ("Seeking Alpha via TradingView", U["sa"]),
                     " and ", ("Tickeron", U["tickeron"]), " (pre-release, Oct 28, 2026; billings consensus approximate); prior guidance from ",
                     ("Q2'26 release", U["q2_26"]), ". n/a = no published consensus found."])

bullet("Every headline line beat, but the mix is what sold the stock.",
       ["Revenue of $2.078B beat consensus of ~$2.06B by ~$18M (0.9%) and non-GAAP EPS of $0.91 beat $0.86 by $0.05, "
        "with a record Q3 non-GAAP operating margin of 38.2% (+130 bps YoY, ~210 bps above the 36.1% consensus). Billings rose 29% to $2.336B "
        "and free cash flow rose 52% to $865M. Yet shares, which had already fallen 5.9% to $174.08 in the regular session, indicated ~25% lower "
        "after hours (~$129). The reason is composition: product revenue grew 37% while service revenue grew only 12.7%, "
        "and revenue and billings landed inside the guidance range rather than clearing the top end as in Q2."])
bullet("Service is the line that matters, and its outlook was trimmed.",
       ["FY26 service revenue guidance moved to $5.150-5.170B from $5.180-5.220B in July, a $40M cut at the midpoint, even as total revenue "
        "guidance rose $70M at the midpoint. CFO Christiane Ohlgart called the shortfall \"really a timing issue\" tied to ramped service activations "
        "on large enterprise wins, and pointed to 26% service billings growth and 14.5% short-term deferred revenue growth. She was careful to "
        "promise \"improved growth rates\" in 2027, not \"acceleration\"."])
bullet("Product strength is flattered by price and inventory; gross margin fell 200 bps.",
       ["Management said pricing contributed roughly 10 percentage points of YoY billings growth, and CEO Ken Xie said pricing has \"probably "
        "stabilized, but not improved yet.\" The inventory cushion that supported first-half shipments has faded and lead times are lengthening. "
        "Product gross margin (GAAP) dropped to 64.4% from 69.8% in Q2 and 67.7% a year ago as component costs rose, pulling non-GAAP gross "
        "margin to 79.6% (from 81.6%). On-hand inventory jumped 39% QoQ to $591M."])
bullet(f"Maintain HOLD; initiating a ${PT} 12-month PT.",
       [f"We lift FY26E non-GAAP EPS to ${EPS26:.2f} (from $3.48) on the Q3 beat and Q4 guide, but cut FY27E to ${EPS27:.2f} (from $3.95) "
        f"on a lower service base, slower product growth as pricing laps and gross margin pressure. Our ${PT} target equals {PT_MULT}x FY27E EPS, "
        f"cross-checked at ~27x FY27E EV/FCF. At ~${PX_REF:.0f}, FTNT still trades at {PX_REF / EPS26:.0f}x FY26E EPS. We want to see service revenue "
        "growth turn up before paying that multiple, so we stay on the sidelines despite the sell-off."])

e = EST


def fmt(v, key):
    if v is None:
        return "n/a"
    if "(%)" in key:
        return f"{v:.1f}%"
    if "EPS" in key:
        return f"{v:.2f}"
    return f"{v:,.0f}"


def chg(old, new, key):
    if "(%)" in key:
        return f"{(new - old) * 100:+.0f} bps"
    return f"{pct(new, old):+.1f}%"


rows = [["Our estimates", "FY25A", "FY26E Prior", "FY26E New", "Change", "FY27E Prior", "FY27E New", "Change"]]
for k, v in e.items():
    rows.append([k.strip() if not k.startswith("  ") else "   " + k.strip(), fmt(v[0], k), fmt(v[1], k), fmt(v[2], k), chg(v[1], v[2], k),
                 fmt(v[3], k), fmt(v[4], k), chg(v[3], v[4], k)])
rows.append(["P/E at ~$129 (x)", f"{PX_REF / 2.76:.1f}x", f"{PX_REF / 3.48:.1f}x", f"{PX_REF / EPS26:.1f}x", "", f"{PX_REF / 3.95:.1f}x",
             f"{PX_REF / EPS27:.1f}x", ""])
table(rows, [1.85, 0.6, 0.7, 0.7, 0.6, 0.7, 0.7, 0.6], size=8.2, keep=True,
      title="Table 2 - Updated financial estimates (old vs. new)",
      source=["FY25A from ", ("Q4'25 8-K Ex. 99.1", U["q4_25"]),
              "; FY26E/FY27E are our estimates (E). \"Prior\" = our pre-results model, which for FY26 was anchored near the July 29, 2026 guidance "
              "midpoints. FY25A non-GAAP gross margin not shown because pre-2026 releases did not reconcile it. Free cash flow per company definition."])

# ----------------------------------------------------------------------------
# DETAILED RESULTS
# ----------------------------------------------------------------------------
heading("Detailed Results: Revenue and Billings")
para("Total revenue grew 20.5% YoY to $2,078.4M, above the $2,055M guidance midpoint but $22M short of the $2,100M top end. That matters "
     "because Fortinet cleared the top of its revenue range by roughly $118M in Q2. Sequentially, revenue rose only 1.5% ($30.5M) after a 10.7% "
     "QoQ increase in Q2. Product revenue of $765.0M rose 36.8% YoY but slipped 1.0% QoQ from Q2's $773.0M, the first sequential product decline outside a "
     "seasonal first quarter in our eight-quarter data set. Service revenue rose 12.7% YoY to $1,313.4M (+3.0% QoQ), down from 13.7% "
     "growth in Q2 and back to the year-ago growth rate.", align="justify")
figure(charts["rev"], "Quarterly revenue by type and total YoY growth, Q4'24A-Q3'26A ($M)", SRC_HIST)
para("Billings rose 29.2% to $2,336.3M, inside the $2,250-2,350M range and ~$36M above the guidance midpoint, but down from 33.4% growth in Q2. "
     "Management highlighted that the total value of deals above $1M grew 51%, driven by U.S. large enterprise, that SASE Firewall billings "
     "grew 31%, OT billings grew nearly 40% and AI-driven security operations billings grew 15%. Our read is that demand is healthy at the top of the "
     "market. However, pricing explains a large part of the headline: Investor Relations clarified on the call that the list-price increases added "
     "around 10 percentage points to YoY billings growth. Ex-pricing, billings growth was closer to the high teens, which is solid but "
     "not the 29% headline.", align="justify")
figure(charts["bill"], "Quarterly billings and YoY growth ($M)", SRC_HIST + ["; billings are non-GAAP (revenue plus change in deferred revenue)"])
para("The chart below is the core of the bear argument. Product growth went from low double digits in early 2025 to 52% in Q2'26 on the firewall "
     "refresh, price increases and a large on-hand inventory position, while service growth went the other way, from 17% in Q4'24 to an "
     "11.5% trough in Q1'26. The Q3 service print (12.7%) supports management's claim that Q1 was the trough, but the recovery is shallow. Service "
     "carries ~87% gross margins and is the recurring revenue the market pays a premium multiple for. A product-led mix lowers both "
     "earnings quality and gross margin.", align="justify")
figure(charts["growth"], "Product vs. service revenue YoY growth: the divergence", SRC_HIST + ["; growth rates computed by us from reported figures"])

heading("Profitability: Operating Leverage Up, Gross Margin Down")
para("Non-GAAP gross margin was 79.6%, down 200 bps YoY and 130 bps QoQ, and below the 80.0% guidance midpoint. The pressure is entirely "
     "in product: GAAP product gross margin fell to 64.4% from 69.8% in Q2'26 and 67.7% in Q3'25, while service gross margin improved to 87.4% "
     "(87.0% a year ago). Ohlgart said that \"in the second half, you see that the costs are creeping up and then impacting the product gross "
     "margin.\" Xie reiterated that the policy is to hold gross margin steady through pricing, but the Q4 guide of 78-80% non-GAAP gross margin "
     "implies another step down at the midpoint, and the price increases have now largely been taken.", align="justify")
para("Operating leverage more than offset the gross margin decline. Non-GAAP operating margin reached 38.2% (+130 bps YoY), above the "
     "35-37% guidance range, as sales and marketing grew 14.0% and R&D 5.4% against 20.5% revenue growth. GAAP operating margin was 33.9% vs. 31.7%. "
     "Non-GAAP EPS of $0.91 (+23%) also benefited from a 2.4% lower diluted share count (742.6M vs. 761.2M) after 2025 buybacks. GAAP EPS of $0.86 "
     "(+39%) included a $17.0M escrow settlement gain that is excluded from non-GAAP results and from free cash flow.", align="justify")
figure(charts["margin"], "Gross margin by type (GAAP) and non-GAAP operating margin (%)", SRC_HIST + ["; segment gross margins computed by us"])
figure(charts["eps"], "Quarterly GAAP and non-GAAP diluted EPS ($)", SRC_HIST)

# ----------------------------------------------------------------------------
# KEY METRICS
# ----------------------------------------------------------------------------
heading("Key Metrics: Deferred Revenue, Inventory and Cash")
para("Total deferred revenue reached $7,934.4M, up 19.3% YoY and $258.7M QoQ. The mix matters for 2027 service revenue: short-term deferred revenue "
     "(recognized within 12 months) grew 14.5% to $3,961.0M, the fastest rate in five quarters according to management, while long-term deferred "
     "revenue grew 24.6% to $3,973.4M. Ohlgart framed short-term deferred revenue as \"a good indicator for future service revenue growth\" and said "
     "contract duration was \"pretty similar\" to prior periods. We take the 14.5% short-term figure as the realistic ceiling for 2027 service growth, "
     "consistent with an \"improved\" rate vs. 2026's ~13%, but not a step change. The faster long-term growth means more of the billings strength is "
     "deferred beyond 2027.", align="justify")
para("Inventory rose to $591.2M from $426.3M at the end of Q2 (+$165M, +39% QoQ), while accounts payable rose to $430.3M from $230.8M at "
     "year-end. Xie said Fortinet normally holds about six months of inventory on hand, that the buffer supported first-half product shipments, "
     "and that this normalized from Q3. He also said component lead times are getting longer. We read the balance sheet build as Fortinet "
     "rebuilding stock at higher input costs. That supports supply continuity but will run through product cost of goods in coming quarters.",
     align="justify")
figure(charts["dr"], "Deferred revenue (short- and long-term) and inventory ($M, period-end)", SRC_HIST + [" (condensed consolidated balance sheets)"])
para("Cash generation remains the strongest part of the story. Operating cash flow was $946.0M and free cash flow $864.8M (41.6% margin, +52% YoY), "
     "taking year-to-date free cash flow to $2.84B (+74%). The Board added $1.2B to the repurchase authorization, leaving $2.0B available. Note that "
     "nine-month repurchases of $972.8M were all executed in the first half: Q3 financing outflow was only $18.2M. Cash and investments were "
     f"$5.3B against $497M of debt, or ~${NET_CASH / 1000:.1f}B of net cash (~${NET_CASH / SHARES:.1f} per diluted share). At ~$129 the authorization "
     "equals roughly 2% of the market capitalization.", align="justify")
figure(charts["fcf"], "Quarterly free cash flow and FCF margin", SRC_HIST + ["; FCF per company definition (Q3'26 excludes $17.0M escrow proceeds)"])

# ----------------------------------------------------------------------------
# GUIDANCE
# ----------------------------------------------------------------------------
heading("Guidance and Outlook")
para("Fortinet raised full-year revenue, billings, operating margin and EPS guidance for the third time this year, but trimmed service revenue "
     "and narrowed gross margin. The Q4 guide implies a sharp deceleration: revenue growth of ~15.5% at the $2.200B midpoint (vs. 20.5% in Q3) and "
     "billings growth of ~20% at the $2.850B midpoint (vs. 29%). The full-year service guide implies Q4 service revenue of $1.357-1.377B, or 11.8-13.5% "
     "growth. Q4 EPS guidance of $0.93-0.95 is well above the $0.88 pre-release consensus cited by Seeking Alpha, and the $2.155-2.245B revenue range "
     "brackets the $2.17B consensus.", align="justify")
table([
    ["Guidance item", "New (Oct 28)", "Prior (Jul 29)", "Change at mid", "Street (pre-release)"],
    ["Q4'26 revenue", "$2.155-2.245B", "n/a", "n/a", "$2.17B"],
    ["Q4'26 billings", "$2.775-2.925B", "n/a", "n/a", "n/a"],
    ["Q4'26 non-GAAP GM / OM", "78-80% / 35.5-37.5%", "n/a", "n/a", "n/a"],
    ["Q4'26 non-GAAP EPS", "$0.93-0.95", "n/a", "n/a", "$0.88"],
    ["FY26 revenue", "$8.125-8.215B", "$8.020-8.180B", "+$70M (raised)", "~$8.12B (Oct 6)"],
    ["FY26 service revenue", "$5.150-5.170B", "$5.180-5.220B", "-$40M (lowered)", "n/a"],
    ["FY26 billings", "$9.568-9.718B", "$9.350-9.550B", "+$193M (raised)", "n/a"],
    ["FY26 non-GAAP GM", "79.7-80.3%", "79.0-81.0%", "Narrowed", "n/a"],
    ["FY26 non-GAAP OM", "36.5-37.5%", "35.0-37.0%", "+100 bps (raised)", "n/a"],
    ["FY26 non-GAAP EPS", "$3.54-3.58", "$3.41-3.47", "+$0.12 (raised)", "n/a"],
], [1.6, 1.35, 1.2, 1.15, 1.2], keep=True, title="Table 3 - Management guidance: new vs. prior vs. Street",
    source=SRC_Q3 + ["; prior guidance from ", ("Q2 2026 8-K Ex. 99.1 (Jul 29, 2026)", U["q2_26"]),
                     "; Street Q4 figures per ", ("Seeking Alpha via TradingView", U["sa"]), "; FY26 revenue consensus as of Oct 6, 2026 per ",
                     ("Hudson Labs", U["hudson"]), ". n/a = not provided or not found."])
para("On 2027, management did not give guidance (\"still 3 months early,\" per Xie) but said total billings and revenue growth should outpace the "
     "addressable market and that \"our 2027 service revenue is expected to grow at a higher rate compared to 2026.\" Asked directly, Ohlgart "
     "said: \"I haven't used the word acceleration. I've used the word improved growth rates.\" We model 14% FY27E service growth, in line with "
     "the short-term deferred revenue trajectory, and only 5% product growth as the pricing benefit laps and the refresh wave matures.",
     align="justify")
figure(charts["guide"], "Evolution of FY26 guidance midpoints and ranges (service revenue in red)",
       [("Q4'25", U["q4_25"]), ", ", ("Q1'26", U["q1_26"]), ", ", ("Q2'26", U["q2_26"]), " and ", ("Q3'26", U["q3_26"]),
        " 8-K Ex. 99.1 earnings releases (guidance sections)"])
figure(charts["guidepos"], "Where results landed within the guidance range: Q2'26 vs. Q3'26 (0% = low end, 100% = high end)",
       [("Q1'26", U["q1_26"]), " and ", ("Q2'26", U["q2_26"]), " releases (guidance); ", ("Q2'26", U["q2_26"]), " and ",
        ("Q3'26", U["q3_26"]), " releases (actuals); our calculations"])
para("Figure 9 shows why the market reacted as it did. In Q2 every metric cleared the top of its range by a wide margin (revenue at 218% of the "
     "range, billings at 282%). In Q3, revenue (76%) and billings (86%) landed inside the range and gross margin finished in the lower third. "
     "Only operating margin and EPS, which benefit from cost discipline and a lower share count, beat the top end. For a stock that had more "
     "than doubled from its 52-week low, an in-range top line was not enough.", align="justify")

# ----------------------------------------------------------------------------
# CALL TAKEAWAYS
# ----------------------------------------------------------------------------
heading("Earnings Call: What Management Said")
bullet("Service timing.", ["Ohlgart attributed the service shortfall to \"headwinds from winning new large enterprise customers with ramp service "
       "activations\" and enterprise agreements that consolidated existing services: \"It's just a little bit of a delay from when it gets "
       "recognized.\" She reiterated that \"the first quarter of 2026 marked the trough for our services revenue growth rate\" (",
       ("Motley Fool transcript", U["fool"]), ")."])
bullet("Pricing.", ["Xie first said pricing has \"about 10% benefit on the top line\"; VP Investor Relations Anthony Luscri later corrected this to "
       "\"around a 10 percentage point impact to year-over-year billings growth, not top line.\" Xie added that pricing has \"probably stabilized, "
       "but not improved yet\" (", ("Investing.com transcript", U["inv_tr"]), ")."])
bullet("Hardware life cycles.", ["Xie acknowledged that some lower-end and retail customers are holding hardware longer, but argued that \"if "
       "you're keeping the hardware like 5, 7, 10 years longer, a lot of function kind of difficult to run,\" and does not expect the stretching "
       "to last. Ohlgart said some U.S. customers are timing hardware purchases for tax depreciation reasons."])
bullet("Channel and duration.", ["Ohlgart said channel inventory is flat to down as a percentage of billings and that billings duration \"didn't "
       "increase significantly,\" which argues against a channel-stuffing explanation for product strength."])
bullet("Analyst focus.", ["Questions centered on 2027 product growth against a tough comparison (Barclays), Q3 deceleration and supply (Stifel), "
       "service attach rates (Jefferies), large-enterprise ramp deals (Goldman Sachs), hardware life extension and gross margin vs. higher prices "
       "(Citi), and the service model for sovereign and neocloud customers and confidence in 2027 service growth (Raymond James)."])

# ----------------------------------------------------------------------------
# THESIS
# ----------------------------------------------------------------------------
heading("Investment Thesis Update")
bullet("Pillar 1 - Networking-security convergence keeps Fortinet a share gainer. Status: UNCHANGED.",
       ["SASE Firewall billings grew 31%, which Xie said is nearly double the market growth rate. OT billings grew nearly 40% and $1M+ deal value grew 51%. "
        "Fortinet was again named a Leader in Gartner's 2026 Hybrid Mesh Firewall Magic Quadrant and added sovereign-cloud partnerships with "
        "Microsoft and Oracle. Competitive position is not the issue. The question is how much of the 2026 product surge was a one-time "
        "combination of refresh timing, pricing and inventory availability. Arete's October 21 double downgrade made exactly this argument, citing "
        "5-20% list-price increases as a non-recurring tailwind and a fading 2020-21 refresh cohort."])
bullet("Pillar 2 - Service revenue compounds at a mid-teens rate. Status: WEAKENED.",
       ["This was the pillar the quarter was meant to repair, and it did not. Service revenue grew 12.7%, the FY26 service guide fell $40M at the "
        "midpoint, and Q4 implies 11.8-13.5% growth. The leading indicators are better (service billings +26%, short-term deferred +14.5%), and "
        "management's activation-timing explanation is plausible for large enterprise deals. But the language for 2027 was deliberately modest. "
        "Mix is also becoming a structural question: sovereign, neocloud and large networking-heavy deployments may carry lower service attach than "
        "the core FortiGate-plus-FortiGuard bundle. We need to see quarterly service growth back above 14% before restoring this pillar."])
bullet("Pillar 3 - Industry-leading margins are durable. Status: WEAKENED (gross) / STRENGTHENED (operating).",
       ["Operating discipline is excellent: a record 38.2% Q3 non-GAAP operating margin and FY26 guidance raised to 36.5-37.5%. Gross margin is "
        "moving the other way. Product gross margin fell 540 bps QoQ and the Q4 guide implies non-GAAP gross margin of 78-80%. With memory and "
        "component costs rising, lead times lengthening, $591M of inventory bought at higher prices and pricing \"stabilized, but not improved,\" "
        "we model FY27E non-GAAP gross margin of 79.0% and operating margin of 36.0%, below the FY26E level."])
bullet("Pillar 4 - Cash generation funds steady capital return. Status: STRENGTHENED.",
       ["Year-to-date FCF of $2.84B (+74%), $4.8B of net cash and a $2.0B buyback authorization give real downside support, and a lower share count "
        "flatters EPS. Deferred revenue growth of 19% means a large share of 2026 billings converts to cash before it shows up as revenue. "
        "The buyback pause in Q3 means Fortinet has room to step in at lower prices."])

heading("Risks to Our View", level=2)
para([{"text": "Upside risks: ", "bold": True},
      "service growth re-accelerates toward the 14.5% short-term deferred revenue rate as delayed activations go live in Q4 and Q1; pricing proves stickier "
      "than we assume; AI-infrastructure and sovereign security demand broadens; Fortinet uses its $2.0B authorization aggressively at depressed prices.  ",
      {"text": "Downside risks: ", "bold": True},
      "product revenue declines YoY in 2027 as pricing and refresh tailwinds lap (Arete's sell case); memory and component inflation compresses product "
      "gross margin further; extended hardware life cycles spread from low-end and retail into the mid-market; service attach falls with "
      "networking-heavy mix. Post-close reports of a possible breach disclosure circulated on October 28 but were unverified at the time of writing (",
      ("Investing.com", U["inv_plunge"]), ")."], align="justify")

# ----------------------------------------------------------------------------
# VALUATION
# ----------------------------------------------------------------------------
heading("Valuation and Price Target")
para([f"Our ${PT} 12-month price target equals {PT_MULT}x FY27E non-GAAP EPS of ${EPS27:.2f}. We use a forward P/E because Fortinet is highly profitable "
      "and the debate is about the durability of earnings growth. We cross-check with EV/FCF: 27x FY27E free cash flow of "
      f"${FCF27 / 1000:.2f}B gives an equity value of ~${(27 * FCF27 + NET_CASH) / SHARES:.0f} per share after adding ~${NET_CASH / 1000:.1f}B of net cash. "
      f"The 34x multiple is a ~15% discount to the stock's two-year average trailing P/E of {pe_mean:.1f}x (range {pe_min:.0f}x-{pe_max:.0f}x). "
      "We think a discount is warranted because FY27E EPS growth of ~6% is well below the ~30% delivered in FY26E, and the mix is shifting "
      f"toward lower-margin, less recurring product revenue. At ~${PX_REF:.0f} pre-market the stock trades at {PX_REF / EPS26:.1f}x FY26E and "
      f"{PX_REF / EPS27:.1f}x FY27E EPS, and {pe_ref:.1f}x trailing EPS, close to the two-year average. Our target implies ~{pct(PT, PX_REF):.0f}% upside "
      "from the indicated pre-market level, which is consistent with a HOLD."], align="justify")
para("For context, the Street went into the print split: MarketBeat showed a consensus Hold with an average target of $162.36 (range $117-225; "
     "1 Strong Buy, 11 Buy, 21 Hold, 6 Sell) as of October 23. Notable pre-print actions included TD Cowen (Buy, $225), JPMorgan (Underweight, "
     "raised to $140 from $118) and Arete (double downgrade to Sell, $117). We expect Street targets to fall toward the low-to-mid $100s after "
     "the reset.", align="justify")
figure(charts["revisions"], "Estimate revisions: prior vs. new (FY26E and FY27E)",
       ["Our estimates; FY26E new estimates incorporate ", ("Q3'26 results and Q4'26 guidance", U["q3_26"])])
figure(charts["pe"], "FTNT price / trailing four-quarter non-GAAP EPS, Nov 2024 - Oct 2026",
       [("Yahoo Finance daily closes", U["yahoo"]), "; non-GAAP EPS from ", ("Q3'24-Q3'26 earnings releases", U["edgar_list"]),
        "; pre-market price indicative (Oct 29, 2026); our calculations"])
para([{"text": "Scenario analysis. ", "bold": True},
      f"Bear (${BEAR[0] * BEAR[1]:.0f}): product revenue declines YoY in 2027, service grows ~11%, operating margin falls to ~34.5%, giving FY27E EPS of "
      f"~${BEAR[0]:.2f} at {BEAR[1]}x. Base (${PT}): our estimates at {PT_MULT}x. Bull (${BULL[0] * BULL[1]:.0f}): service growth reaches ~16% as activations "
      f"go live, product grows ~12% on AI and sovereign demand, operating margin holds at ~37%, giving ~${BULL[0]:.2f} at {BULL[1]}x. The skew from "
      f"~${PX_REF:.0f} is roughly balanced (-{abs(pct(BEAR[0] * BEAR[1], PX_REF)):.0f}% / +{pct(BULL[0] * BULL[1], PX_REF):.0f}%), so we see no reason to buy "
      "the dip until service growth shows a sustained turn. An upgrade trigger would be quarterly service growth of at least 14% with stable "
      "product gross margin. A downgrade trigger would be a YoY product revenue decline before service has re-accelerated."],
     align="justify")
figure(charts["scen"], "12-month scenario values vs. current price ($ per share)",
       ["Our estimates; prices from ", ("Yahoo Finance", U["yahoo"]), " (Oct 28 close; Oct 29 indicative pre-market)"])

# ----------------------------------------------------------------------------
# SOURCES
# ----------------------------------------------------------------------------
heading("Sources and References")
src = [
    ("Earnings materials (Q3 2026)", [
        ("Fortinet Q3 2026 earnings release, 8-K Exhibit 99.1 (Oct 28, 2026), SEC EDGAR", U["q3_26"]),
        ("Fortinet Q3 2026 8-K filing index (Oct 28, 2026), SEC EDGAR", U["q3_26_idx"]),
        ("\"Fortinet Reports Strong Third Quarter 2026 Financial Results\", Fortinet Investor Relations (Oct 28, 2026)", U["pr"]),
        ("Fortinet Q3 2026 earnings call transcript, The Motley Fool (Oct 29, 2026)", U["fool"]),
        ("Fortinet Q3 2026 earnings call transcript, Investing.com (Oct 28, 2026)", U["inv_tr"]),
    ]),
    ("Prior periods and prior guidance (SEC EDGAR)", [
        ("Q2 2026 earnings release, 8-K Ex. 99.1 (Jul 29, 2026) - prior FY26 guidance", U["q2_26"]),
        ("Q2 2026 Form 10-Q (filed Jul 30, 2026)", U["10q_q2"]),
        ("Q1 2026 earnings release, 8-K Ex. 99.1 (May 6, 2026)", U["q1_26"]),
        ("Q4 and FY2025 earnings release, 8-K Ex. 99.1 (Feb 5, 2026)", U["q4_25"]),
        ("Q3 2025 earnings release, 8-K Ex. 99.1 (Nov 5, 2025)", U["q3_25"]),
        ("Q2 2025 earnings release, 8-K Ex. 99.1 (Aug 6, 2025)", U["q2_25"]),
        ("Q1 2025 earnings release, 8-K Ex. 99.1 (May 7, 2025)", U["q1_25"]),
        ("Q4 and FY2024 earnings release, 8-K Ex. 99.1 (Feb 6, 2025)", U["q4_24"]),
        ("Fortinet 8-K filing list, SEC EDGAR", U["edgar_list"]),
    ]),
    ("Consensus, market data and Street commentary", [
        ("\"Fortinet falls despite strong Q3 results and higher guidance\", Seeking Alpha via TradingView (Oct 28, 2026) - EPS, revenue, op. margin and Q4 consensus", U["sa"]),
        ("\"Fortinet (FTNT) Delivers Q3 Beat and Raises Guidance but Shares Drop More Than 20%\", Tickeron (Oct 2026) - billings consensus (approx.), Oct 28 close", U["tickeron"]),
        ("\"Why is Fortinet stock plunging today?\", Investing.com (Oct 28, 2026) - after-hours move", U["inv_plunge"]),
        ("\"Fortinet (FTNT) - Q3 2026 Earnings Preview\", Hudson Labs (Oct 6, 2026) - FY26 revenue consensus", U["hudson"]),
        ("\"Fortinet stock falls as Arete delivers rare double downgrade to sell\", Investing.com (Oct 21, 2026)", U["arete"]),
        ("MarketBeat, JPMorgan price target note and consensus rating summary (Oct 23, 2026)", U["mb_jpm"]),
        ("Yahoo Finance FTNT historical prices (accessed Oct 29, 2026)", U["yahoo"]),
    ]),
]
for grp, items in src:
    para([{"text": grp, "bold": True}], size=9.5, after=1, before=3)
    for text, url in items:
        p = para(["• ", (text, url)], size=9, after=1)
        p.paragraph_format.left_indent = Inches(0.2)

para([{"text": "Notes on data. ", "bold": True},
      "All Fortinet financial figures come from company 8-K exhibits; growth rates, segment gross margins, guidance positions and P/E history are our "
      "calculations. The Q3 2026 Form 10-Q had not been filed at the time of writing, so balance sheet detail is from the condensed statements in the "
      "release. Consensus figures come from media aggregators rather than a primary data terminal. The billings consensus (~$2.30B) is approximate and "
      "matches the guidance midpoint. The pre-market price (~$129) is indicative and was moving at the time of writing. All FY26E/FY27E figures, "
      "scenario values and the price target are our estimates. \"Prior\" estimates are from our internal pre-results model and were not "
      "previously published."], size=8.5, align="justify", before=4)
para([{"text": "Disclosures. ", "bold": True},
      "This report is for informational purposes only and is not an offer or solicitation to buy or sell any security. Ratings: BUY (expected total return "
      ">15% over 12 months), HOLD (-10% to +15%), SELL (<-10%). Estimates and opinions are as of the date of this report and may change without notice."],
     size=8.5, align="justify")

# Footer with page numbers
footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = footer.add_run("Fortinet (FTNT) Q3 2026 Earnings Update  |  October 29, 2026  |  Page "); set_run_font(r, 8, color="7F7F7F")
r = footer.add_run(); set_run_font(r, 8, color="7F7F7F")
for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
    if tag:
        fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), tag); r._r.append(fc)
    else:
        it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._r.append(it)

doc.core_properties.title = "Fortinet (FTNT) Q3 2026 Earnings Update"
doc.core_properties.author = "Equity Research"
doc.save(OUT)
print("Saved", OUT)
print(f"Figures: {fig_no[0]} | trailing P/E mean {pe_mean:.1f}x sd {pe_sd:.1f} min {pe_min:.1f} max {pe_max:.1f} ref {pe_ref:.1f}x (TTM EPS {ttm_now:.2f})")
