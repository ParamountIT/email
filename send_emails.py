import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import argparse
import re

# Load environment variables from .env file
load_dotenv()

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Amazon SES SMTP Configuration
SMTP_SERVER = "email-smtp.eu-west-2.amazonaws.com"
SMTP_PORT = 465

# Email details
SENDER_EMAIL = "contact@riseportraits.co.uk"
SUBJECT_TEMPLATE = "Beautiful Memories of Every Tumble, Stretch, and Smile at {event}!"

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Send emails with a skip list.")
parser.add_argument("email_list", help="Path to the CSV file containing the email list.")
parser.add_argument("skip_list", help="Path to the CSV file containing the skip list.")
args = parser.parse_args()

# Load HTML template
try:
    with open("./templates/LEAD-gymnastics.html", "r", encoding="utf-8") as f:
        html_template = f.read()
except Exception as e:
    print(f"Error reading HTML template: {e}")
    exit()

# Check if the HTML template contains the {event} placeholder
event_placeholder_in_template = "{event}" in html_template

# Load recipient data from the provided email list CSV
print("Loading email list from CSV...")
try:
    email_data = pd.read_csv(args.email_list)
    print(f"Loaded {len(email_data)} emails.")
except Exception as e:
    print(f"Error loading email list CSV: {e}")
    exit()

# Check if the event column is present in the CSV
event_column_present = "event" in email_data.columns

# Abort if the {event} placeholder is in the template but the event column is missing
if event_placeholder_in_template and not event_column_present:
    print("Error: The HTML template contains the {event} placeholder, but the 'event' column is missing in the email list CSV.")
    exit()

# Load skip list from the provided skip list CSV
print("Loading skip list from CSV...")
try:
    skip_list = pd.read_csv(args.skip_list)
    skip_emails = set(skip_list["email"])
    print(f"Loaded {len(skip_emails)} emails to skip.")
except Exception as e:
    print(f"Error loading skip list CSV: {e}")
    exit()

# Filter out emails in the skip list
filtered_email_data = email_data[~email_data["email"].isin(skip_emails)]
print(f"Filtered email list: {len(filtered_email_data)} emails remaining.")

# Display summary and prompt for approval
print("\nSummary:")
print(f"Total emails in the first list: {len(email_data)}")
print(f"Total emails in the skip list: {len(skip_emails)}")
print(f"Total emails to be sent: {len(filtered_email_data)}")

proceed = input("Do you want to proceed with sending emails? (yes/no): ").strip().lower()
if proceed != "yes":
    print("Aborting email sending.")
    exit()

# Function to send email
def send_email(recipient_email, event_name=None):
    # Prepare subject and body
    subject = SUBJECT_TEMPLATE
    html_body = html_template

    if event_name:
        subject = subject.format(event=event_name)
        html_body = html_body.replace("{event}", event_name)
    else:
        # Remove {event} placeholder if no event is provided
        subject = re.sub(r"\{event\}", "", subject)
        html_body = html_body.replace("{event}", "")

    print(f"Preparing email for: {recipient_email} | Event: {event_name if event_name else 'N/A'}")

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
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {str(e)}")
        return False

# Send emails one by one and count successful sends
emails_sent = 0
for index, row in filtered_email_data.iterrows():
    event_name = row["event"] if event_column_present else None
    if send_email(row["email"], event_name):
        emails_sent += 1

# Display final summary
print(f"\nEmail sending complete. Total emails sent: {emails_sent}")
