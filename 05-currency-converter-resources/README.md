# 05 — Currency Converter (MCP Resources)

Local MCP lab: same FastMCP + LangChain setup as [04](../04-currency-converter-langchain), but exchange rates live in a **file** and are exposed as an **MCP resource** instead of a hardcoded Python dict.

```text
05-currency-converter-resources/
  server/
    data/rates.json   # source of truth for demo rates
    server.py         # tools + @mcp.resource("currency://rates")
  client/             # LangChain agent + resources/list + resources/read
```

Compared with earlier labs:

| Lab | Focus |
| --- | --- |
| 01 / 02 | Tools only (hardcoded rates) |
| 03 | Cursor SDK agent |
| 04 | LangChain agent + tools |
| **05** | Same as 04, plus **MCP Resources** backed by `data/rates.json` |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- An LLM API key for whichever provider you set in `LAB_MODEL`

## Setup

```bash
cd 05-currency-converter-resources/server
uv sync

cd ../client
uv sync
```

### Recommended (free): Google Gemini

```powershell
cd 05-currency-converter-resources\client
uv sync

$env:GOOGLE_API_KEY = "AIza..."
$env:LAB_MODEL = "google_genai:gemini-3.5-flash-lite"
```

### Alternative: OpenAI

```powershell
$env:OPENAI_API_KEY = "sk-..."
# optional; this is already the default
$env:LAB_MODEL = "openai:gpt-4.1-mini"
```

## Server surface

| Kind | Name / URI | Purpose |
| --- | --- | --- |
| **Resource** | `currency://rates` | Reads `server/data/rates.json` |
| Tool | `convert_currency` | Convert using rates from that file |
| Tool | `list_rates` | Same data as the resource, as a tool result |

Edit `server/data/rates.json` to add or change currencies; tools and the resource both pick it up (restart the server / client process after edits — rates are cached in-process).

## Run the LangChain client

```bash
cd 05-currency-converter-resources/client
uv run python client.py
```

### If `uv` is not recognized (Windows)

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv run python .\client.py
```

The client will:

1. Launch `../server/server.py` over **stdio**.
2. Call **`resources/list`** and **`resources/read`** on `currency://rates` and **parse** the JSON.
3. Call `tools/list` and build the LangChain agent.
4. Pass the resource payload into the user message, then ask to convert `50 USD -> MXN`.
5. Print the agent transcript.

## Tools vs resources

- **Resources** = read-only data the client fetches (`resources/list` / `resources/read`). This lab’s client **consumes** `currency://rates` and injects it into the agent prompt.
- **Tools** = actions the model can call (`convert_currency`). LangChain’s `MCPAdapter` exposes tools; resources are read via `adapter.client`.

## Optional: Cursor IDE as another client

[`mcp.example.json`](mcp.example.json) registers the same server in Cursor MCP settings. In Cursor you can inspect the `currency://rates` resource as well as the tools.

## Notes

- Rates in `data/rates.json` are for learning; they are **not** live market data.
- Do not write to **stdout** in the server process. MCP uses stdio as the wire protocol; use `logging` (stderr) instead.
- `langchain.mcp` is marked beta in LangChain ≥ 1.4; the API may evolve.
