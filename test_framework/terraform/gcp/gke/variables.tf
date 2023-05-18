variable "gcp_auth_file" {
  type        = string
}

variable "gcp_region" {
  type        = string
  default     = "us-central1"
}

variable "gcp_project" {
  type        = string
}

variable "test_name" {
  type        = string
  default     = "lh-gke-tests"
}
