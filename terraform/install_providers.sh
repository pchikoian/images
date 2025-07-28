#!/bin/sh

set -e

ARCH=$(uname -m)
case "$ARCH" in
  x86_64) TARGET_ARCH="amd64" ;;
  aarch64) TARGET_ARCH="arm64" ;;
  *) echo "Unsupported architecture: $ARCH" && exit 1 ;;
esac

echo "Installing Terraform providers for arch: $TARGET_ARCH"

while read -r line || [ -n "$line" ]; do
  namespace_name=$(echo "$line" | awk '{print $1}')
  version=$(echo "$line" | awk '{print $2}')
  namespace=$(echo "$namespace_name" | cut -d'/' -f1)
  name=$(echo "$namespace_name" | cut -d'/' -f2)
  plugin_dir="/root/.terraform.d/plugins/registry.terraform.io/${namespace}/${name}/${version}/linux_${TARGET_ARCH}"

  mkdir -p "$plugin_dir"
  if [[ $namespace == microsoft* ]]; then
    url="https://github.com/microsoft/terraform-provider-${name}/releases/download/${version}/terraform-provider-${name}_${version}_linux_${TARGET_ARCH}.zip"
  else
    url="https://releases.hashicorp.com/terraform-provider-${name}/${version}/terraform-provider-${name}_${version}_linux_${TARGET_ARCH}.zip"
  fi

  echo "Downloading: $url"
  wget -q "$url" -O /tmp/provider.zip
  unzip -q /tmp/provider.zip -d "$plugin_dir"
  # chmod +x "$plugin_dir/terraform-provider-${name}"
  rm /tmp/provider.zip
done < /tmp/providers.txt

echo "All providers installed for arch: $TARGET_ARCH"
