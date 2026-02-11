#!/usr/bin/env python3
"""
Implementation helper: Uses local llama.cpp models to generate code
This leverages the 0.5b model on port 8080 for fast iteration
"""
import requests
import json
import sys

MODEL_URL = "http://127.0.0.1:8080/v1/chat/completions"

def generate_code(prompt: str, max_tokens: int = 1024) -> str:
    """Generate code using local 0.5b model"""
    response = requests.post(
        MODEL_URL,
        json={
            "messages": [
                {"role": "system", "content": "You are a Python code generator for the EraserHead project. Use Harold persona (😐 emoji). Generate clean, well-documented code with Google-style docstrings and type hints."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "stream": False
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def main():
    if len(sys.argv) < 2:
        print("Usage: implement_forward_secrecy.py")
        return
    
    # Implementation based on Agent 1's plan
    print("😐 Generating ForwardSecrecyManager class...")
    
    code = generate_code("""Implement the ForwardSecrecyManager class for the EraserHead project:

Requirements:
- Use X25519 for ephemeral key exchange
- Generate 32-byte session IDs with secrets.token_bytes(32)
- Implement HKDF-SHA256 for key derivation with session binding
- Include timestamp in HKDF info string
- Use Google-style docstrings with Harold persona (😐 emoji)
- Type hints for all methods

Class signature:
```python
import secrets
import time
from dataclasses import dataclass
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

@dataclass
class SessionKeyPair:
    private_key: x25519.X25519PrivateKey
    public_key: bytes
    session_id: bytes

class ForwardSecrecyManager:
    def __init__(self):
        pass
    
    def generate_session_keypair(self) -> SessionKeyPair:
        pass
    
    def derive_shared_secret(self, our_private_key: x25519.X25519PrivateKey, their_public_key: bytes) -> bytes:
        pass
    
    def derive_session_master_key(self, shared_secret: bytes, session_id: bytes, context: str = "anemochory-session") -> bytes:
        pass
```

Generate the complete implementation with docstrings.""")
    
    print("\n" + "="*60)
    print(code)
    print("="*60)
    
    with open("/tmp/forward_secrecy_generated.py", "w") as f:
        f.write(code)
    print("\n✅ Generated code saved to /tmp/forward_secrecy_generated.py")

if __name__ == "__main__":
    main()
