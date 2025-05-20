# Lambda Email Sender Documentation

## Overview
This Lambda function automates the sending of personalized HTML emails using AWS SES, triggered three times daily at 8am, 11am, and 4pm UK time. The function processes email lists from S3, maintains processing state, and supports event-based email customization.

## AWS Region
- Region: `eu-west-2` (London)

## Runtime Requirements
- Python Version: 3.12
- Architecture: x86_64
- Memory: 256MB
- Timeout: 5 minutes (300 seconds)

### Python Package Requirements
All dependencies must be compatible with Python 3.12 and the Lambda environment:
- boto3 (provided by AWS Lambda runtime)
- aws-lambda-powertools>=3.13.0
- dnspython>=2.4.2

## S3 Bucket Configuration
### Existing Buckets
1. `riseportraits-email-lists`
   - Purpose: Stores email lists and skip lists
   - Structure:
     - Email list CSV files (e.g., "test copy.csv")
     - Skip list CSV files (e.g., "skip.csv")

2. `riseportraits-email-templates`
   - Purpose: Stores HTML email templates
   - Structure:
     - HTML template files (e.g., "LEAD-gymnastics.html")

3. `riseportraits-lambda-deployment`
   - Purpose: Stores Lambda deployment packages
   - Structure:
     - Deployment packages (e.g., "deployment-20240520-1.zip")

## Environment Variables
The following environment variables are configured in the Lambda function:

| Variable Name | Description | Default Value |
|---------------|-------------|---------------|
| `EMAIL_LIST_KEY` | S3 key for the email list CSV | "test copy.csv" |
| `SKIP_LIST_KEY` | S3 key for the skip list CSV | "skip.csv" |
| `TEMPLATE_KEY` | S3 key for the HTML template | "LEAD-gymnastics.html" |
| `SENDER_EMAIL` | Email address to send from | "contact@riseportraits.co.uk" |
| `EMAIL_SEND_LIMIT` | Maximum emails to process per execution | "5" |

## Core Functionality

### 1. Email Processing
- Process emails from CSV list in S3
- Support event-based email customization
- Maintain processing state tracking
- Implement skip list functionality
- Process emails in batches with configurable limits
- Track email send status and dates

### 2. Template Management
- Load HTML templates from S3
- Extract subject line from h1 tags
- Support {event} placeholder in both subject and body
- Template customization based on event data

### 3. Email Sending
- Use AWS SES directly
- Support HTML email format
- Handle email sending failures gracefully
- Implement email validation using standard library

## State Management

### Processing State
- Track sent_status: ('sent', 'skipped', 'failed', '')
- Record send_date in UK format (DD/MM/YYYY HH:MM:SS)
- Maintain processing history
- Handle partial processing states

### Error Handling
- Handle S3 access errors
- Handle SES sending errors
- Handle template processing errors
- Log errors to CloudWatch using aws-lambda-powertools

## Lambda Configuration

### IAM Roles Required
- S3 read/write permissions for `riseportraits-email-lists` and `riseportraits-email-templates`
- SES sending permissions
- CloudWatch logging permissions
- EventBridge trigger permissions

### EventBridge Rules
- 8am UK time trigger (cron(0 8 * * ? *))
- 11am UK time trigger (cron(0 11 * * ? *))
- 4pm UK time trigger (cron(0 16 * * ? *))

## Monitoring and Logging

### CloudWatch Metrics
- Number of emails processed
- Number of successful sends
- Number of failures
- Processing duration
- Error rates

### CloudWatch Logs
- Detailed processing logs using aws-lambda-powertools
- Error logs with stack traces
- State transition logs
- Performance metrics

## Deployment

### Deployment Package
- Python dependencies
- Lambda function code
- Configuration files
- Stored in `riseportraits-lambda-deployment` bucket

### Deployment Process
1. Package Lambda function and dependencies
2. Upload to `riseportraits-lambda-deployment` bucket with unique version name
3. Update CloudFormation stack using `email-sender.yaml` template
4. Configure environment variables through CloudFormation
5. Set up EventBridge triggers through CloudFormation

## CSV Format Specifications

### Email List CSV Format
Required columns:
- `email` (string): Recipient's email address
- `event` (string, optional): Event name for template customization

Auto-generated columns:
- `sent_status` (string): One of ['sent', 'skipped', 'failed', '']
- `send_date` (string): UK format date (DD/MM/YYYY HH:MM:SS)

Example:
```csv
email,event,sent_status,send_date
john@example.com,Summer Gymnastics 2024,,
jane@example.com,Winter Competition 2024,,
```

### Skip List CSV Format
Required columns:
- `email` (string): Email address to skip

Example:
```csv
email
do-not-send@example.com
blocked@example.com
```

### CSV Processing Rules
1. Email List CSV:
   - Must have at least the `email` column
   - `event` column is required if template uses {event} placeholder
   - `sent_status` and `send_date` are managed by the Lambda function
   - Empty `sent_status` indicates unprocessed records
   - Duplicate email addresses are not allowed

2. Skip List CSV:
   - Must have exactly one column named `email`
   - No duplicate email addresses allowed
   - Case-insensitive email matching

3. Data Validation:
   - Email addresses must be valid format
   - No empty email addresses allowed
   - No malformed CSV data allowed

## Security Considerations

### Data Protection
- S3 bucket encryption
- SES email encryption
- Secure environment variables
- IAM role least privilege principle

### Access Control
- S3 bucket policies
- IAM role policies
- SES sending authorization
- CloudWatch log access

## Maintenance

### Regular Tasks
- Monitor CloudWatch metrics
- Review error logs
- Update email templates
- Rotate email lists
- Update skip lists

### Backup and Recovery
- S3 bucket versioning
- Lambda function versioning
- Configuration backups
- State recovery procedures