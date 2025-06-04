import os
import json

from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENROUTER_API_KEY"):
    raise ValueError("OPENROUTER_API_KEY environment variable is required")

client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"))


def call_model(messages, model, temperature=0.5, **kwargs):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            **kwargs
        )

        if not response.choices:
            raise ValueError("No response choices returned from AI model")

        response_message = response.choices[0].message
        return response_message

    except Exception as e:
        # Log the error for debugging
        print(f"Error calling AI model: {e}")
        raise
