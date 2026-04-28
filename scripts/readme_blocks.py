from pathlib import Path


def replace_block(readme_path: str, start_marker: str, end_marker: str, content: str) -> bool:
    """Replace a generated README block and return whether the file changed."""
    path = Path(readme_path)
    readme = path.read_text(encoding="utf-8")

    if start_marker not in readme or end_marker not in readme:
        raise ValueError(f"Missing README markers: {start_marker} / {end_marker}")

    start = readme.index(start_marker) + len(start_marker)
    end = readme.index(end_marker)
    replacement = f"\n{content.strip()}\n"
    updated = readme[:start] + replacement + readme[end:]

    if updated == readme:
        return False

    path.write_text(updated, encoding="utf-8")
    return True
