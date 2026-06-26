"""Typer CLI: the thin presentation layer over the issue_creds package."""

# NB: do NOT add `from __future__ import annotations` here. Typer introspects
# this function's annotations at runtime to build the CLI, and on Python 3.9
# (which is pinned to typer<=0.23.2) stringized annotations break option
# detection — required options silently become positional arguments. Keeping
# annotations as real objects (and using Optional[...] rather than `X | None`)
# keeps the CLI correct across all supported Python/typer versions.

import json
import os
from typing import Annotated, Optional

import typer

from . import __version__, core, output, policies
from .errors import CredsError
from .models import OutputFormat, Role

app = typer.Typer(
    add_completion=False,
    help="Vend short-lived, scope-limited AWS credentials for S3.",
)


def _version_cb(value: bool) -> None:
    """Eager --version callback: print the version and exit before anything else."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def _parse_lifetime(value: str) -> int:
    """Parse a --lifetime string to seconds, as a clean Typer parameter error."""
    try:
        return core.parse_duration(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def main(
    role: Annotated[Role, typer.Option(
        "--role", help="Permission profile to request.")],
    bucket_scope: Annotated[str, typer.Option(
        "--bucket-scope",
        help="Target S3 bucket name (no arn:/s3:// prefix).",
    )] = "reflective-persistent-prod",
    prefix: Annotated[Optional[str], typer.Option(
        "--prefix",
        help="Reads only: restrict to a key prefix, e.g. 'lagranto/runs'. "
             "Ignored for uploads, which are pinned to your JUPYTERHUB_USER "
             "prefix.")] = None,
    lifetime: Annotated[str, typer.Option(
        "--lifetime",
        help="Credential lifetime: '30m', '2h', '1h30m', or seconds.")] = "1h",
    fmt: Annotated[OutputFormat, typer.Option(
        "--format", help="Output format.")] = OutputFormat.env,
    profile_name: Annotated[str, typer.Option(
        "--profile-name",
        help="Profile name for --format profile.")] = "s3-scoped",
    region: Annotated[Optional[str], typer.Option(
        "--region",
        help="Override region (else AWS_REGION/AWS_DEFAULT_REGION).")] = None,
    dry_run: Annotated[bool, typer.Option(
        "--dry-run",
        help="Print the session policy and request params; do not call STS.")] = False,
    version: Annotated[bool, typer.Option(
        "--version", callback=_version_cb, is_eager=True,
        help="Show version and exit.")] = False,
) -> None:
    """Issue scoped, short-lived S3 credentials for use outside of the Hub."""
    try:
        seconds = _parse_lifetime(lifetime)
        cap = core.max_duration()
        if seconds < core.AWS_MIN_DURATION:
            raise CredsError(
                f"lifetime {seconds}s is below the AWS minimum "
                f"({core.AWS_MIN_DURATION}s / 15m)."
            )
        if seconds > cap:
            raise CredsError(
                f"lifetime {seconds}s exceeds the cap {cap}s (raise "
                "ISSUE_CREDS_MAX_LIFETIME and the role's MaxSessionDuration "
                "to allow more)."
            )

        bucket = bucket_scope.removeprefix("s3://").strip("/")

        if role is Role.upload:
            if prefix is not None:
                raise CredsError(
                    "--prefix is not allowed for uploads; write scope is fixed "
                    "to your own JUPYTERHUB_USER prefix."
                )
            effective_prefix: Optional[str] = core.user_prefix()
        elif role is Role.power:
            if prefix is not None:
                raise CredsError(
                    "--prefix is not allowed for the power role; it requests the "
                    "full role identity policy with no prefix scoping."
                )
            effective_prefix = None
        else:
            effective_prefix = prefix

        policy = policies.build_policy(role, bucket, effective_prefix)
        region_ = (
            region
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
        )
        sess = core.session_name()
        arn = core.role_arn_for(role)

        if dry_run:
            typer.echo(f"# role            : {role.value}")
            typer.echo(f"# role ARN        : {arn}")
            typer.echo(f"# session name    : {sess}")
            typer.echo(f"# scope prefix    : {effective_prefix or '(whole bucket)'}")
            typer.echo(f"# duration (s)    : {seconds}")
            typer.echo(f"# region          : {region_ or '(unset)'}")
            typer.echo("# session policy  :")
            typer.echo(
                json.dumps(policy, indent=2) if policy
                else "# (none — power role uses the full role policy)"
            )
            return

        token = core.web_identity_token()
        creds = core.assume_role(arn, sess, token, seconds, policy, region_)
        stdout_text, note = output.render(creds, region_, fmt, profile_name)
        typer.echo(stdout_text)
        if note:
            typer.echo(note, err=True)
    except CredsError as exc:
        typer.echo(f"issue-creds: error: {exc}", err=True)
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
