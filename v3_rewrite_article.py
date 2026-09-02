"""
rewrite_article.py — Equinoxen Media money page retrofit

Combines the claim audit with a full rewrite, so pages get corrected and
reformatted in the same pass instead of two disconnected steps. The
rewrite is generated FROM the audit's verified facts, not from Claude's
memory, so the new version is more accurate than the old one, not just
better formatted.

The post is updated IN PLACE: same post_id, same slug/URL, same featured
image. Nothing is deleted and recreated. Safe to rerun on the same
article every year, that's the intended long-term use, not a one-time
migration.

STANDARD SECTION STRUCTURE (same shape for every article type):
  1. TL;DR answer block (40-60 words, Claude-written from verified facts)
  2. Verified date banner (Python-inserted, always accurate)
  3. Existing body sections (features, pricing, pros/cons, etc.)
  4. Don't Buy If... / Who Should Skip This section
  5. Scoring rubric table(s) (reuses content_pipeline's existing system)
  6. Sources list (Python-assembled from the audit's verified URLs)

FAQPage schema is intentionally NOT included, per your existing site
setup, add it back in once real FAQ content exists on these pages.

USAGE:
  python3 rewrite_article.py --list                  List candidates
  python3 rewrite_article.py --list --pending         Only posts not yet retrofitted
  python3 rewrite_article.py <slug-or-post-id>        Retrofit one post
  python3 rewrite_article.py <slug-or-post-id> --type comparison       Override auto-detected type
  python3 rewrite_article.py <slug-or-post-id> --products "A,B,C"      Override product list
  python3 rewrite_article.py <slug-or-post-id> --refresh                Force fresh rating/research
                                                                          for this run's products,
                                                                          ignoring any existing cache
  python3 rewrite_article.py --all [N]                Retrofit N most recent posts (default 20)

RATING/RESEARCH CONSISTENCY: by default, a product's cached score and
research are left alone if they already exist, so a product mentioned
in five articles keeps the SAME score across all five regardless of
retrofit order. Only products with no existing cache get freshly scored.
Pass --refresh only when you specifically know something changed (a
real pricing update) and want this run to force a fresh reassessment,
understand that doing so changes that product's score everywhere it's
cached, not just on this one article.
"""

import os
import re
import sys
import json
import glob
import time
import requests
import anthropic
from datetime import datetime

from content_pipeline import (
    WP_URL, WP_USER, WP_PASS, ANTHROPIC_API_KEY, SITE_NAME, CURRENT_YEAR,
    AFFILIATE_LINKS, SCORING_RUBRIC, apply_all_rubric_tables, apply_tldr_scores,
    load_published_posts, clean_html_response,
    clear_rating, clear_research, save_research, get_cached_research,
    VOICE_GUIDANCE, SOURCE_PARAPHRASE_GUIDANCE,
)
from audit_claims import fetch_post_content, extract_claims, verify_claim, save_report, AUDIT_MODEL, AUDIT_REPORTS_DIR

RETROFIT_MODEL = "claude-sonnet-4-5"
AUDIT_REPORT_TTL_DAYS = 7  # reuse a recent audit_claims.py report instead of re-auditing from scratch

# ─── PRIORITY PRODUCTS FOR BATCH RETROFITS ────────────────────────
# Posts mentioning any of these get retrofitted first in --all runs.
# PartnerStack itself is a network, not a single product, so there's no
# way to auto-detect its member programs, add them here by name as you
# identify them (or as you get approved for more).
PRIORITY_PRODUCTS = ["freshbooks", "constant contact", "jotform", "zoho"]


def _post_priority(post):
    """Lower sorts first. Priority-product posts sort ahead of everything else."""
    programs = [p.lower() for p in post.get("programs", [])]
    title_lower = post.get("title", "").lower()
    for priority in PRIORITY_PRODUCTS:
        if priority in programs or priority in title_lower:
            return 0
    return 1


