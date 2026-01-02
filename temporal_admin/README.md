# Temporal Admin Tools Docker Image

Extended version of `temporalio/admin-tools:1.29.1-tctl-1.18.4-cli-1.5.0` with updated dependencies.

## What's Different

This image upgrades the base Alpine repositories and SQLite packages to address security vulnerabilities:

- **Alpine repositories**: v3.22 → v3.23
- **SQLite & SQLite libraries**: Upgraded to latest versions from Alpine 3.23

All original Temporal admin tools (`tctl`, `temporal` CLI) remain unchanged and fully compatible.

## Build

```bash
docker build -t temporal-admin:latest .
```

## Usage

Same as the official [temporalio/admin-tools](https://hub.docker.com/r/temporalio/admin-tools) image:

```bash
docker run --rm temporal-admin:latest tctl --version
docker run --rm temporal-admin:latest temporal workflow list
```
