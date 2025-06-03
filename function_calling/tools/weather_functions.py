import requests
import os
import json
from dotenv import load_dotenv
from registry import register_tool

load_dotenv()

@register_tool("get_current_weather", {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather at given coordinates",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"}
            },
            "required": ["latitude", "longitude"]
        }
    }
})
def get_current_weather(latitude, longitude):
    key = os.environ['WEATHERMAP_API_KEY']
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={key}&units=metric"
    response = requests.get(url)
    return response.text

@register_tool("get_forecast", {
    "type": "function",
    "function": {
        "name": "get_forecast",
        "description": "Get 5-day weather forecast for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"]
        }
    }
})
def get_forecast(city):
    key = os.environ['WEATHERMAP_API_KEY']
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={key}&units=metric"
    response = requests.get(url)
    return response.text