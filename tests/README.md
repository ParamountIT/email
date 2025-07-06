# Email Sender Test Suite

## Overview
This comprehensive test suite verifies both the original `EmailSender` class and the enhanced Lambda function's email sending functionality. The tests cover email processing state tracking, template customization, and advanced subject extraction capabilities. The suite uses a local SMTP debugging server to verify email sending without actually delivering emails.

## Test Environment Setup
1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
```

2. Install required packages:
```bash
pip install -r requirements.txt
pip install -r lambda/requirements.txt
pip install boto3  # For Lambda function testing
```

## Test Architecture
The test suite uses:
- `TestSMTPServer`: A mock SMTP server that captures emails instead of sending them
- `EmailSender`: The production email sender class configured for testing
- `LambdaEmailSender`: The enhanced Lambda function email sender with improved subject extraction
- `unittest.mock`: For mocking AWS services (S3, SES) in Lambda tests
- Unittest framework for structured test execution
- Temporary test data copies to ensure test isolation

## Test Classes and Coverage

### EmailSenderTests (Original - 6 tests)
Tests the original email sender functionality with SMTP server integration.

### LambdaFunctionImprovementTests (New - 3 tests)
Tests the enhanced Lambda function with AWS service mocking and advanced subject extraction.

**Total Test Count: 9 tests**

## Test Scenarios

### Original EmailSender Tests

#### Subject Line Handling
**Purpose**: Tests email subject extraction and customization
**Verifies**:
- Automatic subject extraction from template's h1 tag
- Subject template override functionality
- Event variable replacement in subject
- Consistent subject between template and email

#### Scenario 1: No Records Processed
**File**: `data/scenario1/emails.csv`
**Purpose**: Tests initial processing of a fresh email list
**Verifies**:
- Processing starts from the beginning of the list
- Respects the processing limit (2 emails)
- Correctly marks skipped emails
- Updates tracking columns for processed records
- Expected processed: 2 total (1 sent + 1 skipped)

#### Scenario 2: Some Records Processed
**File**: `data/scenario2/emails.csv`
**Purpose**: Tests processing with partially completed list
**Verifies**:
- Only processes unprocessed records
- Preserves existing tracking information
- Respects the processing limit
- Handles mix of sent/skipped/unprocessed states
- Expected processed: 2 new (sent)

#### Scenario 3: All Records Processed
**File**: `data/scenario3/emails.csv`
**Purpose**: Tests behavior with fully processed list
**Verifies**:
- Correctly identifies when no processing is needed
- Preserves existing tracking information
- Handles case where all records are either sent or skipped
- Expected processed: 0 (nothing to process)

### Lambda Function Improvement Tests

#### Enhanced Subject Extraction
**Purpose**: Tests advanced subject extraction with multiple fallback strategies
**Verifies**:
- H1 tag extraction with attributes support
- Case-insensitive HTML parsing
- Title tag fallback when H1 not found
- Default subject when no H1 or title found
- Whitespace trimming from extracted subjects

#### Multi-Template Testing
**Purpose**: Tests Lambda function with multiple real-world templates
**Templates Tested**:
- `test_template.html`: Original gymnastics template
- `football_template.html`: Real football template with emojis
- `title_fallback_template.html`: Tests title fallback functionality
- `no_placeholder_template.html`: Template without {event} placeholder
- `h1_with_attributes_template.html`: H1 with CSS classes and attributes
- `default_fallback_template.html`: No H1 or title tags

**Verifies**:
- Subject extraction works across all template formats
- Safe placeholder replacement with and without events
- Email sending succeeds for all template types
- Fallback strategies work correctly

#### Safe Placeholder Replacement
**Purpose**: Tests safe {event} placeholder handling
**Verifies**:
- Placeholder replacement with event data provided
- Safe placeholder removal when no event data
- No runtime errors with malformed templates
- Graceful handling of mixed placeholder scenarios

## Test Data Structure

### Email Template Structure
The test suite now supports multiple template formats:

#### Advanced HTML Templates
- HTML templates with H1 tags (with or without attributes)
- Templates using title tags as fallback
- Templates with CSS classes and inline styles
- Templates with and without {event} placeholders

#### Template Examples:
```html
<!-- H1 with attributes -->
<h1 class="title" id="subject">Subject with {event}!</h1>

<!-- Title fallback -->
<title>Professional Photography Services for {event}</title>

