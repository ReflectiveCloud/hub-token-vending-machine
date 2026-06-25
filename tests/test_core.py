import pytest

from issue_creds import core
from issue_creds.errors import CredsError
from issue_creds.models import Role


# --- max_duration -----------------------------------------------------------
def test_max_duration_default(monkeypatch):
    monkeypatch.delenv("ISSUE_CREDS_MAX_LIFETIME", raising=False)
    assert core.max_duration() == core.DEFAULT_MAX_DURATION


def test_max_duration_override(monkeypatch):
    monkeypatch.setenv("ISSUE_CREDS_MAX_LIFETIME", "2h")
    assert core.max_duration() == 7200


def test_max_duration_invalid_raises_credserror(monkeypatch):
    monkeypatch.setenv("ISSUE_CREDS_MAX_LIFETIME", "banana")
    with pytest.raises(CredsError):
        core.max_duration()


# --- role_arn_for -----------------------------------------------------------
def test_role_arn_dedicated_takes_precedence(monkeypatch):
    monkeypatch.setenv("ISSUE_CREDS_DOWNLOAD_ROLE_ARN", "arn:dedicated")
    monkeypatch.setenv("AWS_ROLE_ARN", "arn:fallback")
    assert core.role_arn_for(Role.download) == "arn:dedicated"


def test_role_arn_falls_back_to_aws_role_arn(monkeypatch):
    monkeypatch.delenv("ISSUE_CREDS_UPLOAD_ROLE_ARN", raising=False)
    monkeypatch.setenv("AWS_ROLE_ARN", "arn:fallback")
    assert core.role_arn_for(Role.upload) == "arn:fallback"


def test_role_arn_missing_raises(monkeypatch):
    monkeypatch.delenv("ISSUE_CREDS_POWER_ROLE_ARN", raising=False)
    monkeypatch.delenv("AWS_ROLE_ARN", raising=False)
    with pytest.raises(CredsError):
        core.role_arn_for(Role.power)


# --- web_identity_token -----------------------------------------------------
def test_web_identity_token_reads_and_strips(monkeypatch, tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("  the-token\n")
    monkeypatch.setenv("AWS_WEB_IDENTITY_TOKEN_FILE", str(token_file))
    assert core.web_identity_token() == "the-token"


def test_web_identity_token_unset_raises(monkeypatch):
    monkeypatch.delenv("AWS_WEB_IDENTITY_TOKEN_FILE", raising=False)
    with pytest.raises(CredsError):
        core.web_identity_token()


def test_web_identity_token_missing_file_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("AWS_WEB_IDENTITY_TOKEN_FILE", str(tmp_path / "nope"))
    with pytest.raises(CredsError):
        core.web_identity_token()


# --- session_name -----------------------------------------------------------
def test_session_name_prefers_jupyterhub_user(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_USER", "john@reflective.org")
    assert core.session_name() == "john@reflective.org"


def test_session_name_sanitizes_disallowed_chars(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_USER", "a b/c?")
    # space, slash and question mark are not in [\w+=,.@-] -> replaced with '-'
    assert core.session_name() == "a-b-c-"


def test_session_name_truncates_to_64(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_USER", "x" * 100)
    assert len(core.session_name()) == 64


def test_session_name_pads_short_values(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_USER", "x")
    assert core.session_name() == "x-user"


def test_session_name_falls_back_to_client_id(monkeypatch):
    monkeypatch.delenv("JUPYTERHUB_USER", raising=False)
    monkeypatch.setenv("JUPYTERHUB_CLIENT_ID", "client-123")
    assert core.session_name() == "client-123"


def test_session_name_default(monkeypatch):
    monkeypatch.delenv("JUPYTERHUB_USER", raising=False)
    monkeypatch.delenv("JUPYTERHUB_CLIENT_ID", raising=False)
    assert core.session_name() == "issue-creds"


# --- user_prefix ------------------------------------------------------------
def test_user_prefix_strips_surrounding_slashes(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_USER", "/john/")
    assert core.user_prefix() == "john"


def test_user_prefix_unset_raises(monkeypatch):
    monkeypatch.delenv("JUPYTERHUB_USER", raising=False)
    with pytest.raises(CredsError):
        core.user_prefix()
