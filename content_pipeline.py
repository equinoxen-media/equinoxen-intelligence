import os
import json
import time
import requests
import anthropic
from datetime import datetime
from dotenv import load_dotenv
import re
import glob

load_dotenv()

# ─── CONFIGURATION ────────────────────────────────────────────
WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WORDPRESS_USERNAME")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD")

AFFILIATE_LINKS = {
    "hubspot": os.getenv("AFFILIATE_HUBSPOT"),
    "monday": os.getenv("AFFILIATE_MONDAY"),
    "semrush": os.getenv("AFFILIATE_SEMRUSH"),
    "notion": os.getenv("AFFILIATE_NOTION"),
    "webflow": os.getenv("AFFILIATE_WEBFLOW"),
    "jotform": os.getenv("AFFILIATE_JOTFORM"),
    "zoho": os.getenv("AFFILIATE_ZOHO"),
    "unbounce": os.getenv("AFFILIATE_UNBOUNCE"),
}

SITE_NAME = "Equinoxen Media"
SITE_URL = "https://equinoxen.com"
CURRENT_YEAR = datetime.now().year

# Category IDs from WordPress
# Update these after checking your WordPress categories
CATEGORIES = {
    "general": 1,
    "crm": 4,
    "email_marketing": 5,
    "seo_tools": 6,
    "project_management": 7,
    "business_automation": 8,
    "ai_tools": 9,
    "finance": 10,
    "website_builders": 11,
 }

# ─── STEP 1: LOAD INTELLIGENCE REPORT ────────────────────────
def load_latest_intelligence():
    """Load the most recent intelligence report"""
    reports = glob.glob("intelligence_report_*.json")
    if not reports:
        print("❌ No intelligence reports found. Run intelligence.py first.")
        return None
    
    latest = sorted(reports)[-1]
    print(f"📂 Loading intelligence report: {latest}")
    
    with open(latest, 'r') as f:
        return json.load(f)

# ─── STEP 2: GENERATE ARTICLE WITH CLAUDE ─────────────────────
def generate_article(opportunity):
    """Generate a full SEO-optimized review article using Claude"""
    
    title = opportunity.get('title', '')
    keyword = opportunity.get('keyword', '')
    content_type = opportunity.get('type', 'review')
    programs = opportunity.get('programs', [])
    
    print(f"\n✍️  Generating article: {title}")
    print(f"   Keyword: {keyword}")
    print(f"   Type: {content_type}")
    
    # Build affiliate links string for the prompt
    affiliate_info = []
    for program in programs:
        program_lower = program.lower()
        for key, link in AFFILIATE_LINKS.items():
            if key in program_lower and link:
                affiliate_info.append(f"{program}: {link}")
    
    affiliate_str = "\n".join(affiliate_info) if affiliate_info else "Use placeholder [AFFILIATE_LINK] where needed"
    
    # Different prompts for different content types
    if content_type == "review":
        prompt = build_review_prompt(title, keyword, programs, affiliate_str)
    elif content_type == "comparison":
        prompt = build_comparison_prompt(title, keyword, programs, affiliate_str)
    else:
        prompt = build_buying_guide_prompt(title, keyword, programs, affiliate_str)
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = message.content[0].text
        print(f"   ✅ Article generated ({len(content)} characters)")
        return content
        
    except Exception as e:
        print(f"   ❌ Generation error: {e}")
        return None

# ─── REVIEW ARTICLE PROMPT ────────────────────────────────────
def build_review_prompt(title, keyword, programs, affiliate_links):
    product = programs[0] if programs else keyword
    
    return f"""You are an expert SaaS reviewer writing for {SITE_NAME}, an independent 
software review publication. Write a comprehensive, SEO-optimized review article.

ARTICLE DETAILS:
Title: {title}
Primary keyword: {keyword}
Product being reviewed: {product}
Year: {CURRENT_YEAR}
Affiliate links to include: {affiliate_links}

ARTICLE REQUIREMENTS:
- Length: 2,500-3,000 words
- Tone: Expert, honest, helpful — never salesy
- Structure: Use H2 and H3 headings
- Include affiliate disclosure at the very top
- Natural keyword usage — not stuffed

REQUIRED STRUCTURE:
1. Affiliate Disclosure (one sentence at top)
2. Introduction — what problem does this solve (150 words)
3. What is [Product] — overview (200 words)
4. Key Features — 5-7 features with H3 subheadings (600 words)
5. Pricing — all tiers clearly explained (200 words)
6. Pros and Cons — honest bullet points (150 words)
7. Who is it best for — specific use cases (150 words)
8. [Product] Alternatives — 2-3 competitors briefly (200 words)
9. Our Verdict — final recommendation with star rating out of 5 (150 words)
10. CTA — Try [Product] with affiliate link (50 words)

FORMAT REQUIREMENTS:
- Use HTML formatting (h2, h3, p, ul, li, strong tags)
- Include a star rating like: ⭐⭐⭐⭐⭐ (X/5)
- Make the CTA button: <a href="AFFILIATE_LINK" rel="nofollow sponsored" target="_blank" class="button">Try [Product] Free →</a>
- Affiliate disclosure: <p class="disclosure"><strong>Disclosure:</strong> This review contains affiliate links. We may earn a commission if you purchase through our links at no extra cost to you.</p>

Write the complete article now in HTML format:"""

