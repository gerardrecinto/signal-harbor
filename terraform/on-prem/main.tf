terraform {
  required_version = ">= 1.6"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
    citrixadc = {
      source  = "citrix/citrixadc"
      version = "~> 1.0"
    }
  }
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

provider "citrixadc" {
  endpoint = var.netscaler_endpoint
  username = var.netscaler_username
  password = var.netscaler_password
}

locals {
  tags = {
    project    = "signal-harbor"
    managed-by = "terraform"
  }
}

# ---------------------------------------------------------------------------
# MetalLB — bare-metal LoadBalancer for on-prem K8s
# ---------------------------------------------------------------------------
resource "helm_release" "metallb" {
  name             = "metallb"
  repository       = "https://metallb.github.io/metallb"
  chart            = "metallb"
  version          = "0.14.5"
  namespace        = "metallb-system"
  create_namespace = true

  wait    = true
  timeout = 300
}

resource "kubernetes_manifest" "metallb_ip_pool" {
  manifest = {
    apiVersion = "metallb.io/v1beta1"
    kind       = "IPAddressPool"
    metadata = {
      name      = "signalharbor-pool"
      namespace = "metallb-system"
    }
    spec = {
      addresses = [var.metallb_ip_range]
    }
  }

  depends_on = [helm_release.metallb]
}

resource "kubernetes_manifest" "metallb_l2_advertisement" {
  manifest = {
    apiVersion = "metallb.io/v1beta1"
    kind       = "L2Advertisement"
    metadata = {
      name      = "signalharbor-l2"
      namespace = "metallb-system"
    }
    spec = {
      ipAddressPools = ["signalharbor-pool"]
    }
  }

  depends_on = [kubernetes_manifest.metallb_ip_pool]
}

# ---------------------------------------------------------------------------
# Citrix ADC — VIP and backend bindings
# ---------------------------------------------------------------------------
resource "citrixadc_lbvserver" "signalharbor_vip" {
  name            = "signalharbor-lb-vip"
  ipv46           = var.vip_address
  port            = 443
  servicetype     = "SSL"
  lbmethod        = "ROUNDROBIN"
  persistencetype = "COOKIEINSERT"
}

resource "citrixadc_service" "signalharbor_backend" {
  count = var.backend_replica_count

  name        = "signalharbor-backend-${count.index}"
  ip          = "10.0.0.${count.index + 10}" # placeholder — real IPs come from K8s pod/node addressing
  port        = 8080
  servicetype = "HTTP"
}

resource "citrixadc_lbvserver_service_binding" "signalharbor" {
  count = var.backend_replica_count

  name        = citrixadc_lbvserver.signalharbor_vip.name
  servicename = citrixadc_service.signalharbor_backend[count.index].name
}

# ---------------------------------------------------------------------------
# Application module — K8s Service type LoadBalancer so MetalLB assigns IP
# ---------------------------------------------------------------------------
module "app" {
  source = "../modules/k8s-app"

  namespace    = "signalharbor"
  image        = "ghcr.io/gerardrecinto/signal-harbor:${var.app_version}"
  replicas     = var.backend_replica_count
  app_port     = 80
  ingress_host = var.ingress_host

  api_key      = var.api_key
  database_url = var.database_url
  redis_url    = var.redis_url

  depends_on = [
    kubernetes_manifest.metallb_l2_advertisement,
  ]
}
