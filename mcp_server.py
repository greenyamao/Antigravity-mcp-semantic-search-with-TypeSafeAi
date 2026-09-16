"""TypeSafe Code Guard MCP Server.

Provides AI coding assistants with instant, calibrated semantic code navigation
and diff reflection capabilities powered by TypeSafe System One models.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

from typesafe_sdk import Choice, Noul, NoulCriteria, Score, TypeSafeClient

# Load environment variables from .env if present
script_dir = Path(__file__).resolve().parent
load_dotenv(script_dir / ".env")
load_dotenv()

mcp = MCPServer("typesafe-code-guard")

# Default excluded directories and file patterns
EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".agents",
    ".gemini",
    ".system_generated",
    ".next",
    ".nuxt",
    "coverage",
    ".idea",
    ".vscode",
    ".cache",
    "target",
}

DEFAULT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".html",
    ".css",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".sql",
    ".sh",
}


def _get_client() -> Tuple[Optional[TypeSafeClient], Optional[str]]:
    """Get an authenticated TypeSafeClient instance."""
    api_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        return (
            None,
            "Error: TYPESAFE_API_KEY is not configured. Please set the TYPESAFE_API_KEY environment variable or define it in .env.",
        )
    try:
        client = TypeSafeClient(api_key=api_key)
        return client, None
    except Exception as err:
        return None, f"Error initializing TypeSafeClient: {err}"


def _gather_files(
    root_dir: Path, allowed_extensions: Optional[List[str]] = None
) -> List[Tuple[str, str]]:
    """Scan the directory and return candidate (relative_path, preview_summary) pairs."""
    candidates = []
    ext_filter = (
        set(allowed_extensions) if allowed_extensions else DEFAULT_EXTENSIONS
    )

    for path in root_dir.rglob("*"):
        if not path.is_file():
            continue
        # Skip excluded directories
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in ext_filter:
            continue
        if path.name.endswith(".lock") or path.name.endswith("-lock.json"):
            continue

        try:
            rel_path = str(path.relative_to(root_dir)).replace("\\", "/")
            # Read first 30 lines as structural summary
            lines = []
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for _ in range(30):
                    line = f.readline()
                    if not line:
                        break
                    stripped = line.strip()
                    if stripped and not stripped.startswith(("//", "#", "/*")):
                        lines.append(stripped)
            summary = " ".join(lines[:8])[:160]
            candidates.append((rel_path, summary))
        except Exception:
            continue

    return candidates


@mcp.tool()
def typesafe_find_code(
    query: str,
    directory: str = ".",
    file_extensions: Optional[List[str]] = None,
) -> str:
    """Semantically pinpoint the exact file and lines implementing specific behavior or business logic.

    Unlike literal grep, this tool evaluates code by MEANING and BEHAVIOR rather than exact variable names.
    Formulate queries describing the intent (e.g. 'where is session invalidated on logout' or 'where are stripe webhooks verified') rather than single literal words.
    Uses two-stage TypeSafe System One judgments to return the target file and line numbers without context bloat.

    Args:
        query: Natural language description of the behavior or business logic (e.g. 'where is checkout session timeout handled').
        directory: Target directory to search in (defaults to current working directory).
        file_extensions: Optional list of file extensions to filter (e.g. ['.py', '.ts']).
    """
    client, error_msg = _get_client()
    if error_msg:
        return error_msg

    root_path = Path(directory).resolve()
    # If directory is default "." but process was launched from IDE install directory, fallback to script_dir
    if directory == "." and ("antigravity" in str(root_path).lower() or "appdata" in str(root_path).lower()):
        root_path = script_dir
    if not root_path.exists():
        return f"Error: Directory not found: {directory}"

    candidates = _gather_files(root_path, file_extensions)
    if not candidates:
        return f"No matching code files found in directory: {directory}"

    # If more than 25 files, prioritize by keyword relevance
    if len(candidates) > 25:
        query_words = set(re.findall(r"\w+", query.lower()))

        def score_candidate(item: Tuple[str, str]) -> int:
            rel_path, summary = item
            text = (rel_path + " " + summary).lower()
            return sum(1 for word in query_words if word in text)

        candidates = sorted(candidates, key=score_candidate, reverse=True)[:25]

    # Stage 1: Coarse file selection
    file_options = {
        f"F{i:02d}": f"{path}: {summary}"
        for i, (path, summary) in enumerate(candidates)
    }

    try:
        stage1_resp = client.system_one(
            state={"query": query, "candidate_files": file_options},
            questions={
                "best_file": Choice(
                    instructions=f"Which file is most likely to contain or implement the following logic: '{query}'?",
                    criteria={k: None for k in file_options},
                ),
                "has_answer": Noul(
                    instructions=f"Does any of the candidate files likely contain or relate to: '{query}'?",
                    criteria=NoulCriteria(
                        true="At least one candidate file addresses or relates to the query",
                        false="None of these candidate files contain relevant logic",
                    ),
                ),
            },
        )
    except Exception as err:
        return f"TypeSafe API error during file selection: {err}"

    best_file_key = stage1_resp.answers["best_file"].choice
    has_answer_prob = stage1_resp.answers["has_answer"].noul
    file_confidence = stage1_resp.answers["best_file"].confidence

    if has_answer_prob < 0.25 and file_confidence < 0.25:
        return f"No relevant file found for query: '{query}' (Relevance: {has_answer_prob:.2f})."

    # Resolve winning file
    file_idx = int(best_file_key[1:])
    winner_rel_path = candidates[file_idx][0]
    winner_abs_path = root_path / winner_rel_path

    try:
        with open(
            winner_abs_path, "r", encoding="utf-8", errors="ignore"
        ) as f:
            file_lines = f.readlines()
    except Exception as err:
        return f"Error reading target file {winner_rel_path}: {err}"

    if not file_lines:
        return f"Target file `{winner_rel_path}` is empty."

    # Stage 2: Line-level pinpointing inside the winning file
    max_lines = min(len(file_lines), 250)
    tagged_doc = "\n".join(
        f"L{i+1:03d}| {file_lines[i].rstrip()}" for i in range(max_lines)
    )

    try:
        stage2_resp = client.system_one(
            state=tagged_doc,
            questions={
                "where": Choice(
                    instructions=f"Which line of the document implements or contains: '{query}'?",
                    criteria={f"L{i+1:03d}": None for i in range(max_lines)},
                ),
                "line_exists": Noul(
                    instructions=f"Does any line directly implement or contain: '{query}'?",
                    criteria=NoulCriteria(
                        true="At least one line implements or directly relates to this logic",
                        false="The query is not implemented in this file",
                    ),
                ),
            },
        )
    except Exception as err:
        return f"Found file `{winner_rel_path}`, but failed during line pinpointing: {err}"

    best_line_key = stage2_resp.answers["where"].choice
    line_prob = stage2_resp.answers["line_exists"].noul
    line_confidence = stage2_resp.answers["where"].confidence

    target_line_num = int(best_line_key[1:])
    start_line = max(1, target_line_num - 5)
    end_line = min(len(file_lines), target_line_num + 10)

    snippet_lines = []
    for idx in range(start_line - 1, end_line):
        line_prefix = (
            "-> " if idx + 1 == target_line_num else "   "
        )
        snippet_lines.append(
            f"{line_prefix}{idx + 1:4d} | {file_lines[idx].rstrip()}"
        )
    snippet = "\n".join(snippet_lines)

    file_lang = (
        winner_abs_path.suffix.lstrip(".")
        if winner_abs_path.suffix
        else "plaintext"
    )

    return f"""### 🎯 TypeSafe Semantic Search Result
