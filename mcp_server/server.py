"""FilingForge MCP server — a thin adapter over `tools.py`.

Everything real lives in `tools.py` (pure, tested, SDK-free). This module only
registers those functions as MCP tools and starts a transport, so the MCP SDK
stays an optional dependency:

    pip install "filingforge-engine[mcp]"
    filingforge-mcp --root ~/FilingForge

Point any MCP client at it and the model can browse the library, read clean
Markdown, and pull new filings from BSE.

The library root is fixed at startup, not passed per call — a model should not
be able to redirect reads or writes to an arbitrary directory.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from engine.bse_client import BSEClient
from engine.models import CURATED_BY_KEY
from mcp_server import tools

INSTRUCTIONS = """\
A local library of official Indian company filings from BSE, already converted
to clean Markdown.

Start with list_companies to see what is held. Use search_filings to locate a
document, then read_filing on the path it returns — that gives you the clean
Markdown, never the PDF. get_index returns the human-written index.

pull_company downloads a company that is not held yet; it will not guess
between similarly-named companies, so expect to pick from candidates. Annual
reports go back to 1997 where BSE has them.
"""


def build_server(root: Path, *, client_factory=BSEClient) -> MCPServer:
    root = Path(root).expanduser()
    server = MCPServer(
        name="filingforge",
        title="FilingForge — Indian company filings",
        instructions=INSTRUCTIONS,
    )

    @server.tool(description="List every company held in the local library, with filing counts.")
    def list_companies() -> list[dict]:
        return tools.list_companies(root)

    @server.tool(description="Read INDEX.md for one company, or the master index if ticker is omitted.")
    def get_index(ticker: str | None = None) -> str:
        return tools.get_index(root, ticker)

    @server.tool(
        description=(
            "Find filings by text in their title. Narrow with ticker, category "
            "or year. An empty query returns everything in scope, so the filters "
            "alone work as a browser. Returns paths for read_filing."
        )
    )
    def search_filings(query: str = "", ticker: str | None = None,
                       category: str | None = None, year: str | None = None,
                       limit: int = 50) -> list[dict]:
        return tools.search_filings(root, query, ticker=ticker, category=category,
                                    year=year, limit=limit)

    @server.tool(description="Read a filing as clean Markdown. Takes a path from search_filings.")
    def read_filing(path: str) -> str:
        return tools.read_filing(root, path)

    @server.tool(
        description=(
            "Download a company's filings from BSE into the library. Returns "
            "status 'ambiguous' with candidates when the name matches more than "
            f"one company — pick one and pass its scrip code with a ticker. "
            f"Categories: {sorted(CURATED_BY_KEY)}."
        )
    )
    def pull_company(name: str, years: int = 5, categories: list[str] | None = None,
                     ticker: str | None = None) -> dict:
        client = client_factory()
        try:
            return tools.pull_company(name, root, years=years, client=client,
                                      categories=categories, ticker=ticker)
        finally:
            client.close()

    @server.tool(description="Re-pull a company already held, keeping the categories it was built with.")
    def refresh_company(ticker: str, years: int | None = None) -> dict:
        client = client_factory()
        try:
            return tools.refresh_company(root, ticker, client=client, years=years)
        finally:
            client.close()

    return server


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="filingforge-mcp", description=__doc__)
    parser.add_argument("--root", default="~/FilingForge",
                        help="library root (default: ~/FilingForge)")
    parser.add_argument("--transport", default="stdio",
                        choices=["stdio", "sse", "streamable-http"])
    args = parser.parse_args(argv)
    build_server(Path(args.root)).run(transport=args.transport)


if __name__ == "__main__":
    main()
