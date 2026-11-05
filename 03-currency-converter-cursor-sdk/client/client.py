"""Cursor SDK agent that drives the sibling FastMCP currency-converter over MCP."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from cursor_sdk import (
    Agent,
    AgentOptions,
    CursorAgentError,
    LocalAgentOptions,
    StdioMcpServerConfig,
)

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
SERVER_SCRIPT = SERVER_DIR / "server.py"
LAB_DIR = Path(__file__).resolve().parent.parent

PROMPT = (
    "Convert 50 USD to MXN using the available MCP tools. "
    "Call the currency tools; do not invent exchange rates."
)


def _stdio_server_config() -> StdioMcpServerConfig:
    if not SERVER_SCRIPT.is_file():
        raise FileNotFoundError(f"Server script not found: {SERVER_SCRIPT}")

    uv = shutil.which("uv")
    if uv:
        return StdioMcpServerConfig(
            command=uv,
            args=[
                "run",
                "--directory",
                str(SERVER_DIR),
                "python",
                "server.py",
            ],
        )

    if sys.platform == "win32":
        python = SERVER_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        python = SERVER_DIR / ".venv" / "bin" / "python"

    if not python.is_file():
        raise RuntimeError(
            "Neither 'uv' nor the server virtualenv Python was found. "
            "Install uv or run 'uv sync' inside 03-currency-converter-cursor-sdk/server."
        )

    return StdioMcpServerConfig(
        command=str(python),
        args=[str(SERVER_SCRIPT)],
    )


def _print_tool_call(message) -> None:
    print(f"\n[tool_call] name={message.name} status={message.status}")
    if getattr(message, "args", None) is not None:
        print(f"  args={json.dumps(message.args, default=str)}")
    if getattr(message, "result", None) is not None:
        print(f"  result={json.dumps(message.result, default=str)}")


def main() -> None:
    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        print(
            "CURSOR_API_KEY is required. Create a key at "
            "https://cursor.com/dashboard/integrations and export it.",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp_server = _stdio_server_config()
    print(f"MCP stdio: {mcp_server.command} {' '.join(mcp_server.args or [])}")
    print(f"Prompt: {PROMPT}\n")

    try:
        with Agent.create(
            AgentOptions(
                api_key=api_key,
                model="composer-2.5",
                local=LocalAgentOptions(cwd=str(LAB_DIR)),
                mcp_servers={"currency": mcp_server},
            )
        ) as agent:
            print(f"agent_id={agent.agent_id}")
            run = agent.send(PROMPT)
            print(f"run_id={run.id}")

            for message in run.messages():
                if message.type == "assistant":
                    for block in message.message.content:
                        if getattr(block, "type", None) == "text":
                            print(block.text, end="", flush=True)
                elif message.type == "tool_call":
                    _print_tool_call(message)
                elif message.type == "status":
                    print(f"\n[status] {message.status}")

            result = run.wait()
            print(f"\n\n=== run status: {result.status} ===")
            if result.result:
                print(result.result)
            if result.status == "error":
                print("Run started but failed.", file=sys.stderr)
                sys.exit(2)
    except CursorAgentError as err:
        print(
            f"startup failed: {err.message}, retryable={err.is_retryable}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
