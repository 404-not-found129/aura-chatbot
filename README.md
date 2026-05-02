# Aura - Terminal AI Chatbot

Aura is a sleek, terminal-based AI assistant powered by Google's Gemini models and built with Python. It features a rich, visually appealing command-line interface with Markdown support and interactive chat capabilities.

## Features
- **Rich Terminal UI**: Beautifully formatted text and Markdown rendering.
- **Conversational AI**: Maintains chat history using Google's `gemini-2.5-flash` model.
- **Simple Setup**: Just drop in an API key and run.

## Prerequisites
- Python 3.9+
- A Google Gemini API Key. You can get one for free at [Google AI Studio](https://aistudio.google.com/).

## Installation

1. **Clone or Download the Repository:**
   ```bash
   git clone <your-github-repo-url>
   cd "aura chatbot"
   ```

2. **Run the Install Script:**
   Use the provided script to automatically create a virtual environment, install dependencies, and set up your `.env` file.
   ```bash
   ./install.sh
   ```

3. **Configure your API Key:**
   - Open the newly created `.env` file in your text editor and replace `your_api_key_here` with your actual Gemini API key. *(Note: The `.env` file is ignored by Git to keep your API key secure!)*

## Usage

Once installed, you can start the chatbot from anywhere on your computer by simply typing:

```bash
aura
```

### Commands:
- Type your message and hit Enter to chat.
- `clear` - Clears the terminal screen.
- `exit` or `quit` - Exits the chatbot.

## Pushing to GitHub

This repository is already configured with a `.gitignore` file that prevents you from accidentally committing your `.env` file or virtual environment. 

To push your chatbot to your own GitHub repository:
1. Go to [GitHub](https://github.com/new) and create a new, empty repository.
2. Run the following commands in this directory:
   ```bash
   git add .
   git commit -m "Initial commit: Added Aura terminal chatbot"
   git remote add origin <your-new-github-repo-url>
   git push -u origin main
   ```
