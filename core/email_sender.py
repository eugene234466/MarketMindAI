# ============================================================
# CORE/EMAIL_SENDER.PY
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


def send_report(recipient_email, idea, pdf_path, results):

    try:

        msg = build_email(recipient_email, idea, pdf_path, results)
        send_via_smtp(msg, recipient_email)

        print(f"Email sent to {recipient_email}")
        return True

    except Exception as e:

        print(f"Email sending failed: {e}")
        return False


def build_email(recipient_email, idea, pdf_path, results):

    msg = MIMEMultipart("mixed")

    msg["From"] = Config.EMAIL_ADDRESS
    msg["To"] = recipient_email
    msg["Subject"] = f"MarketMind Report — {idea[:50]}"

    alt = MIMEMultipart("alternative")

    alt.attach(MIMEText("Your MarketMind report is attached.", "plain"))
    alt.attach(MIMEText("<h2>Your MarketMind report is ready.</h2>", "html"))

    msg.attach(alt)

    logo_path = os.path.join("app", "static", "images", "logo2.jpg")

    if os.path.exists(logo_path):

        with open(logo_path, "rb") as f:

            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<logo>")

            msg.attach(logo)

    if pdf_path and os.path.exists(pdf_path):

        with open(pdf_path, "rb") as f:

            part = MIMEBase("application", "octet-stream")

            part.set_payload(f.read())

            encoders.encode_base64(part)

            part.add_header(
                "Content-Disposition",
                "attachment; filename=MarketMind_Report.pdf"
            )

            msg.attach(part)

    return msg


def send_via_smtp(msg, recipient):

    with smtplib.SMTP(
        Config.SMTP_SERVER,
        Config.SMTP_PORT,
        timeout=10
    ) as server:

        server.starttls()

        server.login(
            Config.EMAIL_ADDRESS,
            Config.EMAIL_PASSWORD
        )

        server.sendmail(
            Config.EMAIL_ADDRESS,
            recipient,
            msg.as_string()
        )
