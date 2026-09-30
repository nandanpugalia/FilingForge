"""Ensure both desktop builds explicitly collect curl's native dependencies."""
from pathlib import Path
from unittest.mock import Mock

import pytest

from sidecar import build_sidecar


@pytest.mark.parametrize('system,suffix,triple', [
    ('Windows', '.exe', 'x86_64-pc-windows-msvc'),
    ('Darwin', '', 'aarch64-apple-darwin'),
])
def test_sidecar_bundles_curl_for_both_desktop_platforms(tmp_path, monkeypatch, system, suffix, triple):
    raw = tmp_path / 'dist' / f'filingforge-api{suffix}'
    raw.parent.mkdir()
    raw.write_bytes(b'build output')
    run = Mock()
    monkeypatch.setattr(build_sidecar, 'ROOT', tmp_path)
    monkeypatch.setattr(build_sidecar.platform, 'system', lambda: system)
    monkeypatch.setattr(build_sidecar, 'target_triple', lambda: triple)
    monkeypatch.setattr(build_sidecar.subprocess, 'run', run)
    assert build_sidecar.main() == 0
    command = run.call_args.args[0]
    assert any(command[i:i + 2] == ['--collect-all', 'curl_cffi'] for i in range(len(command)))
    assert (tmp_path / 'ui/src-tauri/binaries' / f'filingforge-api-{triple}{suffix}').read_bytes() == raw.read_bytes()
