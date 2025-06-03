import re
import json
import time
import requests
from rich.console import Console

# Load all tool modules via registry
import tools
from registry import available_functions, definitions
from template import function_calling_prompt_template, system_prompt, slack_prompt, gmail_prompt

console = Console()

OLLAMA_URL = "http://localhost:11434/api/generate"
HEADERS = {"Content-Type": "application/json"}
MODEL = "mistral:latest"


# 5.188.10.179
# 185.222.209.14
# 95.70.0.46
# 191.96.249.183
# 115.238.245.8
# 122.226.181.164
# 122.226.181.167
# Check if the subnet 127.0.0.1/24 has any abusive IPs reported in the last 15 days.


# Your input question
# QUESTION = "Is 118.25.6.39 a safe IP?"
QUESTION = "how is the weather in london?"

# def extract_function_calls(question):
#     prompt = f"""
#         You are an assistant that uses tools to answer questions.

#         You are provided a list of available tools. Each tool has a `name` and required `parameters`.

#         IMPORTANT:
#         - You must only use one of the provided tool names from the `function.name` field.
#         - Do not invent or modify tool names. For example, do not use names like "weather_api" unless they are exactly listed.
#         - Use the tool name **as-is**.
#         - Respond using this format only:

#         [TOOL_CALLS] [{{"name": "<tool_name>", "arguments": {{...}}}}]

#         [AVAILABLE_TOOLS]{json.dumps(definitions)}[/AVAILABLE_TOOLS]

#         [INST] {question} [/INST]
#         """
#     data = {
#         "model": MODEL,
#         "prompt": prompt,
#         "stream": False
#     }

#     start = time.time()
#     response = requests.post(OLLAMA_URL, headers=HEADERS, data=json.dumps(data))
#     end = time.time()

#     if response.status_code != 200:
#         return None, None, f"HTTP error: {response.status_code}", end - start

#     try:
#         raw = response.json().get("response", "")
#         fn_calls = json.loads(raw.replace("[TOOL_CALLS] ", ""))
#         return raw, fn_calls, None, end - start
#     except Exception as e:
#         return raw, None, e, end - start

# def extract_function_calls(question):
#     prompt = function_calling_prompt_template\
#         .replace("%%tool_definitions%%", json.dumps(definitions))\
#         .replace("%%question%%", question)

#     data = {
#         "model": MODEL,
#         "prompt": prompt,
#         "stream": False
#     }

#     start = time.time()
#     response = requests.post(OLLAMA_URL, headers=HEADERS, data=json.dumps(data))
#     end = time.time()

#     if response.status_code != 200:
#         return None, None, f"HTTP error: {response.status_code}", end - start

#     try:
#         body = response.json()
#         raw = body.get("response", "")
#         fn_calls = json.loads(raw.replace("[TOOL_CALLS] ", ""))
#         return raw, fn_calls, None, end - start
#     except Exception as e:
#         return raw, None, e, end - start


def extract_function_calls(question):
    prompt = function_calling_prompt_template.replace("%%tool_definitions%%", json.dumps(definitions)).replace("%%question%%", question)

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

    # Extract JSON array using regex
    try:
        json_match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if not json_match:
            return raw, None, "No JSON found in response", end - start
        fn_calls = json.loads(json_match.group(0))
        return raw, fn_calls, None, end - start
    except Exception as e:
        return raw, None, e, end - start

def call_functions(fn_calls):
    results = []
    for call in fn_calls:
        fn = available_functions[call["name"]]
        result = fn(**call["arguments"])
        results.append(result)
    return results

# def answer_question(question, fn_responses):
#     prompt = f"""
# Using the following function responses: {json.dumps(fn_responses)}
# Answer this question: {question}
# """
#     data = {
#         "model": MODEL,
#         "prompt": prompt,
#         "stream": True
#     }

#     response = requests.post(OLLAMA_URL, headers=HEADERS, data=json.dumps(data), stream=True)

#     answer = ""
#     for line in response.iter_lines():
#         if line:
#             chunk = json.loads(line)
#             answer += chunk.get("response", "")
#     return answer

def answer_question(question, fn_responses):
    full_prompt = (
        f"{system_prompt.strip()}\n\n"
        f"{slack_prompt.strip()}\n\n"
        f"{gmail_prompt.strip()}\n\n"
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

# === Run Pipeline ===
if __name__ == "__main__":
    console.print(f"\n[bold blue]Q: {QUESTION}[/bold blue]")

    raw, fn_calls, error, fn_time = extract_function_calls(QUESTION)

    if error:
        console.print(f"[bold red]Function selection error:[/bold red] {error}")
        console.print(f"[dim]Raw model output:[/dim] {raw}")
        exit(1)

    console.print(f"\n[bold]Function calls:[/bold] {fn_calls}")
    fn_responses = call_functions(fn_calls)
    console.print(f"[bold]Function responses:[/bold] {fn_responses}")
    console.print(f"[italic yellow]Function duration: {fn_time:.2f}s[/italic yellow]")

    start = time.time()
    final_answer = answer_question(QUESTION, fn_responses)
    end = time.time()

    console.print(f"\n[bold green]Final Answer:[/bold green] {final_answer}")
    console.print(f"[italic yellow]Answer duration: {end - start:.2f}s[/italic yellow]")
