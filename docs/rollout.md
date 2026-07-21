# issue-creds — Beta Guide for Hub Users

`issue-creds` vends **short-lived, scope-limited AWS S3 credentials** from inside
the Hub. Instead of long-lived keys, you request exactly the access you need
(read, write, or full) for a bounded time.

> **Beta:** this tool is new. Flags and defaults may change, and you may hit rough
> edges — please report anything surprising (see [Getting help](#getting-help)).

## Quick start

Load read credentials into your current shell for 30 minutes:

```bash
eval "$(issue-creds --role download --lifetime 30m)"
aws s3 ls s3://reflective-persistent-prod/
```

`--bucket-scope` defaults to `reflective-persistent-prod`; pass it explicitly to
target a different bucket.

## Roles

| role       | what you get                                              | prefix scoping                                  |
|------------|-----------------------------------------------------------|-------------------------------------------------|
| `download` | read objects + list                                       | optional `--prefix` (whole bucket if omitted)   |
| `upload`   | write + multipart + list (no read)                        | fixed to your own `JUPYTERHUB_USER/` namespace  |
| `power`    | the role's full permissions                               | n/a                                             |

Pick the **narrowest** role that does the job — it limits the damage if a
credential leaks, and it expires on its own.

## Common options

- `--lifetime` — `30m`, `2h`, `1h30m`, or seconds. Default `1h`, minimum `15m`.
- `--prefix lagranto/runs` — restrict `download` to a key prefix.
- `--dry-run` — print exactly what would be requested, without calling AWS.
- `--format` — `env` (default), `profile`, `json`, or `credential-process`.

## Loading credentials

**Into your shell (quick):**
```bash
eval "$(issue-creds --role download)"
```

**Auto-refreshing profile (recommended, on the Hub):** credentials never touch
your shell history and the SDK refreshes them on expiry.
```ini
# ~/.aws/config
[profile s3-download]
credential_process = issue-creds --role download --prefix lagranto/runs --format credential-process
```
Then use `aws s3 ls --profile s3-download`.

## Using credentials on another machine

You can generate credentials on the Hub and use them elsewhere — they're standard
temporary AWS credentials.

- **Do not** use `--format credential-process` off the Hub: it re-runs
  `issue-creds`, which only works inside the Hub. Use `--format profile` (or
  `env`) and copy the values instead.
- Copy **all three** values — access key, secret key, **and session token**
  (`AWS_SESSION_TOKEN`). Omitting the session token gives a confusing signature
  error.
- Include a region (`--region ...` on the Hub, or set `AWS_DEFAULT_REGION` on the
  target).
- Move them over a secure channel — anything holding them has your access until
  they expire.

Example, using a copy-pasteable profile block:
```bash
# on the Hub
issue-creds --role download --region us-east-1 --format profile --profile-name s3-scoped
# → paste the printed [s3-scoped] block into ~/.aws/credentials on the other machine
```

## When credentials expire

They stop working at the expiry time printed to stderr (`# expires ...`), capped
by `--lifetime`. There is **no remote refresh** — just run `issue-creds` again on
the Hub to get fresh ones. If you need longer sessions, raise `--lifetime` (up to
the configured cap).

## Handle them like secrets

These are real AWS credentials for their lifetime. Don't paste them into shared
docs, tickets, or chat; don't commit them. The `credential-process` flow above
keeps them out of your shell history entirely.

## Getting help

- **Something broke or behaved unexpectedly:** [open an issue](https://github.com/ReflectiveCloud/hub-token-vending-machine/issues).
- **A credential worked when it shouldn't have, or you found a security problem:**
  do **not** open a public issue — follow the [Security Policy](../SECURITY.md).
