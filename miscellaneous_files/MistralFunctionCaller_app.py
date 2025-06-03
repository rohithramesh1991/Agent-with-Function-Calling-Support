import json
import time
import re
import requests
from rich.console import Console
import gradio as gr

# Load all tool modules via registry
import tools
from registry import available_functions, definitions
from template import function_calling_prompt_template, system_prompt, slack_prompt

console = Console()

OLLAMA_URL = "http://localhost:11434/api/generate"
HEADERS = {"Content-Type": "application/json"}
MODEL = "gemma3:12b"


# Retrieve the abuse report details for 122.226.181.164
# how is the weather in london?

# 20.163.15.217 is an abused ip?
#  104.244.72.115 is an abused ip?


# what is the temperature in london?
# Ip 95.70.0.46 has it been abused?


# Step 1: Ask model which function(s) to call

def extract_function_calls(question, history=None):
    # Prepare chat history as context (last few turns)
    history_str = format_history(history, max_turns=4)

    # Build prompt with history and tool instructions
    prompt = (
        history_str +
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

    # Try to extract a JSON array (for tool calls), else treat as plain text
    try:
        json_match = re.search(r"\[\s*{.*?}\s*]", raw, re.DOTALL)
        if not json_match:
            # No tool call found, just treat as plain text response
            return raw, None, None, end - start

        json_str = json_match.group(0).replace('\\', '')
        fn_calls = json.loads(json_str)
        return raw, fn_calls, None, end - start
    except Exception as e:
        # If extraction/parsing fails, just return the original text
        return raw, None, None, end - start

# Step 2: Call actual Python functions
def call_function(function_calls):
    if not function_calls:
        return []
    call = function_calls[0]
    fn_name = call["name"]
    args = call.get("arguments", {})   # <--- This line fixes it!
    result = available_functions[fn_name](**args)
    return [result]

# Step 3: Ask model to generate final answer
# def answer_question(question, fn_responses, history=None):
#     # Include the recent chat history for context
#     history_str = format_history(history, max_turns=4)

#     full_prompt = (
#         history_str +
#         f"{system_prompt.strip()}\n\n"
#         f"{slack_prompt.strip()}\n\n"
#         f"Function Responses: {json.dumps(fn_responses)}\n"
#         f"Question: {question}"
#     )

#     data = {
#         "model": MODEL,
#         "prompt": full_prompt,
#         "stream": True
#     }

#     response = requests.post(OLLAMA_URL, headers=HEADERS, data=json.dumps(data), stream=True)

#     answer = ""
#     for line in response.iter_lines():
#         if line:
#             chunk = json.loads(line)
#             answer += chunk.get("response", "")
#     return answer

def answer_question(question, fn_responses, history=None, last_fn_response=None):
    # Prepare history as before
    history_str = format_history(history, max_turns=4)
    last_response_str = ""
    if last_fn_response:
        # Format the last function response as context for the LLM
        last_response_str = f"\nPrevious function response (for reference):\n{json.dumps(last_fn_response, indent=2)}\n"
    
    full_prompt = (
        history_str +
        f"{system_prompt.strip()}\n\n"
        f"{slack_prompt.strip()}\n\n"
        f"{last_response_str}" +         # NEW: Add last function response!
        f"Function Responses: {json.dumps(fn_responses)}\n"
        f"Question: {question}"
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

def format_history(history, max_turns=4):
    """
    Formats chat history for prompt context.
    Returns last max_turns (user, assistant) pairs as a single string.
    """
    if not history:
        return ""
    formatted = ""
    for user, bot in history[-max_turns:]:
        formatted += f"User: {user}\nAssistant: {bot}\n"
    return formatted

# === Gradio Chat Interface ===
# def chat_fn(message, history):
#     raw, fn_calls, error, fn_duration = extract_function_calls(message, history)

#     if error:
#         response = f"Error: {error}\nRaw: {raw}\n Took {fn_duration:.2f}s"
#         return "", history + [(message, response)]

#     if not fn_calls:
#         response = f"{raw}\n\nTook {fn_duration:.2f}s"
#         return "", history + [(message, response)]

#     # Note: Only perform one tool call per turn
#     extra_action_note = ""
#     if len(fn_calls) > 1:
#         extra_action_note = (
#             "\n\n⚠️ Note: You requested multiple actions. "
#             "I will only perform the first one per turn. "
#             "Please specify the next action after this is complete."
#         )

#     # Only call the first function
#     fn_responses = call_function(fn_calls[:1])

#     start = time.time()
#     final_response = answer_question(message, fn_responses, history)
#     end = time.time()

#     final_response += (
#         f"\n\nFn call: {fn_duration:.2f}s | Answer: {end - start:.2f}s"
#         f"{extra_action_note}"
#     )
#     return "", history + [(message, final_response)]

def chat_fn(message, history):
    raw, fn_calls, error, fn_duration = extract_function_calls(message, history)

    if error:
        response = f"Error: {error}\nRaw: {raw}\n Took {fn_duration:.2f}s"
        return "", history + [(message, response)]

    if not fn_calls:
        response = f"{raw}\n\nTook {fn_duration:.2f}s"
        return "", history + [(message, response)]

    # Only perform one tool call per turn
    extra_action_note = ""
    if len(fn_calls) > 1:
        extra_action_note = (
            "\n\n⚠️ Note: You requested multiple actions. "
            "I will only perform the first one per turn. "
            "Please specify the next action after this is complete."
        )

    # Track the previous function response (for use as context)
    fn_responses = call_function(fn_calls[:1])

    # Attach previous function responses in history for answer stage
    # Option 1: Save last fn_response in history, or
    # Option 2: Pass it directly to answer_question below

    start = time.time()
    # Pass history and the *most recent* fn_response
    final_response = answer_question(message, fn_responses, history, last_fn_response=fn_responses[0] if fn_responses else None)
    end = time.time()

    final_response += (
        f"\n\nFn call: {fn_duration:.2f}s | Answer: {end - start:.2f}s"
        f"{extra_action_note}"
    )
    return "", history + [(message, final_response)]


with gr.Blocks() as demo:
    gr.Markdown("<h1 style='text-align: center;'>🤖 Chat Assistant</h1>")
    chatbot = gr.Chatbot(height=500, show_label=False)
    user_input = gr.Textbox(placeholder="Ask anything...", show_label=False, lines=1)
    user_input.submit(chat_fn, [user_input, chatbot], [user_input, chatbot])

demo.launch()