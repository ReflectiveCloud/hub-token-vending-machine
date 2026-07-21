"""Render STS credentials into the requested output format.

Returns ``(stdout_text, stderr_note)`` rather than printing, so it can be unit
tested and so the CLI controls stream routing (keeping stdout clean for
``eval``/``credential_process`` consumers).
"""

from __future__ import annotations

import json
import shlex

from .models import OutputFormat


def render(
    creds: dict,
    region: str | None,
    fmt: OutputFormat,
    profile_name: str,
) -> tuple[str, str | None]:
    """Render an STS Credentials dict in ``fmt``, returning (stdout, stderr_note)."""
    akid = creds["AccessKeyId"]
    secret = creds["SecretAccessKey"]
    token = creds["SessionToken"]
    expiry = creds["Expiration"]
    expiry_iso = expiry.isoformat() if hasattr(expiry, "isoformat") else str(expiry)
    note = f"# expires {expiry_iso}"

    if fmt is OutputFormat.env:
        lines = [
            f"export AWS_ACCESS_KEY_ID={shlex.quote(akid)}",
            f"export AWS_SECRET_ACCESS_KEY={shlex.quote(secret)}",
            f"export AWS_SESSION_TOKEN={shlex.quote(token)}",
        ]
        if region:
            lines.append(f"export AWS_DEFAULT_REGION={shlex.quote(region)}")
        return "\n".join(lines), note

    if fmt is OutputFormat.credential_process:
        # Exact schema AWS SDKs expect from a credential_process helper.
        return json.dumps({
            "Version": 1,
            "AccessKeyId": akid,
            "SecretAccessKey": secret,
            "SessionToken": token,
            "Expiration": expiry_iso,
        }), None

    if fmt is OutputFormat.json:
        return json.dumps({
            "access_key_id": akid,
            "secret_access_key": secret,
            "session_token": token,
            "expiration": expiry_iso,
            "region": region,
        }, indent=2), None

    # profile
    block = (
        f"[{profile_name}]\n"
        f"aws_access_key_id = {akid}\n"
        f"aws_secret_access_key = {secret}\n"
        f"aws_session_token = {token}\n"
    )
    if region:
        block += f"region = {region}\n"
    return block, note
