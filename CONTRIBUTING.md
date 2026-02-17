# Contributing

## Local checks
Install tooling:

```bash
python -m pip install -e ".[dev]"
```

Run checks:

```bash
ruff check .
mypy scripts/check_package_access.py
pytest -q
python -m py_compile scripts/check_package_access.py
```

## Pull requests
- Keep PRs small and scoped to one concern
- Include a short "why" in the PR description
- Update docs when behavior, inputs, or outputs change
- Add or update examples when introducing new options
- CI (ruff, mypy) must be green before merge
- Do not include secrets, tokens, or private registry details
