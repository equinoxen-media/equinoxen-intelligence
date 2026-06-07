

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
    "asana": os.getenv("AFFILIATE_ASANA"),
    "quickbooks": os.getenv("AFFILIATE_QUICKBOOKS"),
    "freshbooks": os.getenv("AFFILIATE_FRESHBOOKS"),
    "zapier": os.getenv("AFFILIATE_ZAPIER"),
    "ahrefs": os.getenv("AFFILIATE_AHREFS"),
    "clickup": os.getenv("AFFILIATE_CLICKUP"),
    "grammarly": os.getenv("AFFILIATE_GRAMMARLY"),
    "canva": os.getenv("AFFILIATE_CANVA"),
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
#Pinterest Board IDs
PINTEREST_BOARDS = {
    "crm": os.getenv("PINTEREST_BOARD_CRM"),
    "email_marketing": os.getenv("PINTEREST_BOARD_EMAIL_MARKETING"),
    "seo_tools": os.getenv("PINTEREST_BOARD_SEO_TOOLS"),
    "project_management": os.getenv("PINTEREST_BOARD_PROJECT_MANAGEMENT"),
    "business_automation": os.getenv("PINTEREST_BOARD_BUSINESS_AUTOMATION"),
    "ai_tools": os.getenv("PINTEREST_BOARD_AI_TOOLS"),
    "finance": os.getenv("PINTEREST_BOARD_FINANCE"),
    "website_builders": os.getenv("PINTEREST_BOARD_WEBSITE_BUILDERS"),
    "general": os.getenv("PINTEREST_BOARD_GENERAL"),
}

# ─── SOCIAL MEDIA CREDENTIALS ─────────────────────────────────
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_ORGANIZATION_ID = os.getenv("LINKEDIN_ORGANIZATION_ID")

PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")

