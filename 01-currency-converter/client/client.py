"""stdio MCP client that launches the sibling currency-converter server."""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
SERVER_SCRIPT = SERVER_DIR / "server.py"


def _server_params() -> StdioServerParameters:
    if not SERVER_SCRIPT.is_file():
        raise FileNotFoundError(f"Server script not found: {SERVER_SCRIPT}")

    uv = shutil.which("uv")
    if uv:
        return StdioServerParameters(
            command=uv,
            args=[
                "run",
                "--directory",
                str(SERVER_DIR),
                "python",
                "server.py",
            ],
        )

    # Fallback when uv is not on PATH: use the server's venv Python if present.
    if sys.platform == "win32":
        python = SERVER_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        python = SERVER_DIR / ".venv" / "bin" / "python"

    if not python.is_file():
        raise RuntimeError(
            "Neither 'uv' nor the server virtualenv Python was found. "
            "Install uv or run 'uv sync' inside 01-currency-converter/server."
        )

    return StdioServerParameters(
        command=str(python),
        args=[str(SERVER_SCRIPT)],
    )


def _print_result(label: str, result) -> None:
    print(f"\n=== {label} ===")
    if result.is_error:
        print("ERROR")
    if getattr(result, "structured_content", None) is not None:
        print(json.dumps(result.structured_content, indent=2))
        return
    for block in result.content:
        text = getattr(block, "text", None)
        print(text if text is not None else block)


async def main() -> None:
    params = _server_params()
    print(f"Launching server: {params.command} {' '.join(params.args)}")

    async with Client(params) as client:
        tools = await client.list_tools()
        print("\n=== tools/list ===")
        for tool in tools.tools:
            print(f"- {tool.name}: {tool.description}")

        rates = await client.call_tool("list_rates", {})
        _print_result("list_rates", rates)

        conversion = await client.call_tool(
            "convert_currency",
            {
                "amount": 50,
                "from_currency": "USD",
                "to_currency": "MXN",
            },
        )
        _print_result("convert_currency 50 USD -> MXN", conversion)

        invalid = await client.call_tool(
            "convert_currency",
            {
                "amount": 10,
                "from_currency": "USD",
                "to_currency": "BTC",
            },
        )
        _print_result("convert_currency invalid currency", invalid)


if __name__ == "__main__":
    asyncio.run(main())
