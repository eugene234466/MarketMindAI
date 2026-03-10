# ============================================================
# CORE/EMAIL_SENDER.PY — Email Delivery
# Sends the generated PDF report via email
# Uses smtplib with Gmail SMTP
# Supports plain text + HTML emails with PDF attachment
# ============================================================

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from datetime import datetime
from config import Config


# ── 1. MAIN FUNCTION ─────────────────────────────────────────
# Called from routes.py
# Sends PDF report to recipient email
def send_report(recipient_email, idea, pdf_path, results):
    try:
        print(f"📧 Sending report to: {recipient_email}")

        # ── BUILD EMAIL ──────────────────────────────────────
        msg = build_email(
            recipient_email,
            idea,
            pdf_path,
            results
        )

        # ── SEND EMAIL ───────────────────────────────────────
        send_via_smtp(msg, recipient_email)

        print(f"✅ Report sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False


# ── 2. BUILD EMAIL ───────────────────────────────────────────
# Constructs the full email with HTML body + PDF attachment
def build_email(recipient_email, idea, pdf_path, results):

    # ── EMAIL STRUCTURE ──────────────────────────────────────
    msg                 = MIMEMultipart("mixed")
    msg["From"]         = Config.EMAIL_ADDRESS
    msg["To"]           = recipient_email
    msg["Subject"]      = f"🧠 MarketMind AI Report — {idea[:50]}"

    # ── ATTACH HTML BODY ─────────────────────────────────────
    html_body  = build_html_body(idea, results)
    plain_body = build_plain_body(idea, results)

    # Create alternative part for plain + HTML
    alt_part   = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(plain_body, "plain"))
    alt_part.attach(MIMEText(html_body,  "html"))
    msg.attach(alt_part)

    # ── ATTACH LOGO IMAGE ────────────────────────────────────
    logo_path = "app/static/images/logo2.jpg"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as logo_file:
            logo = MIMEImage(logo_file.read())
            logo.add_header("Content-ID", "<logo>")
            logo.add_header(
                "Content-Disposition", "inline",
                filename="logo.jpg"
            )
            msg.attach(logo)

    # ── ATTACH PDF REPORT ────────────────────────────────────
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as pdf_file:
            pdf_attachment          = MIMEBase(
                "application", "octet-stream"
            )
            pdf_attachment.set_payload(pdf_file.read())
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                "Content-Disposition",
                f"attachment; filename=MarketMind_Report.pdf"
            )
            msg.attach(pdf_attachment)

    return msg


