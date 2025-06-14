import requests
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from tqdm import tqdm

DISCOURSE_COOKIE = "sample-discourse-cookie"

session = requests.Session()
session.cookies.set("_t", DISCOURSE_COOKIE, domain="discourse.onlinedegree.iitm.ac.in")
session.headers.update({"User-Agent": "Mozilla/5.0"})

BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"

OUTPUT_FILE = "tds_data.jsonl"

def scrape_course_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://tds.s-anand.net/#/2025-01/")
        page.wait_for_timeout(5000)  # wait for JS content to load

        # Get all content inside the main container
        content = page.locator("main").inner_text()
        browser.close()

        return {
            "type": "course",
            "url": "https://tds.s-anand.net/#/2025-01/",
            "text": content
        }

def fetch(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return resp
def get_topic_ids(category_slug="courses/tds-kb", category_id=34):
    topics = []
    for page in tqdm(range(0, 20)):
        url = f"{BASE_URL}/c/{category_slug}/{category_id}.json?page={page}"
        r = session.get(url)
        if r.status_code != 200:
            break
        data = r.json()
        new_topics = data["topic_list"]["topics"]
        if not new_topics:
            break
        topics.extend(new_topics)
    return topics

def get_posts_in_topic(topic_id):
    r = session.get(f"{BASE_URL}/t/{topic_id}.json")
    if r.status_code != 200:
        return []
    data = r.json()
    return [
        {
            "username": post["username"],
            "created_at": post["created_at"],
            "content": BeautifulSoup(post["cooked"], "html.parser").get_text(),
            "post_url": f"{BASE_URL}/t/{topic_id}/{post['post_number']}"
        }
        for post in data["post_stream"]["posts"]
    ]

def main():
    data = []
    print("🔄 Scraping course content...")
    data.append(scrape_course_page())

    with open(OUTPUT_FILE, "w") as f:
        for rec in data:
            f.write(json.dumps(rec) + "\n")
    print(f"✅ Saved {len(data)} records to {OUTPUT_FILE}")

    all_posts = []
    topics = get_topic_ids()

    for topic in tqdm(topics):
        created_at = datetime.fromisoformat(topic["created_at"].replace("Z", "+00:00"))
        if datetime(2025, 1, 1, tzinfo=timezone.utc) <= created_at <= datetime(2025, 4, 14, tzinfo=timezone.utc):
            posts = get_posts_in_topic(topic["id"])
            all_posts.extend(posts)

    with open("tds_discourse_posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2, ensure_ascii=False)

    print(f"Scraped {len(all_posts)} posts.")

if __name__ == "__main__":
    main()
