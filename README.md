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

## Prerequisites

- Python 3.10 or higher
- A local LLM running with OpenAI-compatible API exposed
- `click` available in your Python environment

## Quick Start

### 1. Create an Isolated Environment

DryDocks is meant to run in-place from its own directory. Copy or clone it anywhere, create a virtual environment inside that directory, and install the one external dependency:

```bash
cd /path/to/DryDocks
python -m venv .venv
source .venv/bin/activate
python -m pip install click
```

At that point the suite is ready to run directly with `python app.py`.

### 2. Configure

From the DryDocks directory, run the setup wizard:

```bash
source .venv/bin/activate
python app.py setup
```

You'll be prompted for:
- **Endpoint URL** — e.g., `http://127.0.0.1:8080/v1/messages`
- **API Key** — e.g., `dummy` (for local testing)
- **Model name** — e.g., `qwen`
- **Timeout** — Request timeout in seconds (default: 120)
- **Max retries** — Number of retry attempts (default: 2)
- **Retry delay** — Delay between retries in seconds (default: 1)

Configuration is saved to `.drydocks/config.json` under your current working directory.

### 3. Run Tests

```bash
# Check configuration and connection
python app.py status

# Run all tests (5 iterations each)
python app.py run all --runs 5

# Run specific test
python app.py run pong --runs 10
python app.py run json --runs 10
python app.py run tool_use --runs 10
python app.py run agent_flow --runs 3

# Run with verbose output
python app.py run all --runs 5 --verbose
```

## Configuration File

Configuration is stored at: `.drydocks/config.json` in the directory where you run DryDocks.

Example:
```json
{
  "version": "1.0",
  "endpoint": "http://127.0.0.1:8080/v1/messages",
  "api_key": "dummy",
  "model": "qwen",
  "timeout_seconds": 120,
  "max_retries": 2,
  "retry_delay_seconds": 1
}
```

The file is automatically created by the setup wizard and reused on subsequent runs from that directory. Change any settings by running `python app.py setup` again.

## Standalone Layout

DryDocks keeps all of its state inside the directory where you run it. A typical working directory looks like this after configuration and a test run:

```text
DryDocks/
├── app.py
├── drydocks/
├── .venv/
├── .drydocks/
│   └── config.json
├── results/
│   └── drydocks_YYYYMMDD_HHMMSS.jsonl
└── agent_test_out/
```

Nothing is written to your home directory or global config locations.

## Test Details

### Test 1: Pong (`pong`)
**Complexity:** Beginner  
**What it tests:** Basic connectivity and simple text generation  
**Command:** `python app.py run pong --runs 10`

Sends a prompt asking the LLM to reply with "pong" and validates the exact response.

### Test 2: JSON (`json`)
**Complexity:** Intermediate  
**What it tests:** Structured output generation (JSON parsing)  
**Command:** `python app.py run json --runs 10`

Requests a specific JSON structure and validates all required fields are present and correct.

### Test 3: Tool Use (`tool_use`)
**Complexity:** Advanced  
**What it tests:** Function calling with fresh tool definitions per request  
**Command:** `python app.py run tool_use --runs 10`

Provides a dynamic `write_file` tool and verifies the LLM correctly invokes it with expected parameters.

### Test 4: Agent Flow (`agent_flow`)
**Complexity:** Expert  
**What it tests:** Multi-turn conversations with tool integration  
**Command:** `python app.py run agent_flow --runs 3`

Executes a complete agent workflow:
1. Simple greeting exchange
2. Tool invocation (write C++ file)
3. Tool result handling
4. Final response

Outputs are saved to `agent_test_out/` in the current working directory for inspection.

## Output

### Console Output

Tests produce human-readable output:

```
============================================================
Running tests: pong, json, tool_use, agent_flow
Runs per test: 5
============================================================

============================================================
SUMMARY
============================================================
Total:       20
Passed:      20
Failed:      0
Pass Rate:   100.0%
Duration:    8.45s

By Test:
  pong                     5/5 (100%)
  json                     5/5 (100%)
  tool_use                 5/5 (100%)
  agent_flow               5/5 (100%)
============================================================

Results saved to: results/drydocks_20260519_143025.jsonl
```

### JSONL Results

Detailed results are saved to `results/drydocks_YYYYMMDD_HHMMSS.jsonl` in the current working directory, with one JSON object per line. Each line contains:

```json
{
  "test_name": "pong",
  "run_index": 1,
  "passed": true,
  "duration_seconds": 0.234,
  "error_message": null,
  "metadata": {}
}
```

This format is ideal for CI/CD integration and analysis.

## Commands

```
python app.py setup    # Interactive configuration wizard
python app.py run      # Run tests (see usage below)
python app.py status   # Check config and connection
python app.py reset    # Delete configuration file
```

### `run` Command Options

```
python app.py run [TEST_NAME] [OPTIONS]

TEST_NAME: Test to run (default: all)
  - pong       Simple connectivity
  - json       JSON contract validation
  - tool_use   Tool invocation
  - agent_flow Multi-turn agent workflow
  - all        Run all tests

OPTIONS:
  --runs N      Number of iterations per test (default: 5)
  --verbose     Print detailed output
  --help        Show help
```

## Deployment & Portability

DryDocks is designed to be portable:

1. **Copy the directory** to any machine with Python 3.10+
2. **Create `.venv/` and install `click`** inside that directory
3. **Run `python app.py setup`** from that directory
4. **Run tests** with `python app.py run`

Each copied working directory keeps its own configuration at `.drydocks/config.json`, so the suite stays self-contained and does not write into your home directory.

## Troubleshooting

### "No configuration found"
Run `python app.py setup` to create `.drydocks/config.json` in your current working directory.

### "Connection refused"
- Verify your LLM is running and listening on the configured endpoint
- Check the endpoint URL in configuration (`python app.py status`)
- Ensure firewall/network allows access to the LLM port

### "Invalid JSON in response"
The LLM response is not valid JSON. Check:
- LLM model is correctly set
- LLM API implementation returns valid JSON
- Network isn't corrupting responses

### "Tool use not working"
Ensure your LLM supports function calling (tools parameter in OpenAI API).

### "Agent flow tests failing"
The multi-turn agent flow is complex. Verify:
- LLM can handle multi-turn conversations
- Tool definitions are parsed correctly
- Tool results are properly integrated

## Development

Project structure:
```
DryDocks/
├── app.py                # Standalone app entry point
└── drydocks/
  ├── __init__.py       # Package metadata
  ├── cli.py            # Click command definitions
  ├── config.py         # Configuration management
  ├── api.py            # HTTP client wrapper
  ├── runner.py         # Test discovery & execution
  ├── reporting.py      # Result formatting
  └── tests/
    ├── __init__.py
    ├── base.py       # BaseTest abstract class
    ├── test_01_pong.py
    ├── test_02_json.py
    ├── test_03_tool_use.py
    └── test_04_agent_flow.py
```

To add a new test:
1. Create `drydocks/tests/test_XX_name.py`
2. Inherit from `BaseTest`
3. Implement `run(client, config, run_index) -> TestResult`
4. Set `name` and `description` class attributes

## Requirements

- `click>=8.0` — CLI framework
- Python standard library modules handle HTTP, JSON, and filesystem operations

There is no required global installation or shared config location.

## License

DryDocks is provided as-is for testing LLM API compatibility.

## Support

For issues:
1. Check `python app.py status` for connection issues
2. Review JSONL logs in `results/` for detailed failure info
3. Verify LLM endpoint is accessible and returning valid JSON
