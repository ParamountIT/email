import os
import shutil
import unittest
import pandas as pd
from datetime import datetime
from .smtp_test_server import TestSMTPServer
from send_emails import EmailSender

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

if __name__ == '__main__':
    unittest.main(verbosity=2) 