# scrape_sc2_library.py

import os
import importlib.util
from pathlib import Path

# --- Configuration ---
# The name of the output Markdown file.
OUTPUT_FILE = "python_sc2_library_context.md"

# A list of the package names to find and scrape from the venv.
PACKAGES_TO_SCRAPE = ["sc2"]

# Directories to completely ignore during traversal.
EXCLUDE_DIRS = {"__pycache__"}

# Mapping of file extensions to Markdown language identifiers.
LANGUAGE_MAP = {".py": "python"}


def scrape_library_to_markdown():
    """
    Finds installed Python packages in the environment, reads their source code,
    and compiles it into a single Markdown file for LLM context.
    """
    output_path = Path(__file__).parent / OUTPUT_FILE

    with open(output_path, "w", encoding="utf-8") as md_file:
        md_file.write("# Python-SC2 Library Source Code Context\n\n")
        print(f"Generating library context file at: {output_path}")

        for package_name in PACKAGES_TO_SCRAPE:
            print(f"\nAttempting to find and scrape package: '{package_name}'...")

            try:
                # Use importlib to find the package specification.
                spec = importlib.util.find_spec(package_name)
                if spec is None or spec.origin is None:
                    print(f"  - Could not find package '{package_name}'. Skipping.")
                    continue

                # The package path is the directory containing its __init__.py file.
                package_path = Path(spec.origin).parent
                print(f"  - Found at: {package_path}")
                md_file.write(f"\n---\n## Package: `{package_name}`\n---\n\n")

            except ImportError:
                print(
                    f"  - Could not import package '{package_name}'. Is it installed in your venv?"
                )
                continue

            # Walk through the discovered package directory.
            for dirpath, dirnames, filenames in os.walk(package_path):
                dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

                for filename in sorted(filenames):
                    file_path = Path(dirpath) / filename

                    # We only care about Python files for this task.
                    if file_path.suffix not in LANGUAGE_MAP:
                        continue

                    content = ""
                    try:
                        content = file_path.read_text(encoding="utf-8").strip()
                    except (UnicodeDecodeError, IOError):
                        print(
                            f"  - Skipping unreadable file: {file_path.relative_to(package_path)}"
                        )
                        continue

                    if not content:
                        print(
                            f"  - Skipping empty file: {file_path.relative_to(package_path)}"
                        )
                        continue

                    relative_path = f"{package_name}/{file_path.relative_to(package_path).as_posix()}"
                    print(f"  - Processing: {relative_path}")

                    md_file.write(f"### File: `{relative_path}`\n\n")
                    md_file.write(f"```python\n")
                    md_file.write(content)
                    md_file.write(f"\n```\n\n")

    print(f"\nSuccessfully created '{OUTPUT_FILE}'.")
    print("This file contains the source code for the specified libraries.")


if __name__ == "__main__":
    scrape_library_to_markdown()
