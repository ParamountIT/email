import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Amazon SES SMTP Configuration
SMTP_SERVER = "email-smtp.eu-west-2.amazonaws.com"
SMTP_PORT = 465

# Email details
SENDER_EMAIL = "contact@riseportraits.co.uk"
SUBJECT_TEMPLATE = "Let’s Make {event} Unforgettable — Your Photography Partner"

# Load HTML template
try:
    with open("./templates/LEAD-team-aretas.html", "r", encoding="utf-8") as f:
        html_template = f.read()
except Exception as e:
    print(f"Error reading HTML template: {e}")
    exit()

# Load recipient data from CSV
print("Loading email list from CSV...")
try:
    email_data = pd.read_csv("./addresses/test.csv")
    print(f"Loaded {len(email_data)} emails.")
except Exception as e:
    print(f"Error loading CSV: {e}")
    exit()

def send_email(recipient_email, event_name):
    subject = SUBJECT_TEMPLATE.format(event=event_name)
    html_body = html_template.replace("{event}", event_name)

    print(f"Preparing email for: {recipient_email} | Event: {event_name}")

    try:
        # Construct email message
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        # Connect to SMTP server
        print("Connecting to SMTP server...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        print("Sending email...")
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()

        print(f"✅ Email sent to {recipient_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {str(e)}")

# Send emails one by one
for index, row in email_data.iterrows():
    send_email(row["email"], row["event"])
