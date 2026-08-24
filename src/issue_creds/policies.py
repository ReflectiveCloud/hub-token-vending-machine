"""S3 session-policy construction.

Allow-list by default (fails closed). These policies are passed as the inline
`Policy` to AssumeRoleWithWebIdentity, where they can only *intersect* with the
role's identity policy — never widen it.
"""

from __future__ import annotations

from .models import Role


def _object_resource(bucket: str, prefix: str | None) -> str:
    """Object-level ARN: scoped to ``prefix/*`` if given, else the whole bucket."""
    if prefix:
        return f"arn:aws:s3:::{bucket}/{prefix.strip('/')}/*"
    return f"arn:aws:s3:::{bucket}/*"


def _list_statement(bucket: str, prefix: str | None, actions: list[str]) -> dict:
    """Bucket-level list statement.

    ListBucket is a bucket-level action; the Resource ARN cannot scope it to a
    prefix, so the s3:prefix condition is what actually constrains listing.
    GetBucketLocation does NOT understand s3:prefix and must live in its own
    unconditioned statement (see build_policy) — never fold it in here.
    """
    stmt = {
        "Sid": "ListWithinScope",
        "Effect": "Allow",
        "Action": actions,
        "Resource": [f"arn:aws:s3:::{bucket}"],
    }
    if prefix:
        p = prefix.strip("/")
        # Both forms: clients send the list prefix with a trailing slash
        # ("p/...") or bare ("p", e.g. `aws s3 ls s3://bkt/p`); the pattern
        # "p/*" alone would deny the bare form.
        stmt["Condition"] = {"StringLike": {"s3:prefix": [p, f"{p}/*"]}}
    return stmt


def _root_nav_statement(bucket_arn: str) -> dict:
    """Folder-style listing at the bucket root, for orientation only.

    Matches exactly what `aws s3 ls s3://bucket/` sends: empty prefix with
    delimiter "/". Returns top-level common prefixes (folder names), while
    recursive root listing (sync, ls --recursive) sends no delimiter and
    stays denied, so keys outside the granted prefix are not enumerable.
    """
    return {
        "Sid": "RootFolderNavigation",
        "Effect": "Allow",
        "Action": ["s3:ListBucket"],
        "Resource": [bucket_arn],
        "Condition": {
            "StringEquals": {"s3:prefix": [""], "s3:delimiter": ["/"]}
        },
    }


def build_policy(role: Role, bucket: str, prefix: str | None) -> dict | None:
    """Return an IAM session policy dict, or None for the power role."""
    if role is Role.power:
        return None

    obj = _object_resource(bucket, prefix)
    bucket_arn = f"arn:aws:s3:::{bucket}"
    location = {
        "Sid": "BucketLocation",
        "Effect": "Allow",
        "Action": ["s3:GetBucketLocation"],
        "Resource": [bucket_arn],
    }

    if role is Role.download:
        statements = [
            {
                "Sid": "ReadObjects",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:GetObjectTagging",
                    "s3:GetObjectVersionTagging",
                ],
                "Resource": [obj],
            },
            _list_statement(
                bucket, prefix, ["s3:ListBucket", "s3:ListBucketVersions"]
            ),
            location,
        ]
    else:  # Role.upload — write + multipart + list, deliberately no GetObject
        statements = [
            {
                "Sid": "WriteObjects",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectTagging",
                    "s3:AbortMultipartUpload",
                    "s3:ListMultipartUploadParts",
                ],
                "Resource": [obj],
            },
            _list_statement(
                bucket, prefix, ["s3:ListBucket", "s3:ListBucketMultipartUploads"]
            ),
            location,
        ]

    if prefix:
        # Prefix-scoped policies deny root listing outright without this;
        # unscoped ones don't need it (their ListBucket is unconditioned).
        statements.append(_root_nav_statement(bucket_arn))

    return {"Version": "2012-10-17", "Statement": statements}
