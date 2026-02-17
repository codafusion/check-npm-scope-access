#!/usr/bin/env python3
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import NoReturn

DEPENDENCY_SCOPES = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)


def fail(message: str) -> NoReturn:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def tracked_package_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "package.json", "**/package.json"],
        check=True,
        capture_output=True,
        text=True,
    )
    files = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    return files


def parse_scopes(raw_scopes: str) -> list[str]:
    scopes: set[str] = set()
    for raw_scope in re.split(r"[\s,]+", raw_scopes.strip()):
        scope = raw_scope.strip()
        if not scope:
            continue
        if not scope.startswith("@"):
            fail(f"invalid scope '{scope}'. Scopes must start with '@'.")
        normalized = scope.rstrip("/")
        scopes.add(normalized)

    parsed = sorted(scopes)
    if not parsed:
        fail("no scopes provided. Use the 'scopes' input (for example '@codafusion @acme').")
    return parsed


def discover_scoped_packages(package_files: list[Path], scopes: list[str]) -> list[str]:
    discovered: set[str] = set()
    for package_file in package_files:
        try:
            data = json.loads(package_file.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"failed to parse {package_file}: {exc}")

        for dependency_scope in DEPENDENCY_SCOPES:
            deps = data.get(dependency_scope, {})
            if isinstance(deps, dict):
                for name in deps.keys():
                    if isinstance(name, str) and any(name.startswith(f"{package_scope}/") for package_scope in scopes):
                        discovered.add(name)
    return sorted(discovered)


def check_package_read_access(token: str, package_name: str, registry_url: str) -> int:
    encoded_name = urllib.parse.quote(package_name, safe="")
    url = f"{registry_url.rstrip('/')}/{encoded_name}"
    request = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.npm.install-v1+json",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            return response.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        print(f"ERROR: request failed for {package_name}: {exc}")
        return 0


def describe_failure_status(status: int) -> str:
    if status == 403:
        return "forbidden (token lacks package read access)"
    if status == 404:
        return "not found (package does not exist or is not visible)"
    if status == 401:
        return "unauthorized (invalid or missing token)"
    if status == 0:
        return "request failed (network error or timeout)"
    if 400 <= status < 500:
        return "client error"
    if status >= 500:
        return "registry server error"
    return "unexpected status"


def main() -> None:
    token = os.getenv("TOKEN", "")
    if not token:
        fail("token is missing.")

    scopes = parse_scopes(os.getenv("SCOPES", ""))
    registry_url = os.getenv("REGISTRY_URL", "https://npm.pkg.github.com").strip()
    if not registry_url:
        fail("registry-url is missing.")

    package_files = tracked_package_files()
    if not package_files:
        print("OK: no package.json files found in repository.")
        return

    scoped_packages = discover_scoped_packages(package_files, scopes)
    if not scoped_packages:
        joined_scopes = ", ".join(scopes)
        print(f"OK: no dependencies found for scopes: {joined_scopes}")
        return

    failures: list[str] = []
    print(f"Checking package read access for {len(scoped_packages)} package(s) in scopes: {', '.join(scopes)}")

    for package_name in scoped_packages:
        status = check_package_read_access(token, package_name, registry_url)
        if status == 200:
            print(f"OK: {package_name}")
        else:
            failures.append(f"{package_name} (HTTP {status}: {describe_failure_status(status)})")

    if failures:
        print("ERROR: missing package read access:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("All required scoped packages are readable:")
    for package_name in scoped_packages:
        print(f"- {package_name}")


if __name__ == "__main__":
    main()
