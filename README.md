# Serverless Event-Driven Image Processing Pipeline

##  Project Overview

This project is a resilient, scalable, and fully event-driven serverless image processing pipeline built on AWS. It is designed to automatically process images upon upload using a decoupled architecture, demonstrating cloud-native engineering best practices.

When an image is uploaded to an S3 Input Bucket, it triggers a Lambda function that validates the file, resizes it, applies a text watermark, and stores it in an Output Bucket. Upon completion (success or failure), processing metadata and error states are asynchronously routed via Amazon SQS. Success messages trigger a secondary Lambda function that persists the metadata into an Amazon DynamoDB table, while failures are routed to Dead-Letter Queues (DLQs) for inspection.

### Core Technology Stack

| Layer | Technology |
|---|---|
| Compute | AWS Lambda (Python 3.10) |
| Storage | Amazon S3 |
| Database | Amazon DynamoDB |
| Messaging | Amazon SQS (Standard Queues + DLQs) |
| Infrastructure as Code | Terraform (`~> 4.0` provider) |
| Local Simulation | LocalStack & Docker |

---

##  Setup and Local Development

This project relies on **LocalStack** to simulate the AWS cloud environment locally, allowing for rapid iteration without incurring AWS costs.

### Prerequisites

- Docker & Docker Compose
- Terraform CLI
- Python 3.10
- AWS CLI (configured with dummy credentials: `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`)


### 1. Clone the Repository and Set Up Environment Variables

#### Clone the Repository

```bash
git clone https://github.com/Ravindra-Reddy27/serverless-image-processing-pipeline-withiac.git
cd serverless-image-processing-pipeline-withiac
```

#### Create the `.env` File

Copy the example environment file and create a new `.env` file:

```bash
cp .env.example .env
```

NOTE : You only need add your `LOCALSTACK_AUTH_TOKEN` in the .env, rest leave as it is.


### 2. Spin up the Local Environment

Run the following command from the root directory to start LocalStack in the background.

```bash
docker-compose up -d
```

> **Note:** Ensure LocalStack is fully initialized before proceeding.

### 2. Package Native Linux Dependencies (Cross-Platform Support)

AWS Lambda executes in a Linux environment. Because the Pillow library uses C-extensions, installing it natively on Windows/macOS will cause the Lambda to crash (`ImportModuleError`).

To solve this, use a temporary Docker container to pull the native `manylinux` wheels directly into the function directory:

```bash
docker run --rm -v "${PWD}/src/image_processor:/var/task" python:3.10 `
  pip install Pillow==10.2.0 boto3==1.34.0 urllib3==1.26.18 -t /var/task
```

### 3. Deploy Infrastructure via Terraform

Navigate to the `infra` directory, initialize Terraform, and deploy the stack. Terraform will automatically zip the Lambda functions and provision the S3, SQS, and DynamoDB resources inside LocalStack.

```bash
cd infra
terraform init
terraform apply -auto-approve
cd ..
```

---

##  Usage Guide

This is an event-driven backend; there are no direct REST API endpoints. The pipeline is triggered automatically via S3 `ObjectCreated` events.

### Trigger the Pipeline

Use the AWS CLI to upload an image to the input bucket.  
*(Replace `test_image.png` with a valid local file path.)*

```bash
aws --endpoint-url=http://localhost:4566 s3 cp test_image.png s3://input-image-bucket-ravi
```

### Verify the Processed Output

List the contents of the processed bucket to find your resized, watermarked image:

```bash
aws --endpoint-url=http://localhost:4566 s3 ls s3://processed-image-bucket-ravi
```

### Verify the Metadata Record

Scan the DynamoDB table to see the logged processing duration and dimensions:

```bash
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name ImageMetadataTable
```

---

##  Testing

The repository includes scripts to validate the infrastructure and core logic.

### 1. End-to-End (E2E) Integration Test

The E2E test acts as an automated client. It uploads an image to the local S3 bucket, waits for the asynchronous Lambda and SQS pipeline to complete, and validates the output in both S3 and DynamoDB.

Ensure a valid image named `test_image.png` is in the root directory, then run:

```bash
python tests/e2e_test.py
```

**Expected Result:** Three success checkmarks indicating:
- ✅ Successful S3 upload
- ✅ Successful image processing
- ✅ Validated DynamoDB metadata record


### 2. Unit Tests 

The project includes unit tests that isolate the core logic of the Lambda functions using Python's built-in `unittest.mock` library. Because AWS S3, SQS, and DynamoDB services are fully mocked, you do **not** need Docker or LocalStack running to execute these tests.

#### Run the Image Processor Test

Validates file extension filtering and proper Dead-Letter Queue (DLQ) routing for unsupported files.

```bash
python -m unittest src/image_processor/tests/test_processor.py
```

#### Run the Metadata Updater Test

Validates SQS JSON message parsing and strict DynamoDB type conversion (converting Python `float` values to `decimal.Decimal`).

```bash
python -m unittest src/metadata_updater/tests/test_updater.py
```

---

##  Clean Up & Teardown

To avoid unnecessary resource consumption on your local machine, ensure you tear down the infrastructure and stop the Docker containers when finished.

### 1. Destroy AWS Resources

Navigate to the infrastructure directory and use Terraform to delete all provisioned LocalStack resources.

```bash
cd infra
terraform destroy -auto-approve
cd ..
```

### 2. Stop LocalStack

Stop the LocalStack container and remove the default Docker network.

```bash
docker-compose down
```

> **Note:** Running `terraform destroy` removes all resources created by Terraform, and `docker-compose down` stops and removes the associated containers and networks.


---

##  Assumptions & Trade-offs

**DynamoDB Float Rejection**  
The `boto3` DynamoDB client strictly rejects standard Python `float` types. A workaround was implemented in the `MetadataUpdaterLambda` to parse incoming JSON payloads using `parse_float=decimal.Decimal`, ensuring processing duration logs correctly into the database without casting errors.

**LocalStack Networking Integration**  
To allow Lambda containers to communicate back to the SQS and S3 APIs within LocalStack, the `LOCALSTACK_ENDPOINT` environment variable was configured to use Docker's internal DNS routing (`http://localstack:4566`) rather than `host.docker.internal`, avoiding strict underscore validation errors in `urllib3`.

**Asynchronous Architecture**  
While synchronous processing via API Gateway would provide immediate feedback to a front-end client, an SQS-decoupled architecture was chosen. This prevents timeouts during heavy image processing and protects the database from throttling during traffic spikes.

---

## Future Improvements

- **Amazon SNS Alerts** — Integrate an SNS topic to the `DLQProcessorErrors` queue to automatically fan out email or SMS alerts to the DevOps team when an image fails to process.

- **Pre-Signed URLs for Client Uploads** — Implement an API Gateway + Lambda endpoint to generate temporary S3 pre-signed URLs. This would allow front-end applications to securely upload images directly to the bucket without exposing IAM credentials.

- **AWS Graviton Architecture** — Modify the Terraform definitions and CI/CD packaging to compile the Python C-extensions for the `arm64` architecture to reduce Lambda invocation costs and improve execution speeds.