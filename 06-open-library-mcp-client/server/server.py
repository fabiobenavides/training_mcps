"""FastMCP orchestrator: tools that call the sibling Open Library MCP via Client.

Teaching point for lab 06: an MCP server can itself be an MCP *client*.
This process speaks MCP to the LangChain client over stdio, and speaks MCP
again to launch `../open_library/server.py` as a nested stdio subprocess.
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("book-finder-orchestrator")

OPEN_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "open_library"
OPEN_LIBRARY_SCRIPT = OPEN_LIBRARY_DIR / "server.py"


def _open_library_launch() -> dict[str, Any]:
    """Build an mcpServers config that starts the Open Library MCP over stdio."""
    if not OPEN_LIBRARY_SCRIPT.is_file():
        raise FileNotFoundError(f"Open Library MCP not found: {OPEN_LIBRARY_SCRIPT}")

    uv = shutil.which("uv")
    if uv:
        return {
            "mcpServers": {
                "open_library": {
                    "command": uv,
                    "args": [
                        "run",
                        "--directory",
                        str(OPEN_LIBRARY_DIR),
                        "python",
                        "server.py",
                    ],
                }
            }
        }

    if sys.platform == "win32":
        python = OPEN_LIBRARY_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        python = OPEN_LIBRARY_DIR / ".venv" / "bin" / "python"

    if not python.is_file():
        raise RuntimeError(
            "Neither 'uv' nor the open_library virtualenv Python was found. "
            "Install uv or run 'uv sync' inside 06-open-library-mcp-client/open_library."
        )

    return {
        "mcpServers": {
            "open_library": {
                "command": str(python),
                "args": [str(OPEN_LIBRARY_SCRIPT)],
            }
        }
    }


def _result_payload(result: Any) -> Any:
    """Prefer structured .data; fall back to text content blocks."""
    data = getattr(result, "data", None)
    if data is not None:
        return data

    content = getattr(result, "content", None) or []
    texts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            texts.append(text)
    if len(texts) == 1:
        return texts[0]
    if texts:
        return texts
    return None


async def _call_open_library(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Connect to the Open Library MCP and call one of its tools."""
    config = _open_library_launch()
    command = config["mcpServers"]["open_library"]["command"]
    args = config["mcpServers"]["open_library"]["args"]
    logger.info(
        "Calling Open Library MCP tool=%s via: %s %s",
        tool_name,
        command,
        " ".join(args),
    )

    async with Client(config) as client:
        result = await client.call_tool(tool_name, arguments)
        return _result_payload(result)


@mcp.tool()
async def list_open_library_tools() -> dict:
    """List tools advertised by the nested Open Library MCP (discovery hop).

    Useful to see that this orchestrator is a real MCP client of another server.
    """
    config = _open_library_launch()
    async with Client(config) as client:
        tools = await client.list_tools()
        listed = [
            {
                "name": getattr(tool, "name", str(tool)),
                "description": getattr(tool, "description", "") or "",
            }
            for tool in tools
        ]
    return {
        "upstream": "open_library",
        "tools": listed,
        "note": "These tools live on the sibling Open Library MCP, not on this server.",
    }


@mcp.tool()
async def find_books(query: str, limit: int = 5) -> dict:
    """Find books by calling the Open Library MCP's search_books tool.

    This orchestrator does not talk to openlibrary.org itself. It launches the
    sibling MCP over stdio and forwards the search through MCP tools/call.
    """
    cleaned = query.strip()
    if not cleaned:
        raise ToolError("query must not be empty")
    if limit < 1:
        raise ToolError("limit must be at least 1")

    try:
        payload = await _call_open_library(
            "search_books",
            {"query": cleaned, "limit": min(limit, 20)},
        )
    except Exception as exc:
        raise ToolError(f"Open Library MCP call failed: {exc}") from exc

    return {
        "via": "open_library MCP (search_books)",
        "result": payload,
    }


@mcp.tool()
async def find_authors(name: str, limit: int = 5) -> dict:
    """Find authors by calling the Open Library MCP's search_authors tool."""
    cleaned = name.strip()
    if not cleaned:
        raise ToolError("name must not be empty")
    if limit < 1:
        raise ToolError("limit must be at least 1")

    try:
        payload = await _call_open_library(
            "search_authors",
            {"name": cleaned, "limit": min(limit, 20)},
        )
    except Exception as exc:
        raise ToolError(f"Open Library MCP call failed: {exc}") from exc

    return {
        "via": "open_library MCP (search_authors)",
        "result": payload,
    }


if __name__ == "__main__":
    mcp.run()
