import json
import os
import boto3
import urllib.parse
from datetime import datetime
from PIL import Image, ImageDraw

# Initialize boto3 clients using LocalStack endpoint if running locally
endpoint_url = os.environ.get('LOCALSTACK_ENDPOINT', 'http://localhost:4566')
s3_client = boto3.client('s3', endpoint_url=endpoint_url)
sqs_client = boto3.client('sqs', endpoint_url=endpoint_url)

def handler(event, context):
    # Load Environment Variables
    target_width = int(os.environ.get('TARGET_WIDTH', 200))
    watermark_text = os.environ.get('WATERMARK_TEXT', '© MyCompany')
    processed_bucket = os.environ.get('PROCESSED_BUCKET_NAME')
    success_queue = os.environ.get('SQS_QUEUE_URL')
    dlq_queue = os.environ.get('DLQ_QUEUE_URL')

    for record in event.get('Records', []):
        try:
            # Step 1: Parse S3 event
            source_bucket = record['s3']['bucket']['name']
            original_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            
            # Step 2: Validate file type
            valid_extensions = ('.jpg', '.jpeg', '.png')
            if not original_key.lower().endswith(valid_extensions):
                raise ValueError(f"Unsupported file type for file: {original_key}")

            download_path = f"/tmp/{original_key}"
            processed_key = f"resized_{original_key}"
            upload_path = f"/tmp/{processed_key}"

            # Step 3: Download image
            s3_client.download_file(source_bucket, original_key, download_path)

            # Step 4: Process image (Resize & Watermark)
            start_time = datetime.now()
            with Image.open(download_path) as img:
                original_size = img.size
                
                # Calculate new height maintaining aspect ratio
                w_percent = (target_width / float(img.size[0]))
                h_size = int((float(img.size[1]) * float(w_percent)))
                img = img.resize((target_width, h_size), Image.Resampling.LANCZOS)
                
                # Apply text watermark
                draw = ImageDraw.Draw(img)
                # Drawing text at top-left corner (10, 10)
                draw.text((10, 10), watermark_text, fill=(255, 255, 255))
                
                img.save(upload_path)
                new_size = img.size
            
            duration = (datetime.now() - start_time).total_seconds()

            # Step 5: Upload processed image
            s3_client.upload_file(upload_path, processed_bucket, processed_key)

            # Step 6: Publish Success Message
            success_payload = {
                "originalKey": original_key,
                "processedKey": processed_key,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "SUCCESS",
                "processingDetails": {
                    "originalSize": original_size,
                    "newSize": new_size,
                    "durationSeconds": duration
                }
            }
            sqs_client.send_message(
                QueueUrl=success_queue,
                MessageBody=json.dumps(success_payload)
            )

        except Exception as e:
            # Step 7: Publish Error to DLQ
            error_payload = {
                "originalKey": record.get('s3', {}).get('object', {}).get('key', 'Unknown'),
                "errorType": type(e).__name__,
                "errorMessage": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            sqs_client.send_message(
                QueueUrl=dlq_queue,
                MessageBody=json.dumps(error_payload)
            )
            print(f"Error processing image: {str(e)}")
            # Raise exception so Lambda knows the invocation failed
            raise e

    return {
        'statusCode': 200,
        'body': json.dumps('Event processing complete')
    }