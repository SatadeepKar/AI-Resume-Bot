# AI Resume Bot 🤖📄

AI Resume Bot is a powerful tool designed to help job seekers optimize their resumes using AI. It provides an automated way to analyze, score, and generate tailored resume versions based on specific job descriptions, all through a convenient Telegram interface.

## 🚀 Features

-   **ATS Scoring**: Instantly get an ATS (Applicant Tracking System) score for your resume.
-   **Tailored Suggestions**: Receive specific advice on how to improve your resume for a particular job description.
-   **Automated Generation**: Generate optimized PDF versions of your resume with just a few clicks.
-   **Dual Interface**: Access the system via a robust **FastAPI Backend** or a user-friendly **Telegram Bot**.
-   **Multi-Format Support**: Handles PDF and DOCX files.

## 🛠️ Technology Stack

-   **Backend**: [FastAPI](https://fastapi.tiangolo.com/)
-   **Telegram Bot**: [python-telegram-bot](https://python-telegram-bot.org/)
-   **AI Engines**: OpenAI (GPT-4o) & Groq (Advanced Analysis)
-   **PDF Processing**: pdfkit, PyPDF2
-   **Document Processing**: python-docx

## 📋 Prerequisites

-   Python 3.10+
-   `wkhtmltopdf` (required for PDF generation)
-   An OpenAI API Key
-   A Telegram Bot Token (from [BotFather](https://t.me/botfather))

## ⚙️ Setup & Installation

1.  **Clone the Repository** (or download the source):
    ```bash
    git clone <your-repo-url>
    cd DrCode
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # Linux/macOS
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the root directory based on `.env.example`:
    ```ini
    OPENAI_API_KEY=your_openai_key
    TELEGRAM_BOT_TOKEN=your_bot_token
    API_BASE_URL=http://127.0.0.1:8000
    ```

## 🚀 How to Run

### 1. Start the Backend API
The API handles all the heavy lifting (parsing, scoring, generation).
```bash
python main.py
```

### 2. Start the Telegram Bot
In a new terminal window:
```bash
python bot.py
```

## 📂 Project Structure

-   `main.py`: Entry point for the FastAPI server.
-   `bot.py`: Entry point for the Telegram bot.
-   `api/`: Contains RESTful API routes.
-   `telegram_bot/`: Contains bot handlers and logic.
-   `modules/`: Core logic for parsing, scoring, and generation.
-   `uploads/`: Temporary storage for uploaded resumes.
-   `outputs/`: Storage for generated resumes.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Built with ❤️ for job seekers.*
