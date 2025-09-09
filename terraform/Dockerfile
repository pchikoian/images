# Base image argument
ARG TERRAFORM_VERSION=1.6.6
FROM hashicorp/terraform:${TERRAFORM_VERSION}

ENV TF_PLUGIN_CACHE_DIR="/root/.terraform.d/plugin-cache"
ENV TERRAGRUNT_VERSION="v0.86.2"

RUN mkdir -p ${TF_PLUGIN_CACHE_DIR}

# Copy scripts and provider list
COPY install_providers.sh /usr/local/bin/install_providers.sh
COPY install_terragrunt.sh /usr/local/bin/install_terragrunt.sh
COPY providers.txt /tmp/providers.txt

# Run installation
RUN chmod +x /usr/local/bin/install_*.sh && \
          /usr/local/bin/install_providers.sh && \
          /usr/local/bin/install_terragrunt.sh && \
    apk add --no-cache vim jq yq python3 py3-pip openssl curl && \
    python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip

# Set workdir and copy configs
WORKDIR /app
COPY . /app

# Install Python requirements in virtual environment
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install -r /tmp/requirements.txt

# Add venv to PATH
ENV PATH="/opt/venv/bin:$PATH"

CMD ["terraform", "version"]
