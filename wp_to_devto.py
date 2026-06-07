#!/usr/bin/env python3
"""
wp_to_devto.py
--------------
Fetch an already-published WordPress post and cross-post a teaser to Dev.to.
Claude generates the Markdown teaser; the canonical_url points back to WordPress
so there is no duplicate-content penalty.

Usage:
    python wp_to_devto.py --url "https://yoursite.com/your-post-slug/"
    python wp_to_devto.py --post-id 42
    python wp_to_devto.py --url "..." --keyword "your focus keyword" 
    python wp_to_devto.py --url "..." --dry-run

Requirements (pip install):
    anthropic requests python-dotenv

.env keys needed:
    ANTHROPIC_API_KEY   — https://console.anthropic.com/
    DEVTO_API_KEY       — https://dev.to/settings/extensions
    WP_SITE_URL         — e.g. https://yoursite.com  (no trailing slash)
    WP_USERNAME         — WordPress username (for private/draft posts; optional for public)
    WP_APP_PASSWORD     — WordPress Application Password (optional for public posts)
"""

import argparse
import os
import re
import sys

import requests
from dotenv import load_dotenv
import anthropic

load_dotenv()

# ── env ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEVTO_API_KEY     = os.getenv("DEVTO_API_KEY")
WP_SITE_URL       = os.getenv("WORDPRESS_URL", "").rstrip("/")
WP_USERNAME       = os.getenv("WORDPRESS_USERNAME", "")
WP_APP_PASSWORD   = os.getenv("WORDPRESS_APP_PASSWORD", "")


# ── WordPress helpers ─────────────────────────────────────────────────────────

def _wp_auth():
    """Return requests auth tuple if credentials are provided, else None."""
    if WP_USERNAME and WP_APP_PASSWORD:
        return (WP_USERNAME, WP_APP_PASSWORD)
    return None


def fetch_post_by_id(post_id: int) -> dict:
    """Fetch a WordPress post via the REST API using its numeric ID."""
    if not WP_SITE_URL:
        sys.exit("❌  WP_SITE_URL is not set in .env")

    url = f"{WP_SITE_URL}/wp-json/wp/v2/posts/{post_id}"
    print(f"🔍  Fetching WordPress post #{post_id} …")
    resp = requests.get(url, auth=_wp_auth(), timeout=20)

    if resp.status_code == 404:
        sys.exit(f"❌  Post #{post_id} not found (404). Check the ID.")
    resp.raise_for_status()
    return resp.json()


def fetch_post_by_slug(post_url: str) -> dict:
    """
    Fetch a WordPress post by its full URL.
    Extracts the slug from the URL, then queries the REST API.
    """
    if not WP_SITE_URL:
        sys.exit("❌  WP_SITE_URL is not set in .env")

    # Derive slug — last non-empty path segment
    slug = [s for s in post_url.rstrip("/").split("/") if s][-1]
    api_url = f"{WP_SITE_URL}/wp-json/wp/v2/posts?slug={slug}"
    print(f"🔍  Fetching WordPress post with slug '{slug}' …")
    resp = requests.get(api_url, auth=_wp_auth(), timeout=20)
    resp.raise_for_status()

    posts = resp.json()
    if not posts:
        sys.exit(f"❌  No post found for slug '{slug}'. Is WP_SITE_URL correct?")
    return posts[0]


def extract_featured_image(post: dict) -> str | None:
    """Return the featured image URL from a WP post dict, or None."""
    try:
        embedded = post.get("_embedded", {})
        media    = embedded.get("wp:featuredmedia", [{}])
        return media[0].get("source_url")
    except (IndexError, KeyError, TypeError):
        return None


def fetch_post(url: str | None, post_id: int | None) -> dict:
    """High-level helper — fetch via ID or URL, always embed featured media."""
    if not WP_SITE_URL:
        sys.exit("❌  WP_SITE_URL is not set in .env")

    if post_id:
        api_url = f"{WP_SITE_URL}/wp-json/wp/v2/posts/{post_id}?_embed=1"
        print(f"🔍  Fetching WordPress post #{post_id} …")
        resp = requests.get(api_url, auth=_wp_auth(), timeout=20)
        if resp.status_code == 404:
            sys.exit(f"❌  Post #{post_id} not found.")
        resp.raise_for_status()
        return resp.json()

    if url:
        slug    = [s for s in url.rstrip("/").split("/") if s][-1]
        api_url = f"{WP_SITE_URL}/wp-json/wp/v2/posts?slug={slug}&_embed=1"
        print(f"🔍  Fetching WordPress post with slug '{slug}' …")
        resp    = requests.get(api_url, auth=_wp_auth(), timeout=20)
        resp.raise_for_status()
        posts   = resp.json()
        if not posts:
            sys.exit(f"❌  No post found for slug '{slug}'.")
        return posts[0]

    sys.exit("❌  Provide --url or --post-id")


# ── Claude summary ────────────────────────────────────────────────────────────

