# infra/outputs.tf

output "input_bucket_name" {
  value = aws_s3_bucket.input_bucket.bucket
}

output "processed_bucket_name" {
  value = aws_s3_bucket.processed_bucket.bucket
}

output "image_processed_queue_url" {
  value = aws_sqs_queue.image_processed_queue.url
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.image_metadata_table.name
}