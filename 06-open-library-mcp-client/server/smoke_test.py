"""One-off smoke test: orchestrator -> Open Library MCP (no LLM)."""

from __future__ import annotations

import asyncio
import json

from server import find_books, list_open_library_tools


async def main() -> None:
    tools = await list_open_library_tools()
    print("=== list_open_library_tools ===")
    print(json.dumps(tools, indent=2, default=str))

    result = await find_books("clean code", limit=3)
    print("\n=== find_books('clean code') ===")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
