import json
import os
import boto3
from decimal import Decimal

# Initialize boto3 resource using LocalStack endpoint
endpoint_url = os.environ.get('LOCALSTACK_ENDPOINT', 'http://localstack:4566')
dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)

table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'ImageMetadataTable')
table = dynamodb.Table(table_name)

def handler(event, context):
    for record in event.get('Records', []):
        try:
            # Step 1: Parse SQS message & convert floats to Decimals for DynamoDB
            message_body = json.loads(record['body'], parse_float=Decimal)
            
            # Step 2: Extract metadata
            original_key = message_body['originalKey']
            processed_key = message_body['processedKey']
            timestamp = message_body['timestamp']
            status = message_body['status']
            processing_details = message_body.get('processingDetails', {})

            # Step 3: Store in DynamoDB
            table.put_item(
                Item={
                    'originalKey': original_key,
                    'processedKey': processed_key,
                    'timestamp': timestamp,
                    'status': status,
                    'processingDetails': processing_details
                }
            )
            print(f"Successfully recorded metadata for {original_key}")

        except Exception as e:
            print(f"Error processing metadata record: {str(e)}")
            raise e

    return {
        'statusCode': 200,
        'body': json.dumps('Metadata updated successfully!')
    }