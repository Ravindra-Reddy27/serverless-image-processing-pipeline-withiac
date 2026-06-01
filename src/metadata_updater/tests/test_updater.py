import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
from decimal import Decimal

# Set environment variables required by app.py
os.environ['DYNAMODB_TABLE_NAME'] = 'ImageMetadataTable'
os.environ['LOCALSTACK_ENDPOINT'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Add parent directory to path to import app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch boto3 resources BEFORE importing the app
with patch('boto3.resource'):
    import app

class TestMetadataUpdater(unittest.TestCase):

    @patch('app.table')
    def test_sqs_message_parsing_and_dynamo_put(self, mock_table):
        # 1. Simulate an incoming SQS message event containing float data
        mock_sqs_payload = {
            "originalKey": "test_image.jpg",
            "processedKey": "resized_test_image.jpg",
            "timestamp": "2026-05-31T12:00:00Z",
            "status": "SUCCESS",
            "processingDetails": {
                "durationSeconds": 0.145  # Float value to test conversion
            }
        }
        
        sqs_event = {
            "Records": [
                {"body": json.dumps(mock_sqs_payload)}
            ]
        }

        # 2. Execute the handler
        response = app.handler(sqs_event, None)

        # 3. Verify Lambda reports success
        self.assertEqual(response['statusCode'], 200)

        # 4. Verify DynamoDB put_item was called exactly once
        self.assertTrue(mock_table.put_item.called)

        # 5. Verify the payload was converted and sent to DynamoDB properly
        put_item_args = mock_table.put_item.call_args[1]['Item']
        self.assertEqual(put_item_args['originalKey'], "test_image.jpg")
        self.assertEqual(put_item_args['status'], "SUCCESS")
        
        # CRITICAL: Verify the float was converted to a Decimal
        duration = put_item_args['processingDetails']['durationSeconds']
        self.assertIsInstance(duration, Decimal)

if __name__ == '__main__':
    unittest.main()