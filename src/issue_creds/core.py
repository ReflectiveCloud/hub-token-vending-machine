"""Environment resolution, duration parsing, and the STS call.

Everything here is CLI-agnostic and raises CredsError for user-facing failures.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .errors import CredsError
from .models import Role

# Per-role IAM role ARNs. Each falls back to $AWS_ROLE_ARN so the tool works
# with a single role (session policy as advisory guardrail) and tightens into
# real enforcement once dedicated roles exist and these are set.
_ROLE_ARN_ENV = {
    Role.download: "ISSUE_CREDS_DOWNLOAD_ROLE_ARN",
    Role.upload: "ISSUE_CREDS_UPLOAD_ROLE_ARN",
    Role.power: "ISSUE_CREDS_POWER_ROLE_ARN",
}

# AWS hard limits for AssumeRoleWithWebIdentity duration.
AWS_MIN_DURATION = 900        # 15m
DEFAULT_MAX_DURATION = 3600   # 1h (download/power); see ISSUE_CREDS_MAX_LIFETIME
UPLOAD_MAX_DURATION = 21600   # 6h; uploads may run long. Needs the upload role's
                              # MaxSessionDuration >= 6h to actually be granted by STS.

_DUR_RE = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")


def parse_duration(text: str) -> int:
    """Accept '30m', '2h', '1h30m', '900s', or bare seconds -> int seconds.

    Raises ValueError on malformed input (the CLI converts this to a clean
    parameter error).
    """
    s = text.strip().lower()
    if s.isdigit():
        return int(s)
    m = _DUR_RE.match(s)
    if not m or not any(m.groups()):
        raise ValueError(
            f"invalid duration {text!r}; use forms like '30m', '2h', '1h30m'."
        )
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def max_duration(role: Role) -> int:
    """Cap on requested lifetime for a role.

    Defaults to 1h, except uploads which may run up to 6h. A set
    ISSUE_CREDS_MAX_LIFETIME overrides the per-role default for all roles.
    """
    default = UPLOAD_MAX_DURATION if role is Role.upload else DEFAULT_MAX_DURATION
    raw = os.environ.get("ISSUE_CREDS_MAX_LIFETIME")
    if not raw:
        return default
    try:
        return parse_duration(raw)
    except ValueError as exc:
        raise CredsError(f"ISSUE_CREDS_MAX_LIFETIME: {exc}") from exc


def role_arn_for(role: Role) -> str:
    """Resolve the IAM role ARN for a role: its dedicated env var, else AWS_ROLE_ARN."""
    arn = os.environ.get(_ROLE_ARN_ENV[role]) or os.environ.get("AWS_ROLE_ARN")
    if not arn:
        raise CredsError(
            f"no role ARN for '{role.value}'. Set {_ROLE_ARN_ENV[role]} "
            "or AWS_ROLE_ARN."
        )
    return arn


def web_identity_token() -> str:
    """Read the OIDC token from AWS_WEB_IDENTITY_TOKEN_FILE (set by the hub)."""
    path = os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE")
    if not path:
        raise CredsError("AWS_WEB_IDENTITY_TOKEN_FILE is not set (not on the hub?).")
    try:
        return Path(path).read_text().strip()
    except OSError as exc:
        raise CredsError(f"could not read web identity token: {exc}") from exc


def session_name() -> str:
    """CloudTrail attribution lives here — prefer the real username."""
    raw = (
        os.environ.get("JUPYTERHUB_USER")
        or os.environ.get("JUPYTERHUB_CLIENT_ID")
        or "issue-creds"
    )
    safe = re.sub(r"[^\w+=,.@-]", "-", raw)[:64]
    return safe if len(safe) >= 2 else f"{safe}-user"[:64]


def user_prefix() -> str:
    """Per-user write namespace, taken from the hub-provided username.

    Used as-is (whitespace/slashes trimmed). S3 keys allow '@' and '.', so an
    email username becomes a prefix like 'john@reflective.org/...'. Slugify here
    if you'd rather have filesystem-safe prefixes.
    """
    raw = os.environ.get("JUPYTERHUB_USER")
    if not raw:
        raise CredsError(
            "JUPYTERHUB_USER is not set; cannot determine your upload prefix "
            "(uploads are scoped to your own namespace)."
        )
    return raw.strip().strip("/")


def assume_role(
    role_arn: str,
    session: str,
    token: str,
    seconds: int,
    policy: dict | None,
    region: str | None = None,
) -> dict:
    """Call STS AssumeRoleWithWebIdentity and return the Credentials dict."""
    params = dict(
        RoleArn=role_arn,
        RoleSessionName=session,
        WebIdentityToken=token,
        DurationSeconds=seconds,
    )
    if policy is not None:
        params["Policy"] = json.dumps(policy)
    try:
        sts = boto3.client("sts", region_name=region)
        resp = sts.assume_role_with_web_identity(**params)
    except (ClientError, BotoCoreError) as exc:
        raise CredsError(str(exc)) from exc
    return resp["Credentials"]
