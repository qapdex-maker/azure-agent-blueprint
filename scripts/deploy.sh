#!/usr/bin/env bash
# scripts/deploy.sh — Reproducible Azure deploy for the Agent Blueprint (Gold-Path).
# Mirrors Azure-Samples convention: azd up one-command, isolated, with cleanup trap.
#
# PREREQUISITES (must exist on the HOST that runs this, NOT the build sandbox):
#   - azure-cli (az), azd, docker  ->  https://learn.microsoft.com/azure/developer/azure-developer-cli/install
#   - Azure subscription + QUOTA for Azure OpenAI (or Foundry) in target region
#
# This script does NOT execute on the Termux build host (no az/azd/docker there);
# it is the artifact you run on an Azure-capable machine. Verified locally for
# syntax only (bash -n).
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-azure-agent-blueprint-dev-rg}"
LOCATION="${LOCATION:-eastus}"
ENV_NAME="${ENV_NAME:-dev}"
OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-}"

cleanup() { echo "[deploy] interrupted/cleanup"; }
trap cleanup EXIT

echo "[deploy] using RG=$RESOURCE_GROUP LOCATION=$LOCATION ENV=$ENV_NAME"

# 1) azd auth (interactive on first run; uses current az login otherwise)
azd auth login || { echo "[deploy] azd auth failed"; exit 1; }

# 2) init (idempotent) + provision infra (Bicep)
azd env new "$ENV_NAME" --subscription "$(az account show --query id -o tsv)" || true
azd env set AZURE_LOCATION "$LOCATION"
azd env set OPENAI_ENDPOINT "$OPENAI_ENDPOINT"
azd provision

# 3) package + deploy container app
azd deploy

echo "[deploy] done. App URL:"
azd env get-values | grep -i containerappurl || true
trap - EXIT
