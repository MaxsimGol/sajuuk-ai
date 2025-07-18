import argparse
from pathlib import Path
from typing import List, Set


def generate_tree(
    directory: Path,
    ignore_list: Set[str],
    prefix: str = "",
) -> List[str]:
    """
    Recursively generates a visual tree structure for a given directory.

    Args:
        directory: The root directory Path object to start scanning from.
        ignore_list: A set of file/folder names to ignore.
        prefix: The string prefix for the current level of the tree (for indentation).

    Returns:
        A list of strings, where each string is a line in the tree.
    """
    lines = []
    # Filter out ignored items and sort for consistent output
    try:
        items = sorted(
            [item for item in directory.iterdir() if item.name not in ignore_list]
        )
    except FileNotFoundError:
        return [f"Error: Directory not found at {directory}"]
    except PermissionError:
        return [f"Error: Permission denied for {directory}"]

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        line = f"{prefix}{connector}{item.name}"
        lines.append(line)

        if item.is_dir():
            # Prepare the prefix for the next level of recursion
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(generate_tree(item, ignore_list, prefix=new_prefix))

    return lines


def main():
    """
    Main function to parse arguments and generate the project structure markdown file.
    """
    parser = argparse.ArgumentParser(
        description="Generate a Markdown file representing the project's directory structure.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Example Usage:
--------------
# Generate structure of the current directory, save to project_structure.md
python generate_structure.py

# Generate structure of a specific subdirectory
python generate_structure.py --root ./core

# Save the output to a different file
python generate_structure.py --output my_core_structure.md --root ./core

# Add custom folders/files to ignore
python generate_structure.py --ignore .venv temp_folder another_file.log
""",
    )

    parser.add_argument(
        "--root",
        dest="root_dir",
        default=".",
        help="The root directory to scan. Defaults to the current directory.",
    )
    parser.add_argument(
        "--output",
        dest="output_file",
        default="project_structure.md",
        help="The name of the output Markdown file. Defaults to 'project_structure.md'.",
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        help="Additional file or folder names to ignore.",
    )

    args = parser.parse_args()

    # Default set of common folders and files to ignore
    default_ignore = {
        ".git",
        ".gitignore",
        ".vscode",
        "__pycache__",
        ".idea",
        ".pytest_cache",
        "venv",
        ".venv",
        "env",
        "node_modules",
        # You can add the script's own name and output to avoid listing them
        "generate_structure.py",
        args.output_file,
    }

    # Combine default ignore list with user-provided list
    ignore_set = default_ignore.union(set(args.ignore))

    root_path = Path(args.root_dir)

    print(f"Scanning directory: {root_path.resolve()}")
    print(f"Ignoring: {', '.join(sorted(list(ignore_set)))}")

    tree_lines = generate_tree(root_path, ignore_set)

    # Prepare the final content for the Markdown file
    markdown_content = [
        "### Project File Structure",
        "",
        "```",
        str(root_path),
    ]
    markdown_content.extend(tree_lines)
    markdown_content.append("```")

    output_path = Path(args.output_file)
    try:
        output_path.write_text("\n".join(markdown_content), encoding="utf-8")
        print(f"\nSuccessfully generated project structure at: {output_path.resolve()}")
    except Exception as e:
        print(f"\nError writing to file: {e}")


if __name__ == "__main__":
    main()
