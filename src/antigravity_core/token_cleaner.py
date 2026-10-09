"""
Token Cleaner & Context Optimization Engine for Git Operations.
Reduces token bloat for Bolt, Jules, Antigravity, and Gemini LLM interactions
by stripping noisy cache files, trimming git diffs, and pruning redundant context.
"""

import os
import re
import subprocess
from typing import List, Tuple, Dict, Any, Optional

# File patterns that blow up agent token budgets and MUST be ignored
IGNORE_TOKEN_GLOBS = [
    r"^local_py/",
    r".*discovery_cache.*\.json$",
    r"^\.venv/",
    r"^node_modules/",
    r"^dist/",
    r"^build/",
    r"^\.git/",
    r".*\.pyc$",
    r".*\.pyo$",
    r".*\.so$",
    r".*\.lock$",
    r"package-lock\.json$",
    r"^\.cache/",
    r"^exports/",
    r".*\.log$",
    r"^\.antigravity-ide/crashes/",
]

_IGNORE_REGEX = re.compile("|".join(f"(?:{p})" for p in IGNORE_TOKEN_GLOBS), re.IGNORECASE)


def estimate_tokens(text: str) -> int:
    """Accurately estimates token count (approx. 3.8 chars per token for code/text)."""
    if not text:
        return 0
    return max(1, int(len(text) / 3.8))


class TokenCleaner:
    """
    Cleans and reduces token consumption for git operations,
    agent prompts, and context windows.
    """

    @staticmethod
    def is_token_waste(path: str) -> bool:
        """Checks if a path is considered token waste / context bloat."""
        clean_path = path.replace("\\", "/").strip()
        return bool(_IGNORE_REGEX.search(clean_path))

    @staticmethod
    def clean_file_paths(paths: List[str]) -> Tuple[List[str], int]:
        """
        Filters a list of file paths to remove token-heavy garbage.
        Returns (filtered_paths, paths_excluded_count).
        """
        filtered = [p for p in paths if not TokenCleaner.is_token_waste(p)]
        return filtered, len(paths) - len(filtered)

    @staticmethod
    def clean_git_diff(raw_diff: str, max_hunk_lines: int = 50) -> Tuple[str, int]:
        """
        Compresses and cleans a git diff:
        - Drops noisy lockfiles or binary changes
        - Keeps modified lines and essential hunk headers
        - Trims huge hunks to prevent context overflow
        Returns (cleaned_diff, tokens_saved).
        """
        if not raw_diff:
            return "", 0

        original_tokens = estimate_tokens(raw_diff)
        lines = raw_diff.splitlines()
        cleaned_lines = []
        skip_current_file = False
        current_hunk_lines = 0

        for line in lines:
            if line.startswith("diff --git"):
                current_hunk_lines = 0
                parts = line.split(" ")
                target_file = parts[-1].lstrip("b/") if len(parts) > 3 else ""
                if TokenCleaner.is_token_waste(target_file):
                    skip_current_file = True
                    cleaned_lines.append(f"# [Bolt/Jules Token Cleaner: skipped {target_file}]")
                    continue
                else:
                    skip_current_file = False

            if skip_current_file:
                continue

            if line.startswith("@@"):
                current_hunk_lines = 0
                cleaned_lines.append(line)
                continue

            # Limit giant hunks of unchanged code
            if line.startswith(" "):
                # Unchanged context line
                current_hunk_lines += 1
                if current_hunk_lines > max_hunk_lines:
                    continue
            else:
                current_hunk_lines = 0

            cleaned_lines.append(line)

        cleaned_diff = "\n".join(cleaned_lines)
        cleaned_tokens = estimate_tokens(cleaned_diff)
        tokens_saved = max(0, original_tokens - cleaned_tokens)
        return cleaned_diff, tokens_saved

    @staticmethod
    def clean_prompt_context(content: str, max_chars: int = 12000) -> Tuple[str, int]:
        """
        Compresses prompt context by stripping repeated blank lines,
        redundant logs, and truncating to max_chars.
        Returns (cleaned_content, tokens_saved).
        """
        if not content:
            return "", 0

        orig_tokens = estimate_tokens(content)
        # Collapse multiple blank lines
        cleaned = re.sub(r"\n{3,}", "\n\n", content)
        # Collapse repetitive whitespace
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "\n... [Context pruned by TokenCleaner for token reduction]"

        cleaned_tokens = estimate_tokens(cleaned)
        tokens_saved = max(0, orig_tokens - cleaned_tokens)
        return cleaned, tokens_saved

    @staticmethod
    def inspect_staged_git(repo_root: Optional[str] = None) -> Dict[str, Any]:
        """
        Inspects currently staged git files and reports token efficiency.
        """
        cwd = repo_root or os.getcwd()
        try:
            res = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            staged_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
        except Exception:
            staged_files = []

        valid_files, excluded = TokenCleaner.clean_file_paths(staged_files)
        waste_files = [f for f in staged_files if TokenCleaner.is_token_waste(f)]

        return {
            "staged_count": len(staged_files),
            "valid_files": valid_files,
            "waste_files": waste_files,
            "has_token_waste": len(waste_files) > 0,
            "recommendation": "Clean staged waste files" if waste_files else "Git staged files are token-clean"
        }


# Global helper instance
token_cleaner = TokenCleaner()


if __name__ == "__main__":
    # Test diff cleaning
    dummy_diff = (
        "diff --git a/local_py/some_file.json b/local_py/some_file.json\n"
        "+ {\"huge_key\": \"value\"}\n"
        "diff --git a/src/main.py b/src/main.py\n"
        "@@ -1,3 +1,4 @@\n"
        " def main():\n"
        "+    print('Optimized')\n"
        "     return True\n"
    )
    cleaned, saved = TokenCleaner.clean_git_diff(dummy_diff)
    print("Cleaned Diff:\n", cleaned)
    print(f"Tokens Saved: {saved}")
    print("Staged status:", TokenCleaner.inspect_staged_git())