X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_KEY_SECRET = os.getenv("X_CONSUMER_KEY_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#----PINTEREST BOARD CATEGORIES---------------------------------
def get_pinterest_board(category_id):
    """Match WordPress category ID to Pinterest board ID"""
    category_board_map = {
        4: PINTEREST_BOARDS.get("crm"),
        5: PINTEREST_BOARDS.get("email_marketing"),
        6: PINTEREST_BOARDS.get("seo_tools"),
        7: PINTEREST_BOARDS.get("project_management"),
        8: PINTEREST_BOARDS.get("business_automation"),
        9: PINTEREST_BOARDS.get("ai_tools"),
        10: PINTEREST_BOARDS.get("finance"),
        11: PINTEREST_BOARDS.get("website_builders"),
        1: PINTEREST_BOARDS.get("general"),
    }
    return category_board_map.get(category_id, PINTEREST_BOARDS.get("general"))

# ─── SOCIAL POSTING ───────────────────────────────────────────
def post_to_linkedin(title, excerpt, post_url, image_url=None):
    """Post article to LinkedIn company page with optional image"""
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_ORGANIZATION_ID:
        print("   ⚠️  LinkedIn credentials missing — skipping")
        return False

    print("   📤 Posting to LinkedIn...")

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    # Try to upload image to LinkedIn
    image_asset = None
    if image_url:
        try:
            print("   🖼️  Uploading image to LinkedIn...")

            # Step 1 — Register upload
            register_body = {
                "registerUploadRequest": {
                    "owner": f"urn:li:organization:{LINKEDIN_ORGANIZATION_ID}",
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "serviceRelationships": [
                        {
                            "identifier": "urn:li:userGeneratedContent",
                            "relationshipType": "OWNER"
                        }
                    ]
                }
            }

            register_response = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers=headers,
                json=register_body
            )

            if register_response.status_code == 200:
                register_data = register_response.json()
                upload_url = register_data["value"]["uploadMechanism"][
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
                ]["uploadUrl"]
                image_asset = register_data["value"]["asset"]

                # Step 2 — Download image and upload to LinkedIn
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code == 200:
                    content_type = img_response.headers.get("Content-Type", "image/webp")
                    upload_response = requests.put(
                        upload_url,
                        data=img_response.content,
                        headers={"Content-Type": content_type}
                    )
                    if upload_response.status_code in [200, 201]:
                        print("   ✅ Image uploaded to LinkedIn")
                    else:
                        print(f"   ⚠️  Image upload failed: {upload_response.status_code}")
                        image_asset = None
            else:
                print(f"   ⚠️  Image registration failed: {register_response.status_code}")

        except Exception as e:
            print(f"   ⚠️  LinkedIn image upload error: {e}")
            image_asset = None

    post_text = f"{title}\n\n{excerpt}\n\nRead the full article 👇\n{post_url}"

    if image_asset:
        # Post with uploaded image
        post_body = {
            "author": f"urn:li:organization:{LINKEDIN_ORGANIZATION_ID}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_text
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "media": image_asset,
                            "title": {"text": title}
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    else:
        # Fall back to article link without image
        post_body = {
            "author": f"urn:li:organization:{LINKEDIN_ORGANIZATION_ID}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_text
                    },
                    "shareMediaCategory": "ARTICLE",
                    "media": [
                        {
                            "status": "READY",
                            "originalUrl": post_url,
                            "title": {"text": title}
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

    try:
        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=post_body
        )
        if response.status_code in [200, 201]:
            print("   ✅ LinkedIn posted successfully")
            return True
        else:
            print(f"   ❌ LinkedIn failed: {response.status_code} — {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ LinkedIn error: {e}")
        return False

def post_to_x(title, post_url):
    """Post article to X (Twitter)"""
    if not all([X_CONSUMER_KEY, X_CONSUMER_KEY_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        print("   ⚠️  X credentials missing — skipping")
        return False

    print("   📤 Posting to X...")

    try:
        import hmac
        import hashlib
        import base64
        import urllib.parse
        import uuid

        # Build tweet text — max 280 chars
        tweet = f"{title[:200]}... {post_url} #SaaS #BusinessTools"
        if len(tweet) > 280:
            tweet = f"{title[:180]}... {post_url}"

        # OAuth 1.0a signing
        oauth_timestamp = str(int(time.time()))
        oauth_nonce = uuid.uuid4().hex

        oauth_params = {
            "oauth_consumer_key": X_CONSUMER_KEY,
            "oauth_nonce": oauth_nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": oauth_timestamp,
            "oauth_token": X_ACCESS_TOKEN,
            "oauth_version": "1.0"
        }

        post_params = {"text": tweet}
        all_params = {**oauth_params}

        # Build signature base string
        sorted_params = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
            for k, v in sorted(all_params.items())
        )

        base_url = "https://api.twitter.com/2/tweets"
        signature_base = (
            "POST&" +
            urllib.parse.quote(base_url, safe="") +
            "&" +
            urllib.parse.quote(sorted_params, safe="")
        )

        signing_key = (
            urllib.parse.quote(X_CONSUMER_KEY_SECRET, safe="") +
            "&" +
            urllib.parse.quote(X_ACCESS_TOKEN_SECRET, safe="")
        )

        signature = base64.b64encode(
            hmac.new(
                signing_key.encode("utf-8"),
                signature_base.encode("utf-8"),
                hashlib.sha1
            ).digest()
        ).decode("utf-8")

        oauth_params["oauth_signature"] = signature

        auth_header = "OAuth " + ", ".join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )

        response = requests.post(
            base_url,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json"
            },
            json=post_params
        )

        if response.status_code in [200, 201]:
            print("   ✅ X posted successfully")
            return True
        else:
            print(f"   ❌ X failed: {response.status_code} — {response.text[:200]}")
            return False

    except Exception as e:
        print(f"   ❌ X error: {e}")
        return False


def post_to_pinterest(title, excerpt, post_url, board_id, image_url=None):
    """Post article as a Pin to Pinterest"""
    if not PINTEREST_ACCESS_TOKEN or not board_id:
        print("   ⚠️  Pinterest credentials missing — skipping")
        return False

    print("   📤 Posting to Pinterest...")

    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    pin_data = {
        "board_id": board_id,
        "title": title,
        "description": excerpt,
        "link": post_url,
        "media_source": {
            "source_type": "image_url",
            "url": image_url if image_url else f"https://equinoxen.com/wp-content/uploads/equinoxen-default.jpg"
        }
    }

    try:
        response = requests.post(
            "https://api.pinterest.com/v5/pins",
            headers=headers,
            json=pin_data
        )
        if response.status_code in [200, 201]:
            print("   ✅ Pinterest posted successfully")
            return True
        else:
            print(f"   ❌ Pinterest failed: {response.status_code} — {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Pinterest error: {e}")
        return False

def post_to_social(title, excerpt, post_url, category_id=1, image_url=None, pinterest_image_url=None, article_position=0):
    print("\n📱 Posting to social media...")
    time.sleep(2)

    if article_position == 0:
        post_to_linkedin(title, excerpt, post_url, image_url=image_url)
        time.sleep(2)

    post_to_x(title, post_url)
    time.sleep(2)
    
    # ── PINTEREST DISABLED — API pending approval ────────────
   # board_id = get_pinterest_board(category_id)
   # post_to_pinterest(title, excerpt, post_url, board_id, pinterest_image_url or image_url)

    print("   📱 Social posting complete")

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
    
# ─── SUBMIT POST TO INDEXNOW  ────────────────────────
def submit_to_indexnow(post_url):
    """Submit URL to IndexNow for Bing/DuckDuckGo indexing"""
    try:
        payload = {
            "host": "equinoxen.com",
            "key": os.getenv("INDEXNOW_KEY"),
            "keyLocation": f"https://equinoxen.com/{os.getenv('INDEXNOW_KEY')}.txt",
            "urlList": [post_url]
        }
        response = requests.post(
            "https://api.indexnow.org/indexnow",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code in [200, 202]:
            print(f"   ✅ IndexNow submitted: {post_url}")
        else:
            print(f"   ⚠️  IndexNow failed: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  IndexNow error: {e}")

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
            max_tokens=8000,
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
Note: Include {CURRENT_YEAR} in the article title only — not in headings, slug, or keyword references throughout the body.
Primary keyword: {keyword}
Product being reviewed: {product}
Affiliate links to include: {affiliate_links}

ARTICLE REQUIREMENTS:
- Length: 1,200-1,500 words
- Tone: Expert, honest, helpful — never salesy
- Structure: Use H2 and H3 headings
- Natural keyword usage — not stuffed
- Use the exact phrase "{keyword}" at least 3 times naturally in the article
- Include it in the first paragraph, one H2 heading, and the conclusion

REQUIRED STRUCTURE:
1. Introduction — what problem does this solve (100 words)
2. What is [Product] — overview (125 words)
   - Include CTA button here: Try [Product] →
3. Key Features — 3-5 features with H3 subheadings (400 words)
4. Pricing — all tiers clearly explained (150 words)
5. Pros and Cons — honest bullet points (100 words)
   - Include CTA button here: Try [Product] →
6. Who is it best for — specific use cases (100 words)
7. [Product] Alternatives — 2-3 competitors briefly (120 words)
8. Our Verdict — final recommendation with star rating out of 5 (100 words)
9. CTA — Try [Product] with affiliate link
   - Include CTA button here

FORMAT REQUIREMENTS:
- Use HTML formatting (h2, h3, p, ul, li, strong tags)
- Include a star rating like: ⭐⭐⭐⭐⭐ (X/5)
- Make the CTA button: <a href="AFFILIATE_LINK" rel="nofollow sponsored" target="_blank" class="button">Try [Product] →</a>

CRITICAL FORMATTING RULES:
- Do NOT use H1 tags anywhere in the article — the page title is already H1
- Use H2 for all main section headings
- Use H3 for all subsection headings
- Return ONLY raw HTML — no markdown
- Do NOT wrap in ```html or ``` tags
- No preamble or explanation before the HTML
- Never use hyphens or dashes (- or —) in sentences to connect clauses or add parenthetical thoughts
- Instead of a dash, rewrite as a separate sentence or use a comma
- Example WRONG: "HubSpot is a CRM — and a powerful one at that"
- Example CORRECT: "HubSpot is a CRM, and it is one of the most powerful options available"
- Hyphens are only allowed in hyphenated compound words like "well-known" or "data-driven"
- Use powerful, dramatic word choices in the article title and headings
- Use action-driven, benefit-focused language that creates urgency
- Examples of strong title words: Ultimate, Definitive, Proven, Powerful, Essential, Complete, Brutal, Honest, Exposed, Dominate, Crushing, Game-Changing
- Headings should create curiosity or promise a specific outcome

CRITICAL STYLING RULES:
- Do NOT add any inline styles except on tables
- Do NOT add background-color to any element
- Do NOT add style attributes to p, h2, h3, ul, li, div elements
- For tables use only these inline styles:
  - table: style="width:100%; border-collapse:collapse;"
  - th: style="border:1px solid #D4AF37; padding:8px; text-align:left;"
  - td: style="border:1px solid #D4AF37; padding:8px;"
- Use Eclipse Gold #D4AF37 for table borders to match brand colors
- CTA buttons must use: class="button" — this is the only allowed class attribute
- Let the website CSS handle all other visual styling
- No style="..." on any element except table, th, and td

Write the complete article now in HTML format:"""

# ─── COMPARISON ARTICLE PROMPT ────────────────────────────────
def build_comparison_prompt(title, keyword, programs, affiliate_links):
    product1 = programs[0] if len(programs) > 0 else "Product A"
    product2 = programs[1] if len(programs) > 1 else "Product B"
    
    return f"""You are an expert SaaS reviewer writing for {SITE_NAME},  an independent
software review publication. Write a comprehensive, SEO-optimized comparison article.

ARTICLE DETAILS:
Title: {title}
Note: Include {CURRENT_YEAR} in the article title only — not in headings, slug, or keyword references throughout the body.
Primary keyword: {keyword}
Products compared: {product1} vs {product2}
Affiliate links: {affiliate_links}

ARTICLE REQUIREMENTS:
- Length: 1,500-2,000 words
- Tone: Expert, honest, helpful — never salesy
- Structure: Use H2 and H3 headings
- Natural keyword usage — not stuffed
- Use the exact phrase "{keyword}" at least 3 times naturally in the article
- Include it in the first paragraph, one H2 heading, and the conclusion

REQUIRED STRUCTURE:
1. Introduction — why this comparison matters (100 words)
2. Quick Verdict — summary table showing winner in each category (HTML table)
   - Include CTA button here for both products: Try [Product] →
3. {product1} Overview — key features and pricing (250 words)
4. {product2} Overview — key features and pricing (250 words)
5. Head-to-Head Comparison — 5 categories with winner declared each time (500 words)
   - Include CTA button here: Try [Product] →
6. Pricing Comparison — clear breakdown (150 words)
7. Who Should Choose {product1} — specific use cases (100 words)
8. Who Should Choose {product2} — specific use cases (100 words)
9. Final Verdict — clear recommendation (100 words)
10. CTAs for both products with affiliate links

FORMAT: Use HTML with h2, h3, p, ul, li, table tags.
Include comparison table with checkmarks ✓ and ✗
Star ratings for each product. ⭐⭐⭐⭐⭐ (X/5)

CRITICAL FORMATTING RULES:
- Do NOT use H1 tags anywhere in the article — the page title is already H1
- Use H2 for all main section headings
- Use H3 for all subsection headings
- Return ONLY raw HTML — no markdown
- Do NOT wrap in ```html or ``` tags
- No preamble or explanation
- Never use hyphens or dashes (- or —) in sentences to connect clauses or add parenthetical thoughts
- Instead of a dash, rewrite as a separate sentence or use a comma
- Example WRONG: "HubSpot is a CRM — and a powerful one at that"
- Example CORRECT: "HubSpot is a CRM, and it is one of the most powerful options available"
- Hyphens are only allowed in hyphenated compound words like "well-known" or "data-driven"
- Use powerful, dramatic word choices in the article title and headings
- Use action-driven, benefit-focused language that creates urgency
- Examples of strong title words: Ultimate, Definitive, Proven, Powerful, Essential,>
- Headings should create curiosity or promise a specific outcome

CRITICAL STYLING RULES:
- Do NOT add any inline styles except on tables
- Do NOT add background-color to any element
- Do NOT add style attributes to p, h2, h3, ul, li, div elements
- For tables use only these inline styles:
  - table: style="width:100%; border-collapse:collapse;"
  - th: style="border:1px solid #D4AF37; padding:8px; text-align:left;"
  - td: style="border:1px solid #D4AF37; padding:8px;"
- Use Eclipse Gold #D4AF37 for table borders to match brand colors
- CTA buttons must use: class="button" — this is the only allowed class attribute
- Let the website CSS handle all other visual styling
- No style="..." on any element except table, th, and td

Write the complete article now in HTML:"""

# ─── BUYING GUIDE PROMPT ──────────────────────────────────────
def build_buying_guide_prompt(title, keyword, programs, affiliate_links):
    return f"""You are an expert SaaS reviewer writing for {SITE_NAME}, an independent
software review publication. Write a comprehensive, SEO-optimized buying guidearticle.

ARTICLE DETAILS:
Title: {title}
Note: Include {CURRENT_YEAR} in the article title only — not in headings, slug, or keyword references throughout the body.
Primary keyword: {keyword}
Products to feature: {', '.join(programs)}
Affiliate links: {affiliate_links}

ARTICLE REQUIREMENTS:
- Length: 1,500-2,000 words
- Tone: Expert, honest, helpful — never salesy
- Structure: Use H2 and H3 headings
- Natural keyword usage — not stuffed
- Use the exact phrase "{keyword}" at least 3 times naturally in the article
- Include it in the first paragraph, one H2 heading, and the conclusion

REQUIRED STRUCTURE:
1. Introduction — why this category matters (100 words)
2. What to look for — buying criteria with H3 subheadings (200 words)
3. Top picks — 3-5 products each ending with an affiliate CTA button (800 words total section):
   - Brief overview
   - Key features
   - Pricing
   - Best for
   - Affiliate link CTA
4. Comparison table — all products side by side (HTML table)
5. How to choose — decision framework (200 words)
6. Final recommendations — top 3 for different needs (150 words)

FORMAT: Use HTML. Include star ratings. ⭐⭐⭐⭐⭐ (X/5)
Each product section should have an affiliate CTA button.

CRITICAL FORMATTING RULES:
- Do NOT use H1 tags anywhere in the article — the page title is already H1
- Use H2 for all main section headings
- Use H3 for all subsection headings
- Return ONLY raw HTML — no markdown
- Do NOT wrap in ```html or ``` tags
- No preamble or explanation
- Never use hyphens or dashes (- or —) in sentences to connect clauses or add parenthetical thoughts
- Instead of a dash, rewrite as a separate sentence or use a comma
- Example WRONG: "HubSpot is a CRM — and a powerful one at that"
- Example CORRECT: "HubSpot is a CRM, and it is one of the most powerful options available"
- Hyphens are only allowed in hyphenated compound words like "well-known" or "data-driven"
- Use powerful, dramatic word choices in the article title and headings
- Use action-driven, benefit-focused language that creates urgency
- Examples of strong title words: Ultimate, Definitive, Proven, Powerful, Essential,>
- Headings should create curiosity or promise a specific outcome

CRITICAL STYLING RULES:
- Do NOT add any inline styles except on tables
- Do NOT add background-color to any element
- Do NOT add style attributes to p, h2, h3, ul, li, div elements
- For tables use only these inline styles:
  - table: style="width:100%; border-collapse:collapse;"
  - th: style="border:1px solid #D4AF37; padding:8px; text-align:left;"
  - td: style="border:1px solid #D4AF37; padding:8px;"
- Use Eclipse Gold #D4AF37 for table borders to match brand colors
- CTA buttons must use: class="button" — this is the only allowed class attribute
- Let the website CSS handle all other visual styling
- No style="..." on any element except table, th, and td

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

- slug must not contain the year
- focus_keyword must not contain the year

Return this exact JSON structure:
{{"seo_title": "max 60 chars with keyword", "meta_description": "max 155 chars with keyword and CTA", "excerpt": "2 sentence article summary", "slug": "url-friendly-slug-with-keyword-no-year", "focus_keyword": "{keyword}"}}"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response = message.content[0].text.strip()
        response = response.replace('```json', '').replace('```', '').strip()
        data = json.loads(response)

        # Trim slug to 75 chars, cut at last hyphen to avoid breaking a word
        slug = data.get("slug", "")
        if len(slug) > 75:
            slug = slug[:75].rsplit('-', 1)[0]
            data["slug"] = slug

        return data
        
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

#---- STEP 4.1  CREATE IMAGE -----
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


def upload_image_to_wordpress(image_url, title, alt_text=""):
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
           
            if alt_text and media_id:
                requests.post(
                    f"{media_url}/{media_id}",
                    json={"alt_text": alt_text},
                    auth=(WP_USER, WP_PASS)
                )
            
            print(f"   ✅ Image uploaded — Media ID: {media_id}")
            return media_id
        else:
            print(f"   ⚠️  Image upload failed: {media_response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ⚠️  Image upload error: {e}")
        return None

def generate_branded_image(title, keyword, programs=None, orientation="landscape"):
    """Generate featured image using gpt-image-2 via OpenAI API"""
    try:
        import openai
        import io
        from PIL import Image
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("   ⚠️  No OPENAI_API_KEY — skipping AI image generation")
            return None, None
        
        client = openai.OpenAI(api_key=openai_key)
        
        print(f"   🎨 Generating {orientation} AI image for: {title}")
        
        # Build color hints
        color_hints = {
            "hubspot": "orange accents",
            "monday": "vibrant red and yellow accents",
            "semrush": "orange and blue accents",
            "notion": "black and white minimal accents",
            "webflow": "blue accents",
            "zoho": "red accents",
            "asana": "coral pink accents",
            "klaviyo": "green accents",
            "quickbooks": "green accents",
            "freshbooks": "teal accents",
            "zapier": "orange accents",
            "ahrefs": "blue and orange accents",
            "clickup": "purple accents",
            "grammarly": "green accents",
            "unbounce": "purple and teal accents",
            "jotform": "orange and purple accents",
            "canva": "purple and turquoise accents",
        }
        
        accent_colors = []
        if programs:
            for program in programs:
                for key, color in color_hints.items():
                    if key in program.lower() and color not in accent_colors:
                        accent_colors.append(color)
        
        color_instruction = f"Subtle {', '.join(accent_colors)} incorporated into the design" if accent_colors else "Eclipse Gold accents"
        
        # Size and composition based on orientation
        if orientation == "portrait":
            size = "1024x1536"
            composition = "vertical Pinterest-style composition with strong visual flow from top to bottom"
        else:
            size = "1536x1024"
            composition = "horizontal landscape composition optimized for blog featured image display"
        
        prompt = f"""Create a professional featured image for a blog post titled: '{title}'

Style requirements:
- {composition}
- Flat-lay image style
- All critical design elements centered in the frame
- Clean, modern, professional business/tech aesthetic
- Suitable for a SaaS software review publication
- No text, typography, logos, brand marks, or recognizable company symbols in the image
- Visual metaphor representing the topic: {keyword}
- Dark sophisticated base with gold as primary accents
- Use ALL of these colors as subtle accent elements throughout the design: {color_instruction}
- Each accent color should appear as a separate visible design element
- High contrast, visually striking"""

        response = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            size=size,
            quality="medium",
            n=1,
        )
        
        import base64
        image_data = base64.b64decode(response.data[0].b64_json)
        
        # Convert to webp
        img = Image.open(io.BytesIO(image_data))
        webp_bytes = io.BytesIO()
        img.save(webp_bytes, format='WEBP', quality=70, method=6, optimize=True)
        webp_bytes.seek(0)
        image_data = webp_bytes.getvalue()
        
        print(f"   ✅ {orientation.capitalize()} image generated ({len(image_data) // 1024}KB)")
        return image_data, None
        
    except ImportError:
        print("   ⚠️  openai or Pillow not installed")
        return None, None
    except Exception as e:
        print(f"   ⚠️  Image generation error: {e}")
        return None, None

def upload_branded_image_to_wordpress(title, keyword, programs=None):
    """Generate and upload landscape for WordPress and portrait for Pinterest"""
    try:
        print(f"   🎨 Generating AI featured images...")
        
        base_filename = keyword.lower().replace(' ', '-')[:50]
        
        # Landscape for WordPress featured image
        landscape_data, _ = generate_branded_image(title, keyword, programs, orientation="landscape")
        landscape_id = None
        wordpress_image_url = None
        if landscape_data:
            landscape_id, wordpress_image_url = upload_single_image(
                landscape_data,
                f"{base_filename}-featured.webp",
                "image/webp",
                alt_text=keyword
            )
        
        # ── PINTEREST IMAGE DISABLED — API pending approval ────────────

        # Portrait for Pinterest
#        portrait_data, _ = generate_branded_image(title, keyword, programs, orientation="portrait")
#        pinterest_image_url = None
#        if portrait_data:
#            _, pinterest_image_url = upload_single_image(
#                portrait_data,
#                f"{base_filename}-pinterest.webp",
#                "image/webp",
#                alt_text=keyword
#            )
        pinterest_image_url = None  # ← set to None while pinterest disabled 
        
        return landscape_id, wordpress_image_url, pinterest_image_url
        
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return None, None, None

def upload_single_image(img_data, filename, content_type, alt_text=""):
    """Upload a single image to WordPress media library"""
    try:
        media_url = f"{WP_URL}/wp-json/wp/v2/media"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": content_type
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
            
            # Update alt text
            if alt_text and media_id:
                requests.post(
                    f"{media_url}/{media_id}",
                    json={"alt_text": alt_text},
                    auth=(WP_USER, WP_PASS)
                )
            
            return media_id, media.get("source_url")
        return None, None
    except Exception as e:
        print(f"   ⚠️  Upload error: {e}")
        return None, None

# ─── STEP 5: PUBLISH TO WORDPRESS ─────────────────────────────
def publish_to_wordpress(title, content, metadata, category_id, draft=True, featured_image_id=None):
    """Publish article to WordPress via REST API"""
    
    status = "draft" if draft else "publish"
    print(f"\n📤 Publishing to WordPress as {status}...")
    
    api_url = f"{WP_URL}/wp-json/wp/v2/posts"
    
    focus_keyword = metadata.get("focus_keyword", "")
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
            "rank_math_focus_keyword": focus_keyword,
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
            
            # Trigger WordPress hooks by immediately updating the post
            # This fires save_post/transition_post_status so it appears on blog index
            time.sleep(2)
            try:
                requests.post(
                    f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                    json={"status": "publish"},
                    auth=(WP_USER, WP_PASS),
                    headers={"Content-Type": "application/json"}
                )
                print(f"   🔄 WordPress hooks triggered")
            except Exception as e:
                print(f"   ⚠️  Hook trigger failed: {e}")
    
            # Push Rank Math focus keyword directly via post meta endpoint
            if post_id and focus_keyword:
                try:
#                    requests.post(
#                        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
#                        json={
#                            "meta": {
#                                "rank_math_focus_keyword": focus_keyword
#                            }
#                        },
#                        auth=(WP_USER, WP_PASS),
#                        headers={"Content-Type": "application/json"}
#                    )
                    requests.post(
                        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                        json={
                            "rank_math_focus_keyword": focus_keyword
                        },
                        auth=(WP_USER, WP_PASS),
                        headers={"Content-Type": "application/json"}
                    )
                    print(f"   🎯 Rank Math focus keyword set: {focus_keyword}")

                except Exception as e:
                    print(f"   ⚠️  Focus keyword error: {e}")
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

# ─── STEP 7: CLEANUP OLD FILES ────────────────────────────────────────────
def cleanup_old_files():
    """Keep last 7 intelligence reports and last 9 article files, delete the rest"""
    import glob
    
    # Keep last 7 intelligence reports
    reports = sorted(glob.glob("intelligence_report_*.json"))
    for old_report in reports[:-7]:
        os.remove(old_report)
        print(f"   🧹 Removed old report: {old_report}")
    
    # Keep last 9 article HTML files
    articles = sorted(glob.glob("article_*.html"))
    for old_article in articles[:-9]:
        os.remove(old_article)
        print(f"   🧹 Removed old article: {old_article}")
    
    print("   ✅ Cleanup complete")

# ─── MAIN PIPELINE ────────────────────────────────────────────
def run_pipeline(num_articles=3, publish_as_draft=False, publish_to_wp=True):
    print("=" * 60)
    print("  EQUINOXEN MEDIA — CONTENT PIPELINE")
    print(f"  Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Target: {num_articles} articles")
    print("=" * 60)
    
    intelligence = load_latest_intelligence()
    if not intelligence:
        return
    
    opportunities = intelligence.get('top_opportunities', [])
    if not opportunities:
        print("❌ No opportunities found in intelligence report")
        return
    
    print(f"\n📋 Found {len(opportunities)} opportunities")
    
    results = []
    published_count = 0  # Track successful publishes
    linkedin_posted = False  # Track LinkedIn — only post once
    opp_index = 0  # Track position in opportunity list
    
    while published_count < num_articles and opp_index < len(opportunities):
        opp = opportunities[opp_index]
        opp_index += 1
        
        print(f"\n{'='*60}")
        print(f"  ARTICLE {published_count + 1} of {num_articles} (opportunity {opp_index} of {len(opportunities)})")
        print(f"{'='*60}")
       
        title = opp.get('title', '')
        keyword = opp.get('keyword', '')
        test_slug = keyword.lower().replace(' ', '-')
       
        # ── CHECK IF ALREADY PUBLISHED ──────────────────────────
        already_done, reason = is_already_published(title, keyword, test_slug)
        if already_done:
            print(f"⏭️  Skipping — already published ({reason} match):")
            print(f"   {title}")
            continue
        
        if check_wordpress_for_duplicate(test_slug):
            print(f"⏭️  Skipping — already exists in WordPress")
            print(f"   {title}")
            continue
        
        # Generate article
        article_content = generate_article(opp)
        if not article_content:
            continue
        
        # Generate metadata
        metadata = generate_seo_metadata(title, keyword, article_content)
        
        # Assign category
        category_id = assign_category(keyword, opp.get('programs', []))
       
        # Save locally
        local_file = save_article_locally(title, article_content, metadata)
       
        # Get featured image
        featured_image_id = None
        image_url = None
        pinterest_image_url = None  # ← add this
        if publish_to_wp:
            featured_image_id, image_url, pinterest_image_url = upload_branded_image_to_wordpress(
                title,
                keyword,
                programs=opp.get('programs', [])
            )
            if not featured_image_id:
                unsplash_url = get_featured_image_unsplash(keyword)
                if unsplash_url:
                    featured_image_id = upload_image_to_wordpress(unsplash_url, title, alt_text=keyword)
                    image_url = unsplash_url
                    pinterest_image_url = unsplash_url
        
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
            published_count += 1  # Only increment on successful publish
    
        # ── POST TO SOCIAL MEDIA ─────────────────────────────────
        if post_id and not publish_as_draft:
            post_to_social(
                title,
                metadata.get("excerpt", ""),
                post_url,
                category_id=category_id,
                image_url=image_url,
                pinterest_image_url=pinterest_image_url,
                article_position=0 if not linkedin_posted else 1
            )
            linkedin_posted = True  # LinkedIn only gets the first successful post
    
        results.append({
            "title": title,
            "keyword": keyword,
            "local_file": local_file,
            "post_id": post_id,
            "post_url": post_url,
            "status": "draft" if publish_as_draft else "published"
        })
    
        if published_count < num_articles:
            print(f"\n⏳ Waiting 5 seconds before next article...")
            time.sleep(5)
    
        # ── SUBMIT TO INDEXNOW  ─────────────────────────────────
        if post_id and post_url:
            submit_to_indexnow(post_url)
    
        # ── SUBMIT TO GOOGLE INDEXING ─────────────────────────────────
    
    # Final summary
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\n✅ Published {published_count} of {num_articles} target articles:")
    for r in results:
        print(f"\n  📄 {r['title']}")
        print(f"     Keyword: {r['keyword']}")
        print(f"     Local: {r['local_file']}")
        if r['post_url']:
            print(f"     WordPress: {r['post_url']}")
        print(f"     Status: {r['status']}")
    
    if published_count < num_articles:
        print(f"\n⚠️  Only published {published_count} of {num_articles} — run intelligence.py for fresh opportunities")
    
    print("\n💡 Next steps:")
    print("   1. Review articles in WordPress")
    print("   2. Verify affiliate links are working")
    
    cleanup_old_files()
    return results
    
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
            publish_as_draft=False, # True = draft, False = live
            publish_to_wp=True     # True = send to WordPress
        )
