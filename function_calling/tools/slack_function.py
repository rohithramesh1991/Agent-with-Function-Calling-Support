import requests
import os
from dotenv import load_dotenv
from registry import register_tool

load_dotenv()

@register_tool("send_slack_message", {
    "type": "function",
    "function": {
        "name": "send_slack_message",
        "description": "Send a message to a Slack channel or user (e.g., to alert about abusive IPs)",
        "parameters": {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel (e.g., #alerts) or user ID (e.g., U12345678)"
                },
                "message": {
                    "type": "string",
                    "description": "The message to send"
                }
            },
            "required": ["channel", "message"]
        }
    }
})
def send_slack_message(channel, message):
    slack_token = os.environ.get("SLACK_API_KEY")
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": channel,
        "text": message
    }
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()

    if response.status_code == 200 and result.get("ok"):
        return {
            "status": "success",
            "channel": channel,
            "message": message
        }
    else:
        return {
            "status": "error",
            "error": result.get("error", "unknown_error")
        }

@register_tool("list_slack_channels", {
    "type": "function",
    "function": {
        "name": "list_slack_channels",
        "description": "List all available public and private Slack channels",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
})
def list_slack_channels():
    slack_token = os.environ.get("SLACK_API_KEY")
    url = "https://slack.com/api/conversations.list"
    headers = {
        "Authorization": f"Bearer {slack_token}"
    }
    params = {
        "types": "public_channel,private_channel",
        "limit": 1000
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if response.status_code == 200 and data.get("ok"):
        channels = [
            {
                "name": ch["name"],
                "id": ch["id"],
                "is_private": ch["is_private"]
            }
            for ch in data.get("channels", [])
        ]
        return {
            "status": "success",
            "channels": channels
        }
    else:
        return {
            "status": "error",
            "error": data.get("error", "unknown_error")
        }

@register_tool("lookup_slack_user", {
    "type": "function",
    "function": {
        "name": "lookup_slack_user",
        "description": "Find a Slack user's ID by their email",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The user's email address"
                }
            },
            "required": ["email"]
        }
    }
})
def lookup_slack_user(email):
    slack_token = os.environ.get("SLACK_API_KEY")
    url = "https://slack.com/api/users.lookupByEmail"
    headers = {
        "Authorization": f"Bearer {slack_token}"
    }
    params = {"email": email}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if response.status_code == 200 and data.get("ok"):
        return {
            "status": "success",
            "user_id": data["user"]["id"],
            "real_name": data["user"]["real_name"]
        }
    else:
        return {
            "status": "error",
            "error": data.get("error", "unknown_error")
        }

@register_tool("list_slack_users", {
    "type": "function",
    "function": {
        "name": "list_slack_users",
        "description": "List all Slack users (public info only)",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
})
def list_slack_users():
    slack_token = os.environ.get("SLACK_API_KEY")
    url = "https://slack.com/api/users.list"
    headers = {
        "Authorization": f"Bearer {slack_token}"
    }
    response = requests.get(url, headers=headers)
    data = response.json()

    if response.status_code == 200 and data.get("ok"):
        users = [
            {
                "id": u["id"],
                "real_name": u.get("real_name"),
                "email": u.get("profile", {}).get("email")
            }
            for u in data.get("members", []) if not u.get("is_bot", False)
        ]
        return {
            "status": "success",
            "users": users
        }
    else:
        return {
            "status": "error",
            "error": data.get("error", "unknown_error")
        }
