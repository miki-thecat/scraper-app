import requests
import sys
import time
from threading import Thread
from app import create_app

def run_server():
    app = create_app()
    app.run(port=5001, use_reloader=False)

def verify():
    base_url = "http://localhost:5000"

    # Wait for server to start
    time.sleep(2)

    print("Verifying Virtual News Site...")
    try:
        # 1. Check Virtual News Index
        resp = requests.get(f"{base_url}/virtual-news/")
        if resp.status_code == 200 and "Virtual News" in resp.text:
            print("[OK] Virtual News Index")
        else:
            print(f"[FAIL] Virtual News Index: {resp.status_code}")
            sys.exit(1)

        # 2. Check Virtual News Article
        resp = requests.get(f"{base_url}/virtual-news/article/1")
        if resp.status_code == 200 and "AIエージェント" in resp.text:
            print("[OK] Virtual News Article")
        else:
            print(f"[FAIL] Virtual News Article: {resp.status_code}")
            sys.exit(1)

        # 4. Check Scraping (via API or internal function)
        # I'll use the internal function to verify scraping logic without auth issues
        from app.services import articles
        from app import create_app
        app = create_app()
        with app.app_context():
            print("Verifying Scraper Logic...")
            url = f"{base_url}/virtual-news/article/1"

            try:
                result = articles.ingest_article(url, run_ai=False)
                if result.article.title == "【速報】AIエージェント、驚異的な進化を遂げる":
                    print("[OK] Scraper Ingestion")
                else:
                    print(f"[FAIL] Scraper Ingestion: Title mismatch - {result.article.title}")
            except Exception as e:
                print(f"[FAIL] Scraper Ingestion: {e}")

    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
