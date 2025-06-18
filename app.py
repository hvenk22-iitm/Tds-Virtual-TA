from dotenv import load_dotenv
load_dotenv()
import os
import json
import re
import requests
import traceback
from flask import Flask, request, jsonify
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from flask_cors import CORS

# ==== Configuration ====
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://aiproxy.sanand.workers.dev/openai"

# ==== Setup ====
app = Flask(__name__)
CORS(app)
embedding = OpenAIEmbeddings(model="text-embedding-3-small", 
                             base_url="https://aiproxy.sanand.workers.dev/openai/v1",
                             api_key=API_KEY)
db = FAISS.load_local("tds_faiss_index", embeddings=embedding, allow_dangerous_deserialization=True)

# ==== Utilities ====

def get_top_k_docs(query, k=4):
    return db.similarity_search(query, k=k)

def build_prompt(question, docs):
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Enhanced prompt for better responses
    prompt = f"""You are a helpful Teaching Assistant for the Tools for Data Science (TDS) course. 
Answer the user's question using the provided context. Be specific and direct in your response.

Context:
{context}

Question: {question}

"""
    return prompt

def prepare_image_part(image_b64):
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/webp;base64,{image_b64}"
        }
    }
def normalize_url_to_topic_id(url, topic_id):
    """Replace the last number in the URL path with the topic_id."""
    return re.sub(r'/\d+/?$', f'/{topic_id}', url)

def extract_json_from_answer(answer_text):
    # Find content inside ```json ... ```
    match = re.search(r"```json\s*(\{.*?\})\s*```", answer_text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return parsed.get("answer", answer_text), parsed.get("links", [])
        except json.JSONDecodeError:
            pass  
    return answer_text.strip(), []

def call_gpt_api(prompt, image_b64=None):
    messages = [
        {"role": "system", "content": "You are a knowledgeable Teaching Assistant for the Tools for Data Science (TDS) course. Provide clear, specific answers based on the context provided."},
    ]
    
    if image_b64:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                prepare_image_part(image_b64)
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": prompt
        })
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers=headers,
        json={
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.1  # Lower temperature for more consistent responses
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"AIPipe error {response.status_code}: {response.text}")
    
    json_response = response.json()
    return json_response["choices"][0]["message"]["content"]



# ==== API Endpoint ====

@app.route("/api", methods=["POST"])
def handle_api():
    try:
        data = request.get_json()
        question = data.get("question")
        image_b64 = data.get("image")
        
        if not question:
            return jsonify({"error": "Missing question field"}), 400
        
        # Regular processing
        docs = get_top_k_docs(question)
        prompt = build_prompt(question, docs)
        
        answer = call_gpt_api(prompt, image_b64=image_b64)
        
        # Extract and collect all unique URLs from retrieved documents
        links = []
        
        for doc in docs:
            url = doc.metadata.get("url", "")
            print(url)
            if url:
                links.append({
                    "url": url,
                    "text": doc.page_content[:120].strip()
                })
        final_answer, embedded_links = extract_json_from_answer(answer)

# Merge links (without duplicates)
        link_urls = {link["url"] for link in links}
        for elink in embedded_links:
            if elink.get("url") not in link_urls:
                links.append(elink)

        return jsonify({
            "answer": answer.strip(),
            "links": links
        })
        
    except Exception as e:
        traceback.print_exc()  
        app.logger.exception("Exception occurred")
        return jsonify({"error": str(e)}), 500

# ==== Run Server ====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)