import json

def load_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line.strip()) for line in f]

# Load files
course_data = load_jsonl("tds_course.jsonl")
discourse_data = load_jsonl("tds_discourse_posts.jsonl")

combined = []

for course in course_data:
    combined.append({
        "text": course.get("content") or course.get("text") or course.get("markdown"),
        "source": course["url"],
        "type": "course"
    })

for post in discourse_data:
    combined.append({
        "text": post["content"],
        "source": post["url"],
        "type": "discourse"
    })

# Save to single JSON
with open("tds_combined.json", "w", encoding="utf-8") as f:
    json.dump(combined, f, indent=2, ensure_ascii=False)

print(f"✅ Combined {len(combined)} entries into tds_combined.json")
