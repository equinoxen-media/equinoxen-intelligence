"""
audit_claims.py — Equinoxen Media factual claims auditor

Pulls a published post, has Claude extract every specific factual claim
(pricing, plan limits, feature claims, employee-count thresholds, etc.),
then re-checks each claim against the live vendor site using real web
search (not Claude's training memory, which is how stale claims get
published in the first place).

This is a report-generating tool, not an auto-fixer. It never edits a
live WordPress post. A human reviews the flagged discrepancies and
decides what to change, same as the original AEO plan called for.

USAGE:
  python3 audit_claims.py --list                 List auditable posts
  python3 audit_claims.py <slug-or-post-id>       Audit one post
  python3 audit_claims.py --all [N]               Audit N most recent posts (default 20)

Requires content_pipeline.py in the same directory (reuses its WP
credentials, Anthropic key, and published_posts.json tracker).
"""

import os
import re
import sys
import json
import time
import requests
import anthropic
from datetime import datetime

from content_pipeline import (
    WP_URL, WP_USER, WP_PASS, ANTHROPIC_API_KEY,
    load_published_posts,
)

AUDIT_MODEL = "claude-sonnet-4-5"


# ─── FETCH POST CONTENT ────────────────────────────────────────
def fetch_post_content(post_id):
    """Pull the live title + rendered HTML content for a post by ID."""
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            auth=(WP_USER, WP_PASS),
            params={"context": "edit"},
        )
        if response.status_code != 200:
            print(f"   ❌ Could not fetch post {post_id}: {response.status_code}")
            return None, None
        data = response.json()
        title = data.get("title", {}).get("raw") or data.get("title", {}).get("rendered", "")
        content = data.get("content", {}).get("raw") or data.get("content", {}).get("rendered", "")
        return title, content
    except Exception as e:
        print(f"   ❌ Error fetching post {post_id}: {e}")
        return None, None


