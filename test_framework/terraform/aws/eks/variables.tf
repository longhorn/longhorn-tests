variable "lh_aws_access_key" {
  type        = string
  description = "AWS ACCESS_KEY"
}

variable "lh_aws_secret_key" {
  type        = string
  description = "AWS SECRET_KEY"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
}

variable "test_name" {
  type        = string
  default     = "lh-eks-tests"
}

variable "arch" {
  type        = string
  default     = "amd64"
}
