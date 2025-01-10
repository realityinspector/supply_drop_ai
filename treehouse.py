#treehouse
import os
import json
from collections import defaultdict
from pathlib import Path
import importlib.util
import re

IGNORE_PATTERNS = [
    r'\.pyc$',
    r'\.pyo$',
    r'\.pyd$',
    r'__pycache__',
    r'\.git',
    r'\.env',
    r'\.venv',
    r'\.idea',
    r'\.vscode',
    r'node_modules',
    r'\.DS_Store',
    r'\.cache',
    r'\.config',
    r'\.pytest_cache',
    r'\.pythonlibs',
    r'\.upm',
    r'\.local',
    r'\backups',
    r'\.local',
]

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'}
RELEVANT_EXTENSIONS = {'.py', '.html', '.js', '.json', '.css', '.md'}


def count_files_by_type(directory):
    """Count files by extension in a directory."""
    counts = defaultdict(int)
    for root, _, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            counts[ext] += 1
    return counts


def should_ignore(path):
    """Check if path should be ignored based on patterns."""
    return any(re.search(pattern, str(path)) for pattern in IGNORE_PATTERNS)


def generate_tree(start_path, indent=''):
    """Generate a tree structure of the codebase."""
    tree_content = []
    start_path = Path(start_path)

    try:
        items = sorted(start_path.iterdir())
    except PermissionError:
        return []

    for item in items:
        if should_ignore(item):
            continue

        if item.is_file():
            ext = item.suffix.lower()
            if ext in RELEVANT_EXTENSIONS:
                tree_content.append(f"{indent}├── {item.name}")
        else:
            # For directories
            image_counts = count_files_by_type(item)
            image_files = sum(count for ext, count in image_counts.items()
                              if ext.lower() in IMAGE_EXTENSIONS)

            tree_content.append(f"{indent}├── {item.name}/")
            if image_files > 0:
                tree_content.append(
                    f"{indent}│   └── [{image_files} image files]")

            # Recursively process subdirectories
            subtree = generate_tree(item, indent + "│   ")
            if subtree:
                tree_content.extend(subtree)

    return tree_content


def extract_models_relationships():
    """Extract model relationships from Python files."""
    models_content = []
    models_content.append("\n## Database Models and Relationships\n")

    # This is a placeholder - in a real implementation, we would:
    # 1. Find all model files
    # 2. Parse them for SQLAlchemy model definitions
    # 3. Extract relationships and foreign keys
    # 4. Build a relationship graph

    models_content.append("```mermaid")
    models_content.append("erDiagram")
    models_content.append("    User ||--o{ Community : belongs_to")
    models_content.append("    Community ||--o{ Page : contains")
    models_content.append("    Community ||--o{ Event : hosts")
    models_content.append("    Event ||--o{ EventRegistration : has")
    models_content.append("    User ||--o{ EventRegistration : makes")
    models_content.append("    Page ||--o{ Revision : has")
    models_content.append("    Kit ||--o{ Page : deploys_to")
    models_content.append("```")

    return models_content


def extract_config_map():
    """Extract and map configuration settings."""
    config_content = []
    config_content.append("\n## Configuration Map\n")
    config_content.append("```yaml")

    # Add known config categories from README
    configs = {
        "Environment": ["FLASK_ENV", "SECRET_KEY", "DATABASE_URL"],
        "Auth0": [
            "AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET",
            "AUTH0_MGMT_API_CLIENT_ID", "AUTH0_MGMT_API_SECRET",
            "AUTH0_MGMT_API_AUDIENCE"
        ],
        "Stripe": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
        "Email": [
            "MAILGUN_API_KEY", "MAILGUN_DOMAIN", "MAILGUN_BASE_URL_TEST",
            "MAILGUN_BASE_URL_LIVE"
        ],
        "Social": ["DEFAULT_SOCIAL_TITLE", "DEFAULT_SOCIAL_DESCRIPTION"]
    }

    for category, settings in configs.items():
        config_content.append(f"{category}:")
        for setting in settings:
            config_content.append(f"  - {setting}")
        config_content.append("")

    config_content.append("```")
    return config_content


def get_pyproject_content():
    """Get or generate pyproject.toml content."""
    pyproject_content = []
    pyproject_content.append("\n## Project Configuration (pyproject.toml)\n")
    pyproject_content.append("```toml")

    # Add basic pyproject.toml content
    pyproject_content.extend([
        "[tool.poetry]", 'name = "all-one-thing"', 'version = "0.1.0"',
        'description = "Flask application managing multi-community content with test/live environments"',
        "", "[tool.poetry.dependencies]", "python = '^3.9'",
        "flask = '^2.0.0'", "sqlalchemy = '^1.4.0'", "alembic = '^1.7.0'",
        "python-dotenv = '^0.19.0'", "authlib = '^0.15.0'",
        "stripe = '^2.60.0'", "requests = '^2.26.0'", "",
        "[tool.poetry.dev-dependencies]", "pytest = '^6.2.0'",
        "black = '^21.5b2'", "flake8 = '^3.9.0'", "mypy = '^0.910'", "",
        "[build-system]", 'requires = ["poetry-core>=1.0.0"]',
        'build-backend = "poetry.core.masonry.api"'
    ])

    pyproject_content.append("```")
    return pyproject_content


def main():
    """Generate the complete tree.md file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Generate content sections
    tree_content = generate_tree(current_dir)
    models_content = extract_models_relationships()
    config_content = extract_config_map()
    pyproject_content = get_pyproject_content()

    # Combine all content
    full_content = [
        "# Project Structure and Documentation\n", "## Directory Tree\n",
        "```", *tree_content, "```", *models_content, *config_content,
        *pyproject_content
    ]

    # Write to tree.md
    with open('tree.md', 'w') as f:
        f.write('\n'.join(full_content))


if __name__ == "__main__":
    main()