<!-- Default fallback (no H1 or title) -->
<h2>Sports Photography Services</h2>
```

### Email List CSV Columns
- `email`: Recipient email address
- `event`: Event name for email customization
- `sent_status`: Processing status (sent/skipped/failed/empty)
- `send_date`: Date/time of processing in UK format

### Skip List
**File**: `data/skip_list.csv`
**Purpose**: Contains emails to be excluded from processing
**Structure**:
- Single column: `email`
- Used across all scenarios

## Available Test Templates

### Current Templates in `tests/templates/`
1. **`test_template.html`** - Original gymnastics template
2. **`football_template.html`** - Real football template from production
3. **`title_fallback_template.html`** - Tests title tag fallback
4. **`no_placeholder_template.html`** - Template without {event} placeholder
5. **`h1_with_attributes_template.html`** - H1 with CSS classes/attributes
6. **`default_fallback_template.html`** - No H1 or title tags

## Running Tests

Run all tests with verbose output:
```bash
python -m tests.run_tests -v
```

## Test Implementation Details

### SMTP Test Server (`smtp_test_server.py`)
- Runs on localhost:1025
- Captures emails instead of sending them
- Provides access to sent message details
- Automatically managed by test lifecycle

### AWS Services Mocking
For Lambda function tests:
- `boto3.client('s3')`: Mocked for template and CSV file operations
- `boto3.client('ses')`: Mocked for email sending operations
- Environment variables mocked for Lambda configuration
- S3 responses mocked with actual template content

### Test Configuration
The `EmailSender` is configured for testing with:
- Local SMTP server connection
- Test email template
- Test sender address
- Test mode enabled (suppresses output and confirmations)

The `LambdaEmailSender` is configured with:
- Mocked AWS S3 and SES services
- Environment variables for Lambda configuration
- Real template content from test files
- Mocked successful email sending responses

### Test Data Management
- Test data is copied to a temporary directory for each test
- Each test runs with fresh data
- Temporary files are cleaned up after each test
- Date-based verification of processed records
- Real template files read from disk for Lambda tests

## Enhanced Subject Extraction Features

### Multi-Tier Fallback Strategy
1. **Primary**: Search for `<h1>` tags (with or without attributes)
2. **Fallback**: Search for `<title>` tags if no H1 found
3. **Default**: Use "Email from Rise Portraits" if neither found
4. **Processing**: Case-insensitive matching with whitespace trimming

### Supported HTML Formats
- `<h1>Subject</h1>` - Basic H1 tag
- `<H1>Subject</H1>` - Case-insensitive matching
- `<h1 class="title">Subject</h1>` - H1 with CSS classes
- `<h1 id="subject" style="color: red;">Subject</h1>` - H1 with multiple attributes
- `<title>Subject</title>` - Title tag fallback
- `<title class="page-title">Subject</title>` - Title with attributes

### Placeholder Handling
- Safe {event} replacement when event data is provided
- Graceful placeholder removal when no event data
- Null-safe operations to prevent runtime errors
- Support for templates with and without placeholders

## Adding New Test Scenarios
1. Create new test data files in `tests/data/scenario{N}/`
2. Add new templates to `tests/templates/`
3. Update template test cases in `test_multiple_real_templates()`
4. Add new test methods to appropriate test classes
5. Update this README with new scenario details

## Adding New Templates
1. Create new template file in `tests/templates/`
2. Add template test case to `template_tests` list in `test_multiple_real_templates()`
3. Specify expected subject extraction result
4. Template will be automatically tested for subject extraction and email sending

## Maintenance
- Keep test data files small and focused
- Update expected values if processing logic changes
- Document any new test scenarios in this README
- Maintain consistent date format (DD/MM/YYYY HH:MM:SS) in test data
- Update test configuration if production settings change
- Add new templates to multi-template test when created
- Keep AWS service mocking up to date with Lambda function changes

## Test Results Summary
- **Total Tests**: 9
- **EmailSender Tests**: 6 (original functionality)
- **Lambda Function Tests**: 3 (enhanced functionality)
- **Templates Tested**: 6 different formats
- **Subject Extraction Scenarios**: 5 fallback strategies
- **Placeholder Handling**: 4 different scenarios

## Dependencies
- `pandas`: CSV data manipulation
- `boto3`: AWS service integration
- `aws-lambda-powertools`: Lambda function enhancements
- `unittest.mock`: AWS service mocking
- `aiosmtpd`: SMTP test server
- `python-dotenv`: Environment variable management 