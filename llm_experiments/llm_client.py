import requests
import json


class LLMClient:
    """
    Simple client for interacting with a local Ollama model.
    """

    def __init__(self, model: str, host: str = "http://localhost:11434"):
        self.model = model
        self.url = f"{host}/api/generate"

    def generate(self, prompt: str) -> str:
        """
        Sends a prompt to the local Ollama model and returns the parsed answer.
        """
        payload = {
            "model": self.model, # "mistral" or "codellama:34b" or "qwen3-coder:30b"
            "prompt": prompt,
            "stream": True
        }

        response = requests.post(self.url, json=payload, stream=True)
        final_answer = ""

        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line.decode("utf-8"))

            if "response" in data:
                final_answer += data["response"]

            if data.get("done"):
                break

        return final_answer
