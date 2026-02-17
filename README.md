# check-npm-scope-access

[![Quality](https://github.com/codafusion/check-npm-scope-access/actions/workflows/lint-and-typecheck.yml/badge.svg)](https://github.com/codafusion/check-npm-scope-access/actions/workflows/lint-and-typecheck.yml)

GitHub Action to verify read access to private NPM packages for one or more scopes.

## What it does
- Scans all tracked `package.json` files in the checked-out repository.
- Collects package names from:
  - `dependencies`
  - `devDependencies`
  - `peerDependencies`
  - `optionalDependencies`
- Filters names by the configured scopes.
- Calls `<registry-url>/<url-encoded-package-name>` for each match.
- Fails once at the end with a list of all inaccessible packages.

## Inputs
- `scopes` (required): Comma, whitespace, or newline separated scopes, for example:
  - `@codafusion`
  - `@codafusion @acme`
- `token` (optional): Registry token. Defaults to `${{ github.token }}`.
- `registry-url` (optional): Base URL of the NPM registry API.
  - Default: `https://npm.pkg.github.com`

## Usage

```yaml
name: Verify package access

on:
  pull_request:
  push:
    branches: [main]

jobs:
  check-access:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: read
    steps:
      - uses: actions/checkout@v4
      - name: Check private NPM scope access
        uses: codafusion/check-npm-scope-access@v1
        with:
          scopes: |
            @codafusion
            @another-scope
```

## Notes
- If no `package.json` files are found, the action exits successfully with a notice.
- If no dependency matches the configured scopes, the action exits successfully.
- This action validates real runtime access, not only workflow YAML permissions.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy scripts/check_package_access.py
pytest -q
```

## Releases

- Create and push a semantic version tag, for example `v1.0.0`.
- The `Release` workflow will:
  - publish a GitHub Release for that tag
  - update the moving major tag (for example `v1`) to the same commit
- You can also run the `Release` workflow manually and provide a tag like `v1.0.0`.