# ── 3. BUILD HTML BODY ───────────────────────────────────────
# Professional HTML email template
# Matches MarketMind AI branding
def build_html_body(idea, results):

    # Extract key data
    ai_insights    = results.get("ai_insights", {})
    verdict        = ai_insights.get("verdict", "GO")
    summary        = ai_insights.get("summary", "")
    market_data    = results.get("market_data", {})
    market_size    = market_data.get("market_size", "N/A")
    competition    = market_data.get("competition_level", "N/A")
    profit         = market_data.get("profit_potential", "N/A")
    trend_score    = market_data.get("trend_score", "N/A")
    total_revenue  = results.get(
        "sales_forecast", {}
    ).get("total_year", 0)
    growth_rate    = results.get(
        "sales_forecast", {}
    ).get("growth_rate", "N/A")

    # Verdict styling
    if verdict == "GO":
        verdict_color = "#00c853"
        verdict_text  = "✅ GO — Strong Market Potential!"
    else:
        verdict_color = "#ff3232"
        verdict_text  = "❌ NO GO — Consider Refining"

    # Top 3 recommendations
    recommendations = ai_insights.get("recommendations", [])[:3]
    rec_html = "".join([
        f"<li style='margin-bottom:8px;'>{rec}</li>"
        for rec in recommendations
    ])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background:#f4f4f4;
                 font-family: Inter, Arial, sans-serif;">

        <!-- ── WRAPPER ──────────────────────────────────── -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:#f4f4f4; padding:30px 0;">
        <tr><td align="center">

        <!-- ── EMAIL CONTAINER ──────────────────────────── -->
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff; border-radius:15px;
                      overflow:hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">

            <!-- ── HEADER ───────────────────────────────── -->
            <tr>
                <td style="background:#0a1628; padding:30px;
                           text-align:center;">
                    <img src="cid:logo" height="60"
                         alt="MarketMind AI"
                         style="margin-bottom:10px;"><br>
                    <span style="color:#00e5ff; font-size:22px;
                                 font-weight:700;">
                        MarketMind AI
                    </span><br>
                    <span style="color:rgba(255,255,255,0.6);
                                 font-size:13px;">
                        Market Intelligence Report Ready
                    </span>
                </td>
            </tr>

            <!-- ── IDEA BANNER ───────────────────────────── -->
            <tr>
                <td style="background:#0d1f3c; padding:20px 30px;
                           text-align:center;">
                    <span style="color:rgba(255,255,255,0.6);
                                 font-size:12px;">
                        ANALYZED IDEA
                    </span><br>
                    <span style="color:#ffffff; font-size:16px;
                                 font-weight:600;">
                        "{idea}"
                    </span>
                </td>
            </tr>

            <!-- ── VERDICT ──────────────────────────────── -->
            <tr>
                <td style="padding:25px 30px; text-align:center;
                           border-bottom:1px solid #eee;">
                    <div style="display:inline-block;
                                background:{verdict_color}20;
                                border:2px solid {verdict_color};
                                border-radius:50px;
                                padding:12px 30px;
                                color:{verdict_color};
                                font-size:18px;
                                font-weight:700;">
                        {verdict_text}
                    </div>
                </td>
            </tr>

            <!-- ── SUMMARY ──────────────────────────────── -->
            <tr>
                <td style="padding:25px 30px;">
                    <h3 style="color:#0a1628; margin-bottom:10px;">
                        Executive Summary
                    </h3>
                    <p style="color:#666; line-height:1.7;
                              margin:0; font-size:14px;">
                        {summary}
                    </p>
                </td>
            </tr>

            <!-- ── KPI CARDS ────────────────────────────── -->
            <tr>
                <td style="padding:0 30px 25px;">
                    <table width="100%" cellpadding="8"
                           cellspacing="8">
                    <tr>
                        <!-- Market Size -->
                        <td style="background:#f8f9fa;
                                   border-left:4px solid #00e5ff;
                                   border-radius:8px;
                                   text-align:center; width:25%;">
                            <div style="font-size:20px;
                                        font-weight:700;
                                        color:#0a1628;">
                                {market_size}
                            </div>
                            <div style="font-size:11px;
                                        color:#999;">
                                Market Size
                            </div>
                        </td>

                        <!-- Competition -->
                        <td style="background:#f8f9fa;
                                   border-left:4px solid #00e5ff;
                                   border-radius:8px;
                                   text-align:center; width:25%;">
                            <div style="font-size:20px;
                                        font-weight:700;
                                        color:#0a1628;">
                                {competition}
                            </div>
                            <div style="font-size:11px;
                                        color:#999;">
                                Competition
                            </div>
                        </td>

                        <!-- Profit -->
                        <td style="background:#f8f9fa;
                                   border-left:4px solid #00e5ff;
                                   border-radius:8px;
                                   text-align:center; width:25%;">
                            <div style="font-size:20px;
                                        font-weight:700;
                                        color:#0a1628;">
                                {profit}
                            </div>
                            <div style="font-size:11px;
                                        color:#999;">
                                Profit Potential
                            </div>
                        </td>

                        <!-- Trend Score -->
                        <td style="background:#f8f9fa;
                                   border-left:4px solid #00e5ff;
                                   border-radius:8px;
                                   text-align:center; width:25%;">
                            <div style="font-size:20px;
                                        font-weight:700;
                                        color:#0a1628;">
                                {trend_score}/10
                            </div>
                            <div style="font-size:11px;
                                        color:#999;">
                                Trend Score
                            </div>
                        </td>
                    </tr>
                    </table>
                </td>
            </tr>

            <!-- ── FORECAST ─────────────────────────────── -->
            <tr>
                <td style="padding:0 30px 25px;
                           border-bottom:1px solid #eee;">
                    <table width="100%" cellpadding="0"
                           cellspacing="0"
                           style="background:#0a1628;
                                  border-radius:10px;
                                  padding:20px;">
                    <tr>
                        <td style="text-align:center; padding:10px;">
                            <div style="color:#00e5ff; font-size:11px;
                                        letter-spacing:1px;">
                                PROJECTED ANNUAL REVENUE
                            </div>
                            <div style="color:#ffffff; font-size:28px;
                                        font-weight:700;">
                                ${total_revenue:,}
                            </div>
                            <div style="color:#00ff64; font-size:14px;
                                        font-weight:600;">
                                {growth_rate} Growth
                            </div>
                        </td>
                    </tr>
                    </table>
                </td>
            </tr>

            <!-- ── RECOMMENDATIONS ──────────────────────── -->
            <tr>
                <td style="padding:25px 30px;
                           border-bottom:1px solid #eee;">
                    <h3 style="color:#0a1628; margin-bottom:15px;">
                        Top AI Recommendations
                    </h3>
                    <ul style="color:#666; line-height:1.8;
                               font-size:14px; padding-left:20px;">
                        {rec_html}
                    </ul>
                </td>
            </tr>

            <!-- ── CTA BUTTON ────────────────────────────── -->
            <tr>
                <td style="padding:25px 30px; text-align:center;">
                    <p style="color:#666; font-size:14px;
                              margin-bottom:15px;">
                        Your full PDF report is attached to this email.
                    </p>
                    <a href="http://localhost:5000"
                       style="background:#00e5ff; color:#0a1628;
                              font-weight:700; padding:14px 35px;
                              border-radius:50px; text-decoration:none;
                              font-size:15px; display:inline-block;">
                        🔍 Run Another Analysis
                    </a>
                </td>
            </tr>

            <!-- ── FOOTER ────────────────────────────────── -->
            <tr>
                <td style="background:#f8f9fa; padding:20px 30px;
                           text-align:center; border-radius:0 0 15px 15px;">
                    <p style="color:#999; font-size:11px; margin:0;">
                        Generated by MarketMind AI on
                        {datetime.now().strftime("%B %d, %Y at %H:%M")}
                    </p>
                    <p style="color:#bbb; font-size:10px; margin:8px 0 0;">
                        ⚠️ This report is AI-generated for research purposes.
                        Always validate findings before making business decisions.
                    </p>
                </td>
            </tr>

        </table>
        <!-- END EMAIL CONTAINER -->

        </td></tr>
        </table>
        <!-- END WRAPPER -->

    </body>
    </html>
    """


# ── 4. BUILD PLAIN TEXT BODY ─────────────────────────────────
# Fallback plain text version for email clients
# that don't support HTML
def build_plain_body(idea, results):
    ai_insights = results.get("ai_insights", {})
    verdict     = ai_insights.get("verdict", "GO")
    summary     = ai_insights.get("summary", "")
    market_data = results.get("market_data", {})

    return f"""
