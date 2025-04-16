# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands
- Install dependencies: `pip install -r requirements.txt`
- Run application: `python src/main.py <org_names>`
- Run scheduler: `python src/scheduler.py`
- Run tests: `pytest`
- Lint code: `flake8 src/`
- Format code: `black src/`
- Type check: `mypy src/`

## Code Style Guidelines
- Use Python 3.11+ features
- Format with black (line length: 88)
- Use type hints for all function parameters and return values
- Use async/await for I/O operations
- Handle exceptions with try/except blocks, log errors properly
- Imports order: stdlib, third-party, local modules
- Use f-strings for string formatting
- Follow PEP 8 naming conventions (snake_case for functions/variables)
- Log errors with appropriate level (info, warning, error)
- Use docstrings for classes and functions