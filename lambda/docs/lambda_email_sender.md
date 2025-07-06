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
- Extract subject line from h1 tags (with fallback to title tags)
- Support H1 tags with attributes (classes, styles, etc.)
- Case-insensitive HTML tag parsing
- Provide default subject line when none found in template
- Support {event} placeholder in both subject and body
- Safe placeholder replacement with existence validation
- Template customization based on event data

#### Subject Extraction Logic
The function uses a multi-tier approach to extract email subjects from HTML templates:

1. **Primary**: Search for `<h1>` tags (with or without attributes) using case-insensitive matching
2. **Fallback**: If no H1 found, search for `<title>` tags using the same approach
3. **Default**: If neither found, use "Email from Rise Portraits" as the subject
4. **Cleanup**: All extracted subjects are trimmed of whitespace

#### Placeholder Handling
- Safe {event} placeholder replacement that checks for placeholder existence before formatting
- Graceful removal of unused placeholders when event data is not available
- Null-safe operations to prevent runtime errors when templates are malformed

### 3. Email Sending
- Use AWS SES directly
- Support HTML email format
- Handle email sending failures gracefully
- Implement robust email validation using standard library
- Enhanced subject line processing with fallback mechanisms
- Safe HTML template processing with error recovery

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
- Robust subject line extraction with multiple fallback strategies
- Safe placeholder replacement to prevent runtime errors
- Graceful handling of missing or malformed template elements
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
**System columns (always required)**:
- `email` (string): Recipient's email address

**Auto-generated system columns**:
- `sent_status` (string): One of ['sent', 'skipped', 'failed', '']
- `send_date` (string): UK format date (DD/MM/YYYY HH:MM:SS)

**Dynamic data columns**:
Any additional columns can be used as template placeholders. The Lambda function will automatically discover placeholders in your template and validate that corresponding CSV columns exist.

Common examples:
- `name` (string): Recipient's name
- `event` (string): Event name
- `club` (string): Club or organization name
- `location` (string): Event location
- `level` (string): Membership or skill level
- `contact_person` (string): Contact information

Example with multiple placeholders:
```csv
email,name,event,club,location,level,sent_status,send_date
john@example.com,John Smith,Summer Gymnastics 2024,Elite Gymnastics,London,Advanced,,
jane@example.com,Jane Doe,Winter Competition 2024,City Sports,Birmingham,Beginner,,
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
   - **Dynamic validation**: All template placeholders must have corresponding CSV columns
   - System columns (`email`, `sent_status`, `send_date`) are excluded from placeholder validation
   - `sent_status` and `send_date` are managed by the Lambda function
   - Empty `sent_status` indicates unprocessed records
   - Duplicate email addresses are not allowed

2. Template-CSV Validation (New in v3.0):
   - Lambda function scans template for ALL `{placeholder}` patterns
   - Validates that each placeholder has a corresponding CSV column
   - Fails with clear error message if any placeholders are missing
   - Example: Template with `{name}` requires a `name` column in CSV

3. Skip List CSV:
   - Must have exactly one column named `email`
   - No duplicate email addresses allowed
   - Case-insensitive email matching

4. Data Validation:
   - Email addresses must be valid format
   - No empty email addresses allowed
   - No malformed CSV data allowed
   - All placeholder data is converted to strings for template replacement

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

## Recent Improvements

### Dynamic Placeholder System (v3.0) - **MAJOR UPDATE**
The Lambda function now features a completely redesigned placeholder system that automatically discovers and validates ALL placeholders in email templates:

#### Universal Template Support
- **Automatic discovery**: Scans both subject and body templates for ALL `{placeholder}` patterns
- **Dynamic validation**: Validates that all discovered placeholders have corresponding CSV columns
- **Flexible mapping**: Any CSV column can be used as a template placeholder
- **System column exclusion**: Automatically excludes system columns (email, sent_status, send_date) from validation

#### Validation and Error Handling
- **Pre-execution validation**: Function fails gracefully if placeholders don't match CSV columns
- **Clear error messages**: Specific details about missing columns and available alternatives
- **Comprehensive logging**: Detailed information about which placeholders were replaced with what values

#### Template Examples
```html
<!-- Template with multiple placeholders -->
<html>
  <head>
    <title>Welcome {name} to {club} - {event}!</title>
  </head>
  <body>
    <h1>Hello {name}, welcome to {event} at {club}!</h1>
    <p>Location: {location}</p>
    <p>Your membership level: {level}</p>
    <p>Contact: {contact_person}</p>
  </body>
</html>
```

Required CSV columns for above template:
```csv
email,name,club,event,location,level,contact_person,sent_status,send_date
john@example.com,John Doe,Sports Club,Summer Camp,London,Premium,Jane Smith,,
```

#### Benefits of v3.0
- **No more hardcoded placeholders**: Works with any `{placeholder}` pattern
- **Enhanced flexibility**: Easy to add new placeholders without code changes
- **Better error prevention**: Validation prevents runtime failures
- **Improved debugging**: Clear logs show exactly what data was replaced where

### Enhanced Template Processing (v2.1)
Previous improvements for robustness and compatibility:

#### Subject Line Extraction
- **Multi-tier fallback system**: H1 → Title → Default subject
- **Attribute-aware parsing**: Handles `<h1 class="title">` and similar variations
- **Case-insensitive matching**: Works with `<H1>`, `<h1>`, `<Title>`, etc.
- **Text cleanup**: Automatic whitespace trimming from extracted subjects

#### Error Prevention
- **Null-safe operations**: Prevents crashes when templates are malformed
- **Safe placeholder replacement**: Checks for placeholder existence before formatting
- **Graceful degradation**: Continues processing even when template elements are missing
- **Default value provisioning**: Provides sensible defaults when template parsing fails

#### Benefits
- **Increased reliability**: Fewer runtime errors and failed email sends
- **Better template compatibility**: Works with various HTML template formats
- **Improved user experience**: More predictable behavior with diverse template designs
- **Reduced maintenance**: Less intervention needed for template-related issues

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