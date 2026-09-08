# Local RAG for Codex

English | [Chinese](README.md)

A local-first personal knowledge base with a web document manager and an MCP server for Codex. It supports PDF, DOCX, Markdown, source code, JSON, CSV/TSV, and plain text. Retrieval combines BAAI/bge-small-zh-v1.5 embeddings, BM25, category routing, and RRF.

> Only source code and test fixtures are published. Documents, databases, models, caches, logs, backups, and machine-specific Codex configuration are excluded by .gitignore.

## Architecture

    Upload -> local parsing/OCR -> SQLite and local vector index
                                       |
    Codex -> local_rag MCP -> hybrid search -> cited passages -> answer

The management UI listens only on 127.0.0.1:8765. Codex starts a separate MCP process over STDIO, so the web page does not need to remain open.

## Installation on Windows

Requirements:

- Windows 10 or 11
- Python 3.11 or later
- Git
- A local Codex desktop, CLI, or IDE client

Clone and prepare the project:

    git clone https://github.com/ffjkk/local-rag-for-codex.git
    cd local-rag-for-codex
    powershell -ExecutionPolicy Bypass -File .\prepare.ps1

The preparation script creates .venv, installs pinned dependencies, downloads the embedding model, and initializes an empty library. The model is downloaded once; normal search runs offline.

## Import documents

Double-click open-knowledge-base.cmd or run:

    powershell -ExecutionPolicy Bypass -File .\start-ui.ps1

Open http://127.0.0.1:8765, create categories, upload files or folders, wait for indexing, and preview the extracted text. Scanned PDF pages use local OCR.

Limits: 50 MB per file, 300 MB and 2,000 files per batch, 500 PDF pages, and two million extracted characters per document.

## Connect to Codex

OpenAI documents that Codex stores MCP configuration in ~/.codex/config.toml. Local Codex clients on the same host share this configuration. See the [official Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

Run:

    .\.venv\Scripts\python.exe .\install-global.py

The installer detects the project and CODEX_HOME paths, backs up existing Codex configuration, registers the local_rag STDIO server, and adds a global default-search policy. It refuses to overwrite an existing server with the same name.

Restart the local Codex client and open a new task. If Codex CLI is available, verify with:

    codex mcp get local_rag --json

Example checks:

    Check my local knowledge base status and report document and category counts.

    Explain the deployment process using my local documents and cite document names and line numbers.

The integration is working when Codex calls knowledge_search and returns document names, versions, and extracted-text line numbers.

## Retrieval behavior

- scope="auto" routes to relevant categories and also searches Uncategorized.
- scope="all" is used only when the user explicitly requests the entire library.
- Explicit opt-out skips local retrieval.
- Local sources, web sources, and inference are distinguished.
- Retrieved text is untrusted reference data, never executable instructions.
- Failures and irrelevant results are disclosed without invented support.

Registering MCP exposes the tools. The global AGENTS.md rule establishes default retrieval, subject to normal Codex instruction priority and administrator policy.

## Manual MCP configuration

Add this to %USERPROFILE%\.codex\config.toml and replace the paths:

    [mcp_servers.local_rag]
    command = "C:\\path\\to\\local-rag-for-codex\\.venv\\Scripts\\python.exe"
    args = ["-B", "C:\\path\\to\\local-rag-for-codex\\rag.py", "serve"]
    cwd = "C:\\path\\to\\local-rag-for-codex"
    startup_timeout_sec = 60
    tool_timeout_sec = 120

    [mcp_servers.local_rag.env]
    PYTHONUTF8 = "1"
    PYTHONDONTWRITEBYTECODE = "1"
    TEMP = "C:\\path\\to\\local-rag-for-codex\\tmp"
    TMP = "C:\\path\\to\\local-rag-for-codex\\tmp"
    HF_HOME = "C:\\path\\to\\local-rag-for-codex\\cache\\huggingface"
    HF_HUB_OFFLINE = "1"

Trusted projects may instead use project-scoped .codex/config.toml configuration.

## Privacy

Parsing, OCR, embeddings, indexing, and search run locally. When Codex calls knowledge_search, matching passages enter the Codex model context for answer generation, so local retrieval does not make answer generation fully offline. Do not store passwords, tokens, or private keys in the library.

## Features

- Nested categories and folder-preserving batch uploads.
- PDF OCR, DOCX body/table extraction, and broad text encoding support.
- Safe Markdown, JSON, CSV, and TSV previews.
- Automatic re-indexing after edits and conflict-safe version checks.
- Results with document, category, version, line numbers, passage, and preview URL.

## Commands

    # Web UI
    .\start-ui.ps1 -NoBrowser
    .\stop-ui.ps1
    .\restart-ui.ps1 -NoBrowser

    # Search
    .\.venv\Scripts\python.exe -B .\rag.py status
    .\.venv\Scripts\python.exe -B .\rag.py search "your question"
    .\.venv\Scripts\python.exe -B .\rag.py search "your question" --scope all

    # Tests
    .\.venv\Scripts\python.exe -B -m pytest .\tests --basetemp=.\tmp\pytest -o cache_dir=.\cache\pytest -q
    .\.venv\Scripts\python.exe -B .\verify.py

You can also use stop-knowledge-base.cmd and restart-knowledge-base.cmd.

## Troubleshooting

If Codex cannot see local_rag, inspect it with codex mcp get local_rag --json, restart the local client completely, and open a new task.

If the model is missing, reconnect to the internet and rerun prepare.ps1. Normal MCP startup sets HF_HUB_OFFLINE=1.

The web UI and MCP server are separate processes. If the page works but retrieval fails, run rag.py status and verify all paths in the MCP configuration.

Document edits do not require a Codex restart. Restart only after changing MCP code, configuration, or tool definitions.

## License

No open-source license has been selected. The code is publicly visible, but no permission to copy, modify, or redistribute it is automatically granted.
