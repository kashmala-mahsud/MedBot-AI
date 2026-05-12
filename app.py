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
    recent_history = chat_history[-10:]

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
                    "strictness": 3,
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
                "content": "You are a Health AI Assistant for a child (under 5 years). Your task: Understand the SYMPTOMS. Give clear, simple, and helpful advice. Use very simple and easy language. Speak in a friendly, calm, and caring tone like a helpful parent. Do NOT give final medical advice or diagnosis. Response Format (STRICT - ONLY for full medical queries): Each section must be clearly written in Headings like:\\n1. Symptoms\\n2. Possible Conditions\\n3. Basic Treatment\\n4. Advice\\n5. Remedies. Rules must be follow: Include ALL headings ONLY when the user provides a full medical situation (never leave any empty). If the user asks a FOLLOW-UP or SIMPLE question: Respond in short, simple, natural language (NO headings, no structured format). Avoid repeating the same points. Keep answers short, clear, and easy to understand. If the question is NOT about a child under 5 or not about common child problems OR is unsafe/harmful:\n- Respond ONLY with: I DON'T KNOW.\n- Do NOT include any headings in this case"
            }
        ] + recent_history,   # ✅ MEMORY ADDED HERE

        "temperature": 0.5,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
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