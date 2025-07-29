# Terraform Providers Docker Image

A Docker image based on HashiCorp's official Terraform image with pre-installed cloud providers for multi-cloud infrastructure management.

## Features

- 🐳 **Multi-architecture support**: AMD64 and ARM64
- ☁️ **Pre-installed providers**: Azure, Google Cloud, Azure DevOps, and utility providers
- 🚀 **Ready-to-use**: No need to download providers during `terraform init`
- 🔧 **Configurable**: Easy to add or update providers via configuration file

## Supported Providers

| Provider | Version | Namespace |
|----------|---------|-----------|
| Azure Resource Manager | 4.37.0 | hashicorp/azurerm |
| Google Cloud Platform | 6.45.0 | hashicorp/google |
| Azure DevOps | 1.10.0 | microsoft/azuredevops |
| Random | 3.7.2 | hashicorp/random |
| Archive | 2.7.1 | hashicorp/archive |

## Quick Start

### Pull and Run

```bash
# Pull the image (replace with your registry)
docker pull terraform-providers:latest

# Run Terraform commands
docker run --rm -v $(pwd):/app -w /app terraform-providers:latest terraform version
```

### Build Locally

```bash
# Build the image
docker build -f terraform/Dockerfile -t terraform-providers .

# Verify installation
docker run --rm terraform-providers terraform version
```

## Usage Examples

### Initialize a Terraform Project

```bash
# Mount your Terraform project directory
docker run --rm -v $(pwd):/app -w /app terraform-providers terraform init
```

### Plan Infrastructure Changes

```bash
docker run --rm -v $(pwd):/app -w /app terraform-providers terraform plan
```

### Apply Infrastructure

```bash
docker run --rm -v $(pwd):/app -w /app terraform-providers terraform apply
```

### Interactive Shell

```bash
# Get an interactive shell for development
docker run --rm -it -v $(pwd):/app -w /app terraform-providers sh
```

## Configuration

### Adding New Providers

1. Edit `terraform/providers.txt` with the provider information:
   ```
   namespace/provider-name version
   ```

2. Rebuild the Docker image:
   ```bash
   docker build -f terraform/Dockerfile -t terraform-providers .
   ```

### Custom Terraform Version

Build with a specific Terraform version:

```bash
docker build --build-arg TERRAFORM_VERSION=1.7.0 -f terraform/Dockerfile -t terraform-providers .
```

## Architecture

The image includes:

- **Base**: HashiCorp's official Terraform image
- **Provider Cache**: Pre-populated at `/root/.terraform.d/plugin-cache`
- **Additional Tools**: vim, jq, yq for configuration management

### Provider Sources

- **HashiCorp providers**: Downloaded from `releases.hashicorp.com`
- **Microsoft providers**: Downloaded from GitHub releases
- **Multi-arch support**: Automatic architecture detection and download

## Development

### Project Structure

```
.
├── README.md
└── terraform/
    ├── Dockerfile              # Multi-stage Docker build
    ├── install_providers.sh    # Provider installation script
    └── providers.txt          # Provider version specifications
```

### Testing

```bash
# Build the image
docker build -f terraform/Dockerfile -t terraform-providers-test .

# Test provider availability
docker run --rm terraform-providers-test terraform providers

# Test with a sample configuration
echo 'terraform { required_providers { azurerm = { source = "hashicorp/azurerm", version = "~> 4.37" } } }' > test.tf
docker run --rm -v $(pwd):/app -w /app terraform-providers-test terraform init
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TERRAFORM_VERSION` | Terraform version to use | `1.6.6` |
| `TF_PLUGIN_CACHE_DIR` | Plugin cache directory | `/root/.terraform.d/plugin-cache` |

## Troubleshooting

### Architecture Issues

If you encounter architecture-related errors:

```bash
# Check your system architecture
docker run --rm terraform-providers uname -m

# Force specific platform
docker run --platform linux/amd64 --rm terraform-providers terraform version
```

### Provider Not Found

If a provider is not found during `terraform init`:

1. Verify the provider is listed in `terraform/providers.txt`
2. Check the provider namespace and version
3. Rebuild the image after making changes

## Contributing

1. Fork the repository
2. Add your provider to `terraform/providers.txt`
3. Test the build: `docker build -f terraform/Dockerfile -t test .`
4. Submit a pull request

## License

This project is open source. Please check individual provider licenses for their respective terms.
