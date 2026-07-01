variable "namespace" {
  description = "Kubernetes namespace to deploy into"
  type        = string
}

variable "image" {
  description = "Full container image reference including tag"
  type        = string
}

variable "replicas" {
  description = "Number of deployment replicas"
  type        = number
  default     = 2
}

variable "app_port" {
  description = "Container port the application listens on"
  type        = number
  default     = 80
}

variable "ingress_host" {
  description = "Hostname for the Ingress resource (e.g. signalharbor.example.com)"
  type        = string
}

variable "api_key" {
  description = "API key injected as API_KEY environment variable"
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "PostgreSQL connection URL injected as DATABASE_URL"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection URL injected as REDIS_URL"
  type        = string
  sensitive   = true
}

variable "risk_lookback_hours" {
  description = "Number of hours for risk lookback window (RISK_LOOKBACK_HOURS)"
  type        = number
  default     = 24
}

variable "cache_ttl_seconds" {
  description = "Cache TTL in seconds (CACHE_TTL_SECONDS)"
  type        = number
  default     = 300
}

variable "cpu_request" {
  description = "CPU resource request (e.g. '100m')"
  type        = string
  default     = "100m"
}

variable "cpu_limit" {
  description = "CPU resource limit (e.g. '500m')"
  type        = string
  default     = "500m"
}

variable "memory_request" {
  description = "Memory resource request (e.g. '128Mi')"
  type        = string
  default     = "128Mi"
}

variable "memory_limit" {
  description = "Memory resource limit (e.g. '512Mi')"
  type        = string
  default     = "512Mi"
}
