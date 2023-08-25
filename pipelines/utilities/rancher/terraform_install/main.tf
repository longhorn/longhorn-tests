terraform {
  required_providers {
    rancher2 = {
      source  = "rancher/rancher2"
      version = "~> 1.24"
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

resource "rancher2_app_v2" "longhorn_app" {
  cluster_id = "local"
  name = "longhorn-app"
  namespace = "longhorn-system"
  repo_name = "longhorn-repo"
  chart_name = "longhorn"
  chart_version = var.rancher_chart_install_version
  values = <<-EOF
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
    supportBundleManager:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}support-bundle-kit
    ui:
      repository: ${var.longhorn_repo == "rancher" ? "${var.longhorn_repo}/mirrored-longhornio-" : "${var.longhorn_repo}/"}longhorn-ui
EOF
  wait = true
}