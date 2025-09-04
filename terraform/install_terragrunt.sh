#!/bin/sh

set -e

ARCH=$(uname -m)
case "$ARCH" in
  x86_64) TARGET_ARCH="amd64" ;;
  aarch64) TARGET_ARCH="arm64" ;;
  *) echo "Unsupported architecture: $ARCH" && exit 1 ;;
esac

TERRAGRUNT_VERSION="${TERRAGRUNT_VERSION:-v0.86.2}"

INSTALL_DIR="/usr/local/bin"

echo "Installing Terragrunt $TERRAGRUNT_VERSION for arch: $TARGET_ARCH"

# Download Terragrunt binary
url="https://github.com/gruntwork-io/terragrunt/releases/download/${TERRAGRUNT_VERSION}/terragrunt_linux_${TARGET_ARCH}"
echo "Downloading: $url"

wget -q "$url" -O "${INSTALL_DIR}/terragrunt"
chmod +x "${INSTALL_DIR}/terragrunt"

echo "Terragrunt $TERRAGRUNT_VERSION installed successfully"
terragrunt --version
