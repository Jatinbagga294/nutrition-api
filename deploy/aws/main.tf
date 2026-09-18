terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}

# ---------------------------------------------------------------------------
# Network: the account's default VPC. Enough for this project, and it avoids
# NAT gateways, which are the classic way a small AWS bill becomes a large one.
# ---------------------------------------------------------------------------

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ---------------------------------------------------------------------------
# Secrets: generated here, stored encrypted in SSM Parameter Store, and read by
# the server at boot through its IAM role. They never appear in the user data,
# in git, or in the instance's metadata.
# ---------------------------------------------------------------------------

resource "random_password" "db" {
  length  = 24
  special = false # keeps the value safe to drop into a connection URL
}

resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project}/db_password"
  type  = "SecureString"
  value = random_password.db.result
}

resource "aws_ssm_parameter" "jwt_secret" {
  name  = "/${var.project}/jwt_secret"
  type  = "SecureString"
  value = random_password.jwt.result
}

# ---------------------------------------------------------------------------
# Security groups: the API is reachable from the internet on port 80 only.
# The database accepts connections from the API's security group and nothing
# else. There is no SSH port; use Session Manager (see outputs) to get a shell.
# ---------------------------------------------------------------------------

resource "aws_security_group" "api" {
  name        = "${var.project}-api"
  description = "Public HTTP to the API"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Outbound, for package installs and git clone"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name        = "${var.project}-db"
  description = "Postgres, only from the API server"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Postgres from the API security group"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }
}

# ---------------------------------------------------------------------------
# Database: RDS PostgreSQL, private, encrypted at rest.
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "db" {
  name       = "${var.project}-db"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "db" {
  identifier     = "${var.project}-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "nutrition"
  username = "nutrition"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period = 1
  skip_final_snapshot     = true  # this is a learning deployment; destroy must be clean
  deletion_protection     = false # ...for the same reason
}

# ---------------------------------------------------------------------------
# IAM: the server may read exactly two parameters and open a Session Manager
# shell. It cannot touch anything else in the account.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api" {
  name               = "${var.project}-api"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

data "aws_iam_policy_document" "read_secrets" {
  statement {
    actions = ["ssm:GetParameter"]
    resources = [
      aws_ssm_parameter.db_password.arn,
      aws_ssm_parameter.jwt_secret.arn,
    ]
  }
}

resource "aws_iam_role_policy" "read_secrets" {
  name   = "read-app-secrets"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.read_secrets.json
}

resource "aws_iam_role_policy_attachment" "session_manager" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "api" {
  name = "${var.project}-api"
  role = aws_iam_role.api.name
}

# ---------------------------------------------------------------------------
# Server: Amazon Linux 2023 running the API in Docker.
# ---------------------------------------------------------------------------

data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "api" {
  ami                         = data.aws_ssm_parameter.al2023.value
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.api.id]
  iam_instance_profile        = aws_iam_instance_profile.api.name
  associate_public_ip_address = true

  metadata_options {
    http_tokens = "required" # IMDSv2 only: blocks the SSRF route to instance credentials
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 12
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region       = var.region
    db_param     = aws_ssm_parameter.db_password.name
    jwt_param    = aws_ssm_parameter.jwt_secret.name
    db_host      = aws_db_instance.db.address
    repo_url     = var.repo_url
    cors_origins = var.cors_origins
  })
  user_data_replace_on_change = true

  # The parameters and the permission to read them must exist before boot.
  depends_on = [
    aws_ssm_parameter.db_password,
    aws_ssm_parameter.jwt_secret,
    aws_iam_role_policy.read_secrets,
  ]

  tags = {
    Name = "${var.project}-api"
  }
}

# ---------------------------------------------------------------------------
# Billing alarm: the cheapest insurance in AWS. A forgotten deployment emails you.
# ---------------------------------------------------------------------------

resource "aws_budgets_budget" "monthly" {
  name         = "${var.project}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
