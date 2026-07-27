# ============================================================
# CORE/EMAIL_SENDER.PY — Email Delivery
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


def _site_url() -> str:
    """Returns the live site URL — never localhost."""
    return os.environ.get("SITE_URL", "https://marketmindai-8mir.onrender.com").rstrip("/")


# ── 1. SEND REPORT ────────────────────────────────────────────
def send_report(recipient_email, idea, pdf_path, results):
    try:
        print(f"[Email] Sending report to: {recipient_email}")
        msg = build_email(recipient_email, idea, pdf_path, results)
        send_via_smtp(msg, recipient_email)
        print(f"[Email] Report sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[Email] Send failed: {e}")
        return False


# ── 2. BUILD EMAIL ────────────────────────────────────────────
def build_email(recipient_email, idea, pdf_path, results):
    msg            = MIMEMultipart("mixed")
    msg["From"]    = Config.EMAIL_ADDRESS
    msg["To"]      = recipient_email
    msg["Subject"] = f"MarketMind AI Report — {idea[:50]}"

    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(build_plain_body(idea, results), "plain"))
    alt_part.attach(MIMEText(build_html_body(idea, results),  "html"))
    msg.attach(alt_part)

    logo_path = "app/static/images/logo2.jpg"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<logo>")
            logo.add_header("Content-Disposition", "inline", filename="logo.jpg")
            msg.attach(logo)

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf = MIMEBase("application", "octet-stream")
            pdf.set_payload(f.read())
            encoders.encode_base64(pdf)
            pdf.add_header("Content-Disposition", "attachment; filename=MarketMind_Report.pdf")
            msg.attach(pdf)

    return msg


# ── 3. HTML BODY ──────────────────────────────────────────────
def build_html_body(idea, results):
    ai      = results.get("ai_insights", {})
    verdict = ai.get("verdict", "GO")
    summary = ai.get("summary", "")
    mkt     = results.get("market_data", {})
    sf      = results.get("sales_forecast", {})
    recs    = ai.get("recommendations", [])[:3]
    rec_html = "".join(f"<li style='margin-bottom:8px;'>{r}</li>" for r in recs)
    verdict_color = "#00c853" if verdict == "GO" else "#ff3232"
    verdict_text  = "GO — Strong Market Potential!" if verdict == "GO" else "NO GO — Consider Refining"
    site = _site_url()

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Inter,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:15px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
  <tr>
    <td style="background:#0a1628;padding:30px;text-align:center;">
      <img src="cid:logo" height="60" alt="MarketMind AI" style="margin-bottom:10px;"><br>
      <span style="color:#00e5ff;font-size:22px;font-weight:700;">MarketMind AI</span><br>
      <span style="color:rgba(255,255,255,0.6);font-size:13px;">Market Intelligence Report</span>
    </td>
  </tr>
  <tr>
    <td style="background:#0d1f3c;padding:20px 30px;text-align:center;">
      <span style="color:rgba(255,255,255,0.6);font-size:12px;">ANALYZED IDEA</span><br>
      <span style="color:#fff;font-size:16px;font-weight:600;">"{idea}"</span>
    </td>
  </tr>
  <tr>
    <td style="padding:25px 30px;text-align:center;border-bottom:1px solid #eee;">
      <div style="display:inline-block;background:{verdict_color}20;border:2px solid {verdict_color};
                  border-radius:50px;padding:12px 30px;color:{verdict_color};font-size:18px;font-weight:700;">
        {verdict_text}
      </div>
    </td>
  </tr>
  <tr>
    <td style="padding:25px 30px;">
      <h3 style="color:#0a1628;margin-bottom:10px;">Executive Summary</h3>
      <p style="color:#666;line-height:1.7;margin:0;font-size:14px;">{summary}</p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 30px 25px;">
      <table width="100%" cellpadding="8" cellspacing="8">
      <tr>
        <td style="background:#f8f9fa;border-left:4px solid #00e5ff;border-radius:8px;text-align:center;width:25%;">
          <div style="font-size:16px;font-weight:700;color:#0a1628;">{mkt.get('market_size','N/A')}</div>
          <div style="font-size:11px;color:#999;">Market Size</div>
        </td>
        <td style="background:#f8f9fa;border-left:4px solid #00e5ff;border-radius:8px;text-align:center;width:25%;">
          <div style="font-size:16px;font-weight:700;color:#0a1628;">{mkt.get('competition_level','N/A')}</div>
          <div style="font-size:11px;color:#999;">Competition</div>
        </td>
        <td style="background:#f8f9fa;border-left:4px solid #00e5ff;border-radius:8px;text-align:center;width:25%;">
          <div style="font-size:16px;font-weight:700;color:#0a1628;">{mkt.get('profit_potential','N/A')}</div>
          <div style="font-size:11px;color:#999;">Profit Potential</div>
        </td>
        <td style="background:#f8f9fa;border-left:4px solid #00e5ff;border-radius:8px;text-align:center;width:25%;">
          <div style="font-size:16px;font-weight:700;color:#0a1628;">{mkt.get('trend_score','N/A')}/10</div>
          <div style="font-size:11px;color:#999;">Trend Score</div>
        </td>
      </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:0 30px 25px;border-bottom:1px solid #eee;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#0a1628;border-radius:10px;padding:20px;">
      <tr>
        <td style="text-align:center;padding:10px;">
          <div style="color:#00e5ff;font-size:11px;letter-spacing:1px;">PROJECTED ANNUAL REVENUE</div>
          <div style="color:#fff;font-size:28px;font-weight:700;">${sf.get('total_year', 0):,}</div>
          <div style="color:#00ff64;font-size:14px;font-weight:600;">{sf.get('growth_rate','N/A')} Growth</div>
        </td>
      </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:25px 30px;border-bottom:1px solid #eee;">
      <h3 style="color:#0a1628;margin-bottom:15px;">Top Recommendations</h3>
      <ul style="color:#666;line-height:1.8;font-size:14px;padding-left:20px;">{rec_html}</ul>
    </td>
  </tr>
  <tr>
    <td style="padding:25px 30px;text-align:center;">
      <p style="color:#666;font-size:14px;margin-bottom:15px;">Your full PDF report is attached.</p>
      <a href="{site}"
         style="background:#00e5ff;color:#0a1628;font-weight:700;padding:14px 35px;
                border-radius:50px;text-decoration:none;font-size:15px;display:inline-block;">
        Run Another Analysis
      </a>
    </td>
  </tr>
  <tr>
    <td style="background:#f8f9fa;padding:20px 30px;text-align:center;">
      <p style="color:#999;font-size:11px;margin:0;">
        Generated by MarketMind AI on {datetime.now().strftime("%B %d, %Y at %H:%M")}
      </p>
      <p style="color:#bbb;font-size:10px;margin:8px 0 0;">
        This report is AI-generated for research purposes. Always validate before making business decisions.
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""


