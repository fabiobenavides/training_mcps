"""LangChain agent that drives the sibling FastMCP currency-converter over MCP."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import warnings
from pathlib import Path
from typing import Any

from langchain_core._api import LangChainBetaWarning

# langchain.mcp is beta; keep the lab output readable.
warnings.filterwarnings("ignore", category=LangChainBetaWarning)

from langchain.agents import create_agent
from langchain.mcp import MCPAdapter

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
SERVER_SCRIPT = SERVER_DIR / "server.py"

PROMPT = "Convert 50 USD to MXN using the available tools. Do not invent exchange rates."
DEFAULT_MODEL = "openai:gpt-4.1-mini"


def _server_launch() -> tuple[str, list[str]]:
    if not SERVER_SCRIPT.is_file():
        raise FileNotFoundError(f"Server script not found: {SERVER_SCRIPT}")

    uv = shutil.which("uv")
    if uv:
        return uv, [
            "run",
            "--directory",
            str(SERVER_DIR),
            "python",
            "server.py",
        ]

    if sys.platform == "win32":
        python = SERVER_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        python = SERVER_DIR / ".venv" / "bin" / "python"

    if not python.is_file():
        raise RuntimeError(
            "Neither 'uv' nor the server virtualenv Python was found. "
            "Install uv or run 'uv sync' inside 04-currency-converter-langchain/server."
        )

    return str(python), [str(SERVER_SCRIPT)]


def _mcp_config() -> dict[str, Any]:
    command, args = _server_launch()
    return {
        "mcpServers": {
            "currency": {
                "command": command,
                "args": args,
            }
        }
    }


def _content_to_str(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                parts.append(text if text is not None else json.dumps(block, default=str))
            else:
                text = getattr(block, "text", None)
                parts.append(text if text is not None else str(block))
        return "\n".join(parts)
    return str(content)


def _print_message(message: Any) -> None:
    msg_type = getattr(message, "type", message.__class__.__name__)
    print(f"\n=== {msg_type} ===")

    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        print("tool_calls:")
        print(json.dumps(tool_calls, indent=2, default=str))

    name = getattr(message, "name", None)
    if name:
        print(f"name: {name}")

    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id:
        print(f"tool_call_id: {tool_call_id}")

    text = _content_to_str(getattr(message, "content", None))
    if text:
        print(text)


async def main() -> None:
    model = os.environ.get("LAB_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if model.startswith("openai:") and not os.environ.get("OPENAI_API_KEY", "").strip():
        print(
            "OPENAI_API_KEY is required for the default model "
            f"({DEFAULT_MODEL}). Export it, or set LAB_MODEL to another provider.",
            file=sys.stderr,
        )
        sys.exit(1)

    config = _mcp_config()
    command = config["mcpServers"]["currency"]["command"]
    args = config["mcpServers"]["currency"]["args"]
    print(f"MCP stdio: {command} {' '.join(args)}")
    print(f"Model: {model}")
    print(f"Prompt: {PROMPT}")

    async with MCPAdapter(config) as adapter:
        tools = await adapter.list_tools()
        print("\n=== tools/list ===")
        for tool in tools:
            name = getattr(tool, "name", None) or str(tool)
            description = getattr(tool, "description", "") or ""
            print(f"- {name}: {description}")

        agent = create_agent(
            model,
            tools,
            system_prompt=(
                "You are a helpful assistant. Use the currency MCP tools for "
                "any conversion or rate question. Never invent exchange rates."
            ),
        )

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": PROMPT}]}
        )

    messages = result.get("messages", []) if isinstance(result, dict) else []
    print("\n=== agent transcript ===")
    for message in messages:
        _print_message(message)


if __name__ == "__main__":
    asyncio.run(main())
