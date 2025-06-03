import json
import time
import re
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

    try:
        json_match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if not json_match:
            return raw, None, "No JSON found in response", end - start
        fn_calls = json.loads(json_match.group(0))
        return raw, fn_calls, None, end - start
    except Exception as e:
        return raw, None, e, end - start


def call_function(function_calls):
    responses = []
    for call in function_calls:
        fn_name = call["name"]
        args = call["arguments"]
        result = available_functions[fn_name](**args)
        responses.append(result)
    return responses


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


# === 🚀 Run one test question ===
if __name__ == "__main__":
    question = "How is the weather in London?"

    console.rule("[bold yellow]Testing Question")
    console.print(f"[bold green]Question:[/bold green] {question}")

    raw, fn_calls, error, fn_time = extract_function_calls(question)

    if error:
        console.print(f"[bold red]Error:[/bold red] {error}")
        console.print(f"[bold cyan]Raw Output:[/bold cyan]\n{raw}")
    else:
        console.print(f"[bold cyan]Function Calls:[/bold cyan]\n{fn_calls}")

        fn_responses = call_function(fn_calls)
        final_response = answer_question(question, fn_responses)

        console.rule("[bold green]Final Answer")
        console.print(final_response)
        console.rule()
