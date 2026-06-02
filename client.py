import os

from openai import OpenAI

MODEL = "Qwen/Qwen2.5-7B-Instruct-AWQ"

_client = OpenAI(
    base_url=os.environ["WORKSHOP_SERVER_URL"],
    api_key=os.environ["WORKSHOP_API_KEY"],
)


def chat(prompt: str) -> str:
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    import sys

    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello!"
    print(chat(prompt))
