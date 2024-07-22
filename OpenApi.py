import requests
import json

class OpenApi:
    def __init__(self, api_key):
        self.api_key = api_key
        if self.api_key is None:
            raise ValueError("OpenAI API key is not set.")

    def call_openai_api(self, messages):
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": messages
        }

        response = requests.post(url, headers=headers, json=data)

        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        else:
            print("Error:", response.status_code, response.text)
            return None