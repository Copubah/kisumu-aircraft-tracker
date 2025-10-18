variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "kisumu-aircraft-tracker"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "notification_email" {
  description = "Email address for landing notifications"
  type        = string
}

variable "opensky_username" {
  description = "OpenSky Network username (optional for higher rate limits)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "opensky_password" {
  description = "OpenSky Network password (optional for higher rate limits)"
  type        = string
  default     = ""
  sensitive   = true
}

# Kisumu International Airport coordinates
variable "airport_lat" {
  description = "Kisumu airport latitude"
  type        = number
  default     = -0.0861
}

variable "airport_lon" {
  description = "Kisumu airport longitude"
  type        = number
  default     = 34.7289
}

variable "detection_radius_km" {
  description = "Detection radius around airport in kilometers"
  type        = number
  default     = 5
}

variable "landing_altitude_threshold" {
  description = "Altitude threshold for landing detection (feet)"
  type        = number
  default     = 1000
}