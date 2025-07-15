# create_context.py

import os
from pathlib import Path

# --- Configuration (remains the same) ---
ROOT_DIR = Path(__file__).parent
OUTPUT_FILE = "sajuuk_ai_context.md"
EXCLUDE_DIRS = {"__pycache__", ".venv", ".git", ".idea", ".vscode", "tests"}
EXCLUDE_FILES = {
    "create_context.py",
    "run_tests.py",
    "README.md",
    "requirements.txt",
    ".gitignore",
    "# scrape_sc2_library.py",
    "# scrape_sc2_library.py",
    OUTPUT_FILE,
}
LANGUAGE_MAP = {".py": "python", ".md": "markdown", ".txt": "text", ".json": "json"}


def create_project_markdown():
    """
    Traverses the project directory, reads the content of each NON-EMPTY file,
    and compiles it into a single, large Markdown file formatted for an LLM.
    """
    output_path = ROOT_DIR / OUTPUT_FILE

    with open(output_path, "w", encoding="utf-8") as md_file:
        md_file.write("# Sajuuk AI Project Context\n\n")
        print(f"Generating project context file at: {output_path}")

        for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

            for filename in sorted(filenames):
                if filename in EXCLUDE_FILES:
                    continue

                file_path = Path(dirpath) / filename
                relative_path = file_path.relative_to(ROOT_DIR)

                content = ""
                try:
                    content = file_path.read_text(encoding="utf-8").strip()
                except (UnicodeDecodeError, IOError):
                    # Skip binary files or files that can't be read
                    print(f"Skipping unreadable file: {relative_path}")
                    continue

                # --- THIS IS THE KEY CHANGE ---
                # If the content (after stripping whitespace) is empty, skip the file.
                if not content:
                    print(f"Skipping empty file: {relative_path}")
                    continue

                print(f"Processing: {relative_path}")
                language = LANGUAGE_MAP.get(file_path.suffix, "")

                md_file.write(f"---\n\n")
                md_file.write(
                    f"### File: `{str(relative_path).replace(os.sep, '/')}`\n\n"
                )
                md_file.write(f"```{language}\n")
                md_file.write(content)  # Write the stripped content
                md_file.write(f"\n```\n\n")

    print(f"\nSuccessfully created '{OUTPUT_FILE}'.")
    print(
        "This file contains the entire project structure and can be used as context for an LLM."
    )


if __name__ == "__main__":
    create_project_markdown()
