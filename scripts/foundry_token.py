#!/usr/bin/env python3
"""Fetch an Entra access token for Azure AI Foundry via device-code login.

Replaces `az login` + `az account get-access-token` on hosts without the
Azure CLI (e.g. Termux/Android). Writes the device code to
/tmp/foundry_code.txt (so it survives the noisy Termux shell) and prints the
token to stdout on success. No secrets stored on disk beyond the transient
code file (which is harmless).

Usage:
  python3 scripts/foundry_token.py            # prints token to stdout
  python3 scripts/foundry_token.py --export   # prints FOUNDRY_TOKEN=... line
"""
from __future__ import annotations
import sys
import argparse
from azure.identity import DeviceCodeCredential

TENANT = "885f01ab-7364-4484-be0a-231d541c9e7f"
RESOURCE = "https://ai.azure.com/.default"  # Entra scope for Foundry Agent Service
CODE_FILE = "/data/data/com.termux/files/home/foundry_code.txt"


def _prompt(verification_uri: str, user_code: str, expires_on):
    # Write the code to a file we can read back reliably (Termux shell is noisy)
    msg = (
        f"To sign in, use a web browser to open the page {verification_uri} "
        f"and enter the code {user_code} to authenticate."
    )
    try:
        with open(CODE_FILE, "w") as f:
            f.write(msg + "\n")
    except OSError:
        pass
    sys.stderr.write(msg + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true", help="emit FOUNDRY_TOKEN=... ")
    args = ap.parse_args()

    cred = DeviceCodeCredential(
        tenant_id=TENANT,
        additionally_allowed_tenants=["*"],
        prompt_callback=_prompt,
    )
    token = cred.get_token(RESOURCE)
    if args.export:
        print(f"FOUNDRY_TOKEN={token.token}")
    else:
        print(token.token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
