import os
import shutil
import unittest
import pandas as pd
import json
from datetime import datetime
from unittest.mock import Mock, patch
from .smtp_test_server import TestSMTPServer
from send_emails import EmailSender

# Import Lambda function for testing improvements
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'src'))
from lambda_function import EmailSender as LambdaEmailSender

class EmailSenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_data_dir = os.path.join('tests', 'data')
        cls.temp_dir = os.path.join('tests', 'temp')
        cls.template_path = os.path.join('tests', 'templates', 'test_template.html')
        
        # Create temp directory if it doesn't exist
        if not os.path.exists(cls.temp_dir):
            os.makedirs(cls.temp_dir)
            
    def setUp(self):
        """Set up each test"""
        # Start SMTP test server
        self.smtp_server = TestSMTPServer(host='localhost', port=1025)
        self.smtp_server.start()
        
        # Configure email sender for testing
        test_smtp_config = {
            'server': 'localhost',
            'port': 1025,
            'use_ssl': False
        }
        
        self.email_sender = EmailSender(
            smtp_config=test_smtp_config,
            template_path=self.template_path,
            sender_email='test@example.com',
            test_mode=True
        )
        
    def tearDown(self):
        """Clean up after each test"""
        self.smtp_server.stop()
        # Clean temp directory
        if os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, file))
                
    def copy_test_data(self, scenario):
        """Copy test data to temp directory"""
        source_dir = os.path.join(self.test_data_dir, f'scenario{scenario}')
        email_list = os.path.join(source_dir, 'emails.csv')
        skip_list = os.path.join(self.test_data_dir, 'skip_list.csv')
        
        temp_email_list = os.path.join(self.temp_dir, f'scenario{scenario}_emails.csv')
        temp_skip_list = os.path.join(self.temp_dir, 'skip_list.csv')
        
        shutil.copy2(email_list, temp_email_list)
        shutil.copy2(skip_list, temp_skip_list)
        
        return temp_email_list, temp_skip_list
        
    def verify_results(self, email_list_path, expected_processed):
        """Verify the results of email processing"""
        df = pd.read_csv(email_list_path)
        
        # Count only records processed in this run (using today's date)
        today = datetime.now().strftime('%d/%m/%Y')
        processed = len(df[
            (df['sent_status'].isin(['sent', 'skipped'])) & 
            (df['send_date'].str.startswith(today, na=False))
        ])
        
        self.assertEqual(processed, expected_processed, 
                        f"Expected {expected_processed} processed records, got {processed}")
        
        # Verify SMTP messages for emails sent in this run
        smtp_messages = self.smtp_server.get_messages()
        expected_sent = len(df[
            (df['sent_status'] == 'sent') & 
            (df['send_date'].str.startswith(today, na=False))
        ])
        self.assertEqual(len(smtp_messages), expected_sent,
                        f"Expected {expected_sent} SMTP messages, got {len(smtp_messages)}")
        
    def test_scenario1_no_records_processed(self):
        """Test scenario 1: Fresh email list"""
        email_list, skip_list = self.copy_test_data(1)
        processed = self.email_sender.process_email_list(email_list, skip_list, 2)
        self.assertEqual(processed, 1)  # 1 sent (2 limit - 1 skipped)
        self.verify_results(email_list, 2)  # 2 total (1 sent + 1 skipped)
        
    def test_scenario2_some_records_processed(self):
        """Test scenario 2: Partially processed list"""
        email_list, skip_list = self.copy_test_data(2)
        processed = self.email_sender.process_email_list(email_list, skip_list, 2)
        self.assertEqual(processed, 2)  # 2 sent (no new skips)
        self.verify_results(email_list, 2)  # 2 total processed this run
        
    def test_scenario3_all_records_processed(self):
        """Test scenario 3: Fully processed list"""
        email_list, skip_list = self.copy_test_data(3)
        processed = self.email_sender.process_email_list(email_list, skip_list, 2)
        self.assertEqual(processed, 0)  # Nothing to process
        self.verify_results(email_list, 0)  # Nothing processed this run

    def test_subject_extraction(self):
        """Test that subject is correctly extracted from template"""
        expected_subject = "Beautiful Memories of Every Tumble, Stretch, and Smile at {event}!"
        self.assertEqual(self.email_sender.subject_template, expected_subject)
        
    def test_subject_override(self):
        """Test that provided subject template overrides template extraction"""
        custom_subject = "Custom Subject for {event}"
        email_sender = EmailSender(
            smtp_config={'server': 'localhost', 'port': 1025, 'use_ssl': False},
            template_path=self.template_path,
            subject_template=custom_subject,
            test_mode=True
        )
        self.assertEqual(email_sender.subject_template, custom_subject)
        
    def test_event_replacement_in_subject(self):
        """Test that {event} is properly replaced in subject when sending email"""
        email_list, skip_list = self.copy_test_data(1)
        
        # Create test data with a single email
        df = pd.DataFrame({
            'email': ['test_event@example.com'],
            'event': ['Summer Competition 2024'],
            'sent_status': [''],
            'send_date': ['']
        })
        df.to_csv(email_list, index=False)
        
        # Create empty skip list
        pd.DataFrame({'email': []}).to_csv(skip_list, index=False)
        
        # Process emails
        processed = self.email_sender.process_email_list(email_list, skip_list, 1)
        self.assertEqual(processed, 1, "Expected 1 email to be processed")
        
        # Verify email subject
        messages = self.smtp_server.get_messages()
        self.assertEqual(len(messages), 1, "Expected exactly 1 email to be sent")
        self.assertIn(
            "Beautiful Memories of Every Tumble, Stretch, and Smile at Summer Competition 2024!",
            messages[0]['data']
        )

