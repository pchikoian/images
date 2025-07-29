# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a Docker-based Terraform provider management system. The main purpose is to create a containerized Terraform environment with pre-installed providers for multi-cloud infrastructure management.

## Architecture

The project consists of three main components:

1. **Dockerfile** (`terraform/Dockerfile`): Creates a Terraform container based on HashiCorp's official image with additional providers pre-installed
2. **Provider Installation Script** (`terraform/install_providers.sh`): Shell script that downloads and installs Terraform providers for both AMD64 and ARM64 architectures
3. **Provider Configuration** (`terraform/providers.txt`): Text file listing the required providers and their versions

### Key Components

- **Base Image**: Uses `hashicorp/terraform:${TERRAFORM_VERSION}` (currently 1.6.6)
- **Supported Providers**: 
  - HashiCorp providers (azurerm, random, google, archive)
  - Microsoft providers (azuredevops)
- **Architecture Support**: Both AMD64 and ARM64 architectures
- **Plugin Cache**: Configured at `/root/.terraform.d/plugin-cache`

## Common Development Commands

### Building the Docker Image
```bash
# Build with default Terraform version
docker build -f terraform/Dockerfile -t terraform-providers .

# Build with specific Terraform version
docker build --build-arg TERRAFORM_VERSION=1.7.0 -f terraform/Dockerfile -t terraform-providers .
```

### Running the Container
```bash
# Check Terraform version
docker run --rm terraform-providers

# Interactive shell for development
docker run --rm -it terraform-providers sh

# Mount local directory for Terraform operations
docker run --rm -v $(pwd):/app -w /app terraform-providers terraform init
```

### Provider Management

The `providers.txt` file uses the format:
```
namespace/provider-name version
```

To add new providers:
1. Add the provider entry to `terraform/providers.txt`
2. Rebuild the Docker image
3. The installation script automatically handles HashiCorp and Microsoft provider sources

### Development Workflow

1. Modify `providers.txt` to add/update providers
2. Test the installation script locally if needed: `./terraform/install_providers.sh`
3. Build the Docker image to verify all providers install correctly
4. Test with actual Terraform configurations

## File Structure

```
/
├── README.md                      # Basic project documentation
└── terraform/
    ├── Dockerfile                 # Multi-arch Terraform container
    ├── install_providers.sh       # Provider installation script
    └── providers.txt             # Provider version specifications
```

## Provider Architecture Details

- **Plugin Directory**: `/root/.terraform.d/plugins/registry.terraform.io/{namespace}/{name}/{version}/linux_{arch}`
- **Download Sources**:
  - HashiCorp: `https://releases.hashicorp.com/`
  - Microsoft: `https://github.com/microsoft/terraform-provider-{name}/releases/`
- **Cache Location**: `/root/.terraform.d/plugin-cache`

## Testing

Since this is an infrastructure tooling project, testing involves:
1. Building the Docker image successfully
2. Running `terraform version` to verify base installation
3. Testing provider availability with `terraform providers` in a sample configuration
4. Verifying cross-architecture compatibility (AMD64/ARM64)