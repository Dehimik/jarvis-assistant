# Jarvis Assistant

`Jarvis Assistant` is a desktop voice assistant featuring a modern graphical interface, built on a powerful Python backend. It utilizes a plugin-based architecture, allowing for easy expansion of its speech-to-text and text-to-speech capabilities.

## 🚀 Key Features

  * **Real-time Voice Recognition:** Uses [Vosk](https://alphacephei.com/vosk/) for fast, offline speech recognition.
  * **Flexible Command System:** Control your PC with your voice—open applications, websites, and run custom scripts.
  * **Plugin Architecture:** Easily swap or add new models for speech recognition (STT) and synthesis (TTS).
  * **Modern GUI:** An interface built with React, TypeScript, and Tauri, ensuring low resource consumption and a native desktop feel.
  * **Command Editor:** Add and edit commands directly through the graphical interface (stored in `.yaml` / `.yml` files).
  * **Advanced Logging:**
      * A real-time log viewer page within the application.
      * Detailed logging to a PostgreSQL database.
      * A separate table tracks executed commands and recognition errors.
  * **Flexible Settings:**
      * Select input (microphone) and output (speaker) devices.
      * Choose the language.
      * Manage operating modes (listen only / listen and respond).
      * Configure OpenAI (token).

## 🛠️ Technology Stack

  * **Backend:** **Python**, **FastAPI** (for REST API), **Vosk** (STT), **pyttsx3** (TTS)
  * **Frontend:** **React**, **TypeScript**, **TailwindCSS**
  * **Desktop App:** **Tauri** (Rust)
  * **Database:** **PostgreSQL**

## 🏗️ Architecture

The project consists of two main parts that run concurrently:

1.  **Backend (`assistant/`)**: A Python (FastAPI) server that handles all the logic: speech recognition, command parsing, database interaction, and action execution.
2.  **Frontend (`gui/`)**: A modern web interface (React/TS) compiled into a native desktop window using Tauri. It communicates with the backend via a REST API.

## 📁 Project Structure

```
/
├── assistant/        # Python backend (FastAPI, Vosk, logic)
│   ├── audio/
│   │   └── models/   # -> UNPACK THE VOSK MODEL HERE
│   ├── config/     # Internal configuration (config.yaml)
│   ├── data/       # App-generated data (logs, settings)
│   ├── db/         # Database logic (models, sessions)
│   ├── nlu/        # NLU "engine" for parsing and processing commands
│   ├── plugins/    # Plugin manager
│   └── telemetry/  # Logger and benchmarking
├── configs/          # User-defined YAML files for commands and plugins
├── gui/              # Frontend (React, TS, Tauri)
├── logs/             # Debug log files
└── tests/            # Tests
```

## ⚙️ Installation and Setup

### Prerequisites

Before you begin, ensure you have the following installed:

  * **Python** (3.10+ recommended)
  * **Node.js** and **npm** (or `yarn`)
  * **Rust** and **Cargo** (required for building Tauri)
  * **PostgreSQL** (server installed and running)

-----

### 1\. Database Setup

1.  Start your PostgreSQL server.
2.  Create a new database (e.g., `jarvis_db`) and a user with access privileges.
3.  *Table migrations should run automatically on the first launch.*

-----

### 2\. Backend Setup

1.  Clone the repository:

    ```bash
    git clone https://your-repo-url/jarvis-assistant.git
    cd jarvis-assistant
    ```

2.  Create and activate a virtual environment (recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # for Linux/macOS
    venv\Scripts\activate     # for Windows
    ```

3.  Install the Python dependencies (uses `pyproject.toml`):

    ```bash
    pip install -e .
    ```

4.  Create a `.env` file in the project's root folder (`jarvis-assistant/.env`) and add your database connection string:

    ```ini
    # .env
    JARVIS_DB_DSN="postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_DB_NAME"
    ```

    (Replace `YOUR_USER`, `YOUR_PASSWORD`, and `YOUR_DB_NAME` with your credentials).

-----

### 3\. Vosk Model Setup (Required)

The assistant will not work without a speech recognition model.

1.  Download your preferred [Vosk model](https://alphacephei.com/vosk/models) (e.g., `vosk-model-small-en-us-0.15`).

2.  Create the directory `assistant/audio/models/`.

3.  Unpack the model archive into this directory. The structure should look like this:

    ```
    assistant/audio/models/vosk-model-small-en-us-0.15/
                                ├── am/
                                ├── conf/
                                └── ...
    ```

4.  To select this model, edit the `assistant/config/config.yaml` file.

-----

### 4\. Frontend Setup

1.  Navigate to the `gui` directory:

    ```bash
    cd gui
    ```

2.  Install the Node.js dependencies:

    ```bash
    npm install
    # or
    yarn install
    ```

## ▶️ Running the Project

After completing all setup steps, run the application (this will start both the backend and frontend):

```bash
# While in the /gui directory
npm run tauri:dev
```

This will launch the application in development mode with all features, including hot-reload.

## 📄 Configuration

  * **Changing STT/TTS models:** `assistant/config/config.yaml`
  * **Adding/editing commands:** Via the GUI or by manually editing files in the `configs/` folder.
  * **Database settings:** `.env` file in the project root.