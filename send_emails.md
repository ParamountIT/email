# Email Sender Script Documentation

## Overview
The `send_emails.py` script is designed to send personalized HTML emails to a list of recipients using Amazon SES SMTP service. It supports event-specific customization, includes a skip list feature to exclude certain email addresses, and provides tracking of email processing status. The email subject is automatically extracted from the template's h1 tag, ensuring consistency between the email content and subject line.

## Prerequisites

### Environment Variables
Create a `.env` file with the following credentials:
```
SMTP_USERNAME=your_ses_smtp_username
SMTP_PASSWORD=your_ses_smtp_password
```

### Required Python Packages
```
pandas
python-dotenv
```

### Required Files
1. **Email List CSV** - Contains recipient information
   - Required column: `email`
   - Optional column: `event` (if using event-specific customization)
   - Auto-generated tracking columns:
     - `sent_status`: Records processing status ('sent', 'skipped', or 'failed')
     - `send_date`: Records processing date/time in UK format (DD/MM/YYYY HH:MM:SS)

2. **Skip List CSV** - Contains emails to exclude
   - Required column: `email`

3. **HTML Template** - Located at `./templates/*.html`
   - Must include h1 tag containing the email subject
   - Can include `{event}` placeholder in both subject and body
   - Example:
     ```html
     <h1>Beautiful Memories of Every Tumble, Stretch, and Smile at {event}!</h1>
     ```

## Configuration
- SMTP Server: email-smtp.eu-west-2.amazonaws.com
- SMTP Port: 465
- Sender Email: contact@example.co.uk
- Subject: Automatically extracted from template h1 tag (can be overridden in code)

## Usage

```bash
python send_emails.py [limit] [email_list] [skip_list]
```

### Arguments
- `limit`: Maximum number of emails to process in this execution
- `email_list`: Path to the CSV file containing recipient emails
- `skip_list`: Path to the CSV file containing emails to exclude

### Example
```bash
python send_emails.py 50 ./addresses/recipients.csv ./addresses/skip_list.csv
```

## Process Flow
1. Loads environment variables
2. Reads HTML template
3. Loads and validates email list and skip list
4. Identifies unprocessed emails (empty tracking fields)
5. Filters out skipped emails
6. Applies processing limit
7. Displays summary and requests confirmation
8. Processes emails up to the specified limit
9. Updates tracking information
10. Provides progress updates and final summary

## Processing Logic
- Only processes records with empty tracking fields
- Processes up to the specified limit in each execution
- Updates tracking information only for processed records
- Maintains processing history in the original CSV file

## Error Handling
- Validates template and CSV files before sending
- Checks for required columns in CSV files
- Verifies template placeholder compatibility
- Individual email sending failures don't stop the entire process
- Provides detailed error messages for troubleshooting

## Output
The script provides detailed console output including:
- Total number of emails in the list
- Number of unprocessed emails
- Number of emails in skip list
- Number of emails to be processed in this execution
- Processing limit
- Real-time sending status for each email
- Number of remaining unprocessed emails
- Final summary of successful sends

## Security Features
- Uses SMTP_SSL for secure connection
- Credentials loaded from environment variables
- Skip list functionality to prevent duplicate sends
- Confirmation prompt before sending

## Notes
- The script uses Amazon SES SMTP interface
- HTML template must be UTF-8 encoded
- Email subject is extracted from template's h1 tag
- Event customization applies to both subject and body
- Failed email sends are logged but don't stop the process
- Processing status and dates are preserved in the source CSV file
- Script automatically resumes from the first unprocessed record in each execution 