"""Exception types for issue-creds."""


class CredsError(Exception):
    """A user-facing error. The CLI prints the message and exits non-zero.

    Core/library code raises this instead of touching Typer/Click, so the
    package stays usable (and testable) independently of the CLI layer.
    """
