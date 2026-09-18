output "api_url" {
  description = "Base URL of the deployed API. Add /docs for the interactive documentation."
  value       = "http://${aws_instance.api.public_ip}"
}

output "health_url" {
  description = "Should return {\"status\":\"ok\"} once the server has finished booting (about 5 minutes)."
  value       = "http://${aws_instance.api.public_ip}/health"
}

output "shell_command" {
  description = "Opens a shell on the server through Session Manager. No SSH key or open port needed."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.api.id}"
}

output "bootstrap_log_command" {
  description = "Run this in that shell to see why the API is not up yet."
  value       = "sudo tail -f /var/log/nutrition-bootstrap.log"
}
