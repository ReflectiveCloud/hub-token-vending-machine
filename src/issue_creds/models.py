"""Enums shared across the issue-creds package: roles and output formats."""

from enum import Enum


class Role(str, Enum):
    """Permission profile to request; selects which session policy is built."""

    download = "download"
    upload = "upload"
    power = "power"  # full role identity policy, no session policy applied


class OutputFormat(str, Enum):
    """How issued credentials are rendered to stdout."""

    env = "env"                                 # eval "$(issue-creds ...)"
    profile = "profile"                         # printable ~/.aws/credentials block
    json = "json"                               # human-readable
    credential_process = "credential-process"   # AWS SDK auto-refresh schema
