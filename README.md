# Discord Meeting Notes Bot (Optimized for Apple Silicon)

A lightweight Discord bot that records meetings, transcribes audio with `faster-whisper`, and generates comprehensive meeting notes using quantized LLMs (Llama-2 or Mistral) optimized for Apple Silicon M2 Pro.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/platform-macOS-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/optimized-M2%20Pro-orange.svg" alt="Optimized for M2 Pro">
</p>

## 🌟 Features

- Records voice channels on Discord with automatic 1-hour limit
- Transcribes audio using `faster-whisper` with timestamps
- Generates structured meeting notes with key decision points and action items
- Optimized for Apple Silicon with Metal GPU acceleration
- Memory-efficient with on-demand model loading/unloading
- Persistent storage with SQLite database

## 🧠 How It Works

This bot uses `discord.py` to connect to voice channels and record audio. The recording is then:

1. Processed and saved as a 16kHz WAV file
2. Transcribed with `faster-whisper` (small/medium model)
3. Analyzed by a quantized 4-bit LLM (Llama-2-7B or Mistral-7B)
4. Formatted into structured meeting notes with decision points and action items
5. Saved to a database for future retrieval

All processing happens locally on your machine, with no data sent to external services.

## 💻 Technical Stack

- **Framework**: Python 3.10+ with `discord.py` 2.3.2
- **Speech Recognition**: `faster-whisper` with small/medium models
- **Note Generation**: 4-bit quantized Llama-2-7B or Mistral-7B via `llama-cpp-python`
- **Acceleration**: Metal GPU support via Apple MLX framework
- **Storage**: SQLite database with 30-day retention

## 📋 System Requirements

- MacBook with Apple Silicon (M1/M2/M3 series)
- macOS 13.0+ with Metal support
- 16GB+ RAM recommended
- ~5GB disk space for models

## 🚀 Installation

### Quick Setup

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/discord-meeting-notes.git
   cd discord-meeting-notes
   ```

2. Run the setup script to install dependencies and download models:

   ```bash
   chmod +x setup.py
   ./setup.py
   ```

   Options:

   - `--model mistral-7b` to use Mistral instead of Llama
   - `--no-metal` if you don't want Metal acceleration
   - `--no-deps` to skip dependency installation

### Manual Setup

1. Install llama-cpp-python with Metal support:

   ```bash
   CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
   ```

2. Install other dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Download a quantized model:

   - [Llama-2-7B-GGUF](https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf)
   - [Mistral-7B-GGUF](https://huggingface.co/TheBloke/Mistral-7B-v0.1-GGUF/resolve/main/mistral-7b-v0.1.Q4_K_M.gguf)

4. Copy `.env.example` to `.env` and configure your Discord bot token:
   ```bash
   cp .env.example .env
   # Edit .env with your Discord Bot Token
   ```

## 💬 Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a New Application and add a Bot
3. Enable "Message Content Intent" and "Server Members Intent" in the Bot section
4. Copy your bot token to the `.env` file
5. Generate an OAuth2 URL with the following permissions:
   - `bot`
   - `Read Messages/View Channels`
   - `Send Messages`
   - `Attach Files`
   - `Connect` (Voice)
   - `Speak` (Voice)
6. Invite your bot to your server using the generated URL

## 🎮 Usage

Start the bot:

```bash
python main.py
```

### Commands

- **`!join`** - Bot joins your current voice channel
- **`!startmeeting [name]`** - Start recording (name is optional)
- **`!stopmeeting`** - Stop recording and generate meeting notes
- **`!getnotes [meeting_id]`** - Retrieve notes from previous meetings
- **`!help`** - Show available commands

### Example Session

1. Join a voice channel
2. Type `!join` in a text channel
3. Start your meeting with `!startmeeting Weekly Team Sync`
4. After the meeting, type `!stopmeeting`
5. Wait for processing (typically 1-5 minutes depending on meeting length)
6. Get your structured meeting notes!

## ⚙️ Configuration

Edit the `.env` file to customize:

```
# Model options
WHISPER_MODEL_SIZE=small  # Options: tiny, base, small, medium
LLM_MODEL_PATH=models/llama-2-7b.Q4_K_M.gguf

# Performance tuning
LLM_GPU_LAYERS=1  # Layers to offload to GPU (1-2 recommended for M2)
LLM_THREADS=8     # CPU threads to use
LLM_CONTEXT_SIZE=2048  # Context window size
```

## 📊 Performance

| Configuration               | RAM Usage | Processing Time | Notes                   |
| --------------------------- | --------- | --------------- | ----------------------- |
| Whisper small + Llama-2-7B  | ~6GB      | ~2-3x realtime  | Best balance for M2 Pro |
| Whisper medium + Mistral-7B | ~8GB      | ~3-4x realtime  | Better quality, slower  |

## 🔧 Troubleshooting

- **Metal Acceleration Issues**: If you encounter GPU errors, try setting `LLM_GPU_LAYERS=0` in `.env`
- **Out of Memory**: Reduce `LLM_CONTEXT_SIZE` or use a smaller Whisper model
- **Audio Quality**: Make sure Discord voice quality is set to high in server settings

## 📄 License

[MIT License](LICENSE)

## 🙏 Acknowledgements

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) for efficient speech recognition
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) for local LLM inference
- [TheBloke](https://huggingface.co/TheBloke) for quantized LLM models
- [discord.py](https://github.com/Rapptz/discord.py) for Discord API integration