MarketMind AI — Market Intelligence Report
==========================================

ANALYZED IDEA: {idea}

VERDICT: {verdict}

EXECUTIVE SUMMARY:
{summary}

MARKET OVERVIEW:
- Market Size      : {market_data.get("market_size", "N/A")}
- Competition      : {market_data.get("competition_level", "N/A")}
- Profit Potential : {market_data.get("profit_potential", "N/A")}
- Trend Score      : {market_data.get("trend_score", "N/A")}/10

TOP RECOMMENDATIONS:
{chr(10).join([f"- {r}" for r in ai_insights.get("recommendations", [])[:3]])}

Your full PDF report is attached to this email.

--
Generated by MarketMind AI on {datetime.now().strftime("%B %d, %Y")}
⚠️ AI-generated for research purposes only.
    """


# ── 5. SEND VIA SMTP ─────────────────────────────────────────
# Connects to Gmail SMTP and sends the email
def send_via_smtp(msg, recipient_email):
    with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
        server.starttls()
        server.login(
            Config.EMAIL_ADDRESS,
            Config.EMAIL_PASSWORD
        )
        server.sendmail(
            Config.EMAIL_ADDRESS,
            recipient_email,
            msg.as_string()
        )


# ── 6. SEND WELCOME EMAIL ────────────────────────────────────
# Sends a welcome email when user first uses the app
def send_welcome_email(recipient_email):
    try:
        msg             = MIMEMultipart("alternative")
        msg["From"]     = Config.EMAIL_ADDRESS
        msg["To"]       = recipient_email
        msg["Subject"]  = "🧠 Welcome to MarketMind AI!"

        body = MIMEText(f"""
        Welcome to MarketMind AI!

        You can now analyze any business idea and get:
        ✅ Real-time market trends
        ✅ Competitor analysis
        ✅ Sales predictions
        ✅ Niche opportunities
        ✅ Professional PDF reports

        Visit: http://localhost:5000

        -- MarketMind AI Team
        """, "plain")

        msg.attach(body)
        send_via_smtp(msg, recipient_email)
        print(f"✅ Welcome email sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Welcome email failed: {e}")
        return False
