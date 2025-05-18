import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import argparse
import re
from datetime import datetime

class EmailSender:
    """
    A class to handle batch email sending with tracking and skip list functionality.
    
    This class manages the sending of emails to a list of recipients, with support for:
    - Tracking email send status and dates
    - Skipping specific email addresses
    - Processing limits per execution
    - Event-based email customization
    - SSL/TLS SMTP connections
    - Test mode for automated testing
    
    Attributes:
        smtp_config (dict): SMTP server configuration
        sender_email (str): Email address to send from
        subject_template (str): Email subject template with optional {event} placeholder
        template_path (str): Path to HTML email template
        test_mode (bool): Whether running in test mode
        html_template (str): Loaded HTML template content
        event_placeholder_in_template (bool): Whether template uses {event} placeholder
    """
    
    def __init__(self, smtp_config=None, template_path=None, sender_email=None, subject_template=None, test_mode=False):
        """
        Initialize the EmailSender with optional custom configuration.
        
        Args:
            smtp_config (dict, optional): SMTP server settings. Defaults to Amazon SES configuration.
            template_path (str, optional): Path to HTML template. Defaults to LEAD-gymnastics.html.
            sender_email (str, optional): Sender email address. Defaults to Rise Portraits address.
            subject_template (str, optional): Subject line template. If None, extracted from template.
            test_mode (bool, optional): Whether to run in test mode. Defaults to False.
        """
        # Load environment variables from .env file if not in test mode
        if not test_mode:
            load_dotenv()
            
        # Use provided config or default to production settings
        self.smtp_config = smtp_config or {
            'server': "email-smtp.eu-west-2.amazonaws.com",
            'port': 465,
            'username': os.getenv("SMTP_USERNAME"),
            'password': os.getenv("SMTP_PASSWORD"),
            'use_ssl': True
        }
        
        self.sender_email = sender_email or "contact@riseportraits.co.uk"
        self.template_path = template_path or "./templates/LEAD-gymnastics.html"
        self.test_mode = test_mode
        
        # Load HTML template
        try:
            with open(self.template_path, "r", encoding="utf-8") as f:
                self.html_template = f.read()
        except Exception as e:
            print(f"Error reading HTML template: {e}")
            raise

        # Extract subject from template if not provided
        if subject_template is None:
            extracted_subject = self._extract_subject_from_template(self.html_template)
            if extracted_subject is None:
                raise ValueError("Could not extract subject from template and no subject_template provided")
            self.subject_template = extracted_subject
        else:
            self.subject_template = subject_template
            
        self.event_placeholder_in_template = "{event}" in self.html_template
    
    def process_email_list(self, email_list_path, skip_list_path, limit):
        """
        Process a list of emails, respecting the skip list and processing limit.
        
        Args:
            email_list_path (str): Path to CSV file containing email list
            skip_list_path (str): Path to CSV file containing emails to skip
            limit (int): Maximum number of emails to process in this execution
            
        Returns:
            int: Number of emails successfully processed in this execution
            
        Raises:
            ValueError: If template requires event but CSV is missing event column
            Exception: If there are issues reading files or sending emails
        """
        # Load and prepare data
        email_data = self._load_email_list(email_list_path)
        skip_emails = self._load_skip_list(skip_list_path)
        
        # Get unprocessed emails
        unprocessed_data = email_data[
            (email_data['sent_status'].isna()) | 
            (email_data['sent_status'] == '')
        ].copy()
        
        # Check event column
        event_column_present = "event" in email_data.columns
        if self.event_placeholder_in_template and not event_column_present:
            raise ValueError("Template contains {event} placeholder but CSV is missing event column")
        
        # Process emails
        current_time = datetime.now()
        uk_date_format = current_time.strftime("%d/%m/%Y %H:%M:%S")
        
        # Initialize counters
        processed_count = 0
        emails_sent = 0
        
        # First mark skipped emails up to the limit
        skipped_mask = unprocessed_data["email"].isin(skip_emails)
        for idx, row in unprocessed_data[skipped_mask].iterrows():
            if processed_count >= limit:
                break
            email_data.loc[idx, "sent_status"] = "skipped"
            email_data.loc[idx, "send_date"] = uk_date_format
            processed_count += 1
        
        # Then process remaining emails up to the limit
        remaining_limit = limit - processed_count
        to_process = unprocessed_data[~unprocessed_data["email"].isin(skip_emails)].head(remaining_limit)
        
        # Display summary unless in test mode
        if not self.test_mode:
            self._display_summary(email_data, unprocessed_data, skip_emails, to_process, limit)
            if input("Do you want to proceed with sending emails? (yes/no): ").strip().lower() != "yes":
                print("Aborting email sending.")
                return emails_sent
        
        # Send emails
        for index, row in to_process.iterrows():
            event_name = row["event"] if event_column_present else None
            if self.send_email(row["email"], event_name):
                emails_sent += 1
                email_data.loc[index, "sent_status"] = "sent"
                email_data.loc[index, "send_date"] = uk_date_format
            else:
                email_data.loc[index, "sent_status"] = "failed"
                email_data.loc[index, "send_date"] = uk_date_format
        
        # Save updates
        email_data.to_csv(email_list_path, index=False)
        
        return emails_sent
    
    def send_email(self, recipient_email, event_name=None):
        """
        Send a single email to a recipient.
        
        Args:
            recipient_email (str): Email address to send to
            event_name (str, optional): Event name for template customization
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Prepare subject and body
        subject = self.subject_template
        html_body = self.html_template

        if event_name:
            subject = subject.format(event=event_name)
            html_body = html_body.replace("{event}", event_name)
        else:
            subject = re.sub(r"\{event\}", "", subject)
            html_body = html_body.replace("{event}", "")

        if not self.test_mode:
            print(f"Preparing email for: {recipient_email} | Event: {event_name if event_name else 'N/A'}")

        try:
            # Construct email message
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            # Connect to SMTP server
            if not self.test_mode:
                print("Connecting to SMTP server...")
                
            if self.smtp_config['use_ssl']:
                server = smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'])
                if self.smtp_config.get('username'):
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
            else:
                server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
            
            if not self.test_mode:
                print("Sending email...")
            server.sendmail(self.sender_email, recipient_email, msg.as_string())
            server.quit()

            if not self.test_mode:
                print(f"✅ Email sent to {recipient_email}")
            return True
        except Exception as e:
            if not self.test_mode:
                print(f"❌ Failed to send email to {recipient_email}: {str(e)}")
            return False
    
    def _load_email_list(self, path):
        """
        Load and prepare the email list CSV file.
        
        Args:
            path (str): Path to the email list CSV file
            
        Returns:
            pandas.DataFrame: Loaded and prepared email data
            
        Raises:
            Exception: If there are issues reading the file
        """
        try:
            # Load CSV with string types for status columns
            df = pd.read_csv(path, dtype={
                'sent_status': str,
                'send_date': str
            })
            
            # Ensure tracking columns exist
            if 'sent_status' not in df.columns:
                df['sent_status'] = ''
            if 'send_date' not in df.columns:
                df['send_date'] = ''
                
            return df
        except Exception as e:
            print(f"Error loading email list CSV: {e}")
            raise
    
    def _load_skip_list(self, path):
        """
        Load the skip list CSV file.
        
        Args:
            path (str): Path to the skip list CSV file
            
        Returns:
            set: Set of email addresses to skip
            
        Raises:
            Exception: If there are issues reading the file
        """
        try:
            skip_df = pd.read_csv(path)
            return set(skip_df["email"])
        except Exception as e:
            print(f"Error loading skip list CSV: {e}")
            raise
    
    def _display_summary(self, email_data, unprocessed_data, skip_emails, to_process, limit):
        """
        Display a summary of the email processing task.
        
        Args:
            email_data (pandas.DataFrame): Complete email list data
            unprocessed_data (pandas.DataFrame): Unprocessed email data
            skip_emails (set): Set of emails to skip
            to_process (pandas.DataFrame): Emails to be processed
            limit (int): Processing limit
        """
        print("\nSummary:")
        print(f"Total emails in the list: {len(email_data)}")
        print(f"Unprocessed emails: {len(unprocessed_data)}")
        print(f"Emails in skip list: {len(skip_emails)}")
        print(f"Emails to be processed in this execution: {len(to_process)}")
        print(f"Processing limit set to: {limit}")

    def _extract_subject_from_template(self, template_content):
        """
        Extract the email subject from the template's h1 tag.
        
        Args:
            template_content (str): The HTML template content
            
        Returns:
            str: The extracted subject line, or None if not found
        """
        match = re.search(r'<h1>(.*?)</h1>', template_content)
        return match.group(1) if match else None

def main():
    """
    Main entry point for the email sending script.
    
    Parses command line arguments and runs the email sending process.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Send emails with a skip list.")
    parser.add_argument("limit", type=int, help="Maximum number of emails to process in this execution")
    parser.add_argument("email_list", help="Path to the CSV file containing the email list")
    parser.add_argument("skip_list", help="Path to the CSV file containing the skip list")
    args = parser.parse_args()
    
    # Create sender and process emails
    sender = EmailSender()
    sender.process_email_list(args.email_list, args.skip_list, args.limit)

if __name__ == "__main__":
    main()
