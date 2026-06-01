import boto3
import time
import os

# --- Configuration ---
ENDPOINT_URL = 'http://localhost:4566'
UNIQUE_ID = 'ravi' # Matches your Terraform variable
INPUT_BUCKET = f'input-image-bucket-{UNIQUE_ID}'
PROCESSED_BUCKET = f'processed-image-bucket-{UNIQUE_ID}'
TABLE_NAME = 'ImageMetadataTable'
TEST_FILE = 'test_image.png'

# --- Initialize LocalStack Clients ---
s3 = boto3.client('s3', endpoint_url=ENDPOINT_URL)
dynamodb = boto3.resource('dynamodb', endpoint_url=ENDPOINT_URL)
table = dynamodb.Table(TABLE_NAME)

def run_e2e_test():
    print(f"🚀 Starting End-to-End Test for Image Pipeline...")
    
    if not os.path.exists(TEST_FILE):
        print(f"❌ Error: Please place a real image named '{TEST_FILE}' in the root directory.")
        return

    # 1. Upload the image to trigger the pipeline
    print(f"📦 Uploading {TEST_FILE} to {INPUT_BUCKET}...")
    s3.upload_file(TEST_FILE, INPUT_BUCKET, TEST_FILE)
    
    # 2. Wait for asynchronous processing (Lambdas + SQS take a moment)
    print("⏳ Waiting 10 seconds for Lambdas to process and SQS to route messages...")
    time.sleep(10)
    
    # 3. Verify the Processed Image exists in the output bucket
    processed_key = f"resized_{TEST_FILE}"
    print(f"🔍 Checking for {processed_key} in {PROCESSED_BUCKET}...")
    try:
        s3.head_object(Bucket=PROCESSED_BUCKET, Key=processed_key)
        print("✅ SUCCESS: Processed image found in output bucket!")
    except Exception as e:
        print(f"❌ FAILED: Processed image not found. Error: {e}")
        return

    # 4. Verify the Metadata exists in DynamoDB
    print(f"🔍 Checking DynamoDB table {TABLE_NAME} for originalKey: {TEST_FILE}...")
    try:
        response = table.get_item(Key={'originalKey': TEST_FILE})
        if 'Item' in response:
            print("✅ SUCCESS: Metadata record found in DynamoDB!")
            print(f"   Status: {response['Item'].get('status')}")
            print(f"   Details: {response['Item'].get('processingDetails')}")
        else:
            print("❌ FAILED: Item not found in DynamoDB.")
    except Exception as e:
        print(f"❌ FAILED: DynamoDB query error: {e}")

if __name__ == "__main__":
    run_e2e_test()