# Base image argument
ARG TERRAFORM_VERSION=1.6.6
FROM hashicorp/terraform:${TERRAFORM_VERSION}

ENV TF_PLUGIN_CACHE_DIR="/root/.terraform.d/plugin-cache"
RUN mkdir -p ${TF_PLUGIN_CACHE_DIR}

# Copy scripts and provider list
COPY install_providers.sh /usr/local/bin/install_providers.sh
COPY providers.txt /tmp/providers.txt

# Run installation
RUN chmod +x /usr/local/bin/install_providers.sh && \
          /usr/local/bin/install_providers.sh

# Set workdir and copy configs
WORKDIR /app
COPY . /app

CMD ["terraform", "version"]
