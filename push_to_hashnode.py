import os
import re
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIGURATION ────────────────────────────────────────────
HASHNODE_API_KEY        = os.getenv("HASHNODE_API_KEY")
HASHNODE_PUBLICATION_ID = os.getenv("HASHNODE_PUBLICATION_ID")
WP_URL                  = os.getenv("WORDPRESS_URL")
WP_USER                 = os.getenv("WORDPRESS_USERNAME")
WP_PASS                 = os.getenv("WORDPRESS_APP_PASSWORD")
SITE_URL                = "https://equinoxen.com"
ANTHROPIC_API_KEY       = os.getenv("ANTHROPIC_API_KEY")

# ─── FETCH WORDPRESS POST ─────────────────────────────────────
def fetch_wp_post(post_id=None, slug=None):
    """Fetch a single WordPress post by ID or slug"""
    try:
        if post_id:
            url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
            response = requests.get(url, auth=(WP_USER, WP_PASS))
        elif slug:
            url = f"{WP_URL}/wp-json/wp/v2/posts"
            response = requests.get(url, auth=(WP_USER, WP_PASS), params={"slug": slug})
        else:
            print("❌ Provide a post_id or slug")
            return None

        if response.status_code != 200:
            print(f"❌ WordPress fetch failed: {response.status_code}")
            return None

        data = response.json()
        post = data if post_id else (data[0] if data else None)

        if not post:
            print("❌ Post not found")
            return None

        print(f"✅ Fetched: {post['title']['rendered']}")
        return post

    except Exception as e:
        print(f"❌ WordPress error: {e}")
        return None


def fetch_recent_wp_posts(count=5):
    """Fetch most recent WordPress posts"""
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            auth=(WP_USER, WP_PASS),
            params={"per_page": count, "orderby": "date", "order": "desc"}
        )
        if response.status_code == 200:
            posts = response.json()
            print(f"✅ Fetched {len(posts)} recent posts")
            return posts
        return []
    except Exception as e:
        print(f"❌ Error fetching posts: {e}")
        return []


# ─── STRIP HTML TO MARKDOWN ───────────────────────────────────
def html_to_plain_text(html):
    """Strip HTML tags to plain text for summary generation"""
    # Remove script/style blocks
    html = re.sub(r'<(script|style)[^>]*>.*?</(script|style)>', '', html, flags=re.DOTALL)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:3000]  # Limit for Claude prompt


# ─── GENERATE HASHNODE SUMMARY VIA CLAUDE ────────────────────
def generate_hashnode_summary(title, keyword, excerpt, post_url, article_text):
    """Generate a 400-500 word markdown summary for Hashnode"""
    import anthropic

    print("   ✍️  Generating Hashnode summary with Claude...")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Write a 400-500 word summary article for Hashnode based on this content.

Original title: {title}
Primary keyword: {keyword}
Full article URL: {post_url}
Article excerpt: {excerpt}
Article content (truncated): {article_text}

Requirements:
- Write in plain markdown — no HTML
- Start with a compelling hook paragraph
- Summarise the key points in 3-4 paragraphs
- Do NOT reproduce the full article — this is a teaser that drives traffic back
- End with this exact call to action on its own line:
  "Read the full review at [Equinoxen Media]({post_url})"
- Tone: expert, helpful, never salesy
- No markdown headers — just flowing paragraphs
- Do not include a title line — just the body text

Write the summary now:"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        summary = message.content[0].text.strip()
        print(f"   ✅ Summary generated ({len(summary)} chars)")
        return summary
    except Exception as e:
        print(f"   ⚠️  Claude error: {e}")
        return f"{excerpt}\n\nRead the full review at [Equinoxen Media]({post_url})"


