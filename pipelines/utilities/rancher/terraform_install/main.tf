terraform {
  required_providers {
    rancher2 = {
      source  = "rancher/rancher2"
      version = "~> 8.5.0"
    }
  }
}

provider "rancher2" {
  api_url   = var.api_url
  insecure  = true
  access_key = var.access_key
  secret_key = var.secret_key
}

resource "rancher2_catalog_v2" "longhorn_repo" {
  cluster_id = "local"
  name = "longhorn-repo"
  git_repo = var.rancher_chart_git_repo
  git_branch = var.rancher_chart_git_branch
}

# wait for longhorn repo synced before fetching the longhorn chart
resource "time_sleep" "wait_60_seconds" {
  depends_on = [
    rancher2_catalog_v2.longhorn_repo
  ]

  create_duration = "60s"
}

resource "null_resource" "wait_for_rancher_webhook" {
  depends_on = [
    time_sleep.wait_60_seconds
  ]

  provisioner "local-exec" {
    command = <<EOT
      set -e
      echo "Waiting for Rancher webhook to be ready..."
      # Wait for deployment to exist
      until kubectl get deploy -n cattle-system rancher-webhook >/dev/null 2>&1; do
        echo "rancher-webhook deployment not found, retrying..."
        sleep 5
      done
      # Wait for deployment to be available
      kubectl rollout status deploy/rancher-webhook -n cattle-system --timeout=300s
      echo "Rancher webhook is ready."
    EOT
  }
}

resource "rancher2_app_v2" "longhorn_app" {
  depends_on = [
    null_resource.wait_for_rancher_webhook
  ]

  cluster_id = "local"
  name = "longhorn-app"
  namespace = "longhorn-system"
  repo_name = "longhorn-repo"
  chart_name = "longhorn"
  chart_version = var.rancher_chart_install_version
  values = <<-EOF
global:
  imageRegistry: ""
privateRegistry:
  createSecret: false
  registryUrl: ${var.registry_url}
  registrySecret: ${var.registry_secret}
image:
  csi:
    attacher:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}csi-attacher
    nodeDriverRegistrar:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}csi-node-driver-registrar
    provisioner:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}csi-provisioner
    resizer:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}csi-resizer
    snapshotter:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}csi-snapshotter
    livenessProbe:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}livenessprobe
  longhorn:
    backingImageManager:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}backing-image-manager
    engine:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}longhorn-engine
    instanceManager:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}longhorn-instance-manager
    manager:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}longhorn-manager
    shareManager:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}longhorn-share-manager
    supportBundleKit:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}support-bundle-kit
    ui:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}longhorn-ui
EOF
  wait = true
}