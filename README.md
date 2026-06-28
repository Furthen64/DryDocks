# DryDocks
DryDocks is a portable standalone test app for local LLMs and their harnesses.

A self-contained test suite for validating OpenAI-compatible LLM API endpoints. DryDocks keeps configuration and generated artifacts inside the directory where you run it, so it can be copied between machines without leaving state behind elsewhere on the filesystem.

## Overview

DryDocks provides automated testing for LLM API compatibility across four levels of complexity:

1. **Pong Test** — Basic connectivity check
2. **JSON Test** — Structured output validation
3. **Tool Use Test** — Function calling capability
4. **Agent Flow Test** — Multi-turn conversations with tool usage

All tests target an OpenAI-compatible API endpoint. The default setup flow assumes a local `llama.cpp` server at `http://localhost:8080/v1`, but Ollama, LocalAI, vLLM, and similar endpoints also work.

## Quick Start

1. Create a Python 3.12 virtual environment:

   ```bash
   uv venv .venv --python 3.12
   ```

2. Activate it:

   ```bash
   source .venv/bin/activate
   ```

3. Run setup to create `drydocks.json` in your current working directory:

   ```bash
   ./setup.sh
   ```

   Press enter at the base URL prompt to use the `llama.cpp` default: `http://localhost:8080/v1`.
   The script will probe `/models`, show friendly model names, and let you select by number or exact model id for `drydocks.json`.

4. Run all tests:

   ```bash
   ./runtests.sh
   ```

   DryDocks also writes a plain-text report for each run under `reports/`, with the latest copy at `reports/latest-report.txt`.
