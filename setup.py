from pathlib import Path
from setuptools import find_packages, setup


BASE_DIR = Path(__file__).parent
README_PATH = BASE_DIR / "README.md"
REQUIREMENTS_PATH = BASE_DIR / "requirements.txt"

long_description = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""
requirements = (
    [line.strip() for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if REQUIREMENTS_PATH.exists()
    else []
)


setup(
    name="quickplaybot",
    version="0.1.0",
    description="Telegram bot with PostgreSQL and Redis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Артём",
    author_email="-",
    python_requires=">=3.13",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
)