def _strip_html(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ─── STEP 1: EXTRACT CLAIMS ────────────────────────────────────
def extract_claims(title, content_html):
    """
    Ask Claude to pull out every specific, checkable factual claim from
    the article: prices, plan tiers, feature availability, limits,
    integrations, employee-count thresholds, etc. Vague marketing
    language ("powerful", "easy to use") is deliberately excluded, only
    claims specific enough to be right or wrong.
    """
    print("   🔍 Extracting factual claims...")
    plain_text = _strip_html(content_html)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Read this article and extract every SPECIFIC, checkable factual claim
about the software product(s) it covers. Only include claims precise enough
to be verified as true or false, for example:

- Exact prices or pricing tiers ("$19/month", "Plus plan starts at $30")
- Plan limits or thresholds ("up to 500 employees", "unlimited invoices on the Premium tier")
- Feature availability ("includes a client portal", "does not support recurring invoices")
- Integration claims ("integrates natively with QuickBooks")
- Numeric claims of any kind (user counts, storage limits, API rate limits)

Do NOT include vague marketing language ("powerful", "easy to use", "industry-leading")
since those cannot be fact-checked.

Article title: {title}
Article text:
{plain_text[:6000]}

Return ONLY a JSON array, no markdown, no preamble, in this exact format:
[
  {{"product": "exact product name", "claim_type": "price|plan_limit|feature|integration|other", "claim_text": "the claim as stated in the article, in your own words, concise"}}
]

If there are no specific checkable claims, return an empty array: []"""

    try:
        message = client.messages.create(
            model=AUDIT_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        claims = json.loads(response_text)
        print(f"   ✅ Extracted {len(claims)} checkable claims")
        return claims
    except Exception as e:
        print(f"   ❌ Claim extraction error: {e}")
        return []


# ─── STEP 2: VERIFY EACH CLAIM WITH REAL WEB SEARCH ────────────
def verify_claim(product, claim_type, claim_text):
    """
    Check one claim against the live vendor site using real web search.
    This deliberately uses web search rather than Claude's training
    knowledge, since training knowledge is exactly how a stale or wrong
    claim got published in the first place.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Fact-check this specific claim about {product} using current, live
information from the web. Prioritize the vendor's own pricing/docs pages
over third-party sources.

Claim type: {claim_type}
Claim as published: "{claim_text}"

Search for {product}'s current official pricing and feature pages, then
determine whether this claim is still accurate today.

Return ONLY a JSON object, no markdown, no preamble, in this exact format:
{{
  "status": "confirmed" or "discrepancy" or "outdated" or "unverifiable",
  "finding": "one or two sentences on what you actually found, in your own words",
  "source_url": "the URL you verified against, or empty string if unverifiable"
}}

Status definitions:
- confirmed: the claim matches current vendor information
- discrepancy: the claim does not match what you found (wrong number, wrong feature, etc.)
- outdated: the claim was likely true at some point but vendor info has since changed
- unverifiable: you could not find reliable current information either way"""

    try:
        message = client.messages.create(
            model=AUDIT_MODEL,
            max_tokens=1000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )

        text_parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        response_text = "\n".join(text_parts).strip()
        response_text = response_text.replace("```json", "").replace("```", "").strip()

        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return {"status": "unverifiable", "finding": "Could not parse verification response", "source_url": ""}

        result = json.loads(json_match.group(0))
        return result

    except Exception as e:
        return {"status": "unverifiable", "finding": f"Verification error: {e}", "source_url": ""}


# ─── STEP 3: RUN A FULL AUDIT ON ONE POST ──────────────────────
def audit_post(post_id, title, url):
    print(f"\n{'=' * 60}")
    print(f"  AUDITING: {title}")
    print(f"  {url}")
    print(f"{'=' * 60}")

    fetched_title, content = fetch_post_content(post_id)
    if content is None:
        print("   ❌ Could not fetch post content — skipping")
        return None

    claims = extract_claims(fetched_title or title, content)
    if not claims:
        print("   ℹ️  No specific checkable claims found in this article")
        return {
            "post_id": post_id,
            "title": title,
            "url": url,
            "audited_at": datetime.now().isoformat(),
            "claims": [],
        }

    results = []
    for i, claim in enumerate(claims, 1):
        product = claim.get("product", "Unknown")
        claim_type = claim.get("claim_type", "other")
        claim_text = claim.get("claim_text", "")

        print(f"\n   [{i}/{len(claims)}] Checking: {claim_text[:80]}")
        verification = verify_claim(product, claim_type, claim_text)

        status = verification.get("status", "unverifiable")
        icon = {
            "confirmed": "✅",
            "discrepancy": "🔴",
            "outdated": "🟡",
            "unverifiable": "⚪",
        }.get(status, "⚪")
        print(f"   {icon} {status.upper()}: {verification.get('finding', '')}")

        results.append({
            "product": product,
            "claim_type": claim_type,
            "claim_text": claim_text,
            "status": status,
            "finding": verification.get("finding", ""),
            "source_url": verification.get("source_url", ""),
        })

        time.sleep(1)

    return {
        "post_id": post_id,
        "title": title,
        "url": url,
        "audited_at": datetime.now().isoformat(),
        "claims": results,
    }


# ─── REPORT OUTPUT ──────────────────────────────────────────────
def save_report(audit_result):
    if not audit_result:
        return

    slug = re.sub(r'[^a-z0-9]+', '-', audit_result["title"].lower()).strip('-')[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_filename = f"audit_report_{slug}_{timestamp}.json"
    with open(json_filename, "w") as f:
        json.dump(audit_result, f, indent=2)

    md_filename = f"audit_report_{slug}_{timestamp}.md"
    lines = [
        f"# Claim Audit: {audit_result['title']}",
        f"",
        f"**URL:** {audit_result['url']}",
        f"**Audited:** {audit_result['audited_at'][:10]}",
        f"",
    ]

    claims = audit_result.get("claims", [])
    discrepancies = [c for c in claims if c["status"] == "discrepancy"]
    outdated = [c for c in claims if c["status"] == "outdated"]
    confirmed = [c for c in claims if c["status"] == "confirmed"]
    unverifiable = [c for c in claims if c["status"] == "unverifiable"]

    lines.append(
        f"**Summary:** {len(claims)} claims checked — "
        f"{len(confirmed)} confirmed, {len(discrepancies)} discrepancies, "
        f"{len(outdated)} outdated, {len(unverifiable)} unverifiable"
    )
    lines.append("")

    if discrepancies:
        lines.append("## 🔴 Discrepancies (fix these first)")
        for c in discrepancies:
            lines.append(f"- **{c['product']}** ({c['claim_type']}): \"{c['claim_text']}\"")
            lines.append(f"  - Found: {c['finding']}")
            if c["source_url"]:
                lines.append(f"  - Source: {c['source_url']}")
        lines.append("")

    if outdated:
        lines.append("## 🟡 Possibly Outdated")
        for c in outdated:
            lines.append(f"- **{c['product']}** ({c['claim_type']}): \"{c['claim_text']}\"")
            lines.append(f"  - Found: {c['finding']}")
            if c["source_url"]:
                lines.append(f"  - Source: {c['source_url']}")
        lines.append("")

    if unverifiable:
        lines.append("## ⚪ Unverifiable")
        for c in unverifiable:
            lines.append(f"- **{c['product']}** ({c['claim_type']}): \"{c['claim_text']}\"")
            lines.append(f"  - {c['finding']}")
        lines.append("")

    if confirmed:
        lines.append("## ✅ Confirmed Accurate")
        for c in confirmed:
            lines.append(f"- **{c['product']}** ({c['claim_type']}): \"{c['claim_text']}\"")
        lines.append("")

    with open(md_filename, "w") as f:
        f.write("\n".join(lines))

    print(f"\n   💾 Saved: {json_filename}")
    print(f"   💾 Saved: {md_filename}")

    return md_filename


# ─── CLI HELPERS ─────────────────────────────────────────────────
def list_auditable_posts():
    tracker = load_published_posts()
    posts = tracker.get("posts", [])
    if not posts:
        print("No published posts found in tracker")
        return
    print(f"\n📚 AUDITABLE POSTS ({len(posts)} total):")
    print("=" * 60)
    for post in posts:
        print(f"\n  📄 {post['title']}")
        print(f"     Slug: {post['slug']}")
        print(f"     Post ID: {post['post_id']}")
        print(f"     Created: {post['created_at'][:10]}")


def find_post(identifier):
    """Match a post by slug or numeric post_id from the tracker."""
    tracker = load_published_posts()
    posts = tracker.get("posts", [])
    for post in posts:
        if str(post.get("post_id")) == str(identifier) or post.get("slug") == identifier:
            return post
    return None


def run_all(limit=20):
    tracker = load_published_posts()
    posts = tracker.get("posts", [])[-limit:]
    if not posts:
        print("No published posts found in tracker")
        return

    print(f"\n📋 Auditing {len(posts)} most recent posts...")
    reports = []
    for post in posts:
        result = audit_post(post["post_id"], post["title"], post.get("post_url", ""))
        if result:
            md_file = save_report(result)
            reports.append((post["title"], md_file, result))
        time.sleep(2)

    print(f"\n{'=' * 60}")
    print("  AUDIT BATCH COMPLETE")
    print(f"{'=' * 60}")
    for title, md_file, result in reports:
        discrepancies = len([c for c in result.get("claims", []) if c["status"] == "discrepancy"])
        flag = f"🔴 {discrepancies} discrepancies" if discrepancies else "✅ clean"
        print(f"  {flag} — {title} ({md_file})")


# ─── RUN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--list":
        list_auditable_posts()

    elif sys.argv[1] == "--all":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        run_all(limit)

    else:
        identifier = sys.argv[1]
        post = find_post(identifier)
        if not post:
            print(f"❌ No post found matching '{identifier}'. Try --list to see options.")
            sys.exit(1)

        result = audit_post(post["post_id"], post["title"], post.get("post_url", ""))
        if result:
            save_report(result)

            claims = result.get("claims", [])
            discrepancies = [c for c in claims if c["status"] == "discrepancy"]
            print(f"\n{'=' * 60}")
            if discrepancies:
                print(f"  🔴 {len(discrepancies)} DISCREPANCY(IES) FOUND — review before this page gets more traffic")
            else:
                print(f"  ✅ No discrepancies found ({len(claims)} claims checked)")
            print(f"{'=' * 60}")
