# 04 — Currency Converter (LangChain + MCP)

Local MCP lab: the same FastMCP **currency-converter** server as [02](../02-currency-converter-fastmcp) / [03](../03-currency-converter-cursor-sdk), driven by a **LangChain** agent (`MCPAdapter` + `create_agent`).

Here **LangChain** owns the tool loop. The model is a normal chat LLM (default OpenAI), so swapping providers is mostly a model-string / dependency change — unlike lab 03, where Cursor SDK is a full agent runtime, not a drop-in LangChain chat model.

```text
04-currency-converter-langchain/
  server/     # FastMCP server (tools)
  client/     # LangChain MCPAdapter + create_agent
```

Compared with earlier labs:

| Lab | Who calls tools | LLM layer |
| --- | --- | --- |
| 01 / 02 | Scripted MCP client | none |
| 03 | Cursor agent | Cursor SDK (`composer-2.5`) |
| **04** | LangChain agent | Interchangeable (`LAB_MODEL`) |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- `OPENAI_API_KEY` for the default model (`openai:gpt-4.1-mini`)

## Setup

```bash
cd 04-currency-converter-langchain/server
uv sync

cd ../client
uv sync
```

Export your key (PowerShell):

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

Optional model override:

```powershell
$env:LAB_MODEL = "openai:gpt-4.1-mini"
```

## Server tools

| Tool | Purpose |
| --- | --- |
| `convert_currency` | Convert `amount` from `from_currency` to `to_currency` |
| `list_rates` | List supported currencies and rates vs USD |

Supported currencies: `USD`, `EUR`, `MXN`, `COP`.

## Run the LangChain client

```bash
cd 04-currency-converter-langchain/client
uv run python client.py
```

### If `uv` is not recognized (Windows)

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv run python .\client.py
```

The client will:

1. Launch `../server/server.py` over **stdio** via `MCPAdapter` (`mcpServers` config).
2. Print discovered tools.
3. Build `create_agent(model, tools, ...)`.
4. Ask to convert `50 USD -> MXN`.
5. Print the agent transcript (including tool calls / tool results when present).

## Changing the LLM later

This lab uses the current LangChain MCP API (`langchain.mcp.MCPAdapter`), **not** the legacy `langchain-mcp-adapters` / `MultiServerMCPClient` package.

Default model string: `openai:gpt-4.1-mini` (requires `langchain-openai` + `OPENAI_API_KEY`).

To try another provider later:

1. Add the provider package (e.g. `langchain-anthropic`).
2. Set `LAB_MODEL` to that provider’s model id (e.g. `anthropic:claude-sonnet-4-5`).
3. Export that provider’s API key.

Cursor SDK is **not** a LangChain chat model — keep Cursor integrations in lab 03.

## Optional: Cursor IDE as another client

[`mcp.example.json`](mcp.example.json) shows how to register the same server in Cursor MCP settings. This lab’s primary client is the LangChain script above.

## Notes

- Rates are hardcoded for learning; they are **not** live market data.
- Do not write to **stdout** in the server process. MCP uses stdio as the wire protocol; use `logging` (stderr) instead.
- `langchain.mcp` is marked beta in LangChain ≥ 1.4; the API may evolve.