def build_research_data_from_audit(product, audited_claims):
    """
    Reshape this product's verified claims from the audit into the same
    dict shape research_product() returns, so the retrofit's verification
    work can seed content_pipeline.py's research cache directly, instead
    of that cache staying stale until something separately re-searches
    the same product.
    """
    product_claims = [
        c for c in audited_claims
        if c.get("product") == product and c.get("status") in ("confirmed", "discrepancy", "outdated")
    ]

    def _text(c):
        return c["finding"] if c["status"] in ("discrepancy", "outdated") else c["claim_text"]

    pricing_bits = [_text(c) for c in product_claims if c.get("claim_type") == "price"]
    feature_bits = [_text(c) for c in product_claims if c.get("claim_type") in ("feature", "integration")]
    limit_bits = [_text(c) for c in product_claims if c.get("claim_type") == "plan_limit"]
    source_url = next((c["source_url"] for c in product_claims if c.get("source_url")), "")

    return {
        "pricing": "; ".join(pricing_bits),
        "key_features": feature_bits[:5],
        "limitations": [],
        "notable_limits": "; ".join(limit_bits),
        "source_url": source_url,
    }


def find_recent_audit_report(title):
    """
    Look for an existing audit_report_<slug>_<timestamp>.json produced
    by audit_claims.py for this post. If a fresh one exists (within
    AUDIT_REPORT_TTL_DAYS), reuse its claims instead of re-auditing from
    scratch, since running the same audit twice a week apart wastes
    every web search the first pass already paid for. Returns the
    claims list, or None if nothing recent enough was found.
    """
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:50]
    candidates = sorted(glob.glob(os.path.join(AUDIT_REPORTS_DIR, f"audit_report_{slug}_*.json")))
    if not candidates:
        return None

    latest = candidates[-1]
    try:
        with open(latest, 'r') as f:
            report = json.load(f)
        audited_at = datetime.fromisoformat(report["audited_at"])
        age_days = (datetime.now() - audited_at).days
        if age_days > AUDIT_REPORT_TTL_DAYS:
            print(f"   ⏳ Found audit report ({latest}) but it's {age_days} day(s) old — re-auditing")
            return None
        print(f"   📂 Reusing recent audit report: {latest} ({age_days} day(s) old)")
        raw_claims = report.get("claims", [])

        valid_claims = []
        dropped = 0
        for c in raw_claims:
            if not isinstance(c, dict) or not c.get("claim_text") or not c.get("product"):
                dropped += 1
                continue
            valid_claims.append(c)

        if dropped and not valid_claims and raw_claims:
            print(f"   ⚠️  This cached report is entirely malformed ({dropped}/{len(raw_claims)} claims broken) — it was likely saved before a bug fix. Falling back to a fresh audit instead of using it. Consider deleting {latest}.")
            return None

        if dropped:
            print(f"   ⚠️  {dropped} malformed claim(s) in cached report were dropped, {len(valid_claims)} usable claim(s) kept")

        return valid_claims
    except Exception as e:
        print(f"   ⚠️  Could not read {latest}: {e}")
        return None


# ─── FIND / DETECT ───────────────────────────────────────────────
def find_post(identifier):
    tracker = load_published_posts()
    for post in tracker.get("posts", []):
        if str(post.get("post_id")) == str(identifier) or post.get("slug") == identifier:
            return post
    return None


def detect_content_type(title):
    """Fallback heuristic for posts published before content_type was tracked."""
    title_lower = title.lower()
    if " vs " in title_lower or " vs. " in title_lower:
        return "comparison"
    if re.search(r'\b(best|top)\b', title_lower):
        return "buying_guide"
    return "review"


def get_affiliate_str(programs):
    affiliate_info = []
    for program in programs:
        program_lower = program.lower().replace(" ", "").replace(".", "").replace("-", "")
        for key, link in AFFILIATE_LINKS.items():
            key_clean = key.replace(" ", "").replace(".", "").replace("-", "")
            if key_clean in program_lower and link:
                affiliate_info.append(f"{program}: {link}")
    return "\n".join(affiliate_info) if affiliate_info else "Use placeholder [AFFILIATE_LINK] where needed"


