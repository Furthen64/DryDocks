# DryDocks
DryDocks is a portable standalone test app for local LLMs and their harnesses.

A self-contained test suite for validating OpenAI-compatible LLM API endpoints. DryDocks keeps configuration and generated artifacts inside the directory where you run it, so it can be copied between machines without leaving state behind elsewhere on the filesystem.

## Overview

DryDocks provides automated testing for LLM API compatibility across four levels of complexity:

1. **Pong Test** — Basic connectivity check
2. **JSON Test** — Structured output validation
3. **Tool Use Test** — Function calling capability
4. **Agent Flow Test** — Multi-turn conversations with tool usage

All tests target an OpenAI-compatible API endpoint (e.g., Ollama, LocalAI, vLLM).

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

4. Run all tests:

   ```bash
   ./runtests.sh
   ```
