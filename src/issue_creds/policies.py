"""S3 session-policy construction.

Allow-list by default (fails closed). These policies are passed as the inline
`Policy` to AssumeRoleWithWebIdentity, where they can only *intersect* with the
role's identity policy — never widen it.
"""

from __future__ import annotations

from typing import Optional

from .models import Role


def _object_resource(bucket: str, prefix: Optional[str]) -> str:
    """Object-level ARN: scoped to ``prefix/*`` if given, else the whole bucket."""
    if prefix:
        return f"arn:aws:s3:::{bucket}/{prefix.strip('/')}/*"
    return f"arn:aws:s3:::{bucket}/*"


def _list_statement(bucket: str, prefix: Optional[str], actions: list[str]) -> dict:
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
        stmt["Condition"] = {"StringLike": {"s3:prefix": [f"{p}/*"]}}
    return stmt


def build_policy(role: Role, bucket: str, prefix: Optional[str]) -> Optional[dict]:
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

    return {"Version": "2012-10-17", "Statement": statements}
