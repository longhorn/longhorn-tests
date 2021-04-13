terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
    }
    null = {
      source = "hashicorp/null"
    }
  }
  required_version = ">= 0.13"
}