def generate_devto_summary(title: str, keyword: str, article_html: str, canonical_url: str) -> str:
    """
    Use Claude to generate a Dev.to-friendly Markdown teaser for the article.
    """
    print("   ✍️   Generating Dev.to summary with Claude …")

    client     = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    clean_text = re.sub(r"<[^>]+>", " ", article_html)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    excerpt    = clean_text[:1500]

    prompt = f"""Write a Dev.to post that teases this article without reproducing it fully.

Article title: {title}
Primary keyword: {keyword}
Article excerpt: {excerpt}
Canonical URL: {canonical_url}

REQUIREMENTS:
- Length: 200-300 words of original body content
- Format: Markdown (Dev.to renders it natively)
- Tone: Practical, developer/SaaS-founder friendly — no fluff
- Cover: the core problem the article addresses and 2-3 key takeaways
- End with a clear CTA linking to the full article using the canonical URL
- Do NOT reproduce the full article — this is a teaser to drive traffic back
- Use the exact keyword phrase "{keyword}" once naturally
- Tags line at the very end (not part of body): suggest 4 relevant dev.to tags

STRUCTURE:
## [Engaging hook headline — reuse or rephrase the article title]

[2-3 short paragraphs covering the problem and key takeaways]

**👉 Read the full breakdown: [article title]({canonical_url})**

---
TAGS: tag1, tag2, tag3, tag4

Return only the Markdown — no preamble, no explanation."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        body = message.content[0].text.strip()
        print(f"   ✅  Summary generated ({len(body)} chars)")
        return body
    except Exception as exc:
        print(f"   ⚠️   Claude error: {exc} — using fallback teaser")
        return (
            f"## {title}\n\n"
            f"Looking for the best {keyword}? We broke it all down in our latest post.\n\n"
            f"**👉 Read the full breakdown: [{title}]({canonical_url})**\n\n"
            f"---\nTAGS: saas, software, productivity, reviews"
        )


# ── Dev.to publisher ──────────────────────────────────────────────────────────

def parse_tags_from_body(markdown_body: str) -> tuple[str, list[str]]:
    """
    Extract the TAGS line Claude appends, return (clean_body, tags_list).
    Falls back to sensible defaults if no TAGS line is found.
    """
    default_tags = ["saas", "software", "productivity", "reviews"]
    lines        = markdown_body.strip().splitlines()
    tags         = default_tags

    for i, line in enumerate(lines):
        if line.strip().upper().startswith("TAGS:"):
            raw  = line.split(":", 1)[1]
            parsed = [t.strip().lower().replace(" ", "") for t in raw.split(",") if t.strip()][:4]
            if parsed:
                tags = parsed
            # Drop the TAGS line and any immediately preceding "---" separator
            clean_lines = [l for l in lines[:i] if l.strip() != "---"]
            return "\n".join(clean_lines).strip(), tags

    return markdown_body, tags


def post_to_devto(
    title: str,
    keyword: str,
    article_html: str,
    canonical_url: str,
    cover_image_url: str | None = None,
    dry_run: bool = False,
) -> bool:
    """
    Generate a teaser and publish it to Dev.to.
    Pass dry_run=True to print the payload without actually posting.
    """
    if not DEVTO_API_KEY and not dry_run:
        print("   ⚠️   DEVTO_API_KEY missing — skipping Dev.to publish")
        return False

    print("   📤  Preparing Dev.to post …")

    markdown_body          = generate_devto_summary(title, keyword, article_html, canonical_url)
    clean_body, tags       = parse_tags_from_body(markdown_body)

    payload: dict = {
        "article": {
            "title":         title,
            "published":     True,
            "body_markdown": clean_body,
            "canonical_url": canonical_url,
            "tags":          tags,
        }
    }
    if cover_image_url:
        payload["article"]["main_image"] = cover_image_url

    if dry_run:
        print("\n── DRY RUN — payload that would be sent to Dev.to ─────────────────")
        import json
        print(json.dumps(payload, indent=2))
        print("────────────────────────────────────────────────────────────────────\n")
        return True

    try:
        resp = requests.post(
            "https://dev.to/api/articles",
            headers={"api-key": DEVTO_API_KEY, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            devto_url = resp.json().get("url", "")
            print(f"   ✅  Posted to Dev.to successfully")
            print(f"   🔗  Dev.to URL: {devto_url}")
            return True
        else:
            print(f"   ❌  Dev.to error {resp.status_code}: {resp.text[:400]}")
            return False
    except Exception as exc:
        print(f"   ❌  Dev.to request failed: {exc}")
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cross-post an existing WordPress article to Dev.to via Claude."
    )
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--url",     metavar="URL",     help="Full URL of the WordPress post")
    source.add_argument("--post-id", metavar="ID", type=int, help="WordPress numeric post ID")

    p.add_argument(
        "--keyword",
        metavar="KEYWORD",
        default="",
        help="SEO focus keyword (defaults to the post's first tag or title)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the teaser and print the payload without publishing",
    )
    return p


def main():
    args   = build_parser().parse_args()
    post   = fetch_post(url=args.url, post_id=args.post_id)

    title         = post.get("title", {}).get("rendered", "Untitled")
    article_html  = post.get("content", {}).get("rendered", "")
    canonical_url = post.get("link", args.url or "")
    cover_image   = extract_featured_image(post)

    # Derive keyword: CLI flag → first WP tag name → post title
    keyword = args.keyword.strip()
    if not keyword:
        try:
            embedded_terms = post.get("_embedded", {}).get("wp:term", [[]])[0]
            keyword        = embedded_terms[0].get("name", title) if embedded_terms else title
        except (IndexError, KeyError, TypeError):
            keyword = title

    print(f"\n📰  Title        : {title}")
    print(f"🔑  Keyword      : {keyword}")
    print(f"🔗  Canonical URL: {canonical_url}")
    print(f"🖼️   Cover image  : {cover_image or 'none'}\n")

    ok = post_to_devto(
        title=title,
        keyword=keyword,
        article_html=article_html,
        canonical_url=canonical_url,
        cover_image_url=cover_image,
        dry_run=args.dry_run,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
