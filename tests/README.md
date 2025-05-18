# Email Sender Test Suite

## Overview
This test suite verifies the email sending functionality of the `EmailSender` class with various scenarios focusing on the processing state tracking system and template customization. The tests use a local SMTP debugging server to verify email sending without actually delivering emails.

## Test Environment Setup
1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Test Architecture
The test suite uses:
- `TestSMTPServer`: A mock SMTP server that captures emails instead of sending them
- `EmailSender`: The production email sender class configured for testing
- Unittest framework for structured test execution
- Temporary test data copies to ensure test isolation

## Test Scenarios

### Subject Line Handling
**Purpose**: Tests email subject extraction and customization
**Verifies**:
- Automatic subject extraction from template's h1 tag
- Subject template override functionality
- Event variable replacement in subject
- Consistent subject between template and email

### Scenario 1: No Records Processed
**File**: `data/scenario1/emails.csv`
**Purpose**: Tests initial processing of a fresh email list
**Verifies**:
- Processing starts from the beginning of the list
- Respects the processing limit (2 emails)
- Correctly marks skipped emails
- Updates tracking columns for processed records
- Expected processed: 2 total (1 sent + 1 skipped)

### Scenario 2: Some Records Processed
**File**: `data/scenario2/emails.csv`
**Purpose**: Tests processing with partially completed list
**Verifies**:
- Only processes unprocessed records
- Preserves existing tracking information
- Respects the processing limit
- Handles mix of sent/skipped/unprocessed states
- Expected processed: 2 new (sent)

### Scenario 3: All Records Processed
**File**: `data/scenario3/emails.csv`
**Purpose**: Tests behavior with fully processed list
**Verifies**:
- Correctly identifies when no processing is needed
- Preserves existing tracking information
- Handles case where all records are either sent or skipped
- Expected processed: 0 (nothing to process)

## Test Data Structure

### Email Template Structure
- HTML template with required h1 tag containing email subject
- Subject line in h1 tag can include {event} placeholder
- Same subject is used in email unless overridden
- Example:
  ```html
  <h1>Beautiful Memories of Every Tumble, Stretch, and Smile at {event}!</h1>
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

### Test Configuration
The `EmailSender` is configured for testing with:
- Local SMTP server connection
- Test email template
- Test sender address
- Test mode enabled (suppresses output and confirmations)

### Test Data Management
- Test data is copied to a temporary directory for each test
- Each test runs with fresh data
- Temporary files are cleaned up after each test
- Date-based verification of processed records

## Adding New Test Scenarios
1. Create a new data file in `tests/data/scenario{N}/`
2. Add scenario details to this README
3. Add test method to `EmailSenderTests` class
4. Update test data structure if new test cases are needed

## Maintenance
- Keep test data files small and focused
- Update expected values if processing logic changes
- Document any new test scenarios in this README
- Maintain consistent date format (DD/MM/YYYY HH:MM:SS) in test data
- Update test configuration if production settings change 