# ─── BUILD VERIFIED FACTS BLOCK FROM THE AUDIT ───────────────────
def build_verified_facts_block(audited_claims):
    """
    Turn the audit's per-claim findings into a plain-text block the
    rewrite prompt can hand to Claude as ground truth. Discrepancies and
    outdated claims are corrected using the audit's finding, not the
    original (wrong) claim text. Unverifiable claims are deliberately
    left out, they get flagged separately for manual review rather than
    silently carried into the new version.
    """
    lines = []
    sources = []
    unverifiable = []

    for c in audited_claims:
        product = c.get("product", "the product")
        claim_type = c.get("claim_type", "other")
        status = c.get("status")

        if status == "confirmed":
            lines.append(f"- [{claim_type}] {c.get('claim_text', '')} (confirmed accurate)")
            if c.get("source_url"):
                sources.append((product, c["source_url"], claim_type))

        elif status in ("discrepancy", "outdated"):
            lines.append(f"- [{claim_type}] CORRECTED: {c.get('finding', '')} (previous claim was: \"{c.get('claim_text', '')}\", now outdated or wrong)")
            if c.get("source_url"):
                sources.append((product, c["source_url"], claim_type))

        elif status == "unverifiable":
            unverifiable.append(c)

    facts_block = "\n".join(lines) if lines else "No specific verified facts available, write general accurate content."
    return facts_block, sources, unverifiable


