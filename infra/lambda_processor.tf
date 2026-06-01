# infra/lambda_processor.tf

# 1. IAM Role for Lambda
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "processor_lambda_role" {
  name               = "image_processor_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# 2. Granular IAM Policy (Least Privilege)
data "aws_iam_policy_document" "processor_lambda_policy" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.input_bucket.arn}/*"]
  }
  statement {
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.processed_bucket.arn}/*"]
  }
  statement {
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [
      aws_sqs_queue.image_processed_queue.arn,
      aws_sqs_queue.dlq_processor_errors.arn
    ]
  }
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "processor_lambda_policy_attachment" {
  name   = "processor_lambda_policy"
  role   = aws_iam_role.processor_lambda_role.id
  policy = data.aws_iam_policy_document.processor_lambda_policy.json
}

# 3. Package the Python Code
data "archive_file" "processor_lambda_zip" {
  type        = "zip"
  source_dir  = "../src/image_processor"
  output_path = "image_processor.zip"
}

# 4. Deploy the Lambda Function
resource "aws_lambda_function" "image_processor_lambda" {
  filename         = data.archive_file.processor_lambda_zip.output_path
  function_name    = "ImageProcessorLambda"
  role             = aws_iam_role.processor_lambda_role.arn
  handler          = "app.handler"
  runtime          = "python3.10"
  source_code_hash = data.archive_file.processor_lambda_zip.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      TARGET_WIDTH          = "200"
      WATERMARK_TEXT        = "© MyCompany"
      PROCESSED_BUCKET_NAME = aws_s3_bucket.processed_bucket.bucket
      SQS_QUEUE_URL         = aws_sqs_queue.image_processed_queue.url
      DLQ_QUEUE_URL         = aws_sqs_queue.dlq_processor_errors.url
      # host.docker.internal ensures the Lambda container can reach the LocalStack API gateway
      LOCALSTACK_ENDPOINT   = "http://localstack:4566" 
    }
  }
}

# 5. Grant S3 Permission to Invoke Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.image_processor_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.input_bucket.arn
}

# 6. Configure the S3 Event Notification Trigger
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.input_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.image_processor_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3]
}