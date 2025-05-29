# Email Sender Lambda Documentation

## Overview
The Email Sender Lambda function sends personalized HTML emails to a list of recipients using Amazon SES. It is triggered automatically by AWS EventBridge on a defined schedule. The function supports event-specific customization, a skip list to exclude certain email addresses, and tracks email processing status in the source CSV file stored in S3. The email subject is automatically extracted from the template's h1 tag, ensuring consistency between the email content and subject line.

## Trigger Schedule (UTC)
The Lambda is triggered by EventBridge at the following times:
- 6:00am
- 8:00am
- 9:30am
- 11:00am
- 1:00pm
- 3:00pm
- 5:00pm

## Environment Variables (Configured in Lambda)
- `SENDER_EMAIL`: Sender email address (e.g., contact@riseportraits.co.uk)
- `EMAIL_LIST_KEY`: S3 key for the email list CSV file
- `SKIP_LIST_KEY`: S3 key for the skip list CSV file
- `TEMPLATE_KEY`: S3 key for the HTML email template
- `EMAIL_SEND_LIMIT`: Maximum number of emails to send per execution

## S3 Structure
- **Email List CSV**: Stored in the `riseportraits-email-lists` bucket
- **Skip List CSV**: Stored in the `riseportraits-email-lists` bucket
- **HTML Template**: Stored in the `riseportraits-email-templates` bucket

### Email List CSV Columns
- `email`: Recipient email address (required)
- `event`: Event name for email customization (optional, required if template uses `{event}`)
- `sent_status`: Processing status ('sent', 'skipped', or 'failed')
- `send_date`: Date/time of processing in UK format (DD/MM/YYYY HH:MM:SS)

### Skip List CSV Columns
- `email`: Email addresses to exclude from sending

### HTML Template
- Must include an `<h1>` tag containing the email subject
- Can include `{event}` placeholder in both subject and body
- Example:
  ```html
  <h1>Beautiful Memories of Every Tumble, Stretch, and Smile at {event}!</h1>
  ```

## Processing Logic
- Loads the email list and skip list from S3
- Skips emails in the skip list, marks them as 'skipped' in the CSV
- Sends up to `EMAIL_SEND_LIMIT` emails per run
- Marks each email as 'sent', 'skipped', or 'failed' in the CSV, and updates the file in S3
- Supports `{event}` placeholder in the template and subject (requires `event` column in CSV)
- Only processes records with empty `sent_status`
- Processing date/time is recorded in UK format

## Error Handling
- Errors are logged using AWS Lambda Powertools
- Failed sends are marked as 'failed' in the CSV, and the process continues for other emails
- If the template contains `{event}` but the CSV lacks an `event` column, the function raises an error

## Output
- The Lambda returns a JSON response with the number of emails sent, skipped, and total processed
- Processing status and dates are preserved in the source CSV file in S3

## Security & Best Practices
- Uses AWS SES for sending emails (no SMTP credentials required in Lambda)
- All sensitive configuration is managed via environment variables
- S3 buckets are encrypted and access is restricted via IAM roles

## Notes
- The Lambda function is deployed and managed via CloudFormation (`lambda/infrastructure/templates/email-sender.yaml`)
- The function is written in Python 3.12 and uses only standard libraries and AWS SDK (boto3)
- For test scenarios and local development, see the test suite in `/tests` and the Lambda source in `/lambda/src/lambda_function.py` 