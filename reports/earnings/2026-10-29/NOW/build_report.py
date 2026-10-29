"""Build the ServiceNow (NOW) Q3 2026 earnings update DOCX.

Run make_charts.py first (charts/ folder), then:  python3 build_report.py
Reported data: ServiceNow earnings releases (Form 8-K Ex. 99.1) on SEC EDGAR.
Estimates marked "E" and all price-target math are our own.
"""
import os
from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Pt, Inches, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.join(HERE, "charts")
OUT = os.path.join(HERE, "ServiceNow_Q3_2026_Earnings_Update.docx")

FONT = "Times New Roman"
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
GREY = RGBColor(0x55, 0x55, 0x55)

# ------------------------------------------------------------------ source URLs
U = {
    "q3": "https://www.sec.gov/Archives/edgar/data/0001373715/000137371526000092/erq3fy26.htm",
    "q3a": "https://www.sec.gov/Archives/edgar/data/1373715/000137371526000095/0001373715-26-000095-index.htm",
    "q3a_doc": "https://www.sec.gov/Archives/edgar/data/0001373715/000137371526000095/erq3fy262.htm",
    "q2": "https://www.sec.gov/Archives/edgar/data/0001373715/000137371526000072/erq2fy26.htm",
    "q1": "https://www.sec.gov/Archives/edgar/data/0001373715/000137371526000054/erq1fy26.htm",
    "q4_25": "https://www.sec.gov/Archives/edgar/data/1373715/000137371526000005/erq4fy25.htm",
    "q3_25": "https://www.sec.gov/Archives/edgar/data/1373715/000137371525000305/erq3fy25.htm",
    "q2_25": "https://www.sec.gov/Archives/edgar/data/1373715/000137371525000274/erq2fy25.htm",
    "edgar": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001373715&type=8-K&dateb=&owner=include&count=40",
    "edgar_all": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001373715&owner=include&count=40",
    "fool": "https://www.fool.com/earnings/call-transcripts/2026/10/29/servicenow-now-q3-2026-earnings-call-transcript/",
    "ir": "https://investors.servicenow.com/",
}

doc = Document()

# ------------------------------------------------------------------ base styles
for sname in ["Normal", "Heading 1", "Heading 2", "Heading 3", "Title", "Caption"]:
    st = doc.styles[sname]
    st.font.name = FONT
    rpr = st.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ["w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"]:
        rfonts.set(qn(a), FONT)
    for a in ["w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"]:
        if rfonts.get(qn(a)) is not None:
            del rfonts.attrib[qn(a)]

# force Times New Roman in docDefaults and every style that names a font
for rf in doc.styles.element.iter(qn("w:rFonts")):
    for a_ in ["w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"]:
        if rf.get(qn(a_)) is not None:
            del rf.attrib[qn(a_)]
    for a_ in ["w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"]:
        rf.set(qn(a_), FONT)

normal = doc.styles["Normal"]
normal.font.size = Pt(10)
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.line_spacing = 1.0

for name, size in [("Heading 1", 13), ("Heading 2", 11.5), ("Heading 3", 10.5)]:
    st = doc.styles[name]
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.italic = False
    st.font.color.rgb = NAVY
    st.paragraph_format.space_before = Pt(8 if name == "Heading 1" else 6)
    st.paragraph_format.space_after = Pt(3)
    st.paragraph_format.keep_with_next = True

sec = doc.sections[0]
sec.left_margin = sec.right_margin = Inches(0.8)
sec.top_margin = Inches(0.7)
sec.bottom_margin = Inches(0.7)


# ------------------------------------------------------------------ helpers
def set_run_font(run, size=None, bold=None, italic=None, color=None):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for a in ["w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"]:
        rfonts.set(qn(a), FONT)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    return run


def add_hyperlink(paragraph, text, url, size=None, italic=False):
    """Real Word hyperlink (relationship-based), blue and underlined."""
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    hl = OxmlElement("w:hyperlink")
    hl.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    rfonts = OxmlElement("w:rFonts")
    for a in ["w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"]:
        rfonts.set(qn(a), FONT)
    rpr.append(rfonts)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    rpr.append(color)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rpr.append(u)
    if italic:
        rpr.append(OxmlElement("w:i"))
    if size:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size * 2)))
        rpr.append(sz)
    new_run.append(rpr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    new_run.append(t)
    hl.append(new_run)
    paragraph._p.append(hl)
    return hl


def para(text="", size=10, bold=False, italic=False, align=None, color=None, space_after=4,
         keep_next=False):
    p = doc.add_paragraph()
    if text:
        add_rich(p, text, size=size, bold=bold, italic=italic, color=color)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if keep_next:
        p.paragraph_format.keep_with_next = True
    return p


def add_rich(p, text, size=10, bold=False, italic=False, color=None):
    """Supports **bold** segments inside text."""
    parts = text.split("**")
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        set_run_font(r, size=size, bold=(bold or i % 2 == 1), italic=italic, color=color)
    return p


def bullet(header, body, size=10):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.22)
    p.paragraph_format.first_line_indent = Inches(-0.22)
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run("■  ")
    set_run_font(r, size=size, color=NAVY)
    r = p.add_run(header + " ")
    set_run_font(r, size=size, bold=True)
    add_rich(p, body, size=size)
    return p