# ─── RETROFIT PROMPT (same standard structure for every type) ────
def build_retrofit_prompt(content_type, title, keyword, product, programs,
                           facts_block, affiliate_str, internal_links_str):
    products_str = ", ".join(programs) if programs else product
    rubric_lines = "\n".join(f"- {c} ({w}%)" for c, w in SCORING_RUBRIC)
    rubric_keys = "\n".join(f"{c.lower().replace(' ', '_')}: [1-10]" for c, w in SCORING_RUBRIC)

    if content_type == "comparison":
        product1 = programs[0] if len(programs) > 0 else product
        product2 = programs[1] if len(programs) > 1 else "the alternative"
        scoring_blocks = (
            f"<!--SCORES\nproduct: {product1}\n{rubric_keys}\n-->\n"
            f"<!--SCORES\nproduct: {product2}\n{rubric_keys}\n-->"
        )
        dont_buy_instruction = (
            f"'Who Should Skip {product1}' and 'Who Should Skip {product2}' — one short "
            f"paragraph each on who is genuinely better served by the other option or a "
            f"third alternative."
        )
    elif content_type == "buying_guide":
        scoring_blocks = "\n".join(
            f"<!--SCORES\nproduct: {p}\n{rubric_keys}\n-->" for p in (programs or [product])
        )
        dont_buy_instruction = (
            "For each product in your Top Picks section, one sentence starting with "
            "'Skip this if...' describing who it's NOT a good fit for."
        )
    else:
        scoring_blocks = f"<!--SCORES\nproduct: {product}\n{rubric_keys}\n-->"
        dont_buy_instruction = (
            f"'Don't Buy {product} If...' — a bulleted list of 3-5 specific situations "
            f"where a reader should choose something else, each with a one-line reason."
        )

    return f"""You are an expert SaaS reviewer writing for {SITE_NAME}, an independent
software review publication. You are REWRITING an existing article to bring it up to
current standards. Use the VERIFIED FACTS below as ground truth, do not invent or
assume pricing, limits, or features beyond what is listed there or what is safe,
general, non-numeric description.

ARTICLE DETAILS:
Title: {title}
Note: Include {CURRENT_YEAR} in the title only, not elsewhere.
Primary keyword: {keyword}
Product(s): {products_str}
Affiliate links: {affiliate_str}

VERIFIED FACTS (from a live fact-check against vendor sources, use these,
do not contradict them):
{facts_block}
{VOICE_GUIDANCE}
{SOURCE_PARAPHRASE_GUIDANCE}

REQUIRED STANDARD STRUCTURE (same shape used across the whole site):

1. TL;DR block — place this FIRST, before any other heading. Plain HTML,
   no H2. Format as a short bolded label "In short:" followed by 40-60
   words giving the direct answer a reader (or an AI search engine) needs
   immediately: what the product is best for, its starting price if known
   from verified facts, and a one-line bottom-line recommendation. Do not
   use any numeric claim not present in the verified facts above. End
   with a sentence using hidden score marker(s), one per product you
   mention by name in the TL;DR, in this exact format:
   <!--TLDR_SCORE:ExactProductName--> out of 100 (use the exact product
   name as it appears in "Product(s): {products_str}" above, not an
   abbreviation). For a single-product review that's one marker, for a
   comparison or buying guide covering more than one product in the
   TL;DR, include one marker per product named. Do not write a score
   number yourself, it is filled in automatically from the same score
   computed below.

2. <!--VERIFIED_DATE--> — place this exact hidden marker immediately
   after the TL;DR block. Do not write your own "last verified" text,
   this marker will be replaced automatically with an accurate date.

3. Introduction — what problem does this solve (100 words)

4. Overview and Key Features (400-500 words), using only the verified
   facts above for any specific numbers or claims. Where a feature isn't
   covered by verified facts, describe it generally without inventing
   specifics.

5. Pricing — using ONLY the verified pricing facts above. If pricing
   wasn't part of the verified facts, describe pricing structure generally
   without stating specific dollar amounts.

6. Pros and Cons — honest bullet points (100 words)

7. {dont_buy_instruction}

8. Alternatives/Competitors — brief (100 words)

9. Scoring block — place these hidden HTML comment blocks here, exactly
   as written, do not modify their contents:
{scoring_blocks}

10. Our Verdict — final recommendation (100 words). Do not restate a
    specific overall score number, it's inserted automatically above.

11. <!--SOURCES--> — place this exact hidden marker near the very end of
    the article, after the verdict and before any final CTA. It will be
    replaced automatically with a sources list.

12. CTA — Try [Product] with affiliate link

FORMAT REQUIREMENTS:
- Use HTML formatting (h2, h3, p, ul, li, strong tags)
- Make the CTA button: <a href="AFFILIATE_LINK" rel="nofollow sponsored" target="_blank" class="button">Try [Product] →</a>
- Do NOT use H1 tags anywhere — the page title is already H1
- Use H2 for main sections, H3 for subsections
- Return ONLY raw HTML, no markdown, no ```html fences, no preamble
- Never use hyphens or dashes (- or —) to connect clauses or add parenthetical thoughts.
  Rewrite as a separate sentence or use a comma instead.
- Hyphens are only allowed in hyphenated compound words like "well-known"
- Do not write star ratings (⭐) anywhere, the automatically generated
  rubric table replaces them

CRITICAL STYLING RULES:
- Do NOT add inline styles except on tables
- For tables use only: table: style="width:100%; border-collapse:collapse;"
  th/td: style="border:1px solid #D4AF37; padding:8px;" (th also text-align:left;)
- CTA buttons use class="button" only, no other class attributes

INTERNAL LINKING:
Where naturally relevant, link to these existing articles:
{internal_links_str}
Add 2-3 internal links maximum, only where genuinely relevant.

Write the complete rewritten article now in HTML format:"""


# ─── POST-PROCESS: INJECT DETERMINISTIC DATA ──────────────────────
def apply_verified_date(article_content):
    today = datetime.now().strftime("%B %-d, %Y") if os.name != "nt" else datetime.now().strftime("%B %d, %Y")
    banner = (
        f'<p><em>Pricing and features last verified: {today}. '
        f'This review is reassessed periodically, if anything looks out of date, '
        f'let us know at hello@equinoxen.com.</em></p>'
    )
    return article_content.replace("<!--VERIFIED_DATE-->", banner)


CLAIM_TYPE_LABELS = {
    "price": "pricing",
    "plan_limit": "plan limits",
    "feature": "feature details",
    "integration": "integration details",
    "other": "product details",
}