class LambdaFunctionImprovementTests(unittest.TestCase):
    """Test class for Lambda function improvements"""
    
    def test_enhanced_subject_extraction(self):
        """Test enhanced subject extraction with fallback strategies"""
        
        # Test data for different HTML template scenarios
        test_cases = [
            # Test 1: H1 with attributes
            {
                'template': '''
                <html>
                <head><title>Fallback Title</title></head>
                <body>
                    <h1 class="email-title" id="subject">Subject from H1 with attrs</h1>
                    <p>Content here</p>
                </body>
                </html>
                ''',
                'expected': 'Subject from H1 with attrs'
            },
            # Test 2: H1 with mixed case
            {
                'template': '''
                <html>
                <head><title>Fallback Title</title></head>
                <body>
                    <H1>Subject from Mixed Case H1</H1>
                    <p>Content here</p>
                </body>
                </html>
                ''',
                'expected': 'Subject from Mixed Case H1'
            },
            # Test 3: No H1, fallback to title
            {
                'template': '''
                <html>
                <head><title>Subject from Title Tag</title></head>
                <body>
                    <p>No H1 tag here</p>
                </body>
                </html>
                ''',
                'expected': 'Subject from Title Tag'
            },
            # Test 4: Title with attributes
            {
                'template': '''
                <html>
                <head><title class="page-title">Subject from Title with attrs</title></head>
                <body>
                    <p>No H1 tag here</p>
                </body>
                </html>
                ''',
                'expected': 'Subject from Title with attrs'
            },
            # Test 5: Neither H1 nor title
            {
                'template': '''
                <html>
                <head></head>
                <body>
                    <p>No subject tags</p>
                </body>
                </html>
                ''',
                'expected': 'Email from Rise Portraits'
            }
        ]
        
        # Mock the AWS services and environment
        with patch('lambda_function.boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_ses = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_s3 if service == 's3' else mock_ses
            
            with patch.dict(os.environ, {
                'SENDER_EMAIL': 'test@example.com',
                'EMAIL_LIST_KEY': 'test.csv',
                'SKIP_LIST_KEY': 'skip.csv',
                'TEMPLATE_KEY': 'template.html',
                'EMAIL_SEND_LIMIT': '5'
            }):
                
                for i, test_case in enumerate(test_cases):
                    with self.subTest(test_case=i+1):
                        # Mock S3 response with the test template
                        mock_s3.get_object.return_value = {
                            'Body': Mock(read=Mock(return_value=test_case['template'].encode()))
                        }
                        
                        # Create Lambda EmailSender instance
                        sender = LambdaEmailSender()
                        
                        # Verify the subject was extracted correctly
                        self.assertEqual(sender.subject_template, test_case['expected'])
                        
    def test_safe_placeholder_replacement(self):
        """Test safe placeholder replacement in Lambda function"""
        
        template_with_placeholder = '''
        <html>
        <head><title>Test for {event}</title></head>
        <body>
            <h1>Welcome to {event}!</h1>
            <p>Join us for {event} activities</p>
        </body>
        </html>
        '''
        
        template_no_placeholder = '''
        <html>
        <head><title>Test Email</title></head>
        <body>
            <h1>Welcome!</h1>
            <p>Join us for activities</p>
        </body>
        </html>
        '''
        
        with patch('lambda_function.boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_ses = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_s3 if service == 's3' else mock_ses
            
            # Mock successful email send
            mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
            
            with patch.dict(os.environ, {
                'SENDER_EMAIL': 'test@example.com',
                'EMAIL_LIST_KEY': 'test.csv',
                'SKIP_LIST_KEY': 'skip.csv',
                'TEMPLATE_KEY': 'template.html',
                'EMAIL_SEND_LIMIT': '5'
            }):
                
                # Test 1: Template with placeholder, event provided
                mock_s3.get_object.return_value = {
                    'Body': Mock(read=Mock(return_value=template_with_placeholder.encode()))
                }
                sender = LambdaEmailSender()
                result = sender.send_email('test@example.com', {'event': 'Summer Camp 2024'})
                self.assertTrue(result, "Should succeed with event placeholder and event provided")
                
                # Test 2: Template with placeholder, no event provided
                result = sender.send_email('test@example.com', {'event': ''})
                self.assertTrue(result, "Should succeed with event placeholder but no event")
                
                # Test 3: Template without placeholder, event provided
                mock_s3.get_object.return_value = {
                    'Body': Mock(read=Mock(return_value=template_no_placeholder.encode()))
                }
                sender = LambdaEmailSender()
                result = sender.send_email('test@example.com', {'event': 'Summer Camp 2024'})
                self.assertTrue(result, "Should succeed with no placeholder but event provided")
                
                # Test 4: Template without placeholder, no event
                result = sender.send_email('test@example.com', {'event': ''})
                self.assertTrue(result, "Should succeed with no placeholder and no event")
                
    def test_dynamic_placeholder_validation(self):
        """Test dynamic placeholder validation and replacement"""
        
        # Test template with multiple placeholders
        template_with_multiple_placeholders = '''
        <html>
        <head><title>Welcome {name} to {club}!</title></head>
        <body>
            <h1>Hello {name}, welcome to {event} at {club}!</h1>
            <p>We're excited to have you join us for {event} in {location}.</p>
            <p>Your membership level: {level}</p>
        </body>
        </html>
        '''
        
        # Test template with missing placeholders
        template_missing_placeholders = '''
        <html>
        <head><title>Test Template</title></head>
        <body>
            <h1>Welcome {name} to {nonexistent_field}!</h1>
            <p>Looking forward to {missing_column}.</p>
        </body>
        </html>
        '''
        
        with patch('lambda_function.boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_ses = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_s3 if service == 's3' else mock_ses
            
            # Mock successful email send
            mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
            
            with patch.dict(os.environ, {
                'SENDER_EMAIL': 'test@example.com',
                'EMAIL_LIST_KEY': 'test.csv',
                'SKIP_LIST_KEY': 'skip.csv',
                'TEMPLATE_KEY': 'template.html',
                'EMAIL_SEND_LIMIT': '5'
            }):
                
                # Test 1: Template with all matching placeholders
                mock_s3.get_object.return_value = {
                    'Body': Mock(read=Mock(return_value=template_with_multiple_placeholders.encode()))
                }
                
                # Mock CSV data with all required columns
                csv_data_complete = """email,name,club,event,location,level,sent_status,send_date
test@example.com,John Doe,Sports Club,Summer Camp,London,Premium,,"""
                
                skip_csv_data = """email"""
                
                def mock_get_object_complete(Bucket, Key):
                    if Key == 'test.csv':
                        return {'Body': Mock(read=Mock(return_value=csv_data_complete.encode()))}
                    elif Key == 'skip.csv':
                        return {'Body': Mock(read=Mock(return_value=skip_csv_data.encode()))}
                    elif Key == 'template.html':
                        return {'Body': Mock(read=Mock(return_value=template_with_multiple_placeholders.encode()))}
                
                mock_s3.get_object.side_effect = mock_get_object_complete
                mock_s3.put_object.return_value = {}
                
                # This should succeed - all placeholders have matching columns
                sender = LambdaEmailSender()
                result = sender.send_email('test@example.com', {
                    'name': 'John Doe',
                    'club': 'Sports Club', 
                    'event': 'Summer Camp',
                    'location': 'London',
                    'level': 'Premium'
                })
                self.assertTrue(result, "Should succeed with all placeholders matched")
                
                # Test 2: Template with missing placeholder columns - should fail validation
                mock_s3.get_object.return_value = {
                    'Body': Mock(read=Mock(return_value=template_missing_placeholders.encode()))
                }
                
                # Mock CSV data missing required columns
                csv_data_incomplete = """email,name,sent_status,send_date
test@example.com,John Doe,,"""
                
                def mock_get_object_incomplete(Bucket, Key):
                    if Key == 'test.csv':
                        return {'Body': Mock(read=Mock(return_value=csv_data_incomplete.encode()))}
                    elif Key == 'skip.csv':
                        return {'Body': Mock(read=Mock(return_value=skip_csv_data.encode()))}
                    elif Key == 'template.html':
                        return {'Body': Mock(read=Mock(return_value=template_missing_placeholders.encode()))}
                
                mock_s3.get_object.side_effect = mock_get_object_incomplete
                
                # This should fail with validation error
                sender = LambdaEmailSender()
                result = sender.process_email_list()
                
                # Should return error response instead of raising exception
                self.assertEqual(result['statusCode'], 500)
                error_body = json.loads(result['body'])
                self.assertIn("missing these columns", error_body['error'])
                self.assertIn("nonexistent_field", error_body['error'])
                self.assertIn("missing_column", error_body['error'])
                
    def test_multiple_real_templates(self):
        """Test Lambda function with multiple real-world templates"""
        
        # Define test templates and their expected subjects
        template_tests = [
            {
                'name': 'Original gymnastics template',
                'file': 'test_template.html',
                'expected_subject': 'Beautiful Memories of Every Tumble, Stretch, and Smile at {event}!'
            },
            {
                'name': 'Football template (from root)',
                'file': 'football_template.html',
                'expected_subject': '📸 Capture the Energy, Skill, and Joy of Your Junior Football Stars at {event}!'
            },
            {
                'name': 'Title fallback template',
                'file': 'title_fallback_template.html',
                'expected_subject': 'Professional Photography Services for {event}'
            },
            {
                'name': 'No placeholder template',
                'file': 'no_placeholder_template.html',
                'expected_subject': 'Rise Portraits - Professional Sports Photography'
            },
            {
                'name': 'H1 with attributes template',
                'file': 'h1_with_attributes_template.html',
                'expected_subject': 'Amazing Basketball Action at {event}!'
            },
            {
                'name': 'Default fallback template',
                'file': 'default_fallback_template.html',
                'expected_subject': 'Email from Rise Portraits'
            },
            {
                'name': 'Multi-placeholder template',
                'file': 'multi_placeholder_template.html',
                'expected_subject': 'Hello {name}, Welcome to {event}!'
            }
        ]
        
        with patch('lambda_function.boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_ses = Mock()
            mock_boto3.side_effect = lambda service, **kwargs: mock_s3 if service == 's3' else mock_ses
            
            # Mock successful email send
            mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
            
            with patch.dict(os.environ, {
                'SENDER_EMAIL': 'test@example.com',
                'EMAIL_LIST_KEY': 'test.csv',
                'SKIP_LIST_KEY': 'skip.csv',
                'TEMPLATE_KEY': 'template.html',
                'EMAIL_SEND_LIMIT': '5'
            }):
                
                for template_test in template_tests:
                    with self.subTest(template=template_test['name']):
                        # Read the actual template file
                        template_path = os.path.join('tests', 'templates', template_test['file'])
                        with open(template_path, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                        
                        # Mock S3 response with the template
                        mock_s3.get_object.return_value = {
                            'Body': Mock(read=Mock(return_value=template_content.encode()))
                        }
                        
                        # Create Lambda EmailSender instance
                        sender = LambdaEmailSender()
                        
                        # Verify the subject was extracted correctly
                        self.assertEqual(
                            sender.subject_template, 
                            template_test['expected_subject'],
                            f"Failed for template: {template_test['name']}"
                        )
                        
                        # Test sending email with event data
                        test_row = {'event': 'Summer Championship 2024', 'name': 'Test User', 'club': 'Test Club', 'location': 'Test Location', 'level': 'Premium', 'contact': 'Test Contact'}
                        result = sender.send_email('test@example.com', test_row)
                        self.assertTrue(result, f"Email sending failed for template: {template_test['name']}")
                        
                        # Test sending email with minimal data
                        minimal_row = {'event': '', 'name': '', 'club': '', 'location': '', 'level': '', 'contact': ''}
                        result = sender.send_email('test@example.com', minimal_row)
                        self.assertTrue(result, f"Email sending without event failed for template: {template_test['name']}")

if __name__ == '__main__':
    unittest.main(verbosity=2) 