def source_line(parts, size=8):
    """parts: list of str or (text, url) tuples."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(7)
    r = p.add_run("Source: ")
    set_run_font(r, size=size, italic=True, color=GREY)
    for part in parts:
        if isinstance(part, tuple):
            add_hyperlink(p, part[0], part[1], size=size, italic=True)
        else:
            r = p.add_run(part)
            set_run_font(r, size=size, italic=True, color=GREY)
    return p


FIGN = [0]


def figure(fname, title, src_parts, width=6.1):
    FIGN[0] += 1
    cap = doc.add_paragraph()
    cap.paragraph_format.space_before = Pt(4)
    cap.paragraph_format.space_after = Pt(2)
    cap.paragraph_format.keep_with_next = True
    r = cap.add_run(f"Figure {FIGN[0]} - {title}")
    set_run_font(r, size=9, bold=True, color=NAVY)
    pic = doc.add_paragraph()
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.paragraph_format.space_after = Pt(1)
    pic.paragraph_format.keep_with_next = True
    pic.add_run().add_picture(os.path.join(CH, fname), width=Inches(width))
    source_line(src_parts)


def shade(cell, hexcolor):
    tcpr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcpr.append(shd)


def set_cell_margins(table, top=30, bottom=30, left=70, right=70):
    tblpr = table._element.tblPr
    mar = OxmlElement("w:tblCellMar")
    for k, v in [("top", top), ("left", left), ("bottom", bottom), ("right", right)]:
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblpr.append(mar)


TABN = [0]


def table(title, header, rows, widths, src_parts, bold_rows=(), size=8.5, note=None):
    TABN[0] += 1
    cap = doc.add_paragraph()
    cap.paragraph_format.space_before = Pt(4)
    cap.paragraph_format.space_after = Pt(2)
    cap.paragraph_format.keep_with_next = True
    r = cap.add_run(f"Table {TABN[0]} - {title}")
    set_run_font(r, size=9, bold=True, color=NAVY)
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_cell_margins(t)
    for j, h in enumerate(header):
        c = t.rows[0].cells[j]
        c.text = ""
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
        set_run_font(p.add_run(h), size=size, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shade(c, "1F3A5F")
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            c = t.rows[i].cells[j]
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
            set_run_font(p.add_run(val), size=size, bold=(i - 1) in bold_rows)
            if i % 2 == 0:
                shade(c, "EEF3F8")
    for ri, row in enumerate(t.rows):
        trpr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trpr.append(cs)
        for j, w in enumerate(widths):
            row.cells[j].width = Inches(w)
            if ri < len(t.rows) - 1:
                for cp in row.cells[j].paragraphs:
                    cp.paragraph_format.keep_with_next = True
    if note:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(0)
        set_run_font(p.add_run(note), size=8, italic=True, color=GREY)
    source_line(src_parts)
    return t


def add_page_number_footer(section):
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(fp.add_run("ServiceNow (NOW) | Q3 2026 Earnings Update | October 29, 2026 | Page "),
                 size=8, color=GREY)
    run = fp.add_run()
    set_run_font(run, size=8, color=GREY)
    f1 = OxmlElement("w:fldChar")
    f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = "PAGE"
    f2 = OxmlElement("w:fldChar")
    f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1)
    run._r.append(it)
    run._r.append(f2)


add_page_number_footer(sec)

REL = ("Q3'26 earnings release (8-K Ex. 99.1, Oct 28, 2026)", U["q3"])

# ================================================================== PAGE 1
p = para("EQUITY RESEARCH  |  EARNINGS UPDATE  |  US SOFTWARE", size=8.5, bold=True, color=GREY,
         space_after=2)
p = para("ServiceNow, Inc. (NYSE: NOW)", size=16, bold=True, color=NAVY, space_after=0)
p = para("Q3 2026 EARNINGS UPDATE  |  October 29, 2026", size=10.5, bold=True, space_after=4)
p = para("Q3'26: Clean Beat on Every Guided Metric, but an 18.5% cRPO Guide Resets the Growth "
         "Debate - Maintaining HOLD, 12-Month PT $135", size=13, bold=True, color=NAVY, space_after=5)

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(1)
add_rich(p, "**Rating: MAINTAIN HOLD**   |   **12-month price target: $135** (EV/FY27E FCF of 21x; "
            "first published target under our updated framework)   |   **Implied return: +10%** vs. "
            "~$122.60 indicated pre-market (-10% vs. $150.13 close)", size=9.5)
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(6)
add_rich(p, "Price (Oct 28 close): $150.13 (-3% on day)  |  Pre-market Oct 29: ~$122.60 (about -18%)  |  "
            "52-week range: $81.24-$192.97  |  Diluted shares: 1,043M  |  Market cap at $122.60: ~$128B  |  "
            "Net debt: ~$0.6B  |  All per-share data post 5-for-1 split (effective Dec 17, 2025)",
         size=8.5, color=GREY)

para("Q3 2026 RESULTS: BEAT ON REVENUE, cRPO AND MARGIN; $0.02 MISS ON STREET EPS; Q4 cRPO GUIDE "
     "BELOW STREET", size=10, bold=True, color=NAVY, space_after=2, keep_next=True)

table("Q3'26 reported results vs. guidance and consensus",
      ["Metric", "Q3'26A", "Guide / Consensus", "Variance", "Q3'25A", "YoY"],
      [["Subscription revenue ($M)", "3,988", "3,975-3,980 (guide)", "+$8M vs. high end", "3,299", "+21% (20.5% cc)"],
       ["Total revenue ($M)", "4,106", "~4,090-4,100 (cons.)", "+$6-16M (~0.3%)", "3,407", "+20.5%"],
       ["cRPO ($B) / growth cc", "13.65 / 21%", "20% cc (guide)", "+100bp", "11.35", "+20.5%"],
       ["Non-GAAP operating margin", "32.5%", "31% (guide)", "+150bp", "33.5%", "-100bp"],
       ["Non-GAAP diluted EPS", "$1.00", "$1.02 (cons.)", "-$0.02 (-2%)", "$0.95", "+5%"],
       ["GAAP diluted EPS", "$0.27", "n/a", "n/a", "$0.48", "-44%"],
       ["Free cash flow ($M) / margin", "822 / 20%", "n/a", "n/a", "592 / 17.5%", "+39%"],
       ["Q4'26 cRPO growth guide (cc)", "18.5%", "~20% (Street)", "~-150bp", "n/a", "n/a"]],
      [1.75, 0.8, 1.25, 1.1, 0.8, 1.0],
      [REL, "; Q3'26 guidance from ", ("Q2'26 release (Jul 22, 2026)", U["q2"]),
       "; consensus EPS/revenue as cited in pre-earnings Street coverage (Oct 28, 2026); Street Q4 cRPO "
       "per Morgan Stanley (Oct 29, 2026). Q3'25 EPS restated by company for 5-for-1 split."],
      bold_rows=(0, 4, 7))

para("Key Takeaways", size=10.5, bold=True, color=NAVY, space_after=2, keep_next=True)
bullet("Results beat on the metrics ServiceNow controls, but the Street wanted acceleration and got "
       "the opposite.",
       "Subscription revenue of $3,988M (+21%, +20.5% cc) cleared the top of the $3,975-3,980M guide by "
       "$8M, cRPO of $13.65B grew 21% cc vs. the 20% guide, and non-GAAP operating margin of 32.5% was "
       "150bp above guidance. Non-GAAP EPS of $1.00 rose 5% YoY but missed the $1.02 consensus as higher "
       "interest costs on acquisition debt and a smaller cash balance cut the conversion of operating income "
       "to net income (78% vs. 87% a year ago, our calculation).")
bullet("The Q4 cRPO guide of 18.5% cc is the story.",
       "It sits ~150bp below the ~20% the Street expected and 250bp below Q3's 21%. Management attributed "
       "the step-down to early renewals pulled into Q3 (about half of the Q3 cRPO beat), a higher on-prem "
       "mix in public sector (~25bp) and termination-for-convenience contract terms (~50bp excluded from "
       "cRPO). Morgan Stanley estimates organic cRPO growth slows to ~18% from ~19%, which, with Armis "
       "lapping in 2027, points to high-teens subscription growth next year.")
bullet("AI monetization keeps improving; it is not yet showing up as acceleration.",
       "The FY26 AI ACV target rises to $1.7B from $1.5B, AI net-new ACV grew 65% YoY, 19 deals exceeded "
       "$5M net-new ACV (+135%) and customers above $5M ACV rose ~23% to 680. Some large AI deployments "
       "now carry professional services, shifting ~25bp of subscription growth to services in Q3 and ~50bp "
       "in Q4.")
bullet("Maintaining HOLD; setting a $135 price target.",
       "We trim FY27E subscription revenue 1.1% to $18.55B and non-GAAP EPS 3.4% to $4.51. Our $135 PT "
       "applies 21x EV to FY27E FCF of $6.79B, cross-checked by 30x FY27E EPS. After an ~18% pre-market "
       "fall the stock is closer to fair value, but we want evidence that cRPO growth stabilizes around 18-19% "
       "before turning more constructive.")

# ================================================================== RESULTS ANALYSIS
doc.add_heading("Detailed Results Analysis", level=1)
doc.add_heading("Revenue and bookings: 20%+ growth intact, with inorganic help", level=2)
para("Subscription revenue grew 21% YoY to $3,988M (20.5% cc), 50bp above the high end of the constant-"
     "currency guide. Total revenue of $4,106M (+20.5%) was roughly $6-16M above the ~$4.09-4.10B consensus "
     "range. Professional services and other revenue rose 10% to $118M. Reported growth eased from 24.5% "
     "in Q2'26, the first quarter to include Armis (closed April 20, 2026; the company said at Q1 the "
     "deal adds about 125bp to FY26 subscription growth). Veza closed March 2, 2026 and Moveworks closed "
     "December 15, 2025, so all three deals now sit in the base. ServiceNow does not report organic "
     "subscription growth. Our view is that the headline 21% overstates the organic run-rate by roughly a "
     "point, consistent with Morgan Stanley's ~19% organic cRPO estimate for Q3.")
figure("fig01_subscription_revenue.png",
       "Quarterly subscription revenue ($M) and YoY growth, Q1'25-Q3'26 and Q4'26 guidance midpoint",
       [REL, "; ", ("Q2'26 release", U["q2"]), "; ", ("Q1'26 release", U["q1"]), "; ",
        ("Q4'25 release", U["q4_25"]), "; ", ("Q3'25 release", U["q3_25"]),
        ". Q4'26G = midpoint of $4,245-4,255M guide; growth shown as reported (GAAP)."])
para("Current RPO reached $13.65B, up 20.5% (21% cc), a 100bp beat vs. the 20% cc guide, and total RPO grew "
     "22% to $29.7B. Sequentially cRPO added $450M vs. $430M in Q3'25. The quality of the beat was weaker "
     "than the headline: CFO Gina Mastantuono said early renewals \"contributed about half of the beat in "
     "Q3,\" and that this \"has a negative impact in Q4 because we pulled those deals out of Q4 and into Q3.\" "
     "Excluding the pull-forward, cRPO grew roughly in line with the 20% cc guide. ServiceNow has now beaten "
     "its cRPO cc guide in every quarter shown in Figure 2, typically by 100-250bp, which is why the 18.5% "
     "Q4 guide reads as conservative. Still, it is the lowest cc guide in the series.")
figure("fig02_crpo.png", "cRPO ($B), constant-currency growth and the prior-quarter cc guide",
       [REL, "; prior guides from ", ("Q2'26", U["q2"]), ", ", ("Q1'26", U["q1"]), ", ",
        ("Q4'25", U["q4_25"]), ", ", ("Q3'25", U["q3_25"]), " and ", ("Q2'25", U["q2_25"]),
        " releases. Q4'26G shows guided growth only (no dollar value given)."])

doc.add_heading("Profitability: operating beat, below-the-line drag", level=2)
para("Non-GAAP operating income rose 17% to $1,338M, a 32.5% margin vs. 33.5% a year ago and the 31% guide. "
     "Gross margin is under pressure: non-GAAP subscription gross margin fell to 80% from 83% and non-GAAP "
     "gross margin to 77.5% from 81%, reflecting lower-margin acquired revenue, AI compute costs and a "
     "professional services gross loss of $39M (break-even a year ago) as ServiceNow puts its own people "
     "into large AI deployments. Opex discipline absorbed most of it; management cited more than $1B of "
     "annualized internal AI efficiency. GAAP operating margin fell to 9.5% from 17% as the gap between "
     "GAAP and non-GAAP operating income widened to $953M from $568M, driven by stock comp and acquisition "
     "items including amortization of acquired intangibles.")
figure("fig03_operating_margins.png", "Non-GAAP and GAAP operating margin, Q1'25-Q3'26 and Q4'26 guidance",
       [REL, " and prior quarterly releases (", ("Q2'26", U["q2"]), ", ", ("Q1'26", U["q1"]), ", ",
        ("Q4'25", U["q4_25"]), "). Q4'26G: 32% non-GAAP, 12% GAAP per Q3'26 release."])
para("The EPS miss happened below the operating line. Non-GAAP net income of $1,039M was 78% of non-GAAP "
     "operating income vs. 87% in Q3'25 ($992M of $1,140M). Debt rose to $7.5B ($2.1B short-term, $5.4B "
     "long-term) from $1.5B at year-end 2025, while cash and marketable securities fell to $7.0B from "
     "$10.1B after $9.2B of cash paid for acquisitions year to date. In our view, higher interest expense "
     "and lower interest income explain most of the conversion gap. The release does not split out interest "
     "and tax, so this is our inference. At last year's 87% conversion, Q3 EPS would have been about $1.12. "
     "GAAP EPS fell 44% to $0.27.")
figure("fig04_eps.png", "Quarterly non-GAAP and GAAP diluted EPS (post-split) vs. Q3'26 consensus",
       [REL, " and prior releases; prior-period EPS as restated by ServiceNow for the 5-for-1 split; "
             "consensus $1.02 per pre-earnings Street coverage (Oct 28, 2026)."])

doc.add_heading("Cash flow and balance sheet", level=2)
para("Free cash flow rose 39% to $822M (20% margin vs. 17.5%), and year-to-date FCF is $3,121M (26.5% "
     "margin). Q3 is seasonally ServiceNow's weakest cash quarter because collections are concentrated in "
     "Q4 and Q1. The raised 36% FY26 FCF margin target, on our ~$16.24B FY26E revenue, implies roughly "
     "$2.7B of Q4 FCF vs. $2.0B in Q4'25. Management attributed the raise to lower capex. There was no "
     "buyback in Q3, vs. $584M in Q3'25. All $2,225M of 2026 repurchases came in Q1, including a $2B "
     "accelerated share repurchase, and about $4.2B of authorization remained after Q1. Goodwill rose to "
     "$10.0B from $3.6B at year-end, a reminder of how much of 2026 growth was bought. Current deferred "
     "revenue was $7.6B.")
figure("fig05_fcf.png", "Quarterly free cash flow ($M) and FCF margin",
       [REL, "; ", ("Q2'26", U["q2"]), ", ", ("Q1'26", U["q1"]), " and ", ("Q4'25", U["q4_25"]),
        " releases (non-GAAP FCF as defined by the company; Q1'25-Q3'25 comparatives as restated in 2026 releases)."])

doc.add_heading("Beat/miss scorecard", level=2)
para("Against its own guide ServiceNow beat on every line: subscription revenue by ~0.3% at the midpoint, "
     "constant-currency subscription growth by 50bp, cRPO cc growth by 100bp and non-GAAP operating margin "
     "by 150bp. Against the Street it beat on revenue by about 0.3% and missed on EPS by 2%. That would "
     "normally be a modestly positive print. The ~18% pre-market drop says investors are trading the forward "
     "cRPO trajectory, not the quarter.")
figure("fig06_beat_miss.png", "Q3'26 variance vs. company guidance and Street consensus",
       [REL, "; guidance from ", ("Q2'26 release", U["q2"]),
        "; revenue consensus taken at ~$4.095B midpoint of ~$4.09-4.10B range, EPS consensus $1.02 "
        "(pre-earnings Street coverage, Oct 28, 2026)."])

# ================================================================== GUIDANCE
doc.add_heading("Guidance and Outlook", level=1)
table("Management guidance: new vs. prior and Street",
      ["Metric", "New guide (Oct 28)", "Prior guide (Jul 22)", "Change", "Street / comment"],
      [["Q4'26 subscription revenue", "$4,245-4,255M", "n/a (new)", "+22.5-23% YoY; 21.5% cc", "Includes Armis"],
       ["Q4'26 cRPO growth", "18.5% (GAAP & cc)", "n/a (new)", "vs. Q3'26 21% cc", "~20% (Morgan Stanley)"],
       ["Q4'26 non-GAAP op. margin", "32%", "n/a (new)", "+100bp YoY", "GAAP 12%"],
       ["FY26 subscription revenue", "$15,780-15,790M", "$15,760-15,780M", "+$15M at midpoint", "22.5% (21% cc)"],
       ["FY26 non-GAAP sub. gross margin", "81%", "81%", "Unchanged", "82% at Jan guide"],
       ["FY26 non-GAAP op. margin", "31.5%", "31.5%", "Unchanged", "32% at Jan guide"],
       ["FY26 FCF margin", "36%", "35%", "+100bp", "Lower capex"],
       ["FY26 AI ACV target", "$1.7B", "$1.5B", "+$0.2B", "AI NNACV +65% YoY"],
       ["FY26 diluted shares", "1.04B", "1.04B", "Unchanged", "Q4: 1.05B"]],
      [1.75, 1.2, 1.2, 1.35, 1.2],
      [REL, "; ", ("Q2'26 release (Jul 22, 2026)", U["q2"]), "; ", ("Q4'25 release (Jan 28, 2026)", U["q4_25"]),
       "; AI ACV prior target and Q4 Street cRPO per ", ("Q3'26 call transcript", U["fool"]),
       " and Morgan Stanley (Oct 29, 2026)."],
      bold_rows=(1, 6))
para("The FY26 subscription raise of $15M at the midpoint is essentially the $10.5M Q3 beat (vs. the "
     "guide midpoint) flowed through. Our calculation is that the implied Q4 midpoint of $4,249M (FY midpoint "
     "less $11,536M nine-month actual) is only ~$5M above what the July guide implied. Since January the FY26 "
     "subscription guide has risen $235M at the midpoint (Figure 7). Most of that came in April, when Armis "
     "was added; we estimate Armis's ~125bp at roughly $160M. The organic raise over the year is therefore "
     "a modest ~$75M. The non-GAAP operating margin target held at 31.5%, 50bp below January's 32%, as "
     "ServiceNow absorbs deal dilution. The FCF margin target is back at the 36% it started the year at.")
figure("fig07_guidance_progression.png", "Evolution of FY26 guidance: subscription revenue, operating margin and FCF margin",
       [("Q4'25 release (Jan 28, 2026)", U["q4_25"]), "; ", ("Q1'26 release (Apr 22, 2026)", U["q1"]), "; ",
        ("Q2'26 release (Jul 22, 2026)", U["q2"]), "; ", REL, "."])

doc.add_heading("Unpacking the 18.5% Q4 cRPO guide", level=2)
para("Management named three mechanical drags. (1) Early renewals: about half of Q3's 100bp beat came from "
     "renewals pulled out of Q4. (2) On-prem mix: \"Strong public sector demand is driving higher on-prem "
     "mix in Q4,\" a ~25bp headwind, because on-prem licenses are recognized upfront and fall outside cRPO. "
     "(3) Termination-for-convenience (T4C) clauses, common in public-sector contracts, exclude ~50bp of "
     "backlog growth from cRPO, although management expects that revenue to be recognized. The on-prem and "
     "T4C items explain ~75bp of the 250bp step-down. We estimate the pull-forward at ~50bp, which "
     "leaves a ~125bp residual we cannot attribute to any disclosed item (Figure 8). That "
     "residual, together with Morgan Stanley's estimate that organic cRPO growth slows to ~18% from ~19%, "
     "is why we do not treat the guide as purely mechanical. Mastantuono's comment that cRPO \"is a good "
     "indicator of next year's revenue, [but] it's certainly not perfect\" tells us management expects the "
     "2027 debate to centre on this number.")
figure("fig08_crpo_bridge.png", "Illustrative bridge from Q3'26 cRPO growth (21% cc) to Q4'26 guide (18.5%)",
       [("Q3'26 earnings call transcript (Oct 28, 2026)", U["fool"]), " for on-prem (~25bp) and T4C (~50bp) "
        "items; *pull-forward size and residual are our estimates (management quantified only that early "
        "renewals were ~half of the Q3 beat); ", REL, "."])

doc.add_heading("Key Metrics: Large Customers and AI", level=2)
para("Customers with more than $5M ACV grew ~23% YoY to 680, adding 22 in the quarter vs. 28 in Q2'26. "
     "Nineteen transactions exceeded $5M net-new ACV (+135% YoY) and the renewal rate was 98%. On AI, "
     "ServiceNow raised its FY26 AI ACV target to $1.7B from $1.5B (the year began at $1B). AI net-new ACV "
     "grew 65% YoY, production agentic-AI consumption is up more than 13x year to date, Control Tower "
     "net-new ACV grew more than 6x and EmployeeWorks passed $100M ACV in under three quarters. The 2030 "
     "goal of 30% of ACV from AI was reiterated. The bull case rests on these data points, but at ~$1.7B "
     "AI is still roughly 10% of the subscription base. It is not yet large enough to offset slowing growth "
     "in core IT workflows, or a slower pace of seat additions if customers shrink headcount.")
figure("fig09_customers_ai.png", "Customers with >$5M ACV and FY26 AI ACV target progression",
       [REL, "; ", ("Q2'26", U["q2"]), ", ", ("Q1'26", U["q1"]), ", ", ("Q4'25", U["q4_25"]), " and ",
        ("Q3'25", U["q3_25"]), " releases; prior $1.5B AI ACV target per ",
        ("Q3'26 call transcript", U["fool"]), "; initial $1B target per Q3'26 release."])

doc.add_heading("Management commentary", level=2)
para("CEO Bill McDermott said this \"was more than another beat-and-raise quarter for ServiceNow\" and on "
     "the call argued that \"the business has never been in better shape than it is right now\" and that "
     "the AI \"hockey stick formation has yet to be fully realized.\" On pricing he defended the hybrid "
     "model: \"the customer likes the predictability of the seat-based pricing model,\" with consumption "
     "layered on top. Mastantuono said services attached to AI deployments are temporary: \"upon renewal of "
     "those contracts, the value of those services return to subscription revenue.\" No numeric 2027 "
     "outlook was given. Management said AI momentum will translate into strong revenue growth in 2027 and "
     "beyond, and did not discuss capital return on the call. Analyst questions centred on outcome-based "
     "pricing (Deutsche Bank), the Q4 guide (Wolfe), cRPO acceleration (Morgan Stanley), whether AI "
     "cannibalizes software budgets (William Blair) and how deployment services are accounted for "
     "(Jefferies).")
p = para("Quotes are taken from a third-party transcript that the publisher notes may contain errors, and "
         "should be checked against the official webcast replay.", size=8, italic=True, color=GREY)

# ================================================================== THESIS
doc.add_heading("Investment Thesis Update", level=1)
bullet("Pillar 1 - Durable 20%+ subscription growth at scale. Status: WEAKENED.",
       "Reported growth remains above 20% and the Q4 guide implies 22.5-23%, but that includes Armis, Veza "
       "and Moveworks. Organic cRPO is slowing toward ~18%, and the services shift (50-100bp headwind into "
       "2027 per Morgan Stanley) plus T4C terms (~50bp cRPO headwind in 2027) cap reported growth next year. "
       "We now model 17.5% FY27E subscription growth, down from 19%. Our thesis assumed ServiceNow could hold "
       "~20% organically through 2027, and the Q4 guide makes that harder to underwrite.")
bullet("Pillar 2 - AI as an incremental monetization layer. Status: STRENGTHENED.",
       "The AI ACV target has risen 70% from the $1B starting point and net-new AI ACV grew 65%. Large-deal "
       "metrics are accelerating. The hybrid seat-plus-consumption model gives customers predictability and "
       "lets ServiceNow capture usage. The open question is net, not gross: if agentic AI lowers the number "
       "of human fulfiller seats, AI ACV may partly replace seat revenue rather than add to it. William "
       "Blair asked this directly on the call and management gave no quantitative answer.")
bullet("Pillar 3 - Best-in-class cash generation. Status: UNCHANGED / MODESTLY STRENGTHENED.",
       "The FY26 FCF margin target goes back to 36%, Q3 FCF grew 39% and the non-GAAP operating margin beat "
       "by 150bp. Offsets: FCF does not deduct stock comp, the GAAP margin fell to 9.5%, and the balance "
       "sheet moved from ~$8.6B net cash at year-end 2025 to ~$0.6B net debt after $9.2B of acquisitions. "
       "Interest costs now dilute EPS, which drove this quarter's miss.")
bullet("Pillar 4 - M&A extends the platform into security and identity. Status: UNDER REVIEW.",
       "Armis (asset and exposure security), Veza (identity security) and Moveworks (employee AI assistant) "
       "feed the Autonomous Security and EmployeeWorks offerings, and management says the deals are \"way "
       "ahead\" of plan. Together they lifted goodwill by $6.4B and blur the organic growth picture. We want "
       "organic disclosure, or at least cRPO stability once Armis laps in Q2'27, before crediting the strategy.")

doc.add_heading("Risks Update", level=2)
para("**Downside risks:** (1) further cRPO deceleration below 18% in 1H27, especially if the residual in "
     "Figure 8 proves structural; (2) AI-driven seat compression in IT, HR and customer-service workflows; "
     "(3) public-sector budget or contracting disruption, given the higher on-prem and T4C mix; (4) "
     "integration risk on three acquisitions and a higher interest burden; (5) multiple compression across "
     "application software. **Upside risks:** (1) Q4 cRPO lands at 20% or better, in line with ServiceNow's "
     "record of beating its guide by 100bp or more; (2) faster AI ACV conversion to subscription revenue "
     "once deployment services roll to renewal; (3) resumption of buybacks under the remaining ~$4.2B "
     "authorization; (4) a 2027 framework at the Q4 print that holds 20% cc growth.")

# ================================================================== ESTIMATES & VALUATION
doc.add_heading("Estimate Revisions", level=1)
table("Updated estimates: prior vs. new (our estimates; FY25 actuals for reference)",
      ["$M except per share", "FY25A", "FY26E old", "FY26E new", "Chg", "FY27E old", "FY27E new", "Chg"],
      [["Subscription revenue", "12,883", "15,770", "15,790", "+0.1%", "18,766", "18,553", "-1.1%"],
       ["  Subscription growth", "21.0%", "22.4%", "22.6%", "+20bp", "19.0%", "17.5%", "-150bp"],
       ["Total revenue", "13,278", "16,220", "16,242", "+0.1%", "19,246", "19,113", "-0.7%"],
       ["Q4'26E cRPO growth (cc)", "-", "20.0%", "18.5%", "-150bp", "-", "-", "-"],
       ["Non-GAAP operating income", "~4,116", "5,109", "5,116", "+0.1%", "6,255", "6,116", "-2.2%"],
       ["Non-GAAP operating margin", "31.0%", "31.5%", "31.5%", "0bp", "32.5%", "32.0%", "-50bp"],
       ["Non-GAAP diluted EPS", "$3.51", "$3.92", "$3.90", "-0.5%", "$4.67", "$4.51", "-3.4%"],
       ["Free cash flow", "4,636", "5,677", "5,847", "+3.0%", "7,025", "6,785", "-3.4%"],
       ["FCF margin", "35.0%", "35.0%", "36.0%", "+100bp", "36.5%", "35.5%", "-100bp"],
       ["P/E at $122.60 (x)", "-", "31.3x", "31.4x", "", "26.3x", "27.2x", ""],
       ["EV/FCF at $122.60 (x)", "-", "22.6x", "22.0x", "", "18.3x", "18.9x", ""]],
      [1.6, 0.6, 0.72, 0.72, 0.58, 0.72, 0.72, 0.58],
      [("Q4'25 release", U["q4_25"]), " (FY25A; FY25 non-GAAP operating income approximated as 31% x "
       "revenue); ", REL, "; our estimates. Old estimates = our pre-print model anchored to the July 22 guide."],
      bold_rows=(0, 6, 7), size=8)
para("**What changed and why.** FY26E is essentially unchanged: we move to the new guide midpoint plus "
     "~$5M of upside and adopt the 36% FCF margin. For FY27E we cut subscription growth to 17.5% from 19% "
     "to reflect (a) the Q4 cRPO exit rate of 18.5%, (b) Armis lapping from Q2'27, (c) Morgan Stanley's "
     "50-100bp services-mix headwind, which we partly mirror by raising FY27E services revenue to $560M "
     "from $480M, and (d) ~50bp from T4C terms. We lower FY27E non-GAAP operating margin 50bp to 32.0% to "
     "reflect deployment-services costs and integration. Higher interest expense lowers FY27E EPS by a "
     "further ~$0.05 vs. our prior. FY27E FCF falls 3.4% to $6.79B (35.5% margin) as cash interest and "
     "lower services margins offset a lighter capex profile. FY25A FCF and EPS are from the Q4'25 release.")
figure("fig10_estimate_revisions.png", "Estimate revisions: prior vs. new (FY26E and FY27E)",
       ["Our estimates; FY26 guidance from ", REL, "."])

doc.add_heading("Valuation and Price Target", level=1)
para("**Methodology.** Our 12-month price target of $135 applies 21x EV to FY27E free cash flow of $6.785B. "
     "That gives an enterprise value of $142.5B; we subtract ~$0.56B of net debt (debt of $7.52B less "
     "$6.96B of cash and marketable securities at September 30, 2026, excluding $2.05B of strategic "
     "investments) and divide by the 1.05B Q4 diluted share guide. The result is $135. As a cross-check, "
     "30x FY27E non-GAAP EPS of $4.51 also gives $135. We use 21x, below the ~23x the shares traded on "
     "at Tuesday's close, for three reasons: FCF excludes stock compensation, which is material, as the "
     "$953M quarterly GAAP-to-non-GAAP operating gap shows; organic growth is decelerating into the high "
     "teens; and the balance sheet now carries net debt. At the ~$122.60 indicated open the stock trades on "
     "18.9x EV/FY27E FCF and 27.2x FY27E EPS, vs. 23.2x and 33.3x at the $150.13 close (31.5x forward "
     "P/E on consensus).")
figure("fig11_price_vs_targets.png", "Share price, 52-week range and price targets",
       ["Share prices: NYSE close Oct 28, 2026 and indicated pre-market Oct 29, 2026 (approximate); 52-week "
        "range per market data; Morgan Stanley ($180 to $160, Overweight) and Citizens ($157, Outperform) "
        "notes dated Oct 29, 2026 as reported; Street average approximate; our PT."])
para("**Scenarios.** Bull ($171): FY27E subscription growth of 20% as cRPO re-accelerates on AI and "
     "renewals of services-heavy deals, a 37% FCF margin ($7.2B) and 25x. Base ($135): 17.5% growth, 35.5% "
     "margin, 21x. Bear ($96): growth slows to 15% on seat compression and public-sector friction, a 34% "
     "margin ($6.4B) and 16x, a multiple we think is consistent with mid-teens growth. From the ~$122.60 indicated price, the skew is +40% / +10% / -21%. That is balanced "
     "enough for a Hold but not compelling enough for a Buy until the cRPO trajectory is clearer.")
figure("fig12_valuation_sensitivity.png", "Implied value per share by EV/FY27E FCF multiple under bear/base/bull FCF",
       ["Our estimates; net debt and share count from ", REL, " (balance sheet at Sep 30, 2026; Q4'26 diluted share guide 1.05B)."])
para("**Why HOLD and not BUY after an 18% drop.** Growth above 20%, a 36% FCF margin and an AI ACV target "
     "raised twice this year describe a high-quality franchise, and the post-print price of ~27x FY27E EPS "
     "is undemanding for that profile. But the variable that sets this stock's multiple, forward cRPO growth, "
     "has just stepped down 250bp, and the Q4 guide leaves ~125bp of the decline unexplained. Organic growth "
     "is slowing beneath an acquisition-flattered headline, and debate over AI replacing seats will not be "
     "settled within a quarter. We would turn more constructive on evidence that Q4 cRPO lands at 19.5% or "
     "better, a 2027 framework that holds organic growth around 18% or higher, or buybacks resuming. We "
     "would turn more cautious if 1H27 cRPO falls below 17%.")

# ================================================================== APPENDIX: SOURCES
doc.add_heading("Sources & References", level=1)
para("All URLs below are clickable hyperlinks. Data were accessed October 29, 2026.", size=8.5, italic=True,
     color=GREY)


def src_item(label, desc, url):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.first_line_indent = Inches(-0.2)
    p.paragraph_format.space_after = Pt(2)
    set_run_font(p.add_run("•  "), size=9)
    add_hyperlink(p, label, url, size=9)
    set_run_font(p.add_run(" - " + desc), size=9)


para("Earnings materials (Q3 2026)", size=9.5, bold=True, space_after=2, keep_next=True)
src_item("ServiceNow Q3 2026 earnings release, Form 8-K Ex. 99.1 (filed Oct 28, 2026)",
         "reported results, Q4 and FY26 guidance, balance sheet, cash flow, stock split note", U["q3"])
src_item("Form 8-K/A, accession 0001373715-26-000095 (filed Oct 28, 2026)",
         "amendment filed solely to add Inline XBRL tagging omitted from the original 8-K; no figures changed",
         U["q3a"])
src_item("ServiceNow Q3 2026 earnings call transcript (The Motley Fool, Oct 29, 2026)",
         "management quotes, cRPO bridge items, AI metrics, analyst Q&A (third-party transcript)", U["fool"])
src_item("ServiceNow Investor Relations", "webcast replay and investor materials", U["ir"])
src_item("SEC EDGAR filing index, ServiceNow (CIK 0001373715)",
         "Q3'26 Form 10-Q not yet filed as of publication; balance-sheet data from the earnings release",
         U["edgar_all"])
para("Prior-period materials and prior guidance", size=9.5, bold=True, space_after=2, keep_next=True)
src_item("Q2 2026 earnings release (8-K Ex. 99.1, Jul 22, 2026)",
         "Q2'26 results; Q3'26 guidance; prior FY26 guidance ($15,760-15,780M; 35% FCF margin)", U["q2"])
src_item("Q1 2026 earnings release (8-K Ex. 99.1, Apr 22, 2026)",
         "Q1'26 results; Veza and Armis closing dates; ASR and buyback authorization", U["q1"])
src_item("Q4 2025 earnings release (8-K Ex. 99.1, Jan 28, 2026)",
         "Q4'25 and FY25 results; initial FY26 guidance; 5-for-1 split effective Dec 17, 2025; Moveworks closing",
         U["q4_25"])
src_item("Q3 2025 earnings release (8-K Ex. 99.1, Oct 29, 2025)",
         "Q3'25 results, cRPO and customer metrics; split announcement; Q4'25 guidance", U["q3_25"])
src_item("Q2 2025 earnings release (8-K Ex. 99.1, Jul 23, 2025)", "Q2'25 cRPO; Q3'25 guidance", U["q2_25"])
src_item("SEC EDGAR 8-K filing list, ServiceNow", "index of all Item 2.02 earnings filings", U["edgar"])
para("Consensus, sell-side and market data (no public link)", size=9.5, bold=True, space_after=2, keep_next=True)
for t in ["Consensus non-GAAP EPS of $1.02 and revenue of ~$4.09-4.10B: pre-earnings Street aggregates as cited "
          "in sell-side and press coverage, as of Oct 28, 2026. Not independently reconciled to a primary "
          "consensus database.",
          "Morgan Stanley (Overweight; PT $180 to $160), Oct 29, 2026: organic cRPO deceleration (~19% to ~18%), "
          "services-mix headwind (50-100bp to subscription growth in Q4'26 and 2027), T4C headwind (~50bp to "
          "2027 cRPO), Street Q4 cRPO expectation (~20%).",
          "Citizens (Outperform; PT $157), Oct 29, 2026. Street average PT of ~$157 is approximate.",
          "Share prices: NYSE close Oct 28, 2026 ($150.13); indicated pre-market Oct 29, 2026 (~$122.60, "
          "approximate and subject to change at the open); 52-week range $81.24-$192.97."]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.first_line_indent = Inches(-0.2)
    p.paragraph_format.space_after = Pt(2)
    set_run_font(p.add_run("•  " + t), size=9)

para("Disclosures: This report is for informational purposes only and is not investment advice. Estimates "
     "(E), price targets and scenario values are the author's own and are subject to change. Reported "
     "figures are taken from company filings; where figures could not be verified against a primary source "
     "this is stated. Rating definitions: BUY, expected 12-month total return above 15%; HOLD, -10% to +15%; "
     "SELL, below -10%.", size=7.5, italic=True, color=GREY)

doc.save(OUT)
print("saved", OUT)
