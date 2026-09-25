import ollama

response = ollama.chat(
    model="llama3.2:3b",
    messages=[
        {
            "role": "user",
            "content": "What is an electrical substation? Explain in 3 simple sentences."
        }
    ]
)

print("\n--- Llama Response ---")
print(response["message"]["content"])