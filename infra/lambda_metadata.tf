# infra/lambda_metadata.tf

# 1. IAM Role for Metadata Lambda
resource "aws_iam_role" "metadata_lambda_role" {
  name               = "metadata_updater_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# 2. Granular IAM Policy (Least Privilege)
data "aws_iam_policy_document" "metadata_lambda_policy" {
  statement {
    effect    = "Allow"
    actions   = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [aws_sqs_queue.image_processed_queue.arn]
  }
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.image_metadata_table.arn]
  }
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "metadata_lambda_policy_attachment" {
  name   = "metadata_lambda_policy"
  role   = aws_iam_role.metadata_lambda_role.id
  policy = data.aws_iam_policy_document.metadata_lambda_policy.json
}

# 3. Package the Python Code
data "archive_file" "metadata_lambda_zip" {
  type        = "zip"
  source_dir  = "../src/metadata_updater"
  output_path = "metadata_updater.zip"
}

# 4. Deploy the Metadata Lambda Function
resource "aws_lambda_function" "metadata_updater_lambda" {
  filename         = data.archive_file.metadata_lambda_zip.output_path
  function_name    = "MetadataUpdaterLambda"
  role             = aws_iam_role.metadata_lambda_role.arn
  handler          = "app.handler"
  runtime          = "python3.10"
  source_code_hash = data.archive_file.metadata_lambda_zip.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.image_metadata_table.name
      LOCALSTACK_ENDPOINT = "http://localstack:4566"
    }
  }
}

# 5. Configure SQS to Trigger the Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.image_processed_queue.arn
  function_name    = aws_lambda_function.metadata_updater_lambda.arn
  batch_size       = 1
}