# ─── COMPARISON ARTICLE PROMPT ────────────────────────────────
def build_comparison_prompt(title, keyword, programs, affiliate_links):
    product1 = programs[0] if len(programs) > 0 else "Product A"
    product2 = programs[1] if len(programs) > 1 else "Product B"
    
    return f"""You are an expert SaaS reviewer writing for {SITE_NAME}. 
Write a comprehensive comparison article.

ARTICLE DETAILS:
Title: {title}
Primary keyword: {keyword}
Products compared: {product1} vs {product2}
Year: {CURRENT_YEAR}
Affiliate links: {affiliate_links}

REQUIRED STRUCTURE:
1. Affiliate Disclosure (one sentence)
2. Introduction — why this comparison matters (150 words)
3. Quick Verdict — summary table showing winner in each category (HTML table)
4. {product1} Overview — key features and pricing (300 words)
5. {product2} Overview — key features and pricing (300 words)
6. Head-to-Head Comparison — 5 categories with winner declared each time (500 words)
7. Pricing Comparison — clear breakdown (200 words)
8. Who Should Choose {product1} — specific use cases (150 words)
9. Who Should Choose {product2} — specific use cases (150 words)
10. Final Verdict — clear recommendation (150 words)
11. CTAs for both products with affiliate links

FORMAT: Use HTML with h2, h3, p, ul, li, table tags.
Include comparison table with checkmarks ✓ and ✗
Star ratings for each product.

Write the complete article now in HTML:"""

# ─── BUYING GUIDE PROMPT ──────────────────────────────────────
def build_buying_guide_prompt(title, keyword, programs, affiliate_links):
    return f"""You are an expert SaaS reviewer writing for {SITE_NAME}.
Write a comprehensive buying guide.

ARTICLE DETAILS:
Title: {title}
Primary keyword: {keyword}
Products to feature: {', '.join(programs)}
Year: {CURRENT_YEAR}
Affiliate links: {affiliate_links}

REQUIRED STRUCTURE:
1. Affiliate Disclosure
2. Introduction — why this category matters (150 words)
3. What to look for — buying criteria with H3 subheadings (300 words)
4. Top picks — 5-7 products each with (800 words total):
   - Brief overview
   - Key features
   - Pricing
   - Best for
   - Affiliate link CTA
5. Comparison table — all products side by side (HTML table)
6. How to choose — decision framework (200 words)
7. Final recommendations — top 3 for different needs (150 words)

FORMAT: Use HTML. Include star ratings.
Each product section should have an affiliate CTA button.

Write the complete article now in HTML:"""

