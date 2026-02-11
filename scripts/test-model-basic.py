#!/usr/bin/env python3
"""Quick model test to see if basic inference works"""

from llama_cpp import Llama
from pathlib import Path

model_path = Path("/home/kang/Documents/projects/radkit/eraserhead/models/llama-cpp/qwen2.5-coder-0.5b-instruct-q4_k_m.gguf")

print(f"Loading model: {model_path.name}")

llm = Llama(
    model_path=str(model_path),
    n_ctx=2048,
    n_threads=4,
    verbose=True,
)

print("\n--- Test 1: Simple completion ---")
response = llm(
    "def add(a, b):",
    max_tokens=50,
    temperature=0.1,
    stop=["\n\n"],
)
print(f"Generated: {response['choices'][0]['text']}")

print("\n--- Test 2: Chat completion ---")
response = llm.create_chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful Python coding assistant."},
        {"role": "user", "content": "Write a Python function that adds two numbers."},
    ],
    max_tokens=100,
    temperature=0.1,
)
print(f"Generated: {response['choices'][0]['message']['content']}")