# ─── PUSH TO HASHNODE ─────────────────────────────────────────
def push_to_hashnode(title, summary_markdown, post_url, keyword, debug=False):
    """Push a post to Hashnode via GraphQL API"""

    if not HASHNODE_API_KEY or not HASHNODE_PUBLICATION_ID:
        print("❌ HASHNODE_API_KEY or HASHNODE_PUBLICATION_ID missing in .env")
        return False

    print(f"   📤 Pushing to Hashnode: {title}")

    query = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post {
          id
          url
          title
        }
      }
    }
    """

    variables = {
        "input": {
            "title": title,
            "publicationId": HASHNODE_PUBLICATION_ID,
            "contentMarkdown": f"{summary_markdown}",
            "originalArticleURL": post_url,
            "tags": [],
            "metaTags": {
                "title": title,
                "description": f"Expert {keyword} review and analysis. Read the full breakdown at Equinoxen Media.",
            },
        }
    }

    # Try with and without Bearer prefix
    for auth_format in [HASHNODE_API_KEY, f"Bearer {HASHNODE_API_KEY}"]:
        try:
            response = requests.post(
                "https://gql.hashnode.com/",
                headers={
                    "Authorization": auth_format,
                    "Content-Type": "application/json"
                },
                json={"query": query, "variables": variables},
                timeout=30
            )

            if debug:
                print(f"   🔍 Status: {response.status_code}")
                print(f"   🔍 Response: {response.text[:500]}")

            if response.status_code == 200 and response.text.strip():
                data = response.json()
                errors = data.get("errors")
                if errors:
                    print(f"   ❌ Hashnode GraphQL error: {errors[0].get('message', errors)}")
                    continue

                post_data = data.get("data", {}).get("publishPost", {}).get("post", {})
                hashnode_url = post_data.get("url", "")
                print(f"   ✅ Hashnode posted: {hashnode_url}")
                return hashnode_url

            elif response.status_code == 200 and not response.text.strip():
                print(f"   ⚠️  Empty response with auth format: {auth_format[:20]}... trying next")
                continue
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text[:200]}")
                continue

        except Exception as e:
            print(f"   ❌ Request error: {e}")
            continue

    print("   ❌ All auth formats failed — check your HASHNODE_API_KEY and HASHNODE_PUBLICATION_ID")
    return False


# ─── TEST HASHNODE CONNECTION ─────────────────────────────────
def test_hashnode_connection():
    """Test API key and publication ID are valid"""
    print("\n🔍 Testing Hashnode connection...")

    if not HASHNODE_API_KEY:
        print("❌ HASHNODE_API_KEY not set in .env")
        return False

    if not HASHNODE_PUBLICATION_ID:
        print("❌ HASHNODE_PUBLICATION_ID not set in .env")
        return False

    query = """
    query GetPublication($id: ObjectId!) {
      publication(id: $id) {
        id
        title
        url
      }
    }
    """

    for auth_format in [HASHNODE_API_KEY, f"Bearer {HASHNODE_API_KEY}"]:
        try:
            response = requests.post(
                "https://gql.hashnode.com/",
                headers={
                    "Authorization": auth_format,
                    "Content-Type": "application/json"
                },
                json={
                    "query": query,
                    "variables": {"id": HASHNODE_PUBLICATION_ID}
                },
                timeout=15
            )

            print(f"   Auth format: {auth_format[:30]}...")
            print(f"   Status: {response.status_code}")

            if response.status_code == 200 and response.text.strip():
                data = response.json()
                errors = data.get("errors")
                if errors:
                    print(f"   ❌ Error: {errors[0].get('message')}")
                    continue

                pub = data.get("data", {}).get("publication", {})
                if pub:
                    print(f"   ✅ Connected to publication: {pub.get('title')} ({pub.get('url')})")
                    print(f"   ✅ Working auth format: {auth_format[:30]}...")
                    return auth_format
            else:
                print(f"   ⚠️  Response: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("❌ Could not connect to Hashnode — check credentials")
    return False


# ─── MAIN: PUSH SINGLE POST ───────────────────────────────────
def push_post(post_id=None, slug=None, debug=False):
    """Fetch a WordPress post and push it to Hashnode"""

    print("=" * 60)
    print("  EQUINOXEN → HASHNODE PUBLISHER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Fetch post
    post = fetch_wp_post(post_id=post_id, slug=slug)
    if not post:
        return False

    title = post["title"]["rendered"]
    post_url = post["link"]
    excerpt_html = post.get("excerpt", {}).get("rendered", "")
    excerpt = html_to_plain_text(excerpt_html)[:300]
    content_html = post.get("content", {}).get("rendered", "")
    article_text = html_to_plain_text(content_html)

    # Extract keyword from slug as best guess
    keyword = post.get("slug", "").replace("-", " ")

    print(f"\n📄 Title: {title}")
    print(f"   URL: {post_url}")
    print(f"   Keyword guess: {keyword}")

    # Generate summary
    summary = generate_hashnode_summary(title, keyword, excerpt, post_url, article_text)

    # Push to Hashnode
    print("\n📤 Pushing to Hashnode...")
    result = push_to_hashnode(title, summary, post_url, keyword, debug=debug)

    if result:
        print(f"\n✅ Done — {result}")
    else:
        print("\n❌ Push failed")

    return result


# ─── MAIN: PUSH RECENT POSTS ──────────────────────────────────
def push_recent_posts(count=5, debug=False):
    """Fetch and push the N most recent WordPress posts to Hashnode"""

    print("=" * 60)
    print(f"  EQUINOXEN → HASHNODE BULK PUBLISHER ({count} posts)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    posts = fetch_recent_wp_posts(count)
    if not posts:
        print("❌ No posts fetched")
        return

    results = []
    for i, post in enumerate(posts, 1):
        print(f"\n{'─'*60}")
        print(f"  POST {i} of {len(posts)}")
        print(f"{'─'*60}")

        title = post["title"]["rendered"]
        post_url = post["link"]
        excerpt_html = post.get("excerpt", {}).get("rendered", "")
        excerpt = html_to_plain_text(excerpt_html)[:300]
        content_html = post.get("content", {}).get("rendered", "")
        article_text = html_to_plain_text(content_html)
        keyword = post.get("slug", "").replace("-", " ")

        print(f"📄 {title}")
        print(f"   {post_url}")

        summary = generate_hashnode_summary(title, keyword, excerpt, post_url, article_text)
        result = push_to_hashnode(title, summary, post_url, keyword, debug=debug)

        results.append({
            "title": title,
            "wp_url": post_url,
            "hashnode_url": result if result else "FAILED"
        })

        if i < len(posts):
            print(f"\n⏳ Waiting 5 seconds...")
            import time
            time.sleep(5)

    # Summary
    print("\n" + "=" * 60)
    print("  BULK PUSH COMPLETE")
    print("=" * 60)
    success = [r for r in results if r["hashnode_url"] != "FAILED"]
    print(f"\n✅ {len(success)} of {len(results)} posts pushed successfully\n")
    for r in results:
        status = "✅" if r["hashnode_url"] != "FAILED" else "❌"
        print(f"  {status} {r['title'][:50]}")
        if r["hashnode_url"] != "FAILED":
            print(f"     {r['hashnode_url']}")


# ─── RUN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test connection: python3 push_to_hashnode.py test
        test_hashnode_connection()

    elif len(sys.argv) > 1 and sys.argv[1] == "recent":
        # Push recent posts: python3 push_to_hashnode.py recent 10
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        push_recent_posts(count=count, debug="--debug" in sys.argv)

    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        # Push by post ID: python3 push_to_hashnode.py 123
        push_post(post_id=int(sys.argv[1]), debug="--debug" in sys.argv)

    elif len(sys.argv) > 1:
        # Push by slug: python3 push_to_hashnode.py hubspot-crm-review
        push_post(slug=sys.argv[1], debug="--debug" in sys.argv)

    else:
        print("""
Usage:
  python3 push_to_hashnode.py test              — test API connection
  python3 push_to_hashnode.py 123               — push post by WordPress ID
  python3 push_to_hashnode.py hubspot-crm-review — push post by slug
  python3 push_to_hashnode.py recent 10         — push 10 most recent posts
  python3 push_to_hashnode.py recent 10 --debug — same with debug output
        """)
