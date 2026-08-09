"""The MCP adapter: right tools registered, root pinned, clients closed.

The behaviour itself is covered in test_tools.py / test_pull.py. What matters
here is that the adapter wires it up correctly and does not widen the surface.
"""
import asyncio

import pytest

pytest.importorskip("mcp.server.mcpserver", reason="MCP SDK is an optional extra (separate env: pip install '.[mcp]')")

from mcp_server.server import build_server  # noqa: E402


class _FakeClient:
    """Records that the adapter closes what it opens."""
    opened = 0
    closed = 0

    def __init__(self):
        type(self).opened += 1

    def close(self):
        type(self).closed += 1


@pytest.fixture(autouse=True)
def _reset_client():
    _FakeClient.opened = _FakeClient.closed = 0


def _tool_names(server):
    return {t.name for t in asyncio.run(server.list_tools())}


def test_registers_the_read_and_pull_tools(tmp_path):
    server = build_server(tmp_path, client_factory=_FakeClient)
    assert _tool_names(server) == {
        "list_companies", "get_index", "search_filings",
        "read_filing", "pull_company", "refresh_company",
    }


def test_the_server_is_named_and_carries_instructions(tmp_path):
    server = build_server(tmp_path, client_factory=_FakeClient)
    assert server.name == "filingforge"
    assert "clean Markdown" in (server.instructions or "")


def test_building_a_server_opens_no_network_client(tmp_path):
    build_server(tmp_path, client_factory=_FakeClient)
    assert _FakeClient.opened == 0
