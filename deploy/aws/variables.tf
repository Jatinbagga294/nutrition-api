variable "region" {
  description = "AWS region. ca-central-1 is Montreal, the closest to Toronto."
  type        = string
  default     = "ca-central-1"
}

variable "project" {
  description = "Name prefix for every resource, so they are easy to find and to delete."
  type        = string
  default     = "nutrition-api"
}

variable "repo_url" {
  description = "Public git repository the server clones and builds the API from."
  type        = string
  default     = "https://github.com/Jatinbagga294/nutrition-api.git"
}

variable "instance_type" {
  description = "EC2 size. t3.micro is the smallest that runs the Docker build comfortably."
  type        = string
  default     = "t3.micro"
}

variable "db_instance_class" {
  description = "RDS size. db.t4g.micro is the smallest Postgres instance."
  type        = string
  default     = "db.t4g.micro"
}

variable "cors_origins" {
  description = "Comma-separated sites allowed to call the API from a browser."
  type        = string
  default     = "https://calorie-tracker-two-ashen.vercel.app"
}

variable "alert_email" {
  description = "Where the billing alert goes. Required, so a forgotten deployment cannot bill silently."
  type        = string
}

variable "monthly_budget_usd" {
  description = "You are emailed when actual spend passes 80% of this, and again when forecast spend passes 100%."
  type        = number
  default     = 5
}
