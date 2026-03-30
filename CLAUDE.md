# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands
- Install dependencies: `pip install -r requirements.txt`
- Run application: `python src/main.py <org_names>`
- Run scheduler: `python src/scheduler.py <org_names>`
- Get achievements only: `python src/main.py --achievements-only <org_names>`
- Run tests: `pytest`
- Lint code: `flake8 src/`
- Format code: `black src/`
- Type check: `mypy src/`

## Environment Setup
Required environment variables:
- `GITHUB_TOKEN`: GitHub personal access token
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: JSON string of Firestore service account credentials
- `COLLECTION_INTERVAL`: daily, hourly, minutely, or weekly (default: daily)
- `COLLECTION_TIME`: time to run collection (default: 00:00)
- `GITHUB_IGNORED_USERS`: comma-separated list of GitHub usernames to ignore (default: gregv)

## Architecture Overview
This is a GitHub organization metrics collector with the following key components:

**Core Classes:**
- `GitHubClient`: Handles GitHub API interactions using aiohttp for async requests
- `FirestoreClient`: Manages Firestore database operations for data persistence
- `MetricsCollector`: Orchestrates data collection and coordinates between GitHub and Firestore
- `AchievementsGenerator`: Generates achievement data based on contributor statistics
- `Scheduler`: Handles periodic execution of metrics collection

**Data Flow:**
1. GitHub API → contributor stats, repository data, pull requests, commits
2. Firestore structure: organizations/{org}/repositories/{repo}/contributors/{user}
3. Achievements are generated from aggregated contributor data and stored separately

**Key Operations:**
- Organization processing: fetches all repos → all contributors → individual stats
- Achievement generation: aggregates data across repositories to create achievements
- Scheduled execution: runs collection at configurable intervals

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