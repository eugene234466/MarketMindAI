# ============================================================
# CORE/EMAIL_SENDER.PY — Email Delivery via Resend API
# ============================================================

import os
import resend
from datetime import datetime
from config import Config

resend.api_key = os.environ.get("RESEND_API_KEY", "")
FROM_ADDRESS   = os.environ.get("RESEND_FROM", "MarketMind AI <onboarding@resend.dev>")


def _site_url() -> str:
    return os.environ.get("SITE_URL", "https://marketmindai-8mir.onrender.com").rstrip("/")


# ── 1. SEND REPORT ────────────────────────────────────────────
def send_report(recipient_email, idea, pdf_path, results):
    try:
        print(f"[Email] Sending report to: {recipient_email}")

        params = {
            "from":    FROM_ADDRESS,
            "to":      [recipient_email],
            "subject": "MarketMind AI Report — " + idea[:50],
            "html":    build_html_body(idea, results),
            "text":    build_plain_body(idea, results),
        }

        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                params["attachments"] = [{
                    "filename": "MarketMind_Report.pdf",
                    "content":  list(f.read()),
                }]

        resend.Emails.send(params)
        print(f"[Email] Report sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"[Email] Send failed: {e}")
        return False


# ── 2. SEND PASSWORD RESET EMAIL ─────────────────────────────
def send_reset_email(recipient_email, reset_url):
    try:
        plain = (
            "Hi,\n\n"
            "You requested a password reset for your MarketMind AI account.\n\n"
            "Reset link (valid for 1 hour):\n"
            + reset_url + "\n\n"
            "If you didn't request this, ignore this email.\n\n"
            "-- MarketMind AI"
        )

        html = (
            "<!DOCTYPE html><html><body style='margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;'>"
            "<table width='100%' cellpadding='0' cellspacing='0' style='background:#f4f4f4;padding:30px 0;'>"
            "<tr><td align='center'>"
            "<table width='520' cellpadding='0' cellspacing='0' "
            "style='background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);'>"
            "<tr><td style='background:#0a1628;padding:28px 30px;text-align:center;'>"
            "<span style='color:#00e5ff;font-size:20px;font-weight:700;'>MarketMind AI</span><br>"
            "<span style='color:rgba(255,255,255,0.55);font-size:13px;'>Password Reset</span>"
            "</td></tr>"
            "<tr><td style='padding:32px 30px 20px;'>"
            "<p style='color:#333;font-size:15px;margin:0 0 16px;'>Hi,</p>"
            "<p style='color:#555;font-size:14px;line-height:1.7;margin:0 0 24px;'>"
            "We received a request to reset your MarketMind AI password. "
            "The link below is valid for <strong>1 hour</strong>.</p>"
            "<div style='text-align:center;margin-bottom:28px;'>"
            "<a href='" + reset_url + "' "
            "style='background:#00e5ff;color:#0a1628;font-weight:700;padding:14px 36px;"
            "border-radius:50px;text-decoration:none;font-size:15px;display:inline-block;'>"
            "Reset My Password</a></div>"
            "<p style='color:#999;font-size:12px;margin:0;'>Or copy this link:<br>"
            "<a href='" + reset_url + "' style='color:#00a8c6;'>" + reset_url + "</a></p>"
            "</td></tr>"
            "<tr><td style='background:#f8f9fa;padding:18px 30px;text-align:center;'>"
            "<p style='color:#bbb;font-size:11px;margin:0;'>Didn't request this? You can safely ignore this email.</p>"
            "</td></tr>"
            "</table></td></tr></table></body></html>"
        )

        resend.Emails.send({
            "from":    FROM_ADDRESS,
            "to":      [recipient_email],
            "subject": "Reset your MarketMind AI password",
            "html":    html,
            "text":    plain,
        })
        print(f"[Email] Reset email sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"[Email] Reset email failed: {e}")
        return False


# ── 3. HTML BODY ──────────────────────────────────────────────
def build_html_body(idea, results):
    # Extract all values first — no method calls inside the f-string
    ai             = results.get("ai_insights") or {}
    mkt            = results.get("market_data") or {}
    sf             = results.get("sales_forecast") or {}

    verdict        = ai.get("verdict") or "GO"
    summary        = ai.get("summary") or ""
    market_size    = mkt.get("market_size") or "N/A"
    competition    = mkt.get("competition_level") or "N/A"
    profit         = mkt.get("profit_potential") or "N/A"
    trend_score    = mkt.get("trend_score") or "N/A"
    total_year     = sf.get("total_year") or 0
    growth_rate    = sf.get("growth_rate") or "N/A"

    total_year_fmt = f"{total_year:,}"
    generated_at   = datetime.now().strftime("%B %d, %Y at %H:%M")
    site           = _site_url()

    verdict_color  = "#00c853" if verdict == "GO" else "#ff3232"
    verdict_bg     = "#00c85320" if verdict == "GO" else "#ff323220"
    verdict_text   = "GO — Strong Market Potential!" if verdict == "GO" else "NO GO — Consider Refining"

    recs     = (ai.get("recommendations") or [])[:3]
    rec_html = "".join(
        "<li style='margin-bottom:8px;'>" + r + "</li>"
        for r in recs
    )

    return (
        "<!DOCTYPE html><html><body style='margin:0;padding:0;background:#f4f4f4;font-family:Inter,Arial,sans-serif;'>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='background:#f4f4f4;padding:30px 0;'>"
        "<tr><td align='center'>"
        "<table width='600' cellpadding='0' cellspacing='0' "
        "style='background:#fff;border-radius:15px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);'>"

        # Header
        "<tr><td style='background:#0a1628;padding:30px;text-align:center;'>"
        "<span style='color:#00e5ff;font-size:22px;font-weight:700;'>MarketMind AI</span><br>"
        "<span style='color:rgba(255,255,255,0.6);font-size:13px;'>Market Intelligence Report</span>"
        "</td></tr>"

        # Idea banner
        "<tr><td style='background:#0d1f3c;padding:20px 30px;text-align:center;'>"
        "<span style='color:rgba(255,255,255,0.6);font-size:12px;'>ANALYZED IDEA</span><br>"
        "<span style='color:#fff;font-size:16px;font-weight:600;'>\"" + idea + "\"</span>"
        "</td></tr>"

        # Verdict
        "<tr><td style='padding:25px 30px;text-align:center;border-bottom:1px solid #eee;'>"
        "<div style='display:inline-block;background:" + verdict_bg + ";border:2px solid " + verdict_color + ";"
        "border-radius:50px;padding:12px 30px;color:" + verdict_color + ";font-size:18px;font-weight:700;'>"
        + verdict_text +
        "</div></td></tr>"

        # Summary
        "<tr><td style='padding:25px 30px;'>"
        "<h3 style='color:#0a1628;margin-bottom:10px;'>Executive Summary</h3>"
        "<p style='color:#666;line-height:1.7;margin:0;font-size:14px;'>" + summary + "</p>"
        "</td></tr>"

        # KPI cards
        "<tr><td style='padding:0 30px 25px;'>"
        "<table width='100%' cellpadding='8' cellspacing='8'><tr>"
        "<td style='background:#f8f9fa;border-left:4px solid #00e5ff;border-radius:8px;text-align:center;'>"
        "<div style='font-size:16px;font-weight:700;color:#0a1628;'>" + market_size + "</div>"
        "<div style='font-size:11px;color:#999;'>Market Size</div></td>"
        "<td style='background:#f8f9fa;border-left:4px solid #00e5ff;border-radius:8px;text-align:center;'>"
        "<div style='font-size:16px;font-weight:700;color:#0a1628;'>" + competition + "</div>"
        "<div style='font-size:11px;color:#999;'>Competition</div></td>"
        "<td style='background:#f8f9fa;border-left:4px solid #00e5ff;border-radius:8px;text-align:center;'>"
        "<div style='font-size:16px;font-weight:700;color:#0a1628;'>" + profit + "</div>"
        "<div style='font-size:11px;color:#999;'>Profit Potential</div></td>"
        "<td style='background:#f8f9fa;border-left:4px solid #00e5ff;border-radius:8px;text-align:center;'>"
        "<div style='font-size:16px;font-weight:700;color:#0a1628;'>" + str(trend_score) + "/10</div>"
        "<div style='font-size:11px;color:#999;'>Trend Score</div></td>"
        "</tr></table></td></tr>"

        # Revenue forecast
        "<tr><td style='padding:0 30px 25px;border-bottom:1px solid #eee;'>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='background:#0a1628;border-radius:10px;padding:20px;'>"
        "<tr><td style='text-align:center;padding:10px;'>"
        "<div style='color:#00e5ff;font-size:11px;letter-spacing:1px;'>PROJECTED ANNUAL REVENUE</div>"
        "<div style='color:#fff;font-size:28px;font-weight:700;'>$" + total_year_fmt + "</div>"
        "<div style='color:#00ff64;font-size:14px;font-weight:600;'>" + growth_rate + " Growth</div>"
        "</td></tr></table></td></tr>"

        # Recommendations
        "<tr><td style='padding:25px 30px;border-bottom:1px solid #eee;'>"
        "<h3 style='color:#0a1628;margin-bottom:15px;'>Top Recommendations</h3>"
        "<ul style='color:#666;line-height:1.8;font-size:14px;padding-left:20px;'>" + rec_html + "</ul>"
        "</td></tr>"

        # CTA
        "<tr><td style='padding:25px 30px;text-align:center;'>"
        "<p style='color:#666;font-size:14px;margin-bottom:15px;'>Your full PDF report is attached.</p>"
        "<a href='" + site + "' style='background:#00e5ff;color:#0a1628;font-weight:700;padding:14px 35px;"
        "border-radius:50px;text-decoration:none;font-size:15px;display:inline-block;'>Run Another Analysis</a>"
        "</td></tr>"

        # Footer
        "<tr><td style='background:#f8f9fa;padding:20px 30px;text-align:center;'>"
        "<p style='color:#999;font-size:11px;margin:0;'>Generated by MarketMind AI on " + generated_at + "</p>"
        "<p style='color:#bbb;font-size:10px;margin:8px 0 0;'>"
        "This report is AI-generated for research purposes. Always validate before making business decisions.</p>"
        "</td></tr>"

        "</table></td></tr></table></body></html>"
    )


# ── 4. PLAIN TEXT BODY ────────────────────────────────────────
def build_plain_body(idea, results):
    ai   = results.get("ai_insights") or {}
    mkt  = results.get("market_data") or {}
    recs = (ai.get("recommendations") or [])[:3]
    site = _site_url()
    date = datetime.now().strftime("%B %d, %Y")

    rec_lines = "\n".join("- " + r for r in recs)

    return (
        "MarketMind AI — Market Intelligence Report\n"
        "==========================================\n\n"
        "ANALYZED IDEA: " + idea + "\n"
        "VERDICT: " + (ai.get("verdict") or "GO") + "\n\n"
        "EXECUTIVE SUMMARY:\n" + (ai.get("summary") or "") + "\n\n"
        "MARKET OVERVIEW:\n"
        "- Market Size      : " + (mkt.get("market_size") or "N/A") + "\n"
        "- Competition      : " + (mkt.get("competition_level") or "N/A") + "\n"
        "- Profit Potential : " + (mkt.get("profit_potential") or "N/A") + "\n"
        "- Trend Score      : " + str(mkt.get("trend_score") or "N/A") + "/10\n\n"
        "TOP RECOMMENDATIONS:\n" + rec_lines + "\n\n"
        "Your full PDF report is attached.\n\n"
        "-- MarketMind AI | " + site + "\n"
        "Generated: " + date + "\n"
        "AI-generated for research purposes only."
    )