def apply_sources_section(article_content, sources):
    if not sources:
        return article_content.replace("<!--SOURCES-->", "")

    # Group by (product, url) and collect every claim type verified against
    # that specific source, so the link description says what was actually
    # checked there instead of a repeated generic label.
    grouped = {}
    for product, url, claim_type in sources:
        key = (product, url)
        grouped.setdefault(key, set()).add(claim_type)

    items = []
    for (product, url), claim_types in grouped.items():
        labels = sorted({CLAIM_TYPE_LABELS.get(t, "product details") for t in claim_types})
        if len(labels) == 1:
            label_str = labels[0]
        elif len(labels) == 2:
            label_str = f"{labels[0]} and {labels[1]}"
        else:
            label_str = ", ".join(labels[:-1]) + f", and {labels[-1]}"
        items.append(
            f'<li><a href="{url}" rel="nofollow" target="_blank">'
            f'{product} — {label_str} verified against official source</a></li>'
        )

    section = (
        "<h3>Sources</h3>"
        "<ul>" + "".join(items) + "</ul>"
    )
    return article_content.replace("<!--SOURCES-->", section)


# ─── GENERATE THE RETROFITTED ARTICLE ─────────────────────────────
def generate_retrofit(content_type, title, keyword, programs, facts_block, sources, internal_links_str):
    product = programs[0] if programs else keyword
    affiliate_str = get_affiliate_str(programs)

    prompt = build_retrofit_prompt(
        content_type, title, keyword, product, programs,
        facts_block, affiliate_str, internal_links_str,
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print("   ✍️  Generating retrofitted article from verified facts...")
    message = client.messages.create(
        model=RETROFIT_MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    content = clean_html_response(message.content[0].text)

    # Rubric tables + product rating cache (same system as content_pipeline.py)
    content, scored_products = apply_all_rubric_tables(content)
    for scored_product, weighted_total in scored_products:
        print(f"   📊 {scored_product} rubric score: {weighted_total}/100")

    # Deterministic, Python-controlled data — never trust the model for these
    content = apply_tldr_scores(content, scored_products)
    content = apply_verified_date(content)
    content = apply_sources_section(content, sources)

    return content


# ─── UPDATE THE EXISTING WORDPRESS POST IN PLACE ──────────────────
def update_wordpress_post(post_id, new_content, meta_description=None):
    """
    Updates content only. Deliberately does NOT send 'slug' or
    'featured_media', so the URL and existing featured image are left
    untouched, only the body content (and optionally meta description)
    change.
    """
    payload = {"content": new_content}
    if meta_description:
        payload["meta"] = {"rank_math_description": meta_description}

    try:
        response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            json=payload,
            auth=(WP_USER, WP_PASS),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code in (200, 201):
            print(f"   ✅ Post {post_id} updated in place (URL and image unchanged)")
            return True
        else:
            print(f"   ❌ Update failed: {response.status_code} — {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Update error: {e}")
        return False


def mark_retrofitted(post_id):
    """Stamp the tracker entry itself so --list can show retrofit status."""
    tracker = load_published_posts()
    for post in tracker.get("posts", []):
        if post.get("post_id") == post_id:
            post["last_retrofitted"] = datetime.now().isoformat()
            break
    with open("published_posts.json", "w") as f:
        json.dump(tracker, f, indent=2)


# ─── FULL RETROFIT FOR ONE POST ────────────────────────────────────
def retrofit_post(post, forced_type=None, forced_products=None, refresh=False):
    post_id = post["post_id"]
    title = post["title"]
    keyword = post["keyword"]
    url = post.get("post_url", "")

    print(f"\n{'=' * 60}")
    print(f"  RETROFITTING: {title}")
    print(f"  {url}")
    print(f"{'=' * 60}")

    fetched_title, content_html = fetch_post_content(post_id)
    if content_html is None:
        print("   ❌ Could not fetch current content — skipping")
        return None

    # ── Step 1: audit (reuse a recent report if audit_claims.py or an ──
    # earlier retrofit already checked this post within the TTL window)
    reused_claims = find_recent_audit_report(title)
    if reused_claims is not None:
        claims = reused_claims
        audited = reused_claims
    else:
        claims = extract_claims(fetched_title or title, content_html)
        audited = []
        for i, claim in enumerate(claims, 1):
            print(f"   [{i}/{len(claims)}] Verifying: {claim.get('claim_text', '')[:70]}")
            verification = verify_claim(
                claim.get("product", "Unknown"), claim.get("claim_type", "other"), claim.get("claim_text", "")
            )
            audited.append({**claim, **verification})
            time.sleep(1)

        # Save this as a standalone report too, so a future audit_claims.py
        # run or another retrofit can reuse it within the TTL instead of
        # re-auditing from scratch.
        save_report({
            "post_id": post_id,
            "title": title,
            "url": url,
            "audited_at": datetime.now().isoformat(),
            "claims": audited,
        })

    facts_block, sources, unverifiable = build_verified_facts_block(audited)

    if unverifiable:
        print(f"   ⚠️  {len(unverifiable)} claim(s) unverifiable — omitted from rewrite, review manually:")
        for c in unverifiable:
            print(f"      - {c.get('claim_text', '(malformed claim, missing text)')}")

    # ── Step 2: determine type + product list ──────────────────────
    content_type = forced_type or post.get("content_type") or detect_content_type(title)
    programs = forced_products or post.get("programs") or []
    if not programs:
        seen = []
        for c in claims:
            p = c.get("product")
            if p and p not in seen:
                seen.append(p)
        programs = seen
    if content_type == "buying_guide" and len(programs) > 3:
        print(f"   ✂️  Buying guides are capped at 3 products, trimming {len(programs)} down to the first 3: {', '.join(programs[:3])}")
        programs = programs[:3]

    print(f"   ℹ️  Type: {content_type} | Products: {', '.join(programs) if programs else keyword}")

    # ── Step 2.5: only clear caches if --refresh was explicitly passed ──
    # Default is to LEAVE existing ratings/research alone, so a product
    # mentioned in five articles keeps the same score across all five,
    # regardless of retrofit order. Without --refresh, apply_all_rubric_tables
    # further down will reuse any valid cached rating automatically, and
    # only score fresh for products that have no cache entry yet. Pass
    # --refresh only when you specifically know something changed (a
    # pricing update, a real feature change) and want this run to force
    # a fresh reassessment for these specific products.
    products_to_clear = list(dict.fromkeys(programs + [c.get("product") for c in claims if c.get("product")]))
    if refresh:
        print(f"   🔄 --refresh set: forcing fresh rating/research for {', '.join(products_to_clear)}")
        for p in products_to_clear:
            clear_rating(p)
            clear_research(p)

    # ── Step 3: internal links (reuse published tracker, excluding self) ──
    tracker = load_published_posts()
    internal_links_str = "\n".join(
        f"- {p['title']}: {p['post_url']}"
        for p in tracker.get("posts", [])
        if p.get("post_url") and p["post_id"] != post_id
    )[:2000] or "None"

    # ── Step 4: generate retrofitted content ─────────────────────────
    new_content = generate_retrofit(content_type, title, keyword, programs, facts_block, sources, internal_links_str)

    # ── Step 4.5: seed the research cache, but only for gaps ────────────
    # Fill in research for products that had none, or that --refresh
    # explicitly cleared. Don't overwrite an existing, still-valid
    # research cache just because this particular article's audit
    # touched the same product, that would cause the same cross-article
    # drift problem the rating fix above addresses.
    for p in products_to_clear:
        if refresh or not get_cached_research(p):
            research_data = build_research_data_from_audit(p, audited)
            if any(research_data.values()):
                save_research(p, research_data)

    # ── Step 5: update WordPress in place (same slug/URL/image) ──────
    today = datetime.now().strftime("%Y-%m-%d")
    meta_description = f"Independent {keyword} review, verified {today}. Honest pricing, features, and our take."
    updated = update_wordpress_post(post_id, new_content, meta_description=meta_description)
    if updated:
        mark_retrofitted(post_id)

    return {
        "post_id": post_id,
        "title": title,
        "url": url,
        "content_type": content_type,
        "programs": programs,
        "retrofitted_at": datetime.now().isoformat(),
        "discrepancies_found": len([c for c in audited if c.get("status") == "discrepancy"]),
        "unverifiable_count": len(unverifiable),
    }


# ─── CLI ────────────────────────────────────────────────────────────
def list_candidates(pending_only=False):
    tracker = load_published_posts()
    posts = tracker.get("posts", [])
    if not posts:
        print("No published posts found")
        return
    if pending_only:
        posts = [p for p in posts if not p.get("last_retrofitted")]
    print(f"\n📚 RETROFIT CANDIDATES ({len(posts)}{' pending' if pending_only else ' total'})")
    print(f"   Priority products (retrofitted first in --all runs): {', '.join(PRIORITY_PRODUCTS)}")
    print("=" * 60)
    for post in posts:
        ctype = post.get("content_type") or f"(untracked, guessed: {detect_content_type(post['title'])})"
        flag = "⭐ PRIORITY  " if _post_priority(post) == 0 else ""
        retrofitted = post.get("last_retrofitted")
        status = f"✅ retrofitted {retrofitted[:10]}" if retrofitted else "○ not yet retrofitted"
        print(f"\n  {flag}📄 {post['title']}")
        print(f"     Post ID: {post['post_id']}  |  Slug: {post['slug']}  |  Type: {ctype}")
        print(f"     {status}")
        print(f"     Slug: {post['slug']}  |  Type: {ctype}")


def run_all(limit=20):
    tracker = load_published_posts()
    posts = tracker.get("posts", [])
    if not posts:
        print("No published posts found")
        return

    # Priority-product posts first, then most recently published within
    # each tier, so newly-approved affiliate programs get refreshed
    # ahead of everything else without needing to be run one at a time.
    indexed = list(enumerate(posts))
    indexed.sort(key=lambda pair: (_post_priority(pair[1]), -pair[0]))
    ordered_posts = [post for _, post in indexed][:limit]

    priority_count = len([p for p in ordered_posts if _post_priority(p) == 0])
    print(f"\n📋 Retrofitting {len(ordered_posts)} posts ({priority_count} priority, rest by recency)...")
    results = []
    for post in ordered_posts:
        result = retrofit_post(post)
        if result:
            results.append(result)
        time.sleep(3)

    print(f"\n{'=' * 60}")
    print("  RETROFIT BATCH COMPLETE")
    print(f"{'=' * 60}")
    for r in results:
        flag = f"🔴 {r['discrepancies_found']} fixed" if r['discrepancies_found'] else "✅ no discrepancies"
        print(f"  {flag} — {r['title']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--list":
        list_candidates(pending_only="--pending" in sys.argv)

    elif sys.argv[1] == "--all":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        run_all(limit)

    else:
        identifier = sys.argv[1]
        forced_type = None
        if "--type" in sys.argv:
            forced_type = sys.argv[sys.argv.index("--type") + 1]

        forced_products = None
        if "--products" in sys.argv:
            raw = sys.argv[sys.argv.index("--products") + 1]
            forced_products = [p.strip() for p in raw.split(",") if p.strip()]

        refresh = "--refresh" in sys.argv

        post = find_post(identifier)
        if not post:
            print(f"❌ No post found matching '{identifier}'. Try --list to see options.")
            sys.exit(1)

        result = retrofit_post(post, forced_type=forced_type, forced_products=forced_products, refresh=refresh)
        if result:
            print(f"\n{'=' * 60}")
            print(f"  ✅ Retrofit complete: {result['url']}")
            print(f"  Discrepancies fixed: {result['discrepancies_found']}")
            if result['unverifiable_count']:
                print(f"  ⚠️  {result['unverifiable_count']} claim(s) need manual review (unverifiable)")
            print(f"{'=' * 60}")
