# GitHub Stats Collector

## Overview

GitHub Stats Collector is a Python application designed to gather and analyze statistics from multiple GitHub repositories within specified organizations. It collects data on pull requests, commits, issues, comments, and other relevant metrics, storing this information in a Firestore database for further analysis.

## Features

- Batch processing of multiple GitHub repositories
- Asynchronous data collection for improved performance
- Scheduled runs for periodic data updates
- Firestore integration for data storage
- Deployment-ready for fly.io

## Prerequisites

- Python 3.11
- Conda (for environment management)
- A GitHub account with a personal access token
- A Google Cloud account with Firestore enabled
- fly.io account (for deployment)

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/your-username/github-stats-collector.git
   cd github-stats-collector
   ```

2. Create and activate a Conda environment:
   ```
   conda create -n github-stats-collector python=3.11
   conda activate github-stats-collector
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   Create a `.env` file in the root directory with the following content:
   ```
   GITHUB_TOKEN=your_github_personal_access_token
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/firestore/credentials.json
   GITHUB_ORGS=org1,org2,org3
   ```

## Usage

To run the application locally:

```
python src/main.py
```

For scheduled runs, use the provided scheduler:

```
python src/scheduler.py
```

## Testing

Run the test suite using pytest:

```
pytest
```

## Deployment

This application is configured for deployment on fly.io. To deploy:

1. Install the fly.io CLI
2. Authenticate with fly.io
3. Deploy the application:
   ```
   fly deploy
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.