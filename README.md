# Aura AI Chatbot

Aura is an AI assistant available as both a terminal app and an Android APK. It supports multiple AI providers — Google Gemini, OpenAI GPT, and Anthropic Claude — with a rich, visually appealing interface and file attachment support.

## Download

You can download the latest release files (APK, source, install scripts) directly from Google Drive:

**[Download from Google Drive](https://drive.google.com/drive/folders/1Ddglkx1Y0vmgq7Zm11ikKMt9OBMNtNJj?dmr=1&ec=wgc-drive-%5Bmodule%5D-goto)**

Or clone/download this repository manually (see Installation below).

---

## Features

- **Multi-Provider AI**: Switch between Google Gemini, OpenAI GPT, and Anthropic Claude
- **Streaming Responses**: Real-time token-by-token output with a loading spinner
- **File Attachments**: Attach local files as context for the AI (`/attach <path>`)
- **Rich Terminal UI**: Markdown rendering, syntax highlighting, and styled panels
- **Android App**: Full chat UI APK built with Kivy, targeting Android 10+ (API 29+), compatible with Android 16 / Pixel 10 Pro
- **Slash Commands**: `/provider`, `/model`, `/attach`, `/detach`, `/files`, `/clear`, `/help`

---

## Terminal App

### Prerequisites

- Python 3.9+
- API key(s) for the providers you want to use:
  - **Gemini**: [Google AI Studio](https://aistudio.google.com/) (free tier available)
  - **OpenAI**: [platform.openai.com](https://platform.openai.com/)
  - **Claude**: [console.anthropic.com](https://console.anthropic.com/)

### Installation

1. **Clone or download:**
   ```bash
   git clone <your-github-repo-url>
   cd "aura chatbot"
   ```

2. **Run the install script:**
   ```bash
   ./install.sh
   ```
   This creates a virtual environment, installs dependencies, and sets up your `.env` file.

3. **Add your API key(s) to `.env`:**
   ```
   GEMINI_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here
   ```
   You only need keys for the providers you plan to use.

### Usage

```bash
aura
```

### Commands

| Command | Description |
|---|---|
| `/provider` | Switch AI provider (Gemini / OpenAI / Claude) |
| `/model` | Switch model for the current provider |
| `/attach <path>` | Attach a file as context for the AI |
| `/detach <name>` | Remove an attached file |
| `/files` | List currently attached files |
| `clear` | Clear the terminal screen |
| `exit` / `quit` | Exit the chatbot |

### Supported Models

**Gemini** — `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-pro`, `gemini-1.5-flash`

**OpenAI** — `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`

**Claude** — `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`

---

## Android App

The APK is a full Kivy-based chat app with a dark purple theme, provider/model selection, and API key configuration built in.

### Requirements

- Android 10 or higher (API 29+)
- Compatible with Android 16 / Pixel 10 Pro

### Install

1. Download `aura-1.6.0-debug.apk` from the [Google Drive folder](https://drive.google.com/drive/folders/1Ddglkx1Y0vmgq7Zm11ikKMt9OBMNtNJj?dmr=1&ec=wgc-drive-%5Bmodule%5D-goto) or from `android/aura-1.6.0-debug.apk` in this repo.
2. Transfer the APK to your Android device.
3. Enable **Install from unknown sources** in Settings → Apps → Special app access.
4. Open the APK file to install.

Alternatively, install via ADB with USB debugging enabled:
```bash
adb install aura-1.6.0-debug.apk
```

5. Open the app, tap the settings icon, enter your API key(s), and start chatting.

---

## Pushing to GitHub

A `.gitignore` is included to prevent committing your `.env` file or virtual environment.

```bash
git add .
git commit -m "Initial commit: Aura AI chatbot"
git remote add origin <your-github-repo-url>
git push -u origin main
```
