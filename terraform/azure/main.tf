terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

locals {
  rg_name = var.resource_group_name != "" ? var.resource_group_name : "signalharbor-${var.environment}-rg"

  common_tags = {
    project     = "signal-harbor"
    environment = var.environment
    managed-by  = "terraform"
  }
}

# ---------------------------------------------------------------------------
# Resource Group
# ---------------------------------------------------------------------------
resource "azurerm_resource_group" "signalharbor" {
  name     = local.rg_name
  location = var.location
  tags     = local.common_tags
}

# ---------------------------------------------------------------------------
# Virtual Network
# ---------------------------------------------------------------------------
resource "azurerm_virtual_network" "signalharbor" {
  name                = "signalharbor-${var.environment}-vnet"
  address_space       = ["10.1.0.0/16"]
  location            = azurerm_resource_group.signalharbor.location
  resource_group_name = azurerm_resource_group.signalharbor.name
  tags                = local.common_tags
}

resource "azurerm_subnet" "aks" {
  name                 = "signalharbor-${var.environment}-aks-subnet"
  resource_group_name  = azurerm_resource_group.signalharbor.name
  virtual_network_name = azurerm_virtual_network.signalharbor.name
  address_prefixes     = ["10.1.1.0/24"]
}

resource "azurerm_subnet" "db" {
  name                 = "signalharbor-${var.environment}-db-subnet"
  resource_group_name  = azurerm_resource_group.signalharbor.name
  virtual_network_name = azurerm_virtual_network.signalharbor.name
  address_prefixes     = ["10.1.2.0/24"]

  service_endpoints = ["Microsoft.Sql"]

  delegation {
    name = "fs"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# ---------------------------------------------------------------------------
# AKS Cluster
# ---------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster" "signalharbor" {
  name                = "signalharbor-${var.environment}"
  location            = azurerm_resource_group.signalharbor.location
  resource_group_name = azurerm_resource_group.signalharbor.name
  dns_prefix          = "signalharbor-${var.environment}"

  default_node_pool {
    name            = "default"
    node_count      = var.node_count
    vm_size         = var.aks_vm_size
    vnet_subnet_id  = azurerm_subnet.aks.id
    os_disk_size_gb = 50
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    service_cidr   = "10.2.0.0/16"
    dns_service_ip = "10.2.0.10"
  }

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# PostgreSQL Flexible Server
# ---------------------------------------------------------------------------
resource "azurerm_private_dns_zone" "postgres" {
  name                = "signalharbor-${var.environment}.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.signalharbor.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "signalharbor-${var.environment}-pg-vnetlink"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.signalharbor.id
  resource_group_name   = azurerm_resource_group.signalharbor.name
  tags                  = local.common_tags
}

resource "azurerm_postgresql_flexible_server" "signalharbor" {
  name                   = "signalharbor-${var.environment}-pg"
  resource_group_name    = azurerm_resource_group.signalharbor.name
  location               = azurerm_resource_group.signalharbor.location
  administrator_login    = var.db_username
  administrator_password = var.db_password
  version                = "16"
  storage_mb             = var.db_storage_mb
  sku_name               = var.db_sku
  zone                   = "1"

  delegated_subnet_id = azurerm_subnet.db.id
  private_dns_zone_id = azurerm_private_dns_zone.postgres.id

  high_availability {
    mode = var.environment == "prod" ? "ZoneRedundant" : "Disabled"
  }

  backup_retention_days        = var.environment == "prod" ? 7 : 1
  geo_redundant_backup_enabled = var.environment == "prod"

  tags = local.common_tags

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_database" "signalharbor" {
  name      = "signalharbor"
  server_id = azurerm_postgresql_flexible_server.signalharbor.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# ---------------------------------------------------------------------------
# Azure Cache for Redis
# ---------------------------------------------------------------------------
resource "azurerm_redis_cache" "signalharbor" {
  name                = "signalharbor-${var.environment}-redis"
  resource_group_name = azurerm_resource_group.signalharbor.name
  location            = azurerm_resource_group.signalharbor.location

  capacity            = var.environment == "prod" ? 1 : 0
  family              = "C"
  sku_name            = var.environment == "prod" ? "Standard" : "Basic"
  minimum_tls_version = "TLS1_2"
  enable_non_ssl_port = false

  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Kubernetes provider — auth via AKS
# ---------------------------------------------------------------------------
provider "kubernetes" {
  host                   = azurerm_kubernetes_cluster.signalharbor.kube_config[0].host
  client_certificate     = base64decode(azurerm_kubernetes_cluster.signalharbor.kube_config[0].client_certificate)
  client_key             = base64decode(azurerm_kubernetes_cluster.signalharbor.kube_config[0].client_key)
  cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.signalharbor.kube_config[0].cluster_ca_certificate)
}

# ---------------------------------------------------------------------------
# Application module
# ---------------------------------------------------------------------------
module "app" {
  source = "../modules/k8s-app"

  namespace    = "signalharbor-${var.environment}"
  image        = "ghcr.io/gerardrecinto/signal-harbor:${var.app_version}"
  replicas     = var.environment == "prod" ? 3 : 2
  app_port     = 80
  ingress_host = var.ingress_host

  api_key      = var.api_key
  database_url = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.signalharbor.fqdn}:5432/signalharbor"
  redis_url    = "rediss://:${azurerm_redis_cache.signalharbor.primary_access_key}@${azurerm_redis_cache.signalharbor.hostname}:${azurerm_redis_cache.signalharbor.ssl_port}"

  depends_on = [azurerm_kubernetes_cluster.signalharbor]
}
