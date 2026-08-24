import pytest

from issue_creds.core import parse_duration
from issue_creds.models import Role
from issue_creds.policies import build_policy


def _stmt(policy, sid):
    return next(s for s in policy["Statement"] if s["Sid"] == sid)


def _all_actions(policy):
    return [a for s in policy["Statement"] for a in s["Action"]]


# --- duration parsing -------------------------------------------------------
@pytest.mark.parametrize(
    "text,seconds",
    [("30m", 1800), ("2h", 7200), ("1h30m", 5400), ("900s", 900), ("3600", 3600)],
)
def test_parse_duration_forms(text, seconds):
    assert parse_duration(text) == seconds


def test_parse_duration_invalid():
    with pytest.raises(ValueError):
        parse_duration("banana")


# --- policy: power ----------------------------------------------------------
def test_power_has_no_session_policy():
    assert build_policy(Role.power, "bkt", None) is None


# --- policy: download -------------------------------------------------------
def test_download_whole_bucket_has_no_prefix_condition():
    pol = build_policy(Role.download, "bkt", None)
    assert _stmt(pol, "ReadObjects")["Resource"] == ["arn:aws:s3:::bkt/*"]
    assert "Condition" not in _stmt(pol, "ListWithinScope")


def test_download_prefix_sets_resource_and_list_condition():
    pol = build_policy(Role.download, "bkt", "a/b")
    assert _stmt(pol, "ReadObjects")["Resource"] == ["arn:aws:s3:::bkt/a/b/*"]
    # Both forms so `aws s3 ls s3://bkt/a/b` works with or without a trailing slash.
    cond = _stmt(pol, "ListWithinScope")["Condition"]["StringLike"]["s3:prefix"]
    assert cond == ["a/b", "a/b/*"]


def test_scoped_policies_allow_root_folder_navigation():
    # `aws s3 ls s3://bkt/` (empty prefix + delimiter "/") is allowed for
    # orientation; recursive root listing sends no delimiter and stays denied.
    for role, prefix in [(Role.download, "a/b"), (Role.upload, "user")]:
        nav = _stmt(build_policy(role, "bkt", prefix), "RootFolderNavigation")
        assert nav["Action"] == ["s3:ListBucket"]
        assert nav["Condition"] == {
            "StringEquals": {"s3:prefix": [""], "s3:delimiter": ["/"]}
        }


def test_whole_bucket_download_has_no_root_nav_statement():
    # Unscoped ListBucket is unconditioned; the nav statement would be redundant.
    pol = build_policy(Role.download, "bkt", None)
    assert "RootFolderNavigation" not in [s["Sid"] for s in pol["Statement"]]


# --- policy: upload ---------------------------------------------------------
def test_upload_is_write_only_no_getobject():
    pol = build_policy(Role.upload, "bkt", "user")
    actions = _all_actions(pol)
    assert "s3:PutObject" in actions
    assert "s3:GetObject" not in actions


def test_get_bucket_location_never_carries_prefix_condition():
    # GetBucketLocation doesn't understand s3:prefix; a condition would break it.
    pol = build_policy(Role.upload, "bkt", "user")
    assert "Condition" not in _stmt(pol, "BucketLocation")
