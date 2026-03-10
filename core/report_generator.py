# ============================================================
# CORE/REPORT_GENERATOR.PY — PDF Report Generator
# Uses fpdf2 — no SerpAPI references
# ============================================================

import os
from datetime import datetime

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    print("Install fpdf2: pip install fpdf2")


# ── COLOURS ──────────────────────────────────────────────────
CYAN      = (0,   229, 255)
DARK      = (10,  22,  40)
WHITE     = (255, 255, 255)
GREY      = (150, 150, 150)
GREEN     = (0,   200, 100)
RED       = (255, 80,  80)
LIGHT_BG  = (18,  35,  60)


class MarketMindPDF(FPDF):

    def header(self):
        # Background bar
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 20, "F")

        # Logo text
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*CYAN)
        self.set_xy(10, 5)
        self.cell(0, 10, "MarketMind AI", ln=False)

        # Right side
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.set_xy(0, 7)
        self.cell(200, 6, "Market Intelligence Report", align="R")

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GREY)
        self.cell(0, 5,
            f"Page {self.page_no()} | MarketMind AI 2026 | AI-generated for research purposes only",
            align="C"
        )

    def section_title(self, title, icon=""):
        self.ln(4)
        self.set_fill_color(*LIGHT_BG)
        self.rect(10, self.get_y(), 190, 10, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*CYAN)
        self.set_x(13)
        self.cell(0, 10, f"{icon}  {title}", ln=True)
        self.ln(2)

    def body_text(self, text, color=WHITE):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*color)
        self.set_x(13)
        self.multi_cell(184, 6, self._clean(text))
        self.ln(1)

    def kpi_row(self, items):
        """Render a row of KPI boxes — items is list of (label, value)"""
        box_w  = 60
        box_h  = 18
        gap    = 5
        start_x= 13
        y      = self.get_y()

        for i, (label, value) in enumerate(items):
            x = start_x + i * (box_w + gap)
            self.set_fill_color(*LIGHT_BG)
            self.rect(x, y, box_w, box_h, "F")
            self.set_xy(x, y + 2)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*CYAN)
            self.cell(box_w, 7, self._clean(str(value)), align="C")
            self.set_xy(x, y + 9)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*GREY)
            self.cell(box_w, 6, label, align="C")

        self.ln(box_h + 5)

    def two_col(self, label, value, label_color=GREY, value_color=WHITE):
        self.set_x(13)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*label_color)
        self.cell(55, 6, label + ":", ln=False)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*value_color)
        self.cell(0, 6, self._clean(str(value)), ln=True)

    def divider(self):
        self.set_draw_color(*CYAN)
        self.set_line_width(0.3)
        self.line(13, self.get_y(), 197, self.get_y())
        self.ln(3)

    def _clean(self, text):
        """Remove characters that FPDF can't encode"""
        if not text:
            return ""
        replacements = {
            "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
            "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " ",
            "\u20ac": "EUR", "\u00a3": "GBP", "\u00ae": "(R)", "\u2122": "(TM)",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode("latin-1", errors="replace").decode("latin-1")


# ── MAIN FUNCTION ────────────────────────────────────────────
def generate_pdf(idea, results):
    if not FPDF_AVAILABLE:
        print("fpdf2 not installed")
        return None

    try:
        pdf = MarketMindPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(10, 22, 10)

        # ── PAGE 1: COVER ─────────────────────────────────────
        pdf.add_page()

        # Full-page dark background
        pdf.set_fill_color(*DARK)
        pdf.rect(0, 0, 210, 297, "F")

        # Title
        pdf.set_font("Helvetica", "B", 28)
        pdf.set_text_color(*CYAN)
        pdf.set_xy(0, 60)
        pdf.cell(210, 15, "MarketMind AI", align="C", ln=True)

        pdf.set_font("Helvetica", "", 14)
        pdf.set_text_color(*WHITE)
        pdf.cell(210, 10, "Market Intelligence Report", align="C", ln=True)

        # Divider line
        pdf.set_draw_color(*CYAN)
        pdf.set_line_width(0.8)
        pdf.line(60, pdf.get_y() + 5, 150, pdf.get_y() + 5)
        pdf.ln(15)

        # Idea
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*WHITE)
        pdf.cell(210, 10, f'"{pdf._clean(idea)}"', align="C", ln=True)
        pdf.ln(5)

        # Date
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*GREY)
        pdf.cell(210, 8,
            f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            align="C", ln=True
        )

        # Verdict banner
        ai      = results.get("ai_insights", {})
        verdict = ai.get("verdict", "GO")

        pdf.ln(20)
        color = GREEN if verdict == "GO" else RED
        pdf.set_fill_color(*color)
        pdf.set_xy(60, pdf.get_y())
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*DARK)
        pdf.cell(90, 15, f"VERDICT: {verdict}", align="C", fill=True)
        pdf.ln(30)

        # Data sources note
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*GREY)
        pdf.set_x(0)
        pdf.cell(210, 6,
            "Powered by Gemini AI | Google Trends | Web Intelligence",
            align="C", ln=True
        )


        # ── PAGE 2: ANALYSIS ──────────────────────────────────
        pdf.add_page()
        pdf.set_fill_color(*DARK)
        pdf.rect(0, 0, 210, 297, "F")

        # Executive Summary
        pdf.section_title("Executive Summary", "")
        pdf.body_text(ai.get("summary", "Analysis unavailable."))

        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*GREY)
        pdf.set_x(13)
        pdf.cell(0, 6, "Target Market:", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*WHITE)
        pdf.cell(0, 6, pdf._clean(ai.get("target_market", "N/A")), ln=True)
        pdf.ln(3)

        # Market Overview KPIs
        mkt = results.get("market_data", {})
        pdf.section_title("Market Overview", "")
        pdf.kpi_row([
            ("Market Size",      mkt.get("market_size",       "N/A")),
            ("Competition",      mkt.get("competition_level", "N/A")),
            ("Profit Potential", mkt.get("profit_potential",  "N/A")),
        ])
        pdf.two_col("Trend Score",
            f"{mkt.get('trend_score', 'N/A')}/10")
        pdf.ln(2)
        if mkt.get("trends_summary"):
            pdf.body_text(mkt["trends_summary"], color=GREY)

        # Competitors
        pdf.section_title("Competitor Analysis", "")
        competitors = results.get("competitors", [])
        if competitors:
            for c in competitors[:5]:
                pdf.set_x(13)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(*WHITE)
                pdf.cell(70, 6, pdf._clean(c.get("name", "N/A")), ln=False)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*GREY)
                share  = c.get("market_share", "N/A")
                threat = c.get("threat", "N/A")
                pdf.cell(0, 6, f"Share: {share}  |  Threat: {threat}", ln=True)
                if c.get("strength"):
                    pdf.set_x(20)
                    pdf.set_font("Helvetica", "", 8)
                    pdf.set_text_color(*GREY)
                    pdf.cell(0, 5,
                        f"Strength: {pdf._clean(c['strength'][:80])}",
                        ln=True
                    )
        else:
            pdf.body_text("No competitor data available.", color=GREY)

        # Niche Opportunities
        pdf.section_title("Niche Opportunities", "")
        niches = results.get("niches", [])
        if niches:
            for n in niches[:5]:
                pdf.set_x(13)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(*WHITE)
                score = n.get("score", 0)
                pdf.cell(120, 6,
                    pdf._clean(n.get("name", "N/A")),
                    ln=False
                )
                pdf.set_text_color(*CYAN)
                pdf.cell(0, 6, f"Score: {score}/100", ln=True)
                pdf.set_x(20)
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*GREY)
                pdf.cell(0, 5,
                    pdf._clean(n.get("description", "")[:90]),
                    ln=True
                )
                pdf.ln(1)
        else:
            pdf.body_text("No niche data available.", color=GREY)


        # ── PAGE 3: FORECAST + RECOMMENDATIONS ────────────────
        pdf.add_page()
        pdf.set_fill_color(*DARK)
        pdf.rect(0, 0, 210, 297, "F")

        # Sales Forecast
        sf = results.get("sales_forecast", {})
        pdf.section_title("12-Month Sales Forecast", "")
        pdf.kpi_row([
            ("Annual Revenue", f"${sf.get('total_year', 0):,}"),
            ("Growth Rate",    sf.get("growth_rate", "N/A")),
            ("Peak Month",     sf.get("peak_month",  "N/A")),
        ])

        # Monthly table
        months  = sf.get("months",  [])
        revenue = sf.get("revenue", [])
        if months and revenue:
            # Header row
            pdf.set_x(13)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*CYAN)
            col_w = 184 / min(len(months), 12)
            for m in months[:12]:
                pdf.cell(col_w, 6, pdf._clean(m), align="C", border=False)
            pdf.ln()

            # Value row
            pdf.set_x(13)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*WHITE)
            for v in revenue[:12]:
                pdf.cell(col_w, 6, f"${v:,}", align="C", border=False)
            pdf.ln(8)

        if sf.get("summary"):
            pdf.body_text(sf["summary"], color=GREY)

        pdf.ln(3)

        # AI Recommendations
        pdf.section_title("AI Recommendations", "")
        recs = ai.get("recommendations", [])
        if recs:
            for i, rec in enumerate(recs, 1):
                pdf.set_x(13)
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(*CYAN)
                pdf.cell(8, 6, f"{i}.", ln=False)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*WHITE)
                pdf.multi_cell(176, 6, pdf._clean(rec))
        else:
            pdf.body_text("No recommendations available.", color=GREY)

        pdf.ln(3)

        # Pricing Strategy
        pricing = ai.get("pricing", {})
        pdf.section_title("Pricing Strategy", "")
        pdf.kpi_row([
            ("Budget Tier",  pricing.get("budget",  "N/A")),
            ("Mid Tier",     pricing.get("mid",     "N/A")),
            ("Premium Tier", pricing.get("premium", "N/A")),
        ])

        # Final Verdict
        pdf.section_title("Final Verdict", "")
        pdf.set_x(13)
        color = GREEN if verdict == "GO" else RED
        pdf.set_fill_color(*color)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*DARK)
        label = (
            "GO - This idea has strong market potential!"
            if verdict == "GO"
            else "NO GO - Consider refining this idea"
        )
        pdf.cell(184, 12, label, fill=True, align="C", ln=True)
        pdf.ln(3)
        pdf.body_text(ai.get("verdict_reason", ""), color=GREY)

        pdf.ln(5)
        pdf.divider()
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*GREY)
        pdf.set_x(13)
        pdf.multi_cell(184, 5,
            "DISCLAIMER: This report is generated by MarketMind AI for research "
            "and informational purposes only. All data, predictions and recommendations "
            "are AI-generated and should not be considered as professional financial, "
            "legal or business advice. Always conduct your own due diligence before "
            "making any business decisions. MarketMind AI 2026"
        )

        # ── SAVE FILE ─────────────────────────────────────────
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_idea = "".join(
            c for c in idea[:30] if c.isalnum() or c in " _-"
        ).strip().replace(" ", "_")
        filename  = f"reports/MarketMind_{safe_idea}_{timestamp}.pdf"
        pdf.output(filename)

        print(f"PDF saved: {filename}")
        return filename

    except Exception as e:
        print(f"PDF generation error: {e}")
        return None