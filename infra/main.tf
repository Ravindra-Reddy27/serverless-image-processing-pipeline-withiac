# infra/main.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0" # Pin to v4.x for LocalStack compatibility
    }
  }
}

provider "aws" {
  region                      = var.region
  access_key                  = "test"
  secret_key                  = "test"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # Route all AWS API calls to LocalStack
  endpoints {
    s3       = "http://localhost:4566"
    sqs      = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
    lambda   = "http://localhost:4566"
    iam      = "http://localhost:4566"
    sts      = "http://localhost:4566" # Added STS
  }
}
# --- S3 Buckets ---
resource "aws_s3_bucket" "input_bucket" {
  bucket = "input-image-bucket-${var.unique_id}"
  force_destroy = true
}

resource "aws_s3_bucket" "processed_bucket" {
  bucket = "processed-image-bucket-${var.unique_id}"
  force_destroy = true
}

# --- SQS Queues ---
# 1. Dead-Letter Queue for Metadata Lambda
resource "aws_sqs_queue" "dlq_processed_messages" {
  name = "DLQProcessedMessages"
}

# 2. Main Success Queue (Routes to DLQ after 5 failures)
resource "aws_sqs_queue" "image_processed_queue" {
  name = "ImageProcessedQueue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq_processed_messages.arn
    maxReceiveCount     = 5
  })
}

# 3. Dead-Letter Queue for Processor Lambda Errors
resource "aws_sqs_queue" "dlq_processor_errors" {
  name = "DLQProcessorErrors"
}

# --- DynamoDB Table ---
resource "aws_dynamodb_table" "image_metadata_table" {
  name           = "ImageMetadataTable"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "originalKey"

  attribute {
    name = "originalKey"
    type = "S"
  }
}