# ─── STEP 3: GENERATE SEO METADATA ───────────────────────────
def generate_seo_metadata(title, keyword, article_content):
    """Generate SEO title, meta description and excerpt"""
    print("   🔍 Generating SEO metadata...")
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    prompt = f"""Generate SEO metadata for this article. Return ONLY JSON, no markdown.

Article title: {title}
Primary keyword: {keyword}
Article excerpt (first 200 chars): {article_content[:200]}

Return this exact JSON structure:
{{"seo_title": "max 60 chars with keyword", "meta_description": "max 155 chars with keyword and CTA", "excerpt": "2 sentence article summary", "slug": "url-friendly-slug-with-keyword", "focus_keyword": "{keyword}"}}"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response = message.content[0].text.strip()
        response = response.replace('```json', '').replace('```', '').strip()
        return json.loads(response)
        
    except Exception as e:
        print(f"   ⚠️  Metadata error: {e}")
        return {
            "seo_title": title[:60],
            "meta_description": f"Read our independent {keyword} review and comparison. Find the best tools for your business.",
            "excerpt": f"Our independent review of {keyword}.",
            "slug": keyword.lower().replace(' ', '-'),
            "focus_keyword": keyword
        }

# ─── STEP 4: ASSIGN CATEGORY ──────────────────────────────────
def assign_category(keyword, programs):
    """Assign WordPress category based on keyword"""
    keyword_lower = keyword.lower()
    
    category_map = {
        # CRM — ID 4
        "crm": CATEGORIES.get("crm", 1),
        "salesforce": CATEGORIES.get("crm", 1),
        "hubspot": CATEGORIES.get("crm", 1),
        "zoho": CATEGORIES.get("crm", 1),
        "pipedrive": CATEGORIES.get("crm", 1),
        
        # Email Marketing — ID 5
        "email": CATEGORIES.get("email_marketing", 1),
        "mailchimp": CATEGORIES.get("email_marketing", 1),
        "klaviyo": CATEGORIES.get("email_marketing", 1),
        "omnisend": CATEGORIES.get("email_marketing", 1),
        "convertkit": CATEGORIES.get("email_marketing", 1),
        "newsletter": CATEGORIES.get("email_marketing", 1),
        
        # SEO Tools — ID 6
        "seo": CATEGORIES.get("seo_tools", 1),
        "semrush": CATEGORIES.get("seo_tools", 1),
        "ahrefs": CATEGORIES.get("seo_tools", 1),
        "keyword": CATEGORIES.get("seo_tools", 1),
        "backlink": CATEGORIES.get("seo_tools", 1),
        "rank": CATEGORIES.get("seo_tools", 1),
        
        # Project Management — ID 7
        "project": CATEGORIES.get("project_management", 1),
        "monday": CATEGORIES.get("project_management", 1),
        "notion": CATEGORIES.get("project_management", 1),
        "asana": CATEGORIES.get("project_management", 1),
        "clickup": CATEGORIES.get("project_management", 1),
        "trello": CATEGORIES.get("project_management", 1),
        "task": CATEGORIES.get("project_management", 1),
        
        # Business Automation — ID 8
        "automation": CATEGORIES.get("business_automation", 1),
        "zapier": CATEGORIES.get("business_automation", 1),
        "make": CATEGORIES.get("business_automation", 1),
        "workflow": CATEGORIES.get("business_automation", 1),
        "integrate": CATEGORIES.get("business_automation", 1),
        
        # AI Tools — ID 9
        "ai": CATEGORIES.get("ai_tools", 1),
        "artificial intelligence": CATEGORIES.get("ai_tools", 1),
        "chatgpt": CATEGORIES.get("ai_tools", 1),
        "jasper": CATEGORIES.get("ai_tools", 1),
        "grammarly": CATEGORIES.get("ai_tools", 1),
        "copy.ai": CATEGORIES.get("ai_tools", 1),
        
        # Finance Software — ID 10
        "accounting": CATEGORIES.get("finance", 1),
        "quickbooks": CATEGORIES.get("finance", 1),
        "freshbooks": CATEGORIES.get("finance", 1),
        "xero": CATEGORIES.get("finance", 1),
        "invoice": CATEGORIES.get("finance", 1),
        "bookkeeping": CATEGORIES.get("finance", 1),
        "payroll": CATEGORIES.get("finance", 1),
        "finance": CATEGORIES.get("finance", 1),
        
        # Website Builders — ID 11
        "landing page": CATEGORIES.get("website_builders", 1),
        "webflow": CATEGORIES.get("website_builders", 1),
        "unbounce": CATEGORIES.get("website_builders", 1),
        "leadpages": CATEGORIES.get("website_builders", 1),
        "website builder": CATEGORIES.get("website_builders", 1),
        "wix": CATEGORIES.get("website_builders", 1),
    }
    
    for key, cat_id in category_map.items():
        if key in keyword_lower:
            return cat_id
    
    # Check programs list if keyword didn't match
    for program in programs:
        program_lower = program.lower()
        for key, cat_id in category_map.items():
            if key in program_lower:
                return cat_id
    
    return CATEGORIES.get("general", 1)  # Default to General

# ─── STEP 5: PUBLISH TO WORDPRESS ─────────────────────────────
def publish_to_wordpress(title, content, metadata, category_id, draft=True):
    """Publish article to WordPress via REST API"""
    
    status = "draft" if draft else "publish"
    print(f"\n📤 Publishing to WordPress as {status}...")
    
    api_url = f"{WP_URL}/wp-json/wp/v2/posts"
    
    post_data = {
        "title": metadata.get("seo_title", title),
        "content": content,
        "status": status,
        "slug": metadata.get("slug", ""),
        "excerpt": metadata.get("excerpt", ""),
        "categories": [category_id],
        "tags": [],
        "format": "standard",
        "meta": {
            "rank_math_title": metadata.get("seo_title", ""),
            "rank_math_description": metadata.get("meta_description", ""),
            "rank_math_focus_keyword": metadata.get("focus_keyword", ""),
        }
    }
    
    try:
        response = requests.post(
            api_url,
            json=post_data,
            auth=(WP_USER, WP_PASS),
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            post = response.json()
            post_id = post.get('id')
            post_link = post.get('link')
            print(f"   ✅ Published! ID: {post_id}")
            print(f"   🔗 URL: {post_link}")
            return post_id, post_link
        else:
            print(f"   ❌ Publishing failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None, None
            
    except Exception as e:
        print(f"   ❌ WordPress error: {e}")
        return None, None

# ─── STEP 6: SAVE ARTICLE LOCALLY ─────────────────────────────
def save_article_locally(title, content, metadata):
    """Save generated article as HTML file for review"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = metadata.get("slug", "article").replace("/", "-")
    filename = f"article_{slug}_{timestamp}.html"
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="description" content="{metadata.get('meta_description', '')}">
<title>{metadata.get('seo_title', title)}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.7; }}
h1 {{ color: #0B0B0D; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }}
h2 {{ color: #2D2D2D; margin-top: 40px; }}
h3 {{ color: #444; }}
.disclosure {{ background: #FDF8E8; border-left: 4px solid #D4AF37; padding: 12px 16px; margin-bottom: 24px; font-size: 14px; }}
.button {{ display: inline-block; background: #D4AF37; color: #000; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; margin: 16px 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
th {{ background: #0B0B0D; color: #D4AF37; padding: 10px; text-align: left; }}
td {{ padding: 10px; border-bottom: 1px solid #eee; }}
tr:nth-child(even) {{ background: #f9f9f9; }}
</style>
</head>
<body>
<h1>{title}</h1>
{content}
</body>
</html>"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"   💾 Saved locally: {filename}")
    return filename

# ─── MAIN PIPELINE ────────────────────────────────────────────
def run_pipeline(num_articles=3, publish_as_draft=True, publish_to_wp=True):
    print("=" * 60)
    print("  EQUINOXEN MEDIA — CONTENT PIPELINE")
    print(f"  Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Generating {num_articles} articles")
    print("=" * 60)
    
    # Load intelligence report
    intelligence = load_latest_intelligence()
    if not intelligence:
        return
    
    opportunities = intelligence.get('top_opportunities', [])
    if not opportunities:
        print("❌ No opportunities found in intelligence report")
        return
    
    print(f"\n📋 Found {len(opportunities)} opportunities")
    print(f"   Processing top {num_articles}...")
    
    results = []
    
    for i, opp in enumerate(opportunities[:num_articles]):
        print(f"\n{'='*60}")
        print(f"  ARTICLE {i+1} of {num_articles}")
        print(f"{'='*60}")
        
        # Generate article
        article_content = generate_article(opp)
        if not article_content:
            continue
        
        # Generate metadata
        metadata = generate_seo_metadata(
            opp.get('title', ''),
            opp.get('keyword', ''),
            article_content
        )
        
        # Assign category
        category_id = assign_category(
            opp.get('keyword', ''),
            opp.get('programs', [])
        )
        
        # Save locally
        local_file = save_article_locally(
            opp.get('title', ''),
            article_content,
            metadata
        )
        
        # Publish to WordPress
        post_id = None
        post_url = None
        if publish_to_wp:
            post_id, post_url = publish_to_wordpress(
                opp.get('title', ''),
                article_content,
                metadata,
                category_id,
                draft=publish_as_draft
            )
        
        results.append({
            "title": opp.get('title', ''),
            "keyword": opp.get('keyword', ''),
            "local_file": local_file,
            "post_id": post_id,
            "post_url": post_url,
            "status": "draft" if publish_as_draft else "published"
        })
        
        # Rate limiting between articles
        if i < num_articles - 1:
            print(f"\n⏳ Waiting 5 seconds before next article...")
            time.sleep(5)
    
    # Final summary
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\n✅ Generated {len(results)} articles:")
    for r in results:
        print(f"\n  📄 {r['title']}")
        print(f"     Keyword: {r['keyword']}")
        print(f"     Local: {r['local_file']}")
        if r['post_url']:
            print(f"     WordPress: {r['post_url']}")
        print(f"     Status: {r['status']}")
    
    print("\n💡 Next steps:")
    print("   1. Review draft articles in WordPress")
    print("   2. Add featured images to each post")
    print("   3. Verify affiliate links are working")
    print("   4. Review and publish when ready")
    
    return results

# ─── RUN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    run_pipeline(
        num_articles=3,        # How many articles to generate
        publish_as_draft=True, # True = draft, False = live
        publish_to_wp=True     # True = send to WordPress
    )
