#!/usr/bin/env bash
# scripts/run_tests.sh — canonical self-test (isolated, trap-cleanup).
# Convention: run isolated with its own PREFIX/env, clean up on exit.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/aapl-blueprint-test.XXXXXX")"
export PYTHONPATH="$REPO_ROOT"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "[run_tests] repo=$REPO_ROOT  tmp=$TMP"
echo "[run_tests] python=$(python3 --version 2>&1)"

# 1) syntax: all python modules
echo "[run_tests] py_compile ..."
python3 -m py_compile \
  "$REPO_ROOT/src/agent/base.py" \
  "$REPO_ROOT/src/agent/fakellm.py" \
  "$REPO_ROOT/src/agent/azure.py" \
  "$REPO_ROOT/src/agent/foundry.py" \
  "$REPO_ROOT/src/agent/observability.py" \
  "$REPO_ROOT/src/agent/service.py" \
  "$REPO_ROOT/src/tools/builtin.py" \
  "$REPO_ROOT/src/orchestrator/chain.py" \
  "$REPO_ROOT/tests/test_core.py"
echo "[run_tests] py_compile OK"

# 2) unit tests
echo "[run_tests] unit tests ..."
python3 "$REPO_ROOT/tests/test_core.py"

# 3) IaC / script sanity
echo "[run_tests] bash -n deploy.sh ..."
bash -n "$REPO_ROOT/scripts/deploy.sh" && echo "[run_tests] deploy.sh OK"
python3 -c "import yaml;yaml.safe_load(open('$REPO_ROOT/azure.yaml'));print('[run_tests] azure.yaml OK')"

echo "[run_tests] ALL CHECKS PASSED"
