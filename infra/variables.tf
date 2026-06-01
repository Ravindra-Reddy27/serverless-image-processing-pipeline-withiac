# infra/variables.tf

variable "region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "unique_id" {
  description = "Unique identifier for bucket names"
  default     = "ravi" 
}