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
    "klaviyo": os.getenv("AFFILIATE_KLAVIYO"),
    "asana": os.getenv("AFFILIATE_ASANAE"),
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

# ─── PUBLISHED POSTS TRACKER ──────────────────────────────────
PUBLISHED_TRACKER = "published_posts.json"

def load_published_posts():
    """Load list of already published post slugs"""
    if os.path.exists(PUBLISHED_TRACKER):
        with open(PUBLISHED_TRACKER, 'r') as f:
            return json.load(f)
    return {"slugs": [], "titles": [], "keywords": []}

def save_published_post(title, slug, keyword, post_id, post_url):
    """Save a published post to the tracker"""
    tracker = load_published_posts()
    
    tracker["slugs"].append(slug)
    tracker["titles"].append(title.lower())
    tracker["keywords"].append(keyword.lower())
    tracker["posts"] = tracker.get("posts", [])
    tracker["posts"].append({
        "title": title,
        "slug": slug,
        "keyword": keyword,
        "post_id": post_id,
        "post_url": post_url,
        "created_at": datetime.now().isoformat()
    })
    
    with open(PUBLISHED_TRACKER, 'w') as f:
        json.dump(tracker, f, indent=2)
    
    print(f"   📝 Tracked: {title}")

def is_already_published(title, keyword, slug):
    """Check if a post has already been published"""
    tracker = load_published_posts()
    
    # Check by slug
    if slug in tracker.get("slugs", []):
        return True, "slug"
    
    # Check by keyword
    if keyword.lower() in tracker.get("keywords", []):
        return True, "keyword"
    
    # Check by title similarity
    if title.lower() in tracker.get("titles", []):
        return True, "title"
    
    return False, None

def list_published_posts():
    """Display all published posts"""
    tracker = load_published_posts()
    posts = tracker.get("posts", [])
    
    if not posts:
        print("No posts tracked yet")
        return
    
    print(f"\n📚 PUBLISHED POSTS ({len(posts)} total):")
    print("=" * 60)
    for post in posts:
        print(f"\n  📄 {post['title']}")
        print(f"     Keyword: {post['keyword']}")
        print(f"     URL: {post.get('post_url', 'N/A')}")
        print(f"     Created: {post['created_at'][:10]}")

def check_wordpress_for_duplicate(slug):
    """Check if a post with this slug already exists in WordPress"""
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            auth=(WP_USER, WP_PASS),
            params={"slug": slug, "status": "any"}
        )
        
        if response.status_code == 200:
            posts = response.json()
            if posts:
                print(f"   ⚠️  Post already exists in WordPress: {slug}")
                return True
        return False
        
    except Exception as e:
        return False
    
def show_published():
    """Show all tracked published posts"""
    list_published_posts()
    
def clean_html_response(text):
    """Remove markdown code fences from Claude response"""
    text = text.strip()
    
    # Remove ```html at start
    if text.startswith('```html'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    
    # Remove ``` at end
    if text.endswith('```'):
        text = text[:-3]
    
    return text.strip()
    
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
        
        # Clean markdown code fences
        content = clean_html_response(content)
        
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
- Natural keyword usage — not stuffed

REQUIRED STRUCTURE:
1. Introduction — what problem does this solve (150 words)
2. What is [Product] — overview (200 words)
3. Key Features — 5-7 features with H3 subheadings (600 words)
4. Pricing — all tiers clearly explained (200 words)
5. Pros and Cons — honest bullet points (150 words)
6. Who is it best for — specific use cases (150 words)
7. [Product] Alternatives — 2-3 competitors briefly (200 words)
8. Our Verdict — final recommendation with star rating out of 5 (150 words)
9. CTA — Try [Product] with affiliate link (50 words)

FORMAT REQUIREMENTS:
- Use HTML formatting (h2, h3, p, ul, li, strong tags)
- Include a star rating like: ⭐⭐⭐⭐⭐ (X/5)
- Make the CTA button: <a href="AFFILIATE_LINK" rel="nofollow sponsored" target="_blank" class="button">Try [Product] Free →</a>

CRITICAL FORMATTING RULES:
- Return ONLY raw HTML — no markdown
- Do NOT wrap in ```html or ``` tags
- Start your response directly with the disclosure paragraph
- No preamble or explanation before the HTML

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
1. Introduction — why this comparison matters (150 words)
2. Quick Verdict — summary table showing winner in each category (HTML table)
3. {product1} Overview — key features and pricing (300 words)
4. {product2} Overview — key features and pricing (300 words)
5. Head-to-Head Comparison — 5 categories with winner declared each time (500 words)
6. Pricing Comparison — clear breakdown (200 words)
7. Who Should Choose {product1} — specific use cases (150 words)
8. Who Should Choose {product2} — specific use cases (150 words)
9. Final Verdict — clear recommendation (150 words)
10. CTAs for both products with affiliate links

FORMAT: Use HTML with h2, h3, p, ul, li, table tags.
Include comparison table with checkmarks ✓ and ✗
Star ratings for each product.

CRITICAL FORMATTING RULES:
- Return ONLY raw HTML — no markdown
- Do NOT wrap in ```html or ``` tags  
- Start directly with the disclosure paragraph
- No preamble or explanation

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
1. Introduction — why this category matters (150 words)
2. What to look for — buying criteria with H3 subheadings (300 words)
3. Top picks — 5-7 products each with (800 words total):
   - Brief overview
   - Key features
   - Pricing
   - Best for
   - Affiliate link CTA
4. Comparison table — all products side by side (HTML table)
5. How to choose — decision framework (200 words)
6. Final recommendations — top 3 for different needs (150 words)

FORMAT: Use HTML. Include star ratings.
Each product section should have an affiliate CTA button.

CRITICAL FORMATTING RULES:
- Return ONLY raw HTML — no markdown
- Do NOT wrap in ```html or ``` tags
- Start directly with the disclosure paragraph
- No preamble or explanation

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
            model="claude-sonnet-4-5",
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

#---- STEP 4.1  FETCH IMAGE FROM UNSPLASH -----
def get_featured_image_unsplash(keyword):
    """Fetch relevant image from Unsplash API"""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        print("   ⚠️  No UNSPLASH_ACCESS_KEY — skipping featured image")
        return None
    
    try:
        # Search for relevant image
        search_term = keyword.replace('-', ' ')
        
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": f"{search_term} software technology",
                "per_page": 5,
                "orientation": "landscape",
                "content_filter": "high"
            },
            headers={
                "Authorization": f"Client-ID {access_key}"
            }
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return None
        
        # Get first result
        photo = results[0]
        image_url = photo["urls"]["regular"]
        photographer = photo["user"]["name"]
        
        print(f"   📸 Found image by {photographer}")
        return image_url
        
    except Exception as e:
        print(f"   ⚠️  Unsplash error: {e}")
        return None


def upload_image_to_wordpress(image_url, title):
    """Download image and upload to WordPress media library"""
    try:
        print(f"   📤 Uploading featured image...")
        
        # Download image
        img_response = requests.get(image_url, timeout=30)
        if img_response.status_code != 200:
            return None
        
        # Clean filename
        filename = title.lower()
        filename = ''.join(c if c.isalnum() or c == '-' else '-' for c in filename)
        filename = f"{filename[:50]}.jpg"
        
        # Upload to WordPress media library
        media_url = f"{WP_URL}/wp-json/wp/v2/media"
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg"
        }
        
        media_response = requests.post(
            media_url,
            data=img_response.content,
            headers=headers,
            auth=(WP_USER, WP_PASS)
        )
        
        if media_response.status_code in [200, 201]:
            media = media_response.json()
            media_id = media.get("id")
            print(f"   ✅ Image uploaded — Media ID: {media_id}")
            return media_id
        else:
            print(f"   ⚠️  Image upload failed: {media_response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ⚠️  Image upload error: {e}")
        return None


def generate_branded_image(title, keyword):
    """Generate a simple branded featured image using Pillow"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create image
        W, H = 1200, 630
        img = Image.new('RGB', (W, H), (11, 11, 13))  # Midnight background
        draw = ImageDraw.Draw(img)
        
        # Gold accent bar at top
        draw.rectangle([(0, 0), (W, 6)], fill=(212, 175, 55))
        
        # Gold accent bar at bottom
        draw.rectangle([(0, H-6), (W, H)], fill=(212, 175, 55))
        
        # Category label
        draw.rectangle([(60, 60), (260, 95)], fill=(26, 28, 32))
        draw.text((80, 68), keyword.upper()[:25], fill=(212, 175, 55))
        
        # Main title — wrap text
        words = title.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(' '.join(current_line)) > 35:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw title
        y_text = H//2 - len(lines) * 35
        for line in lines[:4]:
            draw.text((60, y_text), line, fill=(230, 226, 216))
            y_text += 70
        
        # Brand name bottom
        draw.text((60, H-50), "EQUINOXEN MEDIA", fill=(212, 175, 55))
        draw.text((W-250, H-50), "equinoxen.com", fill=(107, 107, 122))
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=90)
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
        
    except ImportError:
        print("   ⚠️  Pillow not installed — skipping branded image")
        return None
    except Exception as e:
        print(f"   ⚠️  Image generation error: {e}")
        return None


def upload_branded_image_to_wordpress(title, keyword):
    """Generate and upload a branded image to WordPress"""
    try:
        print(f"   🎨 Generating branded featured image...")
        
        img_data = generate_branded_image(title, keyword)
        if not img_data:
            return None
        
        # Clean filename
        filename = keyword.lower().replace(' ', '-')[:50] + '.jpg'
        
        media_url = f"{WP_URL}/wp-json/wp/v2/media"
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg"
        }
        
        response = requests.post(
            media_url,
            data=img_data,
            headers=headers,
            auth=(WP_USER, WP_PASS)
        )
        
        if response.status_code in [200, 201]:
            media = response.json()
            media_id = media.get("id")
            print(f"   ✅ Branded image uploaded — ID: {media_id}")
            return media_id
        else:
            print(f"   ⚠️  Upload failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return None

# ─── STEP 5: PUBLISH TO WORDPRESS ─────────────────────────────
def publish_to_wordpress(title, content, metadata, category_id, draft=True, featured_image_id=None):
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
        "meta": {
            "rank_math_title": metadata.get("seo_title", ""),
            "rank_math_description": metadata.get("meta_description", ""),
            "rank_math_focus_keyword": metadata.get("focus_keyword", ""),
        }
    }
    
    # Add featured image if provided
    if featured_image_id:
        post_data["featured_media"] = featured_image_id
    
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
    
        title = opp.get('title', '')
        keyword = opp.get('keyword', '')
    
        # Generate slug for checking
        test_slug = keyword.lower().replace(' ', '-')
    
        # ── CHECK IF ALREADY PUBLISHED ──────────────────────────
        already_done, reason = is_already_published(title, keyword, test_slug)
        if already_done:
            print(f"⏭️  Skipping — already published ({reason} match):")
            print(f"   {title}")
            continue
    
        # Also check WordPress directly
        if check_wordpress_for_duplicate(test_slug):
            print(f"⏭️  Skipping — already exists in WordPress")
            print(f"   {title}")
            continue

        # Generate article
        article_content = generate_article(opp)
        if not article_content:
            continue
    
        # Generate metadata
        metadata = generate_seo_metadata(
            title,
            keyword,
            article_content
        )
    
        # Assign category
        category_id = assign_category(
            keyword,
            opp.get('programs', [])
        )
    
        # Save locally
        local_file = save_article_locally(
            title,
            article_content,
            metadata
        )
    
# Get featured image
        featured_image_id = None
        if publish_to_wp:
            # Try Unsplash first
            image_url = get_featured_image_unsplash(keyword)
            if image_url:
                featured_image_id = upload_image_to_wordpress(image_url, title)
            
            # Fall back to branded image if Unsplash fails
            if not featured_image_id:
                featured_image_id = upload_branded_image_to_wordpress(title, keyword)
        
        # Publish to WordPress
        post_id = None
        post_url = None
        if publish_to_wp:
            post_id, post_url = publish_to_wordpress(
                title,
                article_content,
                metadata,
                category_id,
                draft=publish_as_draft,
                featured_image_id=featured_image_id
            )
    
        # ── TRACK IF PUBLISHED SUCCESSFULLY ─────────────────────
        if post_id:
            save_published_post(
                title,
                metadata.get("slug", test_slug),
                keyword,
                post_id,
                post_url
            )
    
        results.append({
            "title": title,
            "keyword": keyword,
            "local_file": local_file,
            "post_id": post_id,
            "post_url": post_url,
            "status": "draft" if publish_as_draft else "published"
        })
    
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
    
#def show_published():
#    """Show all tracked published posts"""
#    list_published_posts()

# ─── RUN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        # Show published posts: python3 content_pipeline.py list
        show_published()
    else:
        # Run pipeline normally    
        run_pipeline(
            num_articles=3,        # How many articles to generate
            publish_as_draft=True, # True = draft, False = live
            publish_to_wp=True     # True = send to WordPress
        )
