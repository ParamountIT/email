import json
import boto3
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
from datetime import datetime
import io
import os
import logging
from email.utils import parseaddr
from typing import Dict, List, Any, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Configure logging
logger = Logger()

class EmailSender:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.ses_client = boto3.client('ses', region_name='eu-west-2')
        self.sender_email = os.environ['SENDER_EMAIL']
        self.email_list_key = os.environ['EMAIL_LIST_KEY']
        self.skip_list_key = os.environ['SKIP_LIST_KEY']
        self.template_key = os.environ['TEMPLATE_KEY']
        self.email_send_limit = int(os.environ['EMAIL_SEND_LIMIT'])
        self.bucket_name = 'riseportraits-email-lists'
        self.template_bucket = 'riseportraits-email-templates'
        
        # Load template
        self.html_template = self._load_template_from_s3()
        self.subject_template = self._extract_subject_from_template(self.html_template)
        
        # Extract all placeholders from template and subject
        self.template_placeholders = self._extract_template_placeholders()

    def _load_template_from_s3(self):
        try:
            response = self.s3_client.get_object(
                Bucket=self.template_bucket,
                Key=self.template_key
            )
            return response['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error reading HTML template from S3: {e}")
            raise

    def process_email_list(self):
        try:
            # Load and prepare data
            email_data = self._load_csv_from_s3()
            skip_emails = self._load_skip_list_from_s3()
            
            # Get unprocessed emails
            unprocessed_data = [
                row for row in email_data 
                if not row.get('sent_status') or row['sent_status'] == ''
            ]
            
            # Validate template placeholders against CSV columns
            if email_data:
                csv_columns = set(email_data[0].keys())
                self._validate_template_placeholders(csv_columns)
            
            # Process emails
            current_time = datetime.now()
            uk_date_format = current_time.strftime("%d/%m/%Y %H:%M:%S")
            
            # Initialize counters
            processed_count = 0
            emails_sent = 0
            
            # First mark skipped emails up to the limit
            for row in unprocessed_data:
                if processed_count >= self.email_send_limit:
                    break
                if row['email'].lower() in skip_emails:
                    row['sent_status'] = "skipped"
                    row['send_date'] = uk_date_format
                    processed_count += 1
            
            # Then process remaining emails up to the limit
            remaining_limit = self.email_send_limit - processed_count
            to_process = [
                row for row in unprocessed_data 
                if row['email'].lower() not in skip_emails
            ][:remaining_limit]
            
            # Send emails
            for row in to_process:
                if self.send_email(row["email"], row):
                    emails_sent += 1
                    row['sent_status'] = "sent"
                    row['send_date'] = uk_date_format
                else:
                    row['sent_status'] = "failed"
                    row['send_date'] = uk_date_format
            
            # Save updates
            self._save_csv_to_s3(email_data)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Email processing completed',
                    'emails_sent': emails_sent,
                    'emails_skipped': processed_count - emails_sent,
                    'total_processed': processed_count
                })
            }
            
        except Exception as e:
            logger.error(f"Error processing email list: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': str(e)
                })
            }

    def send_email(self, recipient_email, row_data):
        try:
            # Validate email using standard library
            _, addr = parseaddr(recipient_email)
            if not addr or '@' not in addr or '.' not in addr.split('@')[1]:
                logger.error(f"Invalid email address format: {recipient_email}")
                return False
            
            # Prepare subject and body with dynamic placeholder replacement
            subject = self.subject_template or "Email from Rise Portraits"
            html_body = self.html_template

            # Replace all placeholders dynamically
            if self.template_placeholders:
                subject = self._replace_template_placeholders(subject, row_data)
                html_body = self._replace_template_placeholders(html_body, row_data)

            # Send email using SES
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={
                    'ToAddresses': [recipient_email]
                },
                Message={
                    'Subject': {
                        'Data': subject
                    },
                    'Body': {
                        'Html': {
                            'Data': html_body
                        }
                    }
                }
            )
            
            # Log the placeholders that were replaced for debugging
            replaced_placeholders = {p: row_data.get(p, '') for p in self.template_placeholders}
            logger.info(f"Email sent to {recipient_email} with placeholders: {replaced_placeholders}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

    def _load_csv_from_s3(self):
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.email_list_key
            )
            csv_content = response['Body'].read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_content))
            data = list(reader)
            
            # Ensure tracking columns exist
            for row in data:
                if 'sent_status' not in row:
                    row['sent_status'] = ''
                if 'send_date' not in row:
                    row['send_date'] = ''
                
            return data
        except Exception as e:
            logger.error(f"Error loading email list CSV: {e}")
            raise

    def _load_skip_list_from_s3(self):
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.skip_list_key
            )
            csv_content = response['Body'].read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_content))
            return {row['email'].lower() for row in reader}
        except Exception as e:
            logger.error(f"Error loading skip list CSV: {e}")
            raise

    def _save_csv_to_s3(self, data):
        try:
            if not data:
                return
                
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.email_list_key,
                Body=output.getvalue()
            )
        except Exception as e:
            logger.error(f"Error saving CSV to S3: {e}")
            raise

    def _extract_subject_from_template(self, template_content):
        # Try to find subject in h1 tag first (with or without attributes)
        match = re.search(r'<h1[^>]*>(.*?)</h1>', template_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try to find subject in title tag as fallback
        match = re.search(r'<title[^>]*>(.*?)</title>', template_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
        # Return default subject if nothing found
        return "Email from Rise Portraits"

    def _extract_template_placeholders(self):
        """Extract all {placeholder} patterns from both subject and body templates"""
        placeholders = set()
        
        # Find placeholders in HTML template
        html_placeholders = re.findall(r'\{(\w+)\}', self.html_template)
        placeholders.update(html_placeholders)
        
        # Find placeholders in subject template if it exists
        if self.subject_template:
            subject_placeholders = re.findall(r'\{(\w+)\}', self.subject_template)
            placeholders.update(subject_placeholders)
        
        return placeholders

    def _validate_template_placeholders(self, csv_columns):
        """Validate that all template placeholders have corresponding CSV columns"""
        # Exclude system columns from validation
        system_columns = {'email', 'sent_status', 'send_date'}
        available_columns = set(csv_columns) - system_columns
        
        missing_columns = self.template_placeholders - available_columns
        
        if missing_columns:
            missing_list = ", ".join(sorted(missing_columns))
            available_list = ", ".join(sorted(available_columns))
            raise ValueError(
                f"Template contains placeholders {{{missing_list}}} but CSV is missing these columns. "
                f"Available CSV columns: {available_list}"
            )
        
        logger.info(f"Template validation successful. Placeholders: {sorted(self.template_placeholders)}")

    def _replace_template_placeholders(self, template_text, row_data):
        """Replace all placeholders in template text with corresponding row data"""
        result = template_text
        
        for placeholder in self.template_placeholders:
            placeholder_pattern = '{' + placeholder + '}'
            replacement_value = row_data.get(placeholder, '')
            result = result.replace(placeholder_pattern, str(replacement_value))
        
        return result

@logger.inject_lambda_context
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        sender = EmailSender()
        return sender.process_email_list()
    except Exception as e:
        logger.exception("Lambda execution error")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }   