from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

app = Flask(__name__)

# 🧠 Memory
chat_history = []

# Azure OpenAI Configuration
APIM_URL = os.getenv("APIM_URL")
DEPLOYMENT = os.getenv("GPT4O_DEPLOYMENT")
API_VERSION = os.getenv("APIM_API_VERSION")
SUB_KEY = os.getenv("APIM_SUB_KEY")

url = f"{APIM_URL}/deployments/{DEPLOYMENT}/chat/completions?api-version={API_VERSION}"

headers = {
    "Content-Type": "application/json",
    "api-key": SUB_KEY   # (keeping same as you requested)
}


def get_chatbot_response(user_message):
    global chat_history

    # 👉 Add user message to memory
    chat_history.append({
        "role": "user",
        "content": user_message
    })

    # 👉 Keep last 10 messages only
    recent_history = [
    {
        "role": msg["role"],
        "content": str(msg["content"])[:1500]
    }
    for msg in chat_history[-6:]
]

    payload = {
        "data_sources": [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": os.getenv("SEARCH_ENDPOINT"),
                    "index_name": os.getenv("SEARCH_INDEX"),
                    "semantic_configuration": "default",
                    "query_type": "vector_simple_hybrid",
                    "in_scope": True,
                    "strictness": 2,
                    "top_n_documents": 5,
                    "authentication": {
                        "type": "api_key",
                        "key": os.getenv("SEARCH_KEY")
                    },
                    "embedding_dependency": {
                        "type": "deployment_name",
                        "deployment_name": os.getenv("EMBEDDING_DEPLOYMENT")
                    }
                }
            }
        ],

        "messages": [
            {
                "role": "system",
                "content": """
You are a Health AI Assistant for a child under 5 years old.

Your task:
- Understand the child's symptoms.
- Give clear, simple, and helpful basic treatment.
- Use very simple and easy English.
- Speak in a friendly, calm, and caring tone like a helpful parent.
- Do NOT give final medical advice or diagnosis.

STRICT Response Rules:

1. Use headings ONLY when the user gives a full medical situation with symptoms.
   Never leave any heading empty.

   Use these headings:
   1. Symptoms
   2. Possible Conditions
   3. Basic Treatment

2. At the end, ask:
   "If you want, I can also share simple advice and home remedies."

   If the user wants, then provide:
   - Advice
   - Remedies

3. Keep each section SHORT:
   - Maximum 2–4 bullet points OR 1 very short paragraph.
   - Avoid long explanations.
   - Avoid repeating information.
   - Maximum 3 basic treatment points only.

4. If the child may have more than one condition or multiple symptoms with different treatments,
ALWAYS use this markdown table format:

| S.No | Condition/Symptom | Basic Treatment |
|------|-------------------|-----------------|
| 1 | Fever | Paracetamol may help |

5. If the user asks a FOLLOW-UP or SIMPLE question:
   - Respond in short, simple, clear, and natural language.
   - Do NOT use headings.
   - Do NOT use structured format.

6. If the question:
   - is NOT about a child under 5,
   - is NOT about common child problems,
   - OR asks for harmful, illegal, or dangerous actions to perform intentionally,

   Respond ONLY with:
   I DON'T KNOW.

7. Do NOT include any headings when responding with:
   I DON'T KNOW.
"""
            }
        ] + recent_history,   # ✅ MEMORY ADDED HERE

        "temperature": 0.5,
        "max_tokens": 800
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        response_data = response.json()
        assistant_message = response_data['choices'][0]['message']['content']

        # 👉 Save bot response in memory
        chat_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/')
def index():
    return render_template('chat.html')


@app.route('/get', methods=['POST'])
def get_response():
    user_message = request.form.get('msg', '').strip()

    if not user_message:
        return "Please enter a message", 400

    bot_response = get_chatbot_response(user_message)
    return bot_response


# Optional: clear memory
@app.route('/clear', methods=['POST'])
def clear_chat():
    global chat_history
    chat_history = []
    return "Chat cleared"


if __name__ == '__main__':
    app.run()