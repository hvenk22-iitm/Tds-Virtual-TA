import json
from openai import OpenAI
from sentence_transformers.util import cos_sim
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
import tiktoken

# Initialize OpenAI via AIPipe proxy (set your token here)
import os
os.environ["OPENAI_API_KEY"] = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjIwMDEzOThAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.xwfjOlApCo0IL_qDnA9GePxB_2MkGhQAiZu4Ut_vCWU"
os.environ["OPENAI_API_BASE"] = "https://aiproxy.sanand.workers.dev/openai/v1/"

def load_jsonl(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def load_all_data():
    course = load_jsonl("tds_course.jsonl")
    discourse = load_jsonl("tds_discourse_posts.jsonl")
    return course + discourse

def to_documents(data):
    docs = []
    for item in data:
        content = item.get("content") or item.get("text")
        metadata = {"url": item.get("url")}
        if content:
            docs.append(Document(page_content=content, metadata=metadata))
    return docs

def build_faiss():
    all_data = load_all_data()
    documents = to_documents(all_data)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_base=os.environ["OPENAI_API_BASE"])
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local("tds_faiss_index")

    print(f"✅ Saved FAISS index with {len(chunks)} chunks")

if __name__ == "__main__":
    build_faiss()
