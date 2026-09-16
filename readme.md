# 🛡️ TypeSafe Code Guard: MCP Server for Antigravity IDE

A specialized **Model Context Protocol (MCP)** server for AI coding assistants in Antigravity IDE, Cursor, and Claude Code.

It replaces slow, token-heavy brute-force file scanning (`grep` across dozens of files) with **instant semantic code discovery** and adds **calibrated diff sanity checking** before committing, powered by **TypeSafe System One** models (`jev-latest`).

---

## 💡 Why This Exists & How It Works

### The Solo Developer Pain Point:
1. You ask an AI agent to locate a bug or modify existing business logic.
2. The agent runs `grep`, finds 40+ matches, and begins **reading entire files into context**.
3. A single discovery round dumps **25,000 to 40,000 tokens** into the conversation history.
4. **Context Rot sets in**: The bloated context window degrades the model's reasoning, causes hallucinations, makes it forget initial instructions, and burns your token limits within minutes.

### The TypeSafe Code Guard Solution:
All file scanning, ranking, and line-level selection occur **outside** the LLM's context window—within the local Python process and via TypeSafe's sub-second cloud API ($0.00004 per call).

Only the final, targeted answer enters the AI agent's memory:
* 🔍 **`typesafe_find_code`**: The agent describes *what the code does* (e.g. *"where are Stripe webhook signatures verified"*). TypeSafe evaluates semantic intent (even if variables use unexpected names or abstractions) and returns the exact file, line number, and a compact 15-line preview (**~150 tokens instead of 30,000**).
* 🛡️ **`typesafe_audit_diff`**: When the agent finishes editing, the diff is audited against the user's prompt: it catches deleted null checks, removed `try/catch` blocks, unexpected global state modifications, and leftover `console.log` statements.

---

## 🚀 Step-by-Step Setup Guide

### Step 1. Prerequisites
* **Python 3.10+** (verify with `python --version`).
* An API key from the **[TypeSafe Console](https://console.typesafe.ai/settings/keys)**.

---

### Step 2. Install Dependencies
Open a terminal in the folder containing this server and run:

```bash
pip install -r requirements.txt
```

*(Installs `typesafe-sdk`, `mcp`, and `python-dotenv`)*.

---

### Step 3. Configure Your API Key
Copy the template file to create your local `.env`:

```bash
# On Windows PowerShell:
cp .env.example .env
```

Open `.env` and paste your key:

```env
TYPESAFE_API_KEY=your_actual_typesafe_key_here
```

*(Note: `.env` is listed in `.gitignore` to prevent accidental commits).*

---

### Step 4. Register in Antigravity IDE

Open the global Antigravity MCP configuration file:
* **Windows Path:** `C:\Users\<YourUsername>\.gemini\config\mcp_config.json`
* **macOS / Linux:** `~/.gemini/config/mcp_config.json`

Add the server to the `"mcpServers"` object:

```json
{
  "mcpServers": {
    "typesafe-code-guard": {
      "command": "python",
      "args": [
        "C:/path/to/this/folder/mcp_server.py"
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

> **Important:** Replace `C:/path/to/this/folder/mcp_server.py` with the actual absolute path to `mcp_server.py` on your machine (use forward slashes `/`).  
> The `"alwaysAllow"` array ensures the agent can execute these tools **seamlessly without repetitive approval dialogs**.

---

### Step 5. Activate Rules for Your AI Agent

To ensure the agent in your project **knows** about these tools and uses them instead of literal `grep`, place an **`AGENTS.md`** file in the root of your project:

```markdown
# TypeSafe Code Guard Rules
- **Semantic Code Search**: Always call `typesafe_find_code` with a behavioral description (what the code *does*, not literal keywords) before grepping or reading multiple files.
- **Diff Sanity Check**: Call `typesafe_audit_diff` before finishing edits to verify scope alignment and catch removed defensive checks or leftover debug statements.
- For query formulation examples and metric thresholds, activate the `typesafe-code-guard` skill.
```

*(Optional: You can also copy the `.agents/skills/typesafe-code-guard/` folder into your project for on-demand query formulation guides).*

---

## 🧪 Verification & Testing

Ask the agent in your Antigravity chat:
> *"Where is the user authentication or token verification implemented in this project?"*

Instead of reading multiple files via grep, the agent will instantly invoke `typesafe_find_code` and output the exact file, lines, and code snippet in ~2 seconds.