from llm_client import LLMClient

def main():
    llm = LLMClient(model="qwen3-coder:30b") # "mistral" or "codellama:34b" or "qwen3-coder:30b"

    while True:
        prompt = input("\nYour prompt (or 'quit'): ")

        if prompt.lower() == "quit":
            break

        answer = llm.generate(prompt)
        print("\n--- LLM Output ---")
        print(answer)

if __name__ == "__main__":
    main()
