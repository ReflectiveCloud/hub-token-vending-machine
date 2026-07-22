# Security Policy

`issue-creds` vends short-lived, scope-limited AWS credentials. We take its
security seriously and appreciate reports that help keep it trustworthy.

## Reporting a Vulnerability

**Please do not open a public issue for security problems.**

Report privately through either channel:

- **GitHub** — open a private advisory from the repository's **Security** tab
  → **Report a vulnerability**. This is the preferred channel. (Requires
  private vulnerability reporting to be enabled under Settings → Security.)
- **Email** — `john@reflective.org`.

Please include:

- A description of the issue and its impact.
- Steps to reproduce, or a proof of concept.
- Affected version (`issue-creds --version`) and, if relevant, your AWS region
  and how role ARNs are configured (advisory single-role vs. dedicated roles).

**Do not include real credentials, session tokens, or the contents of
`AWS_WEB_IDENTITY_TOKEN_FILE` in your report.** Redact them; we can reproduce
from a description.

We aim to acknowledge a report within **3 business days** and to keep you
updated as we investigate. We support coordinated disclosure and will credit
reporters who wish to be named once a fix is released.

## Supported Versions

This project is pre-1.0. Security fixes are applied to the latest release and
the `main` branch only.

| Version | Supported |
|---------|-----------|
| latest release / `main` | ✅ |
| older releases | ❌ |

## Threat Model & Scope

This mirrors the trust model described in the
[README security note](./README.md#security-note). The inline session policy
applied by this tool can only *intersect* with the role's identity policy — it
can shrink permissions, never widen them. It is **defense-in-depth, not a
security boundary**. Real enforcement comes from separate, tightly-scoped IAM
roles per `download` / `upload` / `power`, gated by the OIDC trust policy.

### In scope — please report

- A generated session policy that grants **more** than the requested role
  intends — e.g. a `download --prefix foo` request that fails to scope and
  exposes the whole bucket, or an `upload` role that can `GetObject` (the
  deliberate no-read guarantee).
- Prefix or path handling that lets a user escape their `JUPYTERHUB_USER`
  namespace where enforcement relies on the session policy.
- Command or shell injection through any output format (`env`, `profile`,
  `json`, `credential-process`).
- The web identity token or issued credentials leaking into logs, stderr,
  temporary files, or process arguments.
- Vulnerabilities in pinned dependencies (`boto3`, `typer`) as used here.

### Out of scope — documented, by design

These follow from the trust model above and are **not** tool vulnerabilities:

- A user who can read `AWS_WEB_IDENTITY_TOKEN_FILE` calling
  `AssumeRoleWithWebIdentity` directly and bypassing the session policy. In
  single-role (advisory) mode the policy is a guardrail, not a boundary.
- Credentials emitted by `--format env` ending up in shell history. Use
  `--format credential-process` (the recommended path) to keep credentials out
  of the shell and on-disk history.
- Operator-side IAM misconfiguration: overly broad role identity policies, a
  permissive OIDC trust policy, a raised `MaxSessionDuration`, or a large
  `ISSUE_CREDS_MAX_LIFETIME`.

## Hardening for Deployers

Most of this tool's security is a property of how it is deployed. To move from
advisory to enforced scoping:

- Create dedicated, least-privilege IAM roles per profile and set
  `ISSUE_CREDS_DOWNLOAD_ROLE_ARN`, `ISSUE_CREDS_UPLOAD_ROLE_ARN`, and
  `ISSUE_CREDS_POWER_ROLE_ARN`. With these set, scoping is enforced by IAM
  rather than by the advisory session policy — no code change required.
- Scope each role's OIDC trust policy as tightly as possible (e.g. to the
  expected `sub`/`aud` claims from the hub).
- Set `MaxSessionDuration` on each role and `ISSUE_CREDS_MAX_LIFETIME` to the
  shortest lifetime your workflows tolerate.
