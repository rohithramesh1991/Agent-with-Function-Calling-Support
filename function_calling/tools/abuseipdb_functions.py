import requests
import os
import json
from dotenv import load_dotenv
from registry import register_tool

load_dotenv()

@register_tool("check_ip_reputation", {
    "type": "function",
    "function": {
        "name": "check_ip_reputation",
        "description":  "Check the abuse reputation of a single IP address",
        "parameters": {
            "type": "object",
            "properties": {
                "ip_address": {"type": "string"},
                "max_age": {"type": "integer", "default": 90}
            },
            "required": ["ip_address"]
        }
    }
})
def check_ip_reputation(ip_address, max_age=90):
    key = os.environ['ABUSEIPDB_API_KEY']
    url = "https://api.abuseipdb.com/api/v2/check"
    headers = {'Key': key, 'Accept': 'application/json'}
    params = {'ipAddress': ip_address, 'maxAgeInDays': max_age}
    response = requests.get(url, headers=headers, params=params)
    return response.text

@register_tool("check_ip_block", {
    "type": "function",
    "function": {
        "name": "check_ip_block",
        "description":  "Check if any IPs in a block are abusive",
        "parameters": {
            "type": "object",
            "properties": {
                "block": {"type": "string"}
            },
            "required": ["block"]
        }
    }
})
def check_ip_block(block):
    key = os.environ['ABUSEIPDB_API_KEY']
    url = "https://api.abuseipdb.com/api/v2/check-block"
    headers = {'Key': key, 'Accept': 'application/json'}
    params = {'network': block, 'maxAgeInDays': 90}
    response = requests.get(url, headers=headers, params=params)
    return response.text