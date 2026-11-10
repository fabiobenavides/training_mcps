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

PROMPT = (
    "Convert 50 USD to MXN using convert_currency. "
    "Use only the exchange rates from the MCP resource already loaded below. "
    "Do not invent rates and do not call list_rates."
)
DEFAULT_MODEL = "openai:gpt-4.1-mini"
# Hard ceiling so a stalled Gemini free-tier call fails instead of hanging forever.
INVOKE_TIMEOUT_SECONDS = 90.0
RATES_URI = "currency://rates"


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
            "Install uv or run 'uv sync' inside 05-currency-converter-resources/server."
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


def _resolve_model(model: str) -> Any:
    """Build a chat model, with timeouts for Gemini free-tier stalls."""
    if model.startswith("google_genai:"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model.split(":", 1)[1],
            timeout=60.0,
            max_retries=1,
        )
    return model


def _resource_text(item: Any) -> str | None:
    text = getattr(item, "text", None)
    if text is not None:
        return text
    content = getattr(item, "content", None)
    if isinstance(content, str):
        return content
    if content is not None:
        return json.dumps(content)
    return None


async def _load_rates_from_resource(adapter: MCPAdapter) -> dict[str, Any]:
    """Consume currency://rates via resources/list + resources/read."""
    client = adapter.client
    resources = await client.list_resources()
    print("\n=== resources/list ===")
    if not resources:
        raise RuntimeError("Server advertised no MCP resources")

    found = False
    for resource in resources:
        uri = str(getattr(resource, "uri", None) or resource)
        name = getattr(resource, "name", "") or ""
        description = getattr(resource, "description", "") or ""
        mime_type = getattr(resource, "mime_type", None) or getattr(
            resource, "mimeType", ""
        )
        print(f"- {uri} ({mime_type})")
        if name:
            print(f"  name: {name}")
        if description:
            print(f"  description: {description}")
        if uri == RATES_URI:
            found = True

    if not found:
        raise RuntimeError(f"Expected MCP resource {RATES_URI!r} was not listed")

    print(f"\n=== resources/read {RATES_URI} ===")
    result = await client.read_resource(RATES_URI)
    contents = getattr(result, "contents", result)
    texts = [text for item in contents if (text := _resource_text(item))]
    if not texts:
        raise RuntimeError(f"Empty content from MCP resource {RATES_URI!r}")

    payload = json.loads(texts[0])
    print(json.dumps(payload, indent=2))
    if not isinstance(payload.get("rates"), dict) or not payload["rates"]:
        raise RuntimeError(f"MCP resource {RATES_URI!r} has no rates")
    return payload


async def main() -> None:
    model = os.environ.get("LAB_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if model.startswith("openai:") and not os.environ.get("OPENAI_API_KEY", "").strip():
        print(
            "OPENAI_API_KEY is required for the default model "
            f"({DEFAULT_MODEL}). Export it, or set LAB_MODEL to another provider.",
            file=sys.stderr,
        )
        sys.exit(1)
    if model.startswith("google_genai:") and not (
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
    ):
        print(
            "GOOGLE_API_KEY (or GEMINI_API_KEY) is required for Gemini models. "
            "Create a key at https://aistudio.google.com/apikey",
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
        # Lab point: rates come from the MCP resource, not from guessing / list_rates.
        rates_payload = await _load_rates_from_resource(adapter)
        rates_json = json.dumps(rates_payload, indent=2)

        tools = await adapter.list_tools()
        print("\n=== tools/list ===")
        for tool in tools:
            name = getattr(tool, "name", None) or str(tool)
            description = getattr(tool, "description", "") or ""
            print(f"- {name}: {description}")

        # Gemini ignores JSON Schema `additionalProperties`; harmless noise.
        warnings.filterwarnings(
            "ignore",
            message=r"Key 'additionalProperties' is not supported in schema.*",
        )

        agent = create_agent(
            _resolve_model(model),
            tools,
            system_prompt=(
                "You are a helpful assistant for currency conversion. "
                f"The client already loaded MCP resource {RATES_URI}; treat that "
                "JSON as the only source of exchange rates. "
                "Call convert_currency to perform the conversion. "
                "Never invent exchange rates."
            ),
        )

        user_message = (
            f"{PROMPT}\n\n"
            f"MCP resource {RATES_URI} contents:\n"
            f"```json\n{rates_json}\n```"
        )

        print(
            f"\nCalling model (timeout {INVOKE_TIMEOUT_SECONDS:.0f}s). "
            "A long pause here is waiting on the LLM API, not MCP."
        )
        try:
            result = await asyncio.wait_for(
                agent.ainvoke(
                    {"messages": [{"role": "user", "content": user_message}]}
                ),
                timeout=INVOKE_TIMEOUT_SECONDS,
            )
        except TimeoutError as err:
            print(
                f"Model call failed (local timeout {INVOKE_TIMEOUT_SECONDS:.0f}s): {err}",
                file=sys.stderr,
            )
            print(
                "Hint: free-tier Gemini is often slow or overloaded. "
                "Retry later, or set LAB_MODEL to another Flash model "
                '(e.g. "google_genai:gemini-3.5-flash-lite").',
                file=sys.stderr,
            )
            sys.exit(3)
        except Exception as err:
            # Keep the lab output readable: one-line detail, no LangGraph stack.
            print(f"Model call failed: {err}", file=sys.stderr)
            err_text = str(err).lower()
            if any(
                token in err_text
                for token in (
                    "503",
                    "504",
                    "unavailable",
                    "deadline_exceeded",
                    "high demand",
                    "resource_exhausted",
                    "429",
                )
            ):
                print(
                    "Hint: provider capacity/quota issue (not an MCP bug). "
                    "Retry later or switch LAB_MODEL.",
                    file=sys.stderr,
                )
            sys.exit(3)

    messages = result.get("messages", []) if isinstance(result, dict) else []
    print("\n=== agent transcript ===")
    for message in messages:
        _print_message(message)


if __name__ == "__main__":
    asyncio.run(main())
