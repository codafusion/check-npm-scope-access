import importlib.util
import urllib.error
import urllib.request
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_package_access.py"
SPEC = importlib.util.spec_from_file_location("check_package_access", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Failed to load scripts/check_package_access.py for tests.")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class _DummyResponse:
    def __init__(self, code: int) -> None:
        self._code = code

    def __enter__(self) -> "_DummyResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False

    def getcode(self) -> int:
        return self._code


def test_parse_scopes_normalizes_and_sorts() -> None:
    result = mod.parse_scopes("@foo, @acme/  @foo")
    assert result == ["@acme", "@foo"]


def test_parse_scopes_rejects_missing_at_prefix() -> None:
    with pytest.raises(SystemExit):
        mod.parse_scopes("acme")


def test_discover_scoped_packages_collects_supported_dependency_sections(tmp_path: Path) -> None:
    package_file = tmp_path / "package.json"
    package_file.write_text(
        """
        {
          "dependencies": {"@acme/core": "^1.0.0", "lodash": "^4.17.21"},
          "devDependencies": {"@foo/dev-tool": "^2.0.0"},
          "peerDependencies": {"@acme/peer": "^3.0.0"},
          "optionalDependencies": {"@foo/optional": "^4.0.0"}
        }
        """,
        encoding="utf-8",
    )

    result = mod.discover_scoped_packages([package_file], ["@acme", "@foo"])
    assert result == ["@acme/core", "@acme/peer", "@foo/dev-tool", "@foo/optional"]


def test_discover_scoped_packages_fails_on_invalid_json(tmp_path: Path) -> None:
    package_file = tmp_path / "package.json"
    package_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(SystemExit):
        mod.discover_scoped_packages([package_file], ["@acme"])


def test_check_package_read_access_returns_200_for_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_urlopen(request: urllib.request.Request) -> _DummyResponse:
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization") or ""
        return _DummyResponse(200)

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)

    status = mod.check_package_read_access("secret-token", "@acme/pkg", "https://npm.pkg.github.com/")

    assert status == 200
    assert captured["url"] == "https://npm.pkg.github.com/%40acme%2Fpkg"
    assert captured["auth"] == "Bearer secret-token"


def test_check_package_read_access_returns_http_status_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(_: urllib.request.Request) -> _DummyResponse:
        raise urllib.error.HTTPError(url="https://example.test", code=403, msg="Forbidden", hdrs=None, fp=None)

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    status = mod.check_package_read_access("token", "@acme/pkg", "https://npm.pkg.github.com")
    assert status == 403


def test_check_package_read_access_returns_zero_on_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_: urllib.request.Request) -> _DummyResponse:
        raise urllib.error.URLError("timeout")

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    status = mod.check_package_read_access("token", "@acme/pkg", "https://npm.pkg.github.com")
    assert status == 0


def test_main_exits_successfully_when_no_package_files(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TOKEN", "token")
    monkeypatch.setenv("SCOPES", "@acme")
    monkeypatch.setenv("REGISTRY_URL", "https://npm.pkg.github.com")
    monkeypatch.setattr(mod, "tracked_package_files", lambda: [])

    mod.main()
    output = capsys.readouterr().out
    assert "OK: no package.json files found in repository." in output


def test_main_aggregates_access_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TOKEN", "token")
    monkeypatch.setenv("SCOPES", "@acme")
    monkeypatch.setenv("REGISTRY_URL", "https://npm.pkg.github.com")
    monkeypatch.setattr(mod, "tracked_package_files", lambda: [Path("package.json")])
    monkeypatch.setattr(mod, "discover_scoped_packages", lambda *_: ["@acme/ok", "@acme/blocked"])

    def fake_check(_: str, package_name: str, __: str) -> int:
        return 200 if package_name == "@acme/ok" else 403

    monkeypatch.setattr(mod, "check_package_read_access", fake_check)

    with pytest.raises(SystemExit):
        mod.main()

    output = capsys.readouterr().out
    assert "ERROR: missing package read access:" in output
    assert "@acme/blocked (HTTP 403: forbidden (token lacks package read access))" in output
