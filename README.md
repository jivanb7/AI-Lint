# AI-Lint

**Static analysis for LLM-powered Python code.** Catches AI-specific anti-patterns before they ship.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## What is this?

Modern AI coding agents -- Claude Code, Codex, Cursor, Copilot, Grok -- are remarkably good at writing correct code. They handle syntax, logic, and even many best practices out of the box. **AI-Lint is not trying to replace that.**

But LLMs have a blind spot: they don't flag their own AI-specific anti-patterns. An LLM will happily generate a `chat.completions.create()` call without `max_tokens`, miss a `try/except` around an API call that can throw five different exception types, or hardcode `model="gpt-4o"` in a dozen places. These aren't _bugs_ -- the code runs fine -- but they're the kind of issues that bite you in production.

**AI-Lint is a safety net, not a replacement.** Think of it the way spell check relates to proofreading: spell check doesn't make you a better writer, but it catches the typos you skim right past. AI-Lint catches the LLM-specific patterns that even good AI agents overlook.

Here's what makes it different:

- **No AI involved.** Zero. It's pure static analysis -- Python AST parsing and pattern matching. Same approach as ruff or pylint, just specialized for LLM code.
- **Runs in seconds.** No API calls, no model inference, no waiting. It parses your files locally.
- **Costs nothing.** No API keys, no subscriptions, no telemetry. Works completely offline.
- **12 purpose-built rules** targeting the exact patterns that show up in AI-generated code.

## Quick Start

```bash
# Install
pip install ailint

# Run on your project
ailint check src/

# See all available rules
ailint list-rules
```

Example output:

```
src/chatbot.py

  L12  CRITICAL  AIL001  User input (user_message) flows into LLM call without sanitization
                         > response = client.chat.completions.create(messages=[{"content": f"Help with: {user_message}"}])
                         Fix: Sanitize user input before passing to LLM: validate length, strip special characters

  L12  WARNING   AIL002  LLM call is missing max_tokens parameter
                         Fix: Add max_tokens=1024 (or appropriate limit) to control costs

  L12  ERROR     AIL006  LLM call is not inside a try/except block
                         Fix: Wrap in try/except to handle API errors (RateLimitError, APIError, Timeout, etc.)

  L3   CRITICAL  AIL005  String matches known API key pattern
                         > api_key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901"
                         Fix: Use environment variables: os.getenv("API_KEY") or a secrets manager

src/chatbot.py: 4 findings (2 critical, 1 error, 1 warning)

Checked 1 file | 4 findings | 2 critical 1 error 1 warning
```

## What It Catches

AI-Lint ships with 12 rules targeting real patterns in LLM-generated Python code:

| Rule | Name | Severity | Description |
|------|------|----------|-------------|
| AIL001 | PromptInjection | CRITICAL | User input flows unsanitized into LLM prompts |
| AIL002 | UnboundedTokenUsage | WARNING | LLM calls missing max_tokens parameter |
| AIL003 | HardcodedModelName | WARNING | Model names hardcoded instead of configurable |
| AIL004 | MissingRetryLogic | WARNING | LLM calls without retry/backoff handling |
| AIL005 | ExposedAPIKey | CRITICAL | API keys hardcoded in source code |
| AIL006 | MissingErrorHandling | ERROR | LLM calls not wrapped in try/except |
| AIL007 | NoInputValidation | WARNING | User input passed to LLM without validation |
| AIL008 | RAGAntiPattern | WARNING | Vector store calls missing limits or filtering |
| AIL009 | MissingTimeout | WARNING | HTTP/LLM calls missing timeout parameter |
| AIL010 | SyncCallInAsyncContext | ERROR | Synchronous blocking calls in async functions |
| AIL011 | TemperatureNotSet | INFO | LLM calls missing explicit temperature |
| AIL012 | NoStreamingForLongResponse | WARNING | Large max_tokens without streaming enabled |

### Example: Prompt Injection (AIL001)

```python
# Bad -- user_input goes straight into the prompt
def summarize(user_input):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize this: {user_input}"}],
    )

# Good -- sanitize first
def summarize(user_input):
    user_input = user_input[:5000]
    user_input = html.escape(user_input)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize this: {user_input}"}],
    )
```

**For detailed examples of all 12 rules with bad/good code patterns, see the [Rules Reference](docs/RULES.md).**

## Configuration

AI-Lint works with zero configuration. When you need to customize, it reads from `pyproject.toml`, `.ailint.yaml`, or CLI flags (in that priority order).

### pyproject.toml

```toml
[tool.ailint]
select = ["AIL001", "AIL005", "AIL006"]  # Only run these rules (empty = all)
ignore = ["AIL011"]                       # Skip these rules
exclude = [".venv", "tests/", "migrations/"]
severity = "WARNING"                      # Minimum severity: INFO, WARNING, ERROR, CRITICAL
format = "terminal"                       # Output: terminal, json, sarif
```

### .ailint.yaml

Generate a starter config:

```bash
ailint init
```

This creates `.ailint.yaml` with sensible defaults:

```yaml
select: []
ignore: []
exclude:
  - .venv
  - node_modules
  - __pycache__
severity: INFO
format: terminal
```

### Inline Ignores

Suppress specific rules on individual lines:

```python
# Ignore a specific rule
response = client.chat.completions.create(model="gpt-4o")  # ailint: ignore[AIL003]

# Ignore all rules on this line
response = client.chat.completions.create(prompt=user_input)  # ailint: ignore
```

## CI/CD Integration

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/jivanb7/AI-Lint
    rev: v0.1.0
    hooks:
      - id: ailint
```

### GitHub Actions

Upload results to GitHub Code Scanning for inline PR annotations:

```yaml
# .github/workflows/ailint.yml
name: AI-Lint
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ailint
      - run: ailint check src/ --format sarif > results.sarif
      - uses: github/codeql-action/upload-sarif@v4
        if: always()
        with:
          sarif_file: results.sarif
```

### GitLab CI

```yaml
# .gitlab-ci.yml
ailint:
  image: python:3.11-slim
  stage: lint
  script:
    - pip install ailint
    - ailint check src/ --severity WARNING
  allow_failure: false
```

## CLI Reference

```
ailint check [PATHS...] [OPTIONS]
```

Run analysis on the specified files or directories. Defaults to the current directory.

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to config file (pyproject.toml or .ailint.yaml) |
| `--select RULES` | Comma-separated rule IDs to enable (e.g., `AIL001,AIL005`) |
| `--ignore RULES` | Comma-separated rule IDs to skip |
| `--severity LEVEL` | Minimum severity: `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `--format FORMAT` | Output format: `terminal`, `json`, `sarif` |

```
ailint list-rules [--format table|json]
```

Display all registered rules with their IDs, severity, and descriptions.

```
ailint init
```

Create a default `.ailint.yaml` configuration file in the current directory.

```
ailint --version
```

Print the installed version.

## How It Works

AI-Lint is pure static analysis. There are no AI models, no API calls, no magic.

1. **Parse**: Each Python file is parsed into an Abstract Syntax Tree using Python's built-in `ast` module.
2. **Annotate**: The AST is walked to attach parent references, enabling rules to inspect context (e.g., "is this call inside a `try/except`?").
3. **Match**: Each of the 12 rules walks the AST looking for specific patterns -- function calls matching known LLM SDK signatures, string constants matching API key formats, sync calls inside `async def` blocks, etc.
4. **Report**: Findings are collected, deduplicated, and formatted for your chosen output (terminal, JSON, or SARIF).

The entire process is deterministic. Same input, same output, every time.

## FAQ

**"Doesn't my LLM already catch these?"**
Mostly, yes. LLMs are great at writing correct code. But they have a consistent blind spot: they don't flag the anti-patterns they just created. An LLM will tell you to add error handling if you _ask_ -- but it won't add it unprompted when generating a quick function. AI-Lint catches those gaps automatically, every time, on every file.

**"Do I need an API key?"**
No. AI-Lint makes zero network requests. It runs entirely on your machine using Python's standard library AST parser. No API keys, no accounts, no internet connection required.

**"What Python versions are supported?"**
Python 3.10 and above.

**"What LLM SDKs does it recognize?"**
OpenAI, Anthropic, LangChain, LlamaIndex, and common HTTP libraries (requests, httpx, aiohttp). The pattern matching covers the most widely used call signatures.

**"Can I add custom rules?"**
Not yet through configuration, but the rule system is designed for extensibility. Each rule is a self-contained class that inherits from `BaseRule` and implements a `check()` method. Contributing new rules is straightforward.

**"How is this different from ruff or pylint?"**
Ruff and pylint are general-purpose Python linters. They catch syntax issues, style violations, and common bugs. AI-Lint is specialized -- it only looks at LLM/AI-specific patterns that general linters don't know about. They're complementary. Run both.

## Contributing

Contributions are welcome. The codebase is designed to make adding new rules simple:

1. Create a new file in `src/ailint/rules/` following the existing pattern
2. Inherit from `BaseRule` and implement the `check()` method
3. Decorate your class with `@registry.register`
4. Add tests in `tests/`

```bash
# Set up development
git clone https://github.com/jivanb7/AI-Lint.git
cd AI-Lint
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
