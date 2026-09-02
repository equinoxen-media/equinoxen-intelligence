"""
find_duplicate_slugs.py — scan every post for a WordPress auto-generated
numeric slug suffix (-2, -3, etc.), the kind WordPress appends on its own
when a new post's slug collides with an existing one. Each match is a
candidate duplicate pair worth checking, the same pattern that turned up
best-crm-small-business-2026 / best-crm-small-business-2026-2.

Deliberately does NOT flag slugs ending in a 4-digit year (...2026, ...2025),
those are intentional, not WordPress collision suffixes. Only 1-2 digit
trailing numbers count, since that's what WordPress's own auto-increment
actually produces (-2, -3, -4, ... never a 4-digit number).

USAGE:
  python3 find_duplicate_slugs.py
"""

import re
import requests
from content_pipeline import WP_URL, WP_USER, WP_PASS


def fetch_all_posts():
    posts = []
    page = 1
    while True:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            auth=(WP_USER, WP_PASS),
            params={"per_page": 100, "page": page, "status": "any", "context": "edit"},
        )
        if response.status_code != 200:
            break
        batch = response.json()
        if not batch:
            break
        posts.extend(batch)
        page += 1
    return posts


def main():
    print("📋 Fetching all posts from WordPress...")
    posts = fetch_all_posts()
    print(f"   Found {len(posts)} total posts\n")

    # Only 1-2 digit trailing numbers, e.g. -2, -3, -15, never a 4-digit
    # year, which is intentional and appears throughout this site's slugs.
    numbered = []
    for post in posts:
        slug = post.get("slug", "")
        match = re.search(r'^(.+)-(\d{1,2})$', slug)
        if match:
            numbered.append({
                "id": post["id"],
                "slug": slug,
                "base_slug": match.group(1),
                "suffix": match.group(2),
                "title": post.get("title", {}).get("rendered", ""),
                "link": post.get("link", ""),
                "status": post.get("status", ""),
            })

    if not numbered:
        print("✅ No WordPress collision-suffix slugs found sitewide")
        return

    print(f"⚠️  Found {len(numbered)} post(s) with a WordPress collision-suffix slug:")
    print("=" * 70)

    for item in numbered:
        print(f"\n  📄 {item['title']}")
        print(f"     Post ID: {item['id']}  |  Status: {item['status']}")
        print(f"     Slug: {item['slug']}")
        print(f"     URL: {item['link']}")
        print(f"     Likely base slug: {item['base_slug']}  (check if a post exists at this exact slug too)")

    print("\n" + "=" * 70)
    print(f"💡 For each of the {len(numbered)} above: check whether a post exists at the")
    print("   base slug (with or without a year suffix), open both, and confirm")
    print("   real content overlap before deciding to redirect one into the other.")
    print("   Don't assume overlap just from the slug pattern, some may be")
    print("   legitimately different articles that happened to collide once.")


if __name__ == "__main__":
    main()
