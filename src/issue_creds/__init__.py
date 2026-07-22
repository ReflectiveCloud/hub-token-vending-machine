"""issue-creds: scope-limited, short-lived AWS S3 credential vending for JupyterHub."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("issue-creds")
except PackageNotFoundError:  # not installed (e.g. running from a bare checkout)
    __version__ = "unknown"
