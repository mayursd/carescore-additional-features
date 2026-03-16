# CareScore AI

![Logo](src/ui/assets/logo.png)

CareScore AI is a Streamlit application designed to evaluate medical students' performance in clinical encounters. It uses AI models to analyze case files and encounter notes, providing a comprehensive evaluation of the student's performance.

## Features

*   **AI-Powered Evaluation:** Utilizes large language models to grade student performance against predefined criteria.
*   **Multi-Modal File Support:** Accepts a wide range of file formats, including `.txt`, `.docx`, `.pdf`, `.m4a`, `.mp3`, and `.mp4`.
*   **Daily.co Integration:** Fetch and process video recordings of clinical encounters directly from Daily.co.
*   **SOAP Note Generation:** Automatically generates SOAP notes from interview transcripts.
*   **AI-Powered SOAP Suggestions:** Provides AI-generated suggestions for improving SOAP notes.
*   **Checklist Evaluation:** Evaluates student performance against a checklist of questions and answers.
*   **PDF Report Generation:** Generates detailed PDF reports of the evaluation results.
*   **Modular Architecture:** The codebase is organized into distinct modules for easy maintenance and extension.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.8+
*   pip
*   Docker (optional, for containerized deployment)
*   `make` (optional, for simplified command execution)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd carescore
    ```

2.  **Install the dependencies:**

    ```bash
    make install
    ```
    (Alternatively: `pip install -r requirements.txt`)

3.  **Set up your environment variables:**

    Create a `.env` file in the root of the project and add your API keys and authentication credentials. You can use the `.env.example` file as a template.

    ```
    CARESCORE_USERNAME=your_username
    CARESCORE_PASSWORD=your_password
    GEMINI_AI_KEY=your_gemini_ai_key
    DAILY_API_KEY=your_daily_api_key
    ```
    **Note:** `CARESCORE_USERNAME` and `CARESCORE_PASSWORD` are required for basic authentication to access the application.

## Usage

To run the application locally, use the following command:

```bash
make start
```
(Alternatively: `streamlit run src/app.py`)

This will start the Streamlit server and open the application in your web browser.

## Project Structure

```
/workspaces/carescore/
├───.gitignore
├───.env.example
├───Dockerfile
├───Makefile
├───pytest.ini
├───requirements.txt
├───tests/
│   ├───conftest.py
│   ├───integration/
│   │   └───test_soap_workflow.py
│   └───unit/
│       ├───test_services.py
│       └───test_utils.py
└───src/
    ├───app.py
    ├───config/
    │   ├───carescore_ai_models.json
    │   └───prompts.py
    ├───static/
    │   └───main.html
    ├───templates/
    │   └───SOAP_Note_Template.docx
    ├───services/
    │   ├───daily_service.py
    │   ├───llm_service.py
    │   └───soap_service.py
    ├───ui/
    │   ├───assets/
    │   │   └───logo.png
    │   └───pages.py
    └───utils/
        ├───audio_video_utils.py
        ├───file_utils.py
        └───pdf_generator.py
```

*   **`src/app.py`**: The main entry point for the Streamlit application.
*   **`src/config/`**: Contains configuration files, such as prompts and AI model definitions.
*   **`src/services/`**: Contains modules for interacting with external services, such as the Daily.co API and LLMs.
*   **`src/ui/`**: Contains the user interface components of the application, built with Streamlit.
*   **`src/utils/`**: Contains utility functions for tasks such as file processing and PDF generation.
*   **`tests/`**: Contains unit and integration tests for the application.
*   **`Dockerfile`**: Defines the Docker image for containerized deployment.
*   **`Makefile`**: Provides a set of commands to automate common development tasks.
*   **`pytest.ini`**: Configuration file for `pytest`.

## Testing

This project includes unit and integration tests using `pytest`.

To run all tests:

```bash
make test
```
(Alternatively: `pytest`)

### Test Structure

*   **`tests/conftest.py`**: Contains fixtures for mocking Streamlit functions and external API calls, ensuring tests run in isolation and without hitting live services.
*   **`tests/unit/`**: Contains unit tests for individual functions and classes within `src/services/` and `src/utils/`.
*   **`tests/integration/`**: Contains integration tests that verify the interaction between different modules, such as the SOAP note generation workflow.

## Dockerization

The application can be containerized using Docker for consistent deployment across different environments.

### Build the Docker image

```bash
make build-docker
```
(Alternatively: `docker build -t carescore-ai .`)

### Run the Docker container

```bash
make run-docker
```

**Important:** When running the Docker container, you must provide your API keys as environment variables. For example:

```bash
GEMINI_AI_KEY="your_gemini_key" \
DAILY_API_KEY="your_daily_key" \
make run-docker
```

Your application will then be accessible at `http://localhost:8501`.

## Audio Recording

The application includes an integrated audio recorder that uses Daily.co for cloud recording functionality. The recorder is embedded directly in the Streamlit interface and securely receives the Daily.co API key as a parameter.

### Features

- **Embedded Recording**: Audio recorder is embedded as an iframe within the Streamlit application
- **Secure API Key Handling**: Daily.co API key is passed securely from the backend environment variables
- **Cloud Recording**: Recordings are stored in Daily.co's cloud infrastructure
- **Real-time Status**: Live status updates during recording sessions

### Usage

1. Navigate to the "Record Audio" section in the application
2. The recorder will automatically initialize with your Daily.co API key
3. Click "Start Recording" to begin capturing audio
4. Click "Stop Recording" when finished
5. Recording ID will be displayed for reference

### Configuration

Ensure your `.env` file includes:
```
DAILY_API_KEY=your_daily_api_key
```

The recorder will automatically use this API key when initializing the Daily.co room.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is proprietary to Leap of Faith Technologies. All rights reserved. See the [LICENSE.md](LICENSE.md) file for details.

## Environment-specific configuration (Streamlit)

We ship two Streamlit config files to keep local DX fast while making production stable:

- `.streamlit/config.toml` (default/dev)
    - `fileWatcherType = "auto"`
    - `runOnSave = true`
- `.streamlit/config.prod.toml` (production overrides)
    - `fileWatcherType = "none"` (disables event-based watcher to avoid Cloud crashes)
    - `runOnSave = false`

Use in production (Streamlit Cloud): set the environment variable

```
STREAMLIT_SETTINGS_PATH=.streamlit/config.prod.toml
```

Additionally, a placeholder directory `src/pages/.gitkeep` is included so the
pages watcher has a concrete path. If you add multi-page apps, place your 
scripts under `src/pages/`.

## Retention cleanup script

We include a standalone utility to purge old Daily.co recordings safely.

- Location: `scripts/cleanup_recordings.py`
- Default behavior: dry-run, 7-day retention.

Examples (PowerShell):

- Preview candidates only:
    - Ensure `DAILY_API_KEY` is set; then run:
    - `python scripts/cleanup_recordings.py --retention-days 7 --dry-run`

- Actually delete (requires confirmation):
    - `python scripts/cleanup_recordings.py --retention-days 7 --yes`

Options:
- `--keep-file path\to\keep_ids.txt` (protect IDs listed one-per-line)
- `--keep-substrings EEC,IPEC,training` (protect if room_name contains any substring)
- `--api-key <DAILY_API_KEY>` (otherwise uses env var)
- `--log-file cleanup.log -v` (write log file and increase verbosity)

Notes:
- The script calls the Daily REST API directly and supports pagination.
- It parses both legacy and new timestamp formats from room names when needed.