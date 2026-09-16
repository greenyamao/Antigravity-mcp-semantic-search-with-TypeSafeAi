# TypeSafe Code Guard

A Model Context Protocol (MCP) server for AI coding assistants (Antigravity IDE, Cursor, Claude Code).

Replaces broad, token-heavy file scanning (`grep` sweeps across dozens of files) with **instant semantic code discovery** and provides **pre-commit diff sanity checking** powered by TypeSafe System One models (`jev-latest`).

---

## Overview

When AI coding assistants search codebases using literal keyword grep, they often ingest 25,000–40,000 tokens of irrelevant file contents into context. This causes **context rot**, degrades reasoning, and exhausts token limits.

**TypeSafe Code Guard** moves candidate search and ranking outside the LLM context:
- **Fast & Cheap**: Evaluates code semantics via sub-second cloud decisions (~$0.00004 per call).
- **Context Efficient**: Ingests only targeted 15-line snippets (~150 tokens vs. 30,000+).
- **Intent-Based**: Matches what code *does* (behavior, business rules) rather than guessing variable names.

---

## Tools

### 1. `typesafe_find_code`
Two-stage semantic locator:
1. **File Selection**: Scans the project tree and identifies the most relevant file via TypeSafe `Choice` and `Noul` evaluations without loading file contents into the LLM context.
2. **Line Pinpointing**: Ranks line blocks within the target file and returns a 15-line preview with exact line numbers and confidence scores.

### 2. `typesafe_audit_diff`
Semantic reflection mirror for git diffs:
- Evaluates task intent against actual code modifications.
- Flags unexpected global state mutations, removed defensive checks (`try/catch`, null guards), breaking contract changes, and leftover debug statements (`console.log`, `print`).

---

## Installation

### 1. Prerequisites
- Python 3.10+
- TypeSafe API key ([console.typesafe.ai](https://console.typesafe.ai/settings/keys))

### 2. Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Setup
```bash
cp .env.example .env
```
Set your key in `.env`:
```env
TYPESAFE_API_KEY=your_typesafe_api_key_here
```

### 4. Register in Antigravity IDE
Add the server to your global MCP configuration:
- **Windows**: `C:\Users\<Username>\.gemini\config\mcp_config.json`
- **macOS / Linux**: `~/.gemini/config/mcp_config.json`

```json
{
  "mcpServers": {
    "typesafe-code-guard": {
      "command": "python",
      "args": [
        "C:/path/to/repository/mcp_server.py"
      ],
      "env": {},
      "alwaysAllow": [
        "typesafe_find_code",
        "typesafe_audit_diff"
      ]
    }
  }
}
```
*Note: Use forward slashes (`/`) in file paths. The `alwaysAllow` array allows seamless execution without manual approval prompts.*

### 5. Install Skill & Rules (Global)
Install the bundled skill and rules globally so TypeSafe Code Guard automatically protects **all projects** opened in Antigravity IDE without copying files into every repository:

#### Windows (PowerShell)
```powershell
# Ensure target directories exist
New-Item -ItemType Directory -Force "$env:USERPROFILE\.gemini\config\skills", "$env:USERPROFILE\.gemini\config\rules" | Out-Null

# Install skill & rules
Copy-Item -Recurse .agents\skills\typesafe-code-guard $env:USERPROFILE\.gemini\config\skills\
Copy-Item AGENTS.md $env:USERPROFILE\.gemini\config\rules\typesafe.md
```

#### macOS / Linux
```bash
# Ensure target directories exist
mkdir -p ~/.gemini/config/skills ~/.gemini/config/rules

# Install skill & rules
cp -r .agents/skills/typesafe-code-guard ~/.gemini/config/skills/
cp AGENTS.md ~/.gemini/config/rules/typesafe.md
```

---

## Verification

Open **any project** in Antigravity IDE and prompt:
> "Where is the user authentication or token verification implemented in this project?"

The agent will invoke `typesafe_find_code` and return the exact file, lines, and snippet without reading full files into context.