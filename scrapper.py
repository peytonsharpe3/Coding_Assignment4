import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import urljoin

# --- Configuration ---
ENDPOINT = "https://cdong1--azure-proxy-web-app.modal.run"
API_KEY = "supersecretkey"
MODEL = "gpt-4o"

RAW_FILE = "raw_blob.txt"
STRUCTURED_FILE = "structured.json"

# 1) Collector
BASE_URL = "https://quotes.toscrape.com/"

def simple_collect():
    """
    Scrape the homepage (first page) of quotes.toscrape.com
    Returns a list of dicts: {text, author, author_url, tags}
    """
    r = requests.get(BASE_URL)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    records = []
    for item in soup.select("div.quote"):
        text = item.select_one("span.text").get_text(strip=True)
        author = item.select_one("small.author").get_text(strip=True)
        # author page is in the <a href="/author/..."> inside the quote block
        author_rel = item.select_one("a")["href"]
        author_url = urljoin(BASE_URL, author_rel)
        tags = [t.get_text(strip=True) for t in item.select(".tags a.tag")]

        records.append({
            "text": text,
            "author": author,
            "author_url": author_url,
            "tags": tags
        })
    return records


def collect_all_pages(start_url=BASE_URL, max_pages=None):
    """
    Scrape all pages by following the 'Next' pagination link.
    - start_url: initial page to start from
    - max_pages: optional cap on number of pages to fetch (None => no cap)
    Returns a list of dicts like simple_collect().
    """
    url = start_url
    records = []
    pages_fetched = 0

    while url:
        r = requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select("div.quote"):
            text = item.select_one("span.text").get_text(strip=True)
            author = item.select_one("small.author").get_text(strip=True)
            author_rel = item.select_one("a")["href"]
            author_url = urljoin(BASE_URL, author_rel)
            tags = [t.get_text(strip=True) for t in item.select(".tags a.tag")]

            records.append({
                "text": text,
                "author": author,
                "author_url": author_url,
                "tags": tags
            })

        pages_fetched += 1
        if max_pages and pages_fetched >= max_pages:
            break

        # Find the "Next" link (the site shows "* Next →")
        next_link = soup.select_one("li.next > a")
        if next_link and next_link.get("href"):
            url = urljoin(BASE_URL, next_link["href"])
        else:
            url = None

    return records

# 2) Structurer: call LLM to return JSON
def structure(records):
    client = OpenAI(base_url=ENDPOINT, api_key=API_KEY)
    prompt = (
        "Return ONLY a JSON array. For each input record, output an object with: "
        "text, author, author_url, tags"
    )
    msgs = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(records)}
    ]
    resp = client.chat.completions.create(model=MODEL, messages=msgs)
    return json.loads(resp.choices[0].message.content)

def main():
    # Collect
    raw = simple_collect()
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        for r in raw:
            f.write(json.dumps(r) + "\n")
    print(f"Saved raw data to {RAW_FILE} ({len(raw)} records)")

    # Structure
    structured = structure(raw)
    with open(STRUCTURED_FILE, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2)
    print(f"Saved structured JSON to {STRUCTURED_FILE}")

if __name__ == "__main__":
    main()