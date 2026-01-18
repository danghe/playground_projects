# M&A Health Forecast

A cross-platform web application for forecasting M&A market health using ARIMA/VAR models and Gemini AI.

## Quick Start

### Windows
1.  Double-click `run_app.bat`.
    *   This will automatically set up the environment, install dependencies, and start the app.

### Mac / Linux
1.  Open your Terminal.
2.  Navigate to this folder.
3.  Run the following command:
    ```bash
    chmod +x run_app.sh
    ./run_app.sh
    ```
    *   This will automatically set up the environment, install dependencies, and start the app.

## Requirements

*   **Python**: You must have Python installed.
    *   [Download Python](https://www.python.org/downloads/)
*   **Gemini API Key** (Optional): To use the AI features, you need a Google Gemini API key.
    1.  Create a file named `.env` in this folder (or use the one provided).
    2.  Add your key: `GEMINI_API_KEY=your_key_here`.

## Troubleshooting

*   **"Python not found"**: Ensure you ticked "Add Python to PATH" when installing Python.
*   **Browser doesn't open**: Open your browser manually and go to `http://127.0.0.1:5000`.
*   **"Permission denied" (Mac/Linux)**:
    Run this command in the terminal to make the script executable:
    ```bash
    chmod +x run_app.sh
    ```
*   **"Command not found" or "Bad interpreter" (Mac/Linux)**:
    If you copied the files from Windows, they might have incorrect line endings. Run this command to fix it:
    ```bash
    sed -i '' 's/\r$//' run_app.sh
    ```
