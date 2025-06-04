import json
import time
import re
import requests
from rich.console import Console
import gradio as gr

# Load all tool modules via registry
import tools
from registry import available_functions, definitions
from template import function_calling_prompt_template, system_prompt, slack_prompt, switch_to_answer_prompt

console = Console()

OLLAMA_URL = "http://localhost:11434/api/generate"
HEADERS = {"Content-Type": "application/json"}
MODEL = "qwen2.5:latest"

# New: Structured message object: role, name, content
def format_messages(messages):
    """
    Formats the chat history as a message list:
    Each message is a dict: {role: ..., content: ..., [name: ...]}
    """
    formatted = ""
    for msg in messages:
        if msg["role"] == "tool":
            formatted += f'Tool [{msg["name"]}]: {msg["content"]}\n'
        elif msg["role"] == "system":
            formatted += f'System: {msg["content"]}\n'
        else:
            formatted += f'{msg["role"].capitalize()}: {msg["content"]}\n'
    return formatted

def extract_function_calls(question, messages=None):
    # Build prompt with messages (rich context) + tool instructions
    messages = messages or []
    # Only show the last N messages to stay under context window
    truncated = messages[-12:] if len(messages) > 12 else messages

    chat_context = format_messages(truncated)
    prompt = (
        chat_context +
        function_calling_prompt_template
            .replace("%%tool_definitions%%", json.dumps(definitions))
            .replace("%%question%%", question)
    )

    data = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    start = time.time()
    response = requests.post(OLLAMA_URL, headers=HEADERS, data=json.dumps(data))
    end = time.time()

    if response.status_code != 200:
        return None, None, f"HTTP error: {response.status_code}", end - start

    body = response.json()
    raw = body.get("response", "")

    try:
        json_match = re.search(r"\[\s*{.*?}\s*]", raw, re.DOTALL)
        if not json_match:
            return raw, None, None, end - start
        json_str = json_match.group(0).replace('\\', '')
        fn_calls = json.loads(json_str)
        return raw, fn_calls, None, end - start
    except Exception as e:
        return raw, None, None, end - start

def call_function(function_calls):
    if not function_calls:
        return []
    call = function_calls[0]
    fn_name = call["name"]
    args = call.get("arguments", {})
    result = available_functions[fn_name](**args)
    return [result]

def answer_question(question, fn_responses, messages=None):
    """
    After tool execution, instruct the LLM to answer using the latest tool result.
    """
    messages = messages or []
    full_messages = messages.copy()
    if fn_responses:
        # Add the tool output as a message
        tool_msg = {
            "role": "tool",
            "name": fn_responses[0].get("name", "tool") if isinstance(fn_responses[0], dict) else "tool",
            "content": json.dumps(fn_responses[0], indent=2) if isinstance(fn_responses[0], dict) else str(fn_responses[0])
        }
        full_messages.append(tool_msg)

    formatted = format_messages(full_messages[-12:])

    full_prompt = (
        f"{system_prompt.strip()}\n\n"
        f"{slack_prompt.strip()}\n\n"
        f"{formatted}\n"
        f"{switch_to_answer_prompt}"
        f"User: {question}\n"
    )

    data = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": True
    }

    response = requests.post(OLLAMA_URL, headers=HEADERS, data=json.dumps(data), stream=True)
    answer = ""
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            answer += chunk.get("response", "")
    return answer


def messages_to_chatbot_pairs(messages):
    """
    Converts the message history (list of message dicts) to list of (user, assistant) tuples for Gradio Chatbot.
    Only user/assistant roles are shown; tool/system messages are skipped or shown as "Assistant" comments.
    """
    pairs = []
    last_user = None
    for msg in messages:
        if msg["role"] == "user":
            last_user = msg["content"]
        elif msg["role"] == "assistant":
            # Pair it with the last user
            pairs.append((last_user, msg["content"]))
            last_user = None
        # Optionally, you could show tool output as assistant lines too:
        elif msg["role"] == "tool":
            # Uncomment to show tool messages as assistant bubbles (optional)
            pairs.append((None, f'[TOOL:{msg.get("name")}] {msg["content"]}'))
    return pairs

def ensure_dict_messages(messages):
    """
    Converts history from [(user, assistant), ...] tuples (as used by Gradio) 
    to [{'role': ..., 'content': ...}, ...] dicts for your internal logic.
    """
    dict_msgs = []
    for entry in messages or []:
        if isinstance(entry, dict):  # Already in new format
            dict_msgs.append(entry)
        elif isinstance(entry, (tuple, list)) and len(entry) == 2:
            user, assistant = entry
            if user:
                dict_msgs.append({"role": "user", "content": user})
            if assistant:
                dict_msgs.append({"role": "assistant", "content": assistant})
    return dict_msgs

# Gradio's "history" now stores a list of message dicts, not (user, assistant) tuples!
def chat_fn(message, messages):
    messages = ensure_dict_messages(messages)
    messages.append({"role": "user", "content": message})

    raw, fn_calls, error, fn_duration = extract_function_calls(message, messages)
    if error:
        response = f"Error: {error}\nRaw: {raw}\n Took {fn_duration:.2f}s"
        messages.append({"role": "assistant", "content": response})
        return "", messages_to_chatbot_pairs(messages)  # Return tuples

    if not fn_calls:
        response = f"{raw}\n\nTook {fn_duration:.2f}s"
        messages.append({"role": "assistant", "content": response})
        return "", messages_to_chatbot_pairs(messages)

    extra_action_note = ""
    if len(fn_calls) > 1:
        extra_action_note = (
            "\n\n⚠️ Note: You requested multiple actions. "
            "I will only perform the first one per turn. "
            "Please specify the next action after this is complete."
        )

    fn_responses = call_function(fn_calls[:1])
    tool_name = fn_calls[0]["name"] if fn_calls and isinstance(fn_calls[0], dict) and "name" in fn_calls[0] else "tool"
    tool_content = (
        json.dumps(fn_responses[0], indent=2) if isinstance(fn_responses[0], dict)
        else str(fn_responses[0])
    )
    tool_msg = {
        "role": "tool",
        "name": tool_name,
        "content": tool_content
    }
    messages.append(tool_msg)


    start = time.time()
    final_response = answer_question(message, fn_responses, messages)
    end = time.time()
    final_response += (
        f"\n\nFn call: {fn_duration:.2f}s | Answer: {end - start:.2f}s"
        f"{extra_action_note}"
    )
    messages.append({"role": "assistant", "content": final_response})

    return "", messages_to_chatbot_pairs(messages)

with gr.Blocks() as demo:
    gr.Markdown("<h1 style='text-align: center;'>🤖 Chat Assistant</h1>")
    chatbot = gr.Chatbot(height=500, show_label=False)
    user_input = gr.Textbox(placeholder="Ask anything...", show_label=False, lines=1)
    user_input.submit(chat_fn, [user_input, chatbot], [user_input, chatbot])

demo.launch()