- **Target File**: `{winner_rel_path}`
- **Exact Line**: `{target_line_num}` (Range: `{start_line} - {end_line}`)
- **Confidence**: `{line_confidence:.2f}` (Document relevance: `{line_prob:.2f}`)

```{file_lang}
{snippet}
```

*Note: You can inspect lines {start_line} to {end_line} directly without reading the entire file.*"""


@mcp.tool()
def typesafe_audit_diff(
    task_description: str,
    git_diff: str = "",
) -> str:
    """Semantically evaluate a git diff against user task intent before applying or committing changes.

    Flags scope creep, state changes, broken public contracts, removed error guards, and leftover debug statements.

    Args:
        task_description: The prompt or goal requested by the user.
        git_diff: The git diff content. If omitted, automatically runs `git diff HEAD`.
    """
    client, error_msg = _get_client()
    if error_msg:
        return error_msg

    diff_text = git_diff.strip()
    if not diff_text:
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            diff_text = res.stdout.strip()
            if not diff_text:
                # Also check unstaged changes if HEAD diff is empty
                res_unstaged = subprocess.run(
                    ["git", "diff"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                diff_text = res_unstaged.stdout.strip()
        except Exception as err:
            return f"Error executing git diff: {err}"

    if not diff_text:
        return "No git changes detected in the working tree to audit."

    # Extract modified file paths from diff
    changed_files = re.findall(
        r"^diff --git a/(.*?) b/", diff_text, re.MULTILINE
    )
    if not changed_files:
        changed_files = ["(unspecified modified files)"]

    # Limit diff size to fit comfortably in state
    truncated_diff = diff_text[:14000]

    state = {
        "task_description": task_description,
        "changed_files": changed_files,
        "diff": truncated_diff,
    }

    try:
        resp = client.system_one(
            state=state,
            questions={
                "scope_alignment": Score(
                    instructions="Rate how well this diff aligns with the requested task without unnecessary modifications:",
                    criteria=[
                        "Minimal & focused: only requested modifications were made",
                        "Cascading changes: extra files/state touched to support the requested feature",
                        "Severe scope creep: unrelated refactors, deleted logic, or excessive changes",
                    ],
                ),
                "touches_state": Noul(
                    instructions="Does this diff modify global application state, stores, contexts, or database schemas?"
                ),
                "breaks_contracts": Noul(
                    instructions="Does this diff alter public function/component signatures, exported methods, or prop types?"
                ),
                "removes_defenses": Noul(
                    instructions="Does this diff remove error handling, try/catch blocks, null/undefined checks, or input validations?"
                ),
                "leftover_debug": Noul(
                    instructions="Does this diff contain leftover debugging code such as print statements, console.log calls, hardcoded test strings, or unhandled TODOs?"
                ),
            },
        )
    except Exception as err:
        return f"TypeSafe API error during diff audit: {err}"

    scope = resp.answers["scope_alignment"].score
    touches_state_prob = resp.answers["touches_state"].noul
    breaks_contracts_prob = resp.answers["breaks_contracts"].noul
    removes_defenses_prob = resp.answers["removes_defenses"].noul
    leftover_debug_prob = resp.answers["leftover_debug"].noul

    # Build actionable reflection insights
    insights = []

    if scope >= 1.5:
        insights.append(
            "⚠️ **High Scope Creep**: The diff appears to modify substantially more code than required by the task."
        )
    elif scope >= 0.8:
        insights.append(
            "ℹ️ **Cascading Changes**: Additional files or state were modified. Verify that these secondary changes are strictly required."
        )

    if touches_state_prob > 0.70:
        insights.append(
            f"ℹ️ **State Management Modified** ({touches_state_prob:.0%}): Global stores or state files were touched ({', '.join(changed_files)}). Verify if local state would suffice."
        )

    if removes_defenses_prob > 0.65:
        insights.append(
            f"⚠️ **Defensive Checks Removed** ({removes_defenses_prob:.0%}): Error handling or null checks appear to have been deleted. Verify that defensive guards remain intact."
        )

    if breaks_contracts_prob > 0.70:
        insights.append(
            f"⚠️ **Public Contracts Altered** ({breaks_contracts_prob:.0%}): Function signatures or component props were changed. Ensure callers are updated."
        )

    if leftover_debug_prob > 0.75:
        insights.append(
            f"🧹 **Debug Leftovers Detected** ({leftover_debug_prob:.0%}): Temporary print/console.log statements or mock data were detected in the diff."
        )

    if not insights:
        insights.append(
            "✅ **Clean Diff**: Modifications are surgical, focused, and free of leftover debugging artifacts."
        )

    insights_text = "\n".join(f"- {item}" for item in insights)

    return f"""### 🛡️ TypeSafe Diff Audit Report
**Task**: "{task_description}"  
**Modified Files**: {", ".join(f"`{f}`" for f in changed_files)}

#### 📊 Calibrated Metrics
- **Scope Alignment**: `{scope:.2f} / 2.0`
- **Touches State**: `{touches_state_prob:.2f}`
- **Removes Defenses**: `{removes_defenses_prob:.2f}`
- **Breaks Contracts**: `{breaks_contracts_prob:.2f}`
- **Leftover Debug**: `{leftover_debug_prob:.2f}`

#### 💡 Reflection Insights
{insights_text}"""


if __name__ == "__main__":
    mcp.run()
