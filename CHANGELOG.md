Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

[v0.1.1]

Added

- Prefix-scoped credentials (upload, and download with `--prefix`) now allow
  folder-style listing at the bucket root (`aws s3 ls s3://bucket/`) so users
  can see top-level folder names; recursive listing at the root remains denied.

Fixed

- Prefix-scoped listing no longer requires a trailing slash:
  `aws s3 ls s3://bucket/prefix` and `aws s3 ls s3://bucket/prefix/` both work.

[v0.1.0]

Added

- A CLI to fetch AWS S3 credentials for use outside of the Hub.
- CI to run tests, lint, and publish to PyPi

Removed

- N/A
- 