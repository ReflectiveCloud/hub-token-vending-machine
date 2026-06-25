# Contributing to issue-creds

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.
All contributors are expected to follow our [Code of Conduct](./CODE_OF_CONDUCT.md).

> Found a security issue? Please **do not** open a public issue or PR — follow
> our [Security Policy](./SECURITY.md) for private disclosure instead.

## Getting Started

1. Fork and clone the repository:

```bash
git clone https://github.com/ReflectiveCloud/hub-token-vending-machine.git
cd hub-token-vending-machine
```

2. Install in editable mode with the development extras:

```bash
pip install -e .[dev]
```

See the [README](./README.md#install) for usage and configuration details.

## Development Workflow

1. Create a branch for your work using one of these prefixes:

```bash
git checkout -b feat/your-feature-name       # new feature
git checkout -b fix/your-bug-fix             # bug fix
git checkout -b docs/what-you-documented     # documentation only
git checkout -b test/what-you-tested         # adding/improving tests
git checkout -b refactor/what-you-refactored # restructure without behavior change
git checkout -b perf/what-you-optimized      # performance improvement
```

2. Make your changes and ensure they pass all tests.

3. Commit your changes with a clear message:

```bash
git commit -m "Add brief description of change"
```

4. Push and open a pull request against the `main` branch.

## Code Style
- PEP 8 with 4-space indentation
- Type hints encouraged for public APIs
- Linting is enforced in CI with [Ruff](https://docs.astral.sh/ruff/); run it
  locally before pushing:

```bash
ruff check .
```

- No enforced formatter yet; please match the surrounding style

## Running Tests

Tests run fully offline — no AWS account or network access required:

```bash
pip install -e .[dev]
pytest
```

### Writing Tests

- Tests live in `tests/` and use [pytest](https://docs.pytest.org/).
- Mock any cloud or network calls; tests must run offline. STS and other AWS
  calls should be stubbed (e.g. by monkeypatching `issue_creds.core`).
- Aim for one test file per source module (e.g. `test_output.py` for `output.py`).

## Reporting Issues

For non-security bugs, please include:

- Python version
- Package version (`issue-creds --version`)
- Steps to reproduce the issue
- Full error traceback

(For security vulnerabilities, see the [Security Policy](./SECURITY.md) instead.)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 license.
