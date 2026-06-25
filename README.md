# issue-creds

Vend short-lived, scope-limited AWS S3 credentials from inside the hub. Wraps
STS `AssumeRoleWithWebIdentity` and applies an inline **session policy** that can
only *intersect* with the role's identity policy — it can shrink permissions,
never widen them.

## Install

```bash
pip install issue-creds            # from a built wheel/sdist or your index
# or, from a checkout:
pip install .
```
This installs an `issue-creds` command on `$PATH`. In the hub image:
```dockerfile
RUN pip install --no-cache-dir issue-creds
```

## Usage

```bash
# Read the whole bucket for 30 minutes
issue-creds --role download --bucket-scope reflective-persistent-prod --lifetime 30m
# Read a single prefix
issue-creds --role download --bucket-scope reflective-persistent-prod --prefix lagranto/runs
# Upload — scope is fixed to your own JUPYTERHUB_USER prefix (no --prefix allowed)
issue-creds --role upload --bucket-scope reflective-persistent-prod
# Full role (the legacy "power user" behaviour)
issue-creds --role power --bucket-scope reflective-persistent-prod
```

Load into the current shell:
```bash
eval "$(issue-creds --role download --bucket-scope reflective-persistent-prod)"
```
Inspect what *would* be requested without calling STS:
```bash
issue-creds --role upload --bucket-scope reflective-persistent-prod --dry-run
```

### Auto-refreshing profile (recommended)
`--format credential-process` emits AWS's auto-refresh schema, so SDKs re-invoke
the tool on expiry and credentials never touch your shell or history:
```ini
# ~/.aws/config
[profile s3-download]
credential_process = issue-creds --role download --bucket-scope reflective-persistent-prod --prefix lagranto/runs --format credential-process
```
Other formats: `--format env` (default), `--format profile`, `--format json`.

## Roles
| role       | grants                                                            | prefix scoping                          |
|------------|-------------------------------------------------------------------|-----------------------------------------|
| `download` | Get/List (+versions), GetBucketLocation                           | optional `--prefix` (whole bucket if omitted) |
| `upload`   | Put, multipart, List/ListMultipart, GetBucketLocation (no Get)    | forced to `JUPYTERHUB_USER/*`           |
| `power`    | full role identity policy (no session policy)                     | n/a                                     |

## Configuration (environment)
| variable                        | purpose                                                              |
|---------------------------------|----------------------------------------------------------------------|
| `AWS_ROLE_ARN`                  | default role ARN (fallback for all roles)                            |
| `ISSUE_CREDS_DOWNLOAD_ROLE_ARN` | dedicated download role ARN (optional; overrides the fallback)       |
| `ISSUE_CREDS_UPLOAD_ROLE_ARN`   | dedicated upload role ARN (optional)                                 |
| `ISSUE_CREDS_POWER_ROLE_ARN`    | dedicated power role ARN (optional)                                  |
| `ISSUE_CREDS_MAX_LIFETIME`      | cap on `--lifetime` (default `1h`); also raise the role's `MaxSessionDuration` |
| `AWS_WEB_IDENTITY_TOKEN_FILE`   | OIDC token file (set by the hub)                                     |
| `JUPYTERHUB_USER`               | drives the upload prefix and CloudTrail session name                 |

## Security note
The session policy is **defense-in-depth, not a boundary**. Any user who can read
`AWS_WEB_IDENTITY_TOKEN_FILE` can call `AssumeRoleWithWebIdentity` themselves
without the restrictive policy and get whatever the underlying role allows. Real
enforcement comes from **separate, tightly-scoped IAM roles** per `download` /
`upload` / `power`, gated by the OIDC trust policy. Set the dedicated role ARN
env vars above to switch from advisory to enforced — no code change required.
## Development
```bash
pip install -e .[dev]
pytest
```
