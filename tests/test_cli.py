from datetime import datetime, timezone

import pytest
from typer.testing import CliRunner

from issue_creds import __version__, core
from issue_creds.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Start each test from a known environment."""
    for var in (
        "AWS_ROLE_ARN",
        "ISSUE_CREDS_DOWNLOAD_ROLE_ARN",
        "ISSUE_CREDS_UPLOAD_ROLE_ARN",
        "ISSUE_CREDS_POWER_ROLE_ARN",
        "ISSUE_CREDS_MAX_LIFETIME",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "JUPYTERHUB_USER",
        "JUPYTERHUB_CLIENT_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AWS_ROLE_ARN", "arn:aws:iam::123456789012:role/test")


# --- version ----------------------------------------------------------------
def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


# --- lifetime bounds --------------------------------------------------------
def test_lifetime_below_minimum_fails():
    result = runner.invoke(
        app, ["--role", "download", "--bucket-scope", "bkt", "--lifetime", "60s"]
    )
    assert result.exit_code == 1
    assert "below the AWS minimum" in result.output


def test_lifetime_above_cap_fails():
    result = runner.invoke(
        app, ["--role", "download", "--bucket-scope", "bkt", "--lifetime", "2h"]
    )
    assert result.exit_code == 1
    assert "exceeds the cap" in result.output


def test_lifetime_within_raised_cap_is_accepted(monkeypatch):
    monkeypatch.setenv("ISSUE_CREDS_MAX_LIFETIME", "4h")
    result = runner.invoke(
        app,
        ["--role", "download", "--bucket-scope", "bkt",
         "--lifetime", "2h", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "duration (s)    : 7200" in result.output


def test_invalid_lifetime_is_a_parameter_error():
    result = runner.invoke(
        app, ["--role", "download", "--bucket-scope", "bkt", "--lifetime", "banana"]
    )
    assert result.exit_code != 0


# --- prefix scoping rules ---------------------------------------------------
def test_upload_rejects_prefix(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_USER", "john")
    result = runner.invoke(
        app, ["--role", "upload", "--bucket-scope", "bkt", "--prefix", "x"]
    )
    assert result.exit_code == 1
    assert "--prefix is not allowed for uploads" in result.output


def test_power_rejects_prefix():
    result = runner.invoke(
        app, ["--role", "power", "--bucket-scope", "bkt", "--prefix", "x"]
    )
    assert result.exit_code == 1
    assert "not allowed for the power role" in result.output


# --- dry-run ----------------------------------------------------------------
def test_dry_run_download_shows_policy_and_skips_sts():
    result = runner.invoke(
        app,
        ["--role", "download", "--bucket-scope", "s3://bkt/", "--prefix", "a/b",
         "--dry-run"],
    )
    assert result.exit_code == 0
    # bucket-scope is normalized (s3:// + slashes stripped).
    assert '"arn:aws:s3:::bkt/a/b/*"' in result.output
    assert "s3:GetObject" in result.output
    assert "scope prefix    : a/b" in result.output


def test_dry_run_upload_pins_user_prefix(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_USER", "john@reflective.org")
    result = runner.invoke(
        app, ["--role", "upload", "--bucket-scope", "bkt", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "scope prefix    : john@reflective.org" in result.output
    assert "s3:PutObject" in result.output
    assert "s3:GetObject" not in result.output


def test_dry_run_power_has_no_session_policy():
    result = runner.invoke(
        app, ["--role", "power", "--bucket-scope", "bkt", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "power role uses the full role policy" in result.output


def test_missing_role_arn_fails(monkeypatch):
    monkeypatch.delenv("AWS_ROLE_ARN", raising=False)
    result = runner.invoke(
        app, ["--role", "download", "--bucket-scope", "bkt", "--dry-run"]
    )
    assert result.exit_code == 1
    assert "no role ARN" in result.output


# --- full path with STS stubbed ---------------------------------------------
def test_happy_path_renders_env_format(monkeypatch):
    monkeypatch.setattr(core, "web_identity_token", lambda: "fake-token")

    def fake_assume_role(arn, sess, token, seconds, policy, region):
        assert token == "fake-token"
        assert seconds == 1800
        return {
            "AccessKeyId": "AKIA",
            "SecretAccessKey": "secret",
            "SessionToken": "tok",
            "Expiration": datetime(2026, 6, 23, 12, 0, 0, tzinfo=timezone.utc),
        }

    monkeypatch.setattr(core, "assume_role", fake_assume_role)
    result = runner.invoke(
        app, ["--role", "download", "--bucket-scope", "bkt", "--lifetime", "30m"]
    )
    assert result.exit_code == 0
    assert "export AWS_ACCESS_KEY_ID=AKIA" in result.output
    assert "# expires 2026-06-23T12:00:00+00:00" in result.output
