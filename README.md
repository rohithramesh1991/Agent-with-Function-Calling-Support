# Agent-with-Function-Calling-Support

# 🤖 Chat Assistant

A local, extensible chat assistant with function-calling and tool integration, powered by [Ollama](https://ollama.com/) and [Gradio](https://www.gradio.app/).  
This assistant can execute function calls (tools) and answer user questions using the results, in a conversational interface.

---

## Features

- **Conversational LLM chat** powered by an Ollama-hosted model (default: `qwen2.5:latest`)
- **Tool/function-calling:** Structured function calls are parsed and executed via your custom registry.
- **Rich chat interface:** Gradio frontend, with history, tool outputs, and user/assistant roles.
- **Easily extensible:** Add new tools in `tools.py`, new prompts in `template.py`.

---

## Quick Start
```bash
### 1. **Clone the repository**

git clone https://github.com/yourusername/chat-assistant.git
cd chat-assistant

### 2. **Install dependencies**
pip install -r requirements.txt

### 3. **Start Ollama with your model**
Install Ollama if not already installed, and pull the desired model (default is Qwen 2.5):

ollama run qwen2.5

### 4. **Run the app**
python Qwen_fc_app.py

### 5. **Open in your browser**
The Gradio interface will open at: http://localhost:7860
```
