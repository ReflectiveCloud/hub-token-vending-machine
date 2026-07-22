import json
import shlex
from datetime import datetime, timezone

import pytest

from issue_creds.models import OutputFormat
from issue_creds.output import render


def _parse_exports(text):
    """Parse `export VAR=VALUE` lines the way a POSIX shell would, so tests
    assert eval-safety rather than a particular quoting style."""
    env = {}
    for line in text.splitlines():
        tokens = shlex.split(line)  # raises on unbalanced quotes -> unsafe output
        assert tokens[0] == "export"
        key, _, value = tokens[1].partition("=")
        env[key] = value
    return env


@pytest.fixture
def creds():
    return {
        "AccessKeyId": "AKIAEXAMPLE",
        "SecretAccessKey": "secret/with+special=chars",
        "SessionToken": "token//value==",
        "Expiration": datetime(2026, 6, 23, 12, 0, 0, tzinfo=timezone.utc),
    }


def test_env_format_round_trips_through_shell(creds):
    text, note = render(creds, "us-east-1", OutputFormat.env, "s3-scoped")
    env = _parse_exports(text)
    assert env["AWS_ACCESS_KEY_ID"] == "AKIAEXAMPLE"
    assert env["AWS_SECRET_ACCESS_KEY"] == "secret/with+special=chars"
    assert env["AWS_SESSION_TOKEN"] == "token//value=="
    assert env["AWS_DEFAULT_REGION"] == "us-east-1"
    assert note == "# expires 2026-06-23T12:00:00+00:00"


def test_env_format_neutralizes_hostile_region(creds):
    # A region containing shell metacharacters must round-trip as a single,
    # inert value — never break out of quoting into a second command.
    hostile = "x'; rm -rf /"
    text, _ = render(creds, hostile, OutputFormat.env, "s3-scoped")
    env = _parse_exports(text)
    assert env["AWS_DEFAULT_REGION"] == hostile


def test_env_format_omits_region_when_absent(creds):
    text, _ = render(creds, None, OutputFormat.env, "s3-scoped")
    assert "AWS_DEFAULT_REGION" not in text


def test_credential_process_schema(creds):
    text, note = render(creds, "us-east-1", OutputFormat.credential_process, "s3")
    payload = json.loads(text)
    assert payload == {
        "Version": 1,
        "AccessKeyId": "AKIAEXAMPLE",
        "SecretAccessKey": "secret/with+special=chars",
        "SessionToken": "token//value==",
        "Expiration": "2026-06-23T12:00:00+00:00",
    }
    # No stderr note: the SDK reads Expiration from the JSON itself.
    assert note is None


def test_json_format(creds):
    text, note = render(creds, "us-west-2", OutputFormat.json, "s3")
    payload = json.loads(text)
    assert payload["access_key_id"] == "AKIAEXAMPLE"
    assert payload["region"] == "us-west-2"
    assert payload["expiration"] == "2026-06-23T12:00:00+00:00"
    assert note is None


def test_profile_format(creds):
    text, note = render(creds, "eu-west-1", OutputFormat.profile, "my-profile")
    assert text.startswith("[my-profile]\n")
    assert "aws_access_key_id = AKIAEXAMPLE" in text
    assert "aws_session_token = token//value==" in text
    assert "region = eu-west-1" in text
    assert note == "# expires 2026-06-23T12:00:00+00:00"


def test_profile_format_omits_region_when_absent(creds):
    text, _ = render(creds, None, OutputFormat.profile, "my-profile")
    assert "region =" not in text


def test_string_expiration_is_passed_through():
    creds = {
        "AccessKeyId": "AKIA",
        "SecretAccessKey": "s",
        "SessionToken": "t",
        "Expiration": "2026-06-23T12:00:00Z",
    }
    _, note = render(creds, None, OutputFormat.env, "s3")
    assert note == "# expires 2026-06-23T12:00:00Z"