# ── 4. PLAIN TEXT BODY ────────────────────────────────────────
def build_plain_body(idea, results):
    ai  = results.get("ai_insights", {})
    mkt = results.get("market_data", {})
    return f"""MarketMind AI — Market Intelligence Report
==========================================

ANALYZED IDEA: {idea}
VERDICT: {ai.get('verdict', 'GO')}

EXECUTIVE SUMMARY:
{ai.get('summary', '')}

MARKET OVERVIEW:
- Market Size      : {mkt.get('market_size', 'N/A')}
- Competition      : {mkt.get('competition_level', 'N/A')}
- Profit Potential : {mkt.get('profit_potential', 'N/A')}
- Trend Score      : {mkt.get('trend_score', 'N/A')}/10

TOP RECOMMENDATIONS:
{chr(10).join(f'- {r}' for r in ai.get('recommendations', [])[:3])}

Your full PDF report is attached.

-- MarketMind AI | {_site_url()}
Generated: {datetime.now().strftime("%B %d, %Y")}
AI-generated for research purposes only."""


# ── 5. SMTP SEND ──────────────────────────────────────────────
def send_via_smtp(msg, recipient_email):
    with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
        server.starttls()
        server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
        server.sendmail(Config.EMAIL_ADDRESS, recipient_email, msg.as_string())


# ── 6. PASSWORD RESET EMAIL ───────────────────────────────────
def send_reset_email(recipient_email: str, reset_url: str) -> bool:
    try:
        msg            = MIMEMultipart("alternative")
        msg["From"]    = Config.EMAIL_ADDRESS
        msg["To"]      = recipient_email
        msg["Subject"] = "Reset your MarketMind AI password"

        plain = f"""Hi,

You requested a password reset for your MarketMind AI account.

Reset link (valid for 1 hour):
{reset_url}

If you didn't request this, ignore this email.

-- MarketMind AI"""

        html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 0;">
<tr><td align="center">
<table width="520" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
  <tr>
    <td style="background:#0a1628;padding:28px 30px;text-align:center;">
      <span style="color:#00e5ff;font-size:20px;font-weight:700;">MarketMind AI</span><br>
      <span style="color:rgba(255,255,255,0.55);font-size:13px;">Password Reset</span>
    </td>
  </tr>
  <tr>
    <td style="padding:32px 30px 20px;">
      <p style="color:#333;font-size:15px;margin:0 0 16px;">Hi,</p>
      <p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 24px;">
        We received a request to reset your MarketMind AI password.
        The link below is valid for <strong>1 hour</strong>.
      </p>
      <div style="text-align:center;margin-bottom:28px;">
        <a href="{reset_url}"
           style="background:#00e5ff;color:#0a1628;font-weight:700;padding:14px 36px;
                  border-radius:50px;text-decoration:none;font-size:15px;display:inline-block;">
          Reset My Password
        </a>
      </div>
      <p style="color:#999;font-size:12px;margin:0;">
        Or copy this link: <a href="{reset_url}" style="color:#00a8c6;">{reset_url}</a>
      </p>
    </td>
  </tr>
  <tr>
    <td style="background:#f8f9fa;padding:18px 30px;text-align:center;">
      <p style="color:#bbb;font-size:11px;margin:0;">
        Didn't request this? You can safely ignore this email.
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))
        send_via_smtp(msg, recipient_email)
        print(f"[Email] Reset email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[Email] Reset email failed: {e}")
        return False
