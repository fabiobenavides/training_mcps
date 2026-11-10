# 06 — Open Library (MCP client inside the server)

Local MCP lab: a FastMCP **orchestrator** that is itself an **MCP client** of a sibling **Open Library** MCP. The LangChain agent only talks to the orchestrator; the orchestrator launches Open Library over stdio and forwards searches with `Client.call_tool`.

```text
LangChain client  --stdio-->  server/ (orchestrator)
                                   |
                                   | FastMCP Client (stdio)
                                   v
                              open_library/  --HTTP-->  openlibrary.org
```

```text
06-open-library-mcp-client/
  open_library/   # MCP wrapping Open Library Search API
  server/         # Orchestrator: Client -> open_library tools
  client/         # LangChain agent + MCPAdapter
```

Compared with earlier labs:

| Lab | Focus |
| --- | --- |
| 01 / 02 | Tools only |
| 03 | Cursor SDK agent |
| 04 | LangChain agent + tools |
| 05 | MCP **Resources** |
| **06** | MCP server that **calls another MCP** (`Client`) |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Network access to `https://openlibrary.org` (no API key)
- An LLM API key for whichever provider you set in `LAB_MODEL`

## Setup

```bash
cd 06-open-library-mcp-client/open_library
uv sync

cd ../server
uv sync

cd ../client
uv sync
```

### Recommended (free): Google Gemini

```powershell
cd 06-open-library-mcp-client\client
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

## Server surfaces

### `open_library/` (upstream MCP)

| Tool | Purpose |
| --- | --- |
| `search_books` | `GET https://openlibrary.org/search.json` |
| `search_authors` | `GET https://openlibrary.org/search/authors.json` |

### `server/` (orchestrator — what the LangChain client connects to)

| Tool | Purpose |
| --- | --- |
| `list_open_library_tools` | `tools/list` against the nested Open Library MCP |
| `find_books` | Calls Open Library MCP `search_books` via `Client` |
| `find_authors` | Calls Open Library MCP `search_authors` via `Client` |

The orchestrator does **not** call `openlibrary.org` directly. Each `find_*` tool starts the sibling MCP (stdio) and uses MCP `tools/call`.

## Run the LangChain client

```bash
cd 06-open-library-mcp-client/client
uv run python client.py
```

### If `uv` is not recognized (Windows)

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv run python .\client.py
```

The client will:

1. Launch `../server/server.py` over **stdio**.
2. Call `tools/list` on the orchestrator.
3. Ask the model to search for books about “clean code” using `find_books`.
4. When the orchestrator handles that tool call, it launches `../open_library/server.py` and forwards the search.
5. Print the agent transcript.

## Optional smoke test (no LLM)

After `open_library/` and `server/` are synced:

```powershell
cd 06-open-library-mcp-client\server
uv run python smoke_test.py
```

That lists tools on the nested Open Library MCP, then calls `find_books("clean code")` through it.

## Optional: Cursor IDE as another client

[`mcp.example.json`](mcp.example.json) registers both the orchestrator and the raw Open Library MCP in Cursor MCP settings.

## Notes

- Do not write to **stdout** in either MCP server process. MCP uses stdio as the wire protocol; use `logging` (stderr) instead.
- Nested stdio means two MCP processes: orchestrator + Open Library. Expect a bit more startup latency on the first tool call.
- Open Library is a public API; be polite with request volume (this lab uses small `limit` values).
- `langchain.mcp` is marked beta in LangChain ≥ 1.4; the API may evolve.
