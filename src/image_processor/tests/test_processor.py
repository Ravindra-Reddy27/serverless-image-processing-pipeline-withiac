import unittest
from unittest.mock import patch
import os
import sys

# Set environment variables required by app.py to DUMMY values for testing
os.environ['TARGET_WIDTH'] = '200'
os.environ['WATERMARK_TEXT'] = '© MyCompany'
os.environ['PROCESSED_BUCKET_NAME'] = 'processed-bucket-test'
os.environ['SQS_QUEUE_URL'] = 'http://test-queue'
os.environ['DLQ_QUEUE_URL'] = 'http://test-dlq'
os.environ['LOCALSTACK_ENDPOINT'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Add parent directory to path to import app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch boto3 clients BEFORE importing the app to prevent actual AWS connections
with patch('boto3.client'):
    import app

class TestImageProcessor(unittest.TestCase):
    
    @patch('app.sqs_client')
    @patch('app.s3_client')
    def test_validation_rejects_unsupported_files(self, mock_s3, mock_sqs):
        # 1. Simulate an S3 event for a .txt file (unsupported)
        bad_event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "input-bucket-test"},
                    "object": {"key": "document.txt"}
                }
            }]
        }

        # 2. Execute the handler and assert it raises an exception
        with self.assertRaises(ValueError):
            app.handler(bad_event, None)
        
        # 3. Verify the error was caught and sent to the DLQ
        self.assertTrue(mock_sqs.send_message.called, "SQS send_message was not called for the DLQ")
        
        # 4. Validate the DLQ message payload
        call_args = mock_sqs.send_message.call_args[1]
        self.assertEqual(call_args['QueueUrl'], 'http://test-dlq')
        self.assertIn('ValueError', call_args['MessageBody'])
        self.assertIn('Unsupported file type', call_args['MessageBody'])

if __name__ == '__main__':
    unittest.main()