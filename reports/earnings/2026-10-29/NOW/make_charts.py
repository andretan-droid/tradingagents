"""Chart generation for ServiceNow (NOW) Q3 2026 earnings update.

All reported figures come from ServiceNow earnings releases (Form 8-K Ex. 99.1) on SEC EDGAR.
Figures labelled "E" or "est." are our estimates. Per-share data are on a post-split basis
(5-for-1 split effective December 17, 2025), as restated by the company.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "-",
    "legend.frameon": False,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "text.parse_math": False,
})

NAVY = "#1F3A5F"
TEAL = "#3A7CA5"
LIGHT = "#A9C6DE"
GREY = "#8C8C8C"
RED = "#B23A3A"
GREEN = "#2E7D4F"
GOLD = "#C9962B"
FIG = (6.6, 2.75)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name))
    plt.close(fig)


def label_bars(ax, bars, fmt, dy=0, size=8, color="black"):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + dy, fmt.format(h),
                ha="center", va="bottom", fontsize=size, color=color)


# ---------------------------------------------------------------- data (reported)
Q = ["Q1'25", "Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26", "Q3'26"]
sub_rev = [3005, 3113, 3299, 3466, 3671, 3877, 3988]
sub_yoy = [None, None, 21.5, 21.0, 22.0, 24.5, 21.0]
ng_om = [31.0, 29.5, 33.5, 31.0, 32.0, 29.5, 32.5]
gaap_om = [14.5, 11.0, 17.0, 12.5, 13.5, 4.0, 9.5]
ng_eps = [0.81, 0.81, 0.95, 0.92, 0.97, 0.90, 1.00]
gaap_eps = [0.44, 0.37, 0.48, 0.38, 0.45, 0.29, 0.27]
fcf = [1477, 535, 592, 2032, 1665, 634, 822]
fcf_m = [48.0, 16.5, 17.5, 57.0, 44.0, 16.0, 20.0]

# ---------------------------------------------------------------- Fig 1 subscription revenue
fig, ax = plt.subplots(figsize=FIG)
x = np.arange(len(Q) + 1)
bars = ax.bar(x[:-1], sub_rev, color=[LIGHT] * 6 + [NAVY], width=0.62)
gb = ax.bar(x[-1], 4250, color="white", edgecolor=NAVY, hatch="///", width=0.62)
label_bars(ax, list(bars) + list(gb), "{:,.0f}", dy=30, size=7.5)
ax.set_xticks(x)
ax.set_xticklabels(Q + ["Q4'26G"])
ax.set_ylabel("Subscription revenue ($M)")
ax.set_ylim(0, 7000)
ax2 = ax.twinx()
yy = [v for v in sub_yoy] + [22.75]
xs = [i for i, v in enumerate(yy) if v is not None]
ax2.plot(xs, [yy[i] for i in xs], color=GOLD, marker="o", lw=1.8, label="YoY growth (GAAP, %)")
for i in xs:
    ax2.text(i, yy[i] + 0.45, f"{yy[i]:.1f}%", ha="center", fontsize=7.5, color=GOLD)
ax2.set_ylim(4, 27)
ax2.set_ylabel("YoY growth (%)")
ax2.grid(False)
ax2.spines["top"].set_visible(False)
ax2.legend(loc="upper left")
ax.set_title("Subscription revenue: Q3'26 $3,988M (+21% YoY); Q4'26 guide $4,245-4,255M")
save(fig, "fig01_subscription_revenue.png")

# ---------------------------------------------------------------- Fig 2 cRPO
fig, ax = plt.subplots(figsize=FIG)
cq = ["Q2'25", "Q3'25", "Q4'25", "Q1'26", "Q2'26", "Q3'26", "Q4'26G"]
crpo = [10.92, 11.35, 12.85, 12.64, 13.20, 13.65]
crpo_cc = [21.5, 20.5, 21.0, 21.0, 21.5, 21.0, 18.5]
guide_cc = [None, 18.0, 19.0, 20.0, 19.5, 20.0, None]
x = np.arange(len(cq))
bars = ax.bar(x[:-1], crpo, color=[LIGHT] * 5 + [NAVY], width=0.6)
label_bars(ax, bars, "${:.2f}B", dy=0.15, size=7.5)
ax.set_ylim(0, 24)
ax.set_ylabel("cRPO ($B)")
ax.set_xticks(x)
ax.set_xticklabels(cq)
ax2 = ax.twinx()
ax2.plot(x, crpo_cc, color=GOLD, marker="o", lw=1.8, label="cRPO growth, constant currency (%)")
gx = [i for i, v in enumerate(guide_cc) if v is not None]
ax2.scatter(gx, [guide_cc[i] for i in gx], marker="_", s=260, color=RED, lw=2,
            label="Prior-quarter cc guide (%)", zorder=5)
for i, v in enumerate(crpo_cc):
    ax2.text(i + 0.12, v + 0.35, f"{v:.1f}%", fontsize=7.5, color=GOLD)
ax2.set_ylim(8, 23.5)
ax2.set_ylabel("Growth (%)")
ax2.grid(False)
ax2.spines["top"].set_visible(False)
ax2.legend(loc="upper center", fontsize=7.5, ncol=2, bbox_to_anchor=(0.5, -0.12))
ax.set_title("cRPO beat the cc guide by 100bp in Q3, but the Q4 guide steps down to 18.5% cc")
save(fig, "fig02_crpo.png")

# ---------------------------------------------------------------- Fig 3 margins
fig, ax = plt.subplots(figsize=FIG)
mq = Q + ["Q4'26G"]
x = np.arange(len(mq))
ax.plot(x, ng_om + [32.0], color=NAVY, marker="o", lw=2, label="Non-GAAP operating margin")
ax.plot(x, gaap_om + [12.0], color=TEAL, marker="s", lw=2, ls="--", label="GAAP operating margin")
for i, (a, b) in enumerate(zip(ng_om + [32.0], gaap_om + [12.0])):
    ax.text(i, a + 1.2, f"{a:.1f}%", ha="center", fontsize=7.5, color=NAVY)
    ax.text(i, b - 3.4, f"{b:.1f}%", ha="center", fontsize=7.5, color=TEAL)
ax.axvspan(len(mq) - 1.5, len(mq) - 0.5, color=GREY, alpha=0.12)
ax.set_xticks(x)
ax.set_xticklabels(mq)
ax.set_ylim(-2, 40)
ax.set_ylabel("% of revenue")
ax.legend(loc="center left", fontsize=8)
ax.set_title("Operating margin: non-GAAP 32.5% (-100bp YoY); GAAP 9.5% after deal-related costs")
save(fig, "fig03_operating_margins.png")

# ---------------------------------------------------------------- Fig 4 EPS
fig, ax = plt.subplots(figsize=FIG)
x = np.arange(len(Q))
w = 0.38
b1 = ax.bar(x - w / 2, ng_eps, w, color=NAVY, label="Non-GAAP diluted EPS")
b2 = ax.bar(x + w / 2, gaap_eps, w, color=LIGHT, label="GAAP diluted EPS")
for b in b1:
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() - 0.09, f"${b.get_height():.2f}", ha="center", fontsize=7, color="white")
label_bars(ax, b2, "${:.2f}", dy=0.015, size=7.5)
ax.scatter([x[-1] - w / 2], [1.02], marker="D", color=RED, zorder=5, s=28,
           label="Q3'26 consensus non-GAAP EPS ($1.02)")
ax.set_xticks(x)
ax.set_xticklabels(Q)
ax.set_ylim(0, 1.25)
ax.set_ylabel("$ per share (post-split)")
ax.legend(loc="upper left", fontsize=7.5, ncol=3)
ax.set_title("Non-GAAP EPS $1.00 (+5% YoY) missed $1.02 consensus; GAAP EPS fell to $0.27")
save(fig, "fig04_eps.png")

# ---------------------------------------------------------------- Fig 5 FCF
fig, ax = plt.subplots(figsize=FIG)
x = np.arange(len(Q))
bars = ax.bar(x, fcf, color=[LIGHT] * 6 + [NAVY], width=0.6)
label_bars(ax, bars, "${:,.0f}", dy=30, size=7.5)
ax.set_ylabel("Free cash flow ($M)")
ax.set_ylim(0, 3300)
ax.set_xticks(x)
ax.set_xticklabels(Q)
ax2 = ax.twinx()
ax2.plot(x, fcf_m, color=GOLD, marker="o", lw=1.8, label="FCF margin (%)")
ax2.set_ylim(-70, 70)
ax2.set_yticks([0, 20, 40, 60])
for i, v in enumerate(fcf_m):
    ax2.text(i, v + 4, f"{v:.1f}%", ha="center", fontsize=7.5, color=GOLD)
ax2.set_ylabel("FCF margin (%)")
ax2.grid(False)
ax2.spines["top"].set_visible(False)
ax2.legend(loc="upper center", ncol=1, fontsize=7.5, bbox_to_anchor=(0.5, -0.12))
ax.set_title("Q3 FCF $822M (20% margin) vs. $592M; FY26 FCF margin target raised to 36%")
save(fig, "fig05_fcf.png")

# ---------------------------------------------------------------- Fig 6 beat/miss scorecard
fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.6, 2.6), gridspec_kw={"width_ratios": [1, 1.15]})
lab = ["Subscription rev.\nvs. guide mid", "Total revenue\nvs. consensus", "Non-GAAP EPS\nvs. consensus"]
val = [(3988 / 3977.5 - 1) * 100, (4106 / 4095 - 1) * 100, (1.00 / 1.02 - 1) * 100]
cols = [GREEN if v >= 0 else RED for v in val]
bb = axa.barh(lab, val, color=cols, height=0.55)
for b, v in zip(bb, val):
    axa.text(v + (0.08 if v >= 0 else -0.08), b.get_y() + b.get_height() / 2, f"{v:+.1f}%",
             va="center", ha="left" if v >= 0 else "right", fontsize=8)
axa.axvline(0, color="black", lw=0.8)
axa.set_xlim(-3, 1.5)
axa.set_title("Dollar metrics: variance (%)", fontsize=9.5)
axa.invert_yaxis()
lab2 = ["cRPO growth (cc)\nvs. guide", "Sub. rev. growth (cc)\nvs. guide", "Non-GAAP op. margin\nvs. guide"]
val2 = [100, 50, 150]
bb = axb.barh(lab2, val2, color=GREEN, height=0.55)
for b, v in zip(bb, val2):
    axb.text(v + 4, b.get_y() + b.get_height() / 2, f"+{v}bp", va="center", fontsize=8)
axb.set_xlim(0, 190)
axb.set_title("Growth/margin metrics: variance (bp)", fontsize=9.5)
axb.invert_yaxis()
fig.suptitle("Q3'26 scorecard: beat on every company-guided metric, one-cent miss on Street EPS",
             fontsize=10.5, fontweight="bold", y=1.04)
fig.tight_layout()
save(fig, "fig06_beat_miss.png")

# ---------------------------------------------------------------- Fig 7 FY26 guidance progression
fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.6, 2.6), gridspec_kw={"width_ratios": [1.2, 1]})
dates = ["Jan-26\n(Q4'25)", "Apr-26\n(Q1'26)", "Jul-26\n(Q2'26)", "Oct-26\n(Q3'26)"]
lo = [15530, 15735, 15760, 15780]
hi = [15570, 15775, 15780, 15790]
mid = [(a + b) / 2 for a, b in zip(lo, hi)]
x = np.arange(4)
axa.bar(x, [h - l for l, h in zip(lo, hi)], bottom=lo, color=LIGHT, width=0.5, label="Guided range")
axa.plot(x, mid, color=NAVY, marker="o", lw=1.8, label="Midpoint")
for i, m in enumerate(mid):
    axa.text(i, hi[i] + 12, f"${m:,.0f}M", ha="center", fontsize=7.5)
axa.set_ylim(15450, 15880)
axa.set_xticks(x)
axa.set_xticklabels(dates, fontsize=8)
axa.set_ylabel("FY26 subscription revenue ($M)")
axa.set_title("FY26 subscription revenue guide", fontsize=9.5)
axa.legend(loc="lower right", fontsize=7.5)
ngom = [32.0, 31.5, 31.5, 31.5]
fcfm = [36.0, 35.0, 35.0, 36.0]
axb.plot(x, ngom, color=NAVY, marker="o", lw=1.8, label="Non-GAAP op. margin")
axb.plot(x, fcfm, color=GOLD, marker="s", lw=1.8, label="FCF margin")
for i in range(4):
    axb.text(i, ngom[i] - 0.45, f"{ngom[i]:.1f}%", ha="center", fontsize=7.5, color=NAVY)
    axb.text(i, fcfm[i] + 0.2, f"{fcfm[i]:.0f}%", ha="center", fontsize=7.5, color=GOLD)
axb.set_ylim(30, 37.5)
axb.set_xticks(x)
axb.set_xticklabels(dates, fontsize=8)
axb.set_ylabel("% of revenue")
axb.set_title("FY26 margin targets", fontsize=9.5)
axb.legend(loc="center right", fontsize=7.5)
fig.suptitle("FY26 guide raised $15M at the midpoint; FCF margin target restored to 36%",
             fontsize=10.5, fontweight="bold", y=1.04)
fig.tight_layout()
save(fig, "fig07_guidance_progression.png")

# ---------------------------------------------------------------- Fig 8 Q4 cRPO bridge (illustrative)
fig, ax = plt.subplots(figsize=FIG)
steps = [("Q3'26 cRPO\ngrowth (cc)", 21.0, "total"),
         ("Early-renewal\npull-forward*", -0.50, "delta"),
         ("Higher on-prem\nmix (mgmt)", -0.25, "delta"),
         ("T4C contract\nexclusion (mgmt)", -0.50, "delta"),
         ("Underlying/other\n(residual)*", -1.25, "delta"),
         ("Q4'26 guide\n(cc)", 18.5, "total")]
run = 0
for i, (lbl, v, kind) in enumerate(steps):
    if kind == "total":
        ax.bar(i, v, color=NAVY if i == 0 else RED, width=0.55)
        ax.text(i, v + 0.12, f"{v:.1f}%", ha="center", fontsize=8.5, fontweight="bold")
        run = v
    else:
        ax.bar(i, v, bottom=run, color=LIGHT, edgecolor=GREY, width=0.55)
        ax.text(i, run + 0.12, f"{v:+.2f}pp", ha="center", fontsize=8)
        run += v
ax.set_xticks(range(len(steps)))
ax.set_xticklabels([s[0] for s in steps], fontsize=8)
ax.set_ylim(16, 22.5)
ax.set_ylabel("cRPO growth, cc (%)")
ax.set_title("Bridging Q3's 21% to the Q4 guide of 18.5%: ~75bp is identified mechanics")
save(fig, "fig08_crpo_bridge.png")

# ---------------------------------------------------------------- Fig 9 >$5M customers + AI ACV target
fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.6, 2.6), gridspec_kw={"width_ratios": [1.3, 1]})
cq5 = ["Q3'25", "Q4'25", "Q1'26", "Q2'26", "Q3'26"]
c5 = [553, 603, 630, 658, 680]
bars = axa.bar(cq5, c5, color=[LIGHT] * 4 + [NAVY], width=0.6)
label_bars(axa, bars, "{:.0f}", dy=6, size=8)
axa.set_ylim(0, 780)
axa.set_title("Customers with >$5M ACV (+23% YoY)", fontsize=9.5)
ai = [1.0, 1.5, 1.7]
bars = axb.bar(["Initial FY26\ntarget", "Prior\ntarget", "New target\n(Oct-26)"], ai,
               color=[LIGHT, LIGHT, NAVY], width=0.55)
label_bars(axb, bars, "${:.1f}B", dy=0.03, size=8)
axb.set_ylim(0, 2.1)
axb.set_title("FY26 AI ACV target ($B)", fontsize=9.5)
fig.suptitle("Large-customer and AI monetization metrics remain the bull case's best evidence",
             fontsize=10.5, fontweight="bold", y=1.04)
fig.tight_layout()
save(fig, "fig09_customers_ai.png")

# ---------------------------------------------------------------- Fig 10 estimate revisions
fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.5))
items = [("Subscription revenue ($M)", [15770, 15790], [18766, 18553], "{:,.0f}"),
         ("Non-GAAP EPS ($)", [3.92, 3.90], [4.67, 4.51], "{:.2f}"),
         ("Free cash flow ($M)", [5677, 5847], [7025, 6785], "{:,.0f}")]
for ax, (t, fy26, fy27, fmt) in zip(axs, items):
    x = np.arange(2)
    w = 0.36
    b1 = ax.bar(x - w / 2, [fy26[0], fy27[0]], w, color=LIGHT, label="Prior est.")
    b2 = ax.bar(x + w / 2, [fy26[1], fy27[1]], w, color=NAVY, label="New est.")
    top = max(fy27) * 1.22
    ax.set_ylim(0, top)
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + top * 0.01, fmt.format(b.get_height()),
                ha="center", va="bottom", fontsize=6.5, rotation=90)
    ax.set_xticks(x)
    ax.set_xticklabels(["FY26E", "FY27E"])
    ax.set_title(t, fontsize=9)
    ax.tick_params(axis="y", labelsize=7)
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.08))
fig.suptitle("Estimate revisions: FY27E subscription revenue -1.1%, EPS -3.4%, FCF -3.4%",
             fontsize=10.5, fontweight="bold", y=1.05)
fig.tight_layout()
save(fig, "fig10_estimate_revisions.png")

# ---------------------------------------------------------------- Fig 11 price vs targets
fig, ax = plt.subplots(figsize=FIG)
pts = [("52-week low", 81.24, GREY), ("Pre-market 10/29 (approx.)", 122.60, RED),
       ("Our PT (Hold)", 135.00, NAVY), ("Close 10/28", 150.13, TEAL),
       ("Street avg. PT (approx.)", 157.00, GOLD), ("Citizens PT (Outperform)", 157.00, GOLD),
       ("Morgan Stanley PT (OW, from $180)", 160.00, GOLD), ("52-week high", 192.97, GREY)]
y = np.arange(len(pts))
ax.barh(y, [p[1] for p in pts], color=[p[2] for p in pts], height=0.55)
for i, p in enumerate(pts):
    ax.text(p[1] + 2, i, f"${p[1]:.2f}", va="center", fontsize=8)
ax.set_yticks(y)
ax.set_yticklabels([p[0] for p in pts], fontsize=8)
ax.set_xlim(0, 225)
ax.set_xlabel("$ per share")
ax.invert_yaxis()
ax.set_title("Our $135 PT sits ~10% above the indicated open and below Street targets")
save(fig, "fig11_price_vs_targets.png")

# ---------------------------------------------------------------- Fig 12 EV/FCF sensitivity
fig, ax = plt.subplots(figsize=FIG)
mults = np.array([16, 18, 20, 21, 22, 24, 26])
net_debt = 0.563  # $B, Sep-30-2026: debt $7.524B less cash & marketable securities $6.961B
shares = 1.050    # B, Q4'26 diluted share guide
for fcf27, lbl, c, ls in [(6.364, "Bear FCF $6.4B", RED, "--"), (6.785, "Base FCF $6.8B", NAVY, "-"),
                          (7.218, "Bull FCF $7.2B", GREEN, "--")]:
    px = (mults * fcf27 - net_debt) / shares
    ax.plot(mults, px, color=c, ls=ls, marker="o", lw=1.8, label=lbl)
ax.axhline(122.60, color=GREY, lw=1, ls=":")
ax.text(16.1, 124.5, "Pre-market ~$122.60", fontsize=7.5, color=GREY)
ax.axhline(150.13, color=GREY, lw=1, ls=":")
ax.text(16.1, 152.0, "10/28 close $150.13", fontsize=7.5, color=GREY)
ax.scatter([21], [135], color=NAVY, s=60, zorder=6)
ax.annotate("PT $135\n(21x base)", (21, 135), xytext=(22.3, 112), fontsize=8,
            arrowprops=dict(arrowstyle="->", color=NAVY))
ax.set_xlabel("EV / FY27E free cash flow (x)")
ax.set_ylabel("Implied value per share ($)")
ax.legend(loc="upper left", fontsize=7.5)
ax.set_title("Valuation sensitivity: implied value per share by EV/FCF multiple and FY27E FCF")
save(fig, "fig12_valuation_sensitivity.png")

print("charts written:", sorted(os.listdir(OUT)))
