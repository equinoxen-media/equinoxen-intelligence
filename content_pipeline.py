import os
import json
import time
import requests
import anthropic
from datetime import datetime
import zoneinfo
from dotenv import load_dotenv
import re
import glob

load_dotenv()

# ─── CONFIGURATION ────────────────────────────────────────────
WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WORDPRESS_USERNAME")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD")

AFFILIATE_LINKS = {
    # ── CRM & Sales ──────────────────────────────────────────
    "hubspot": os.getenv("AFFILIATE_HUBSPOT"),
    "zoho": os.getenv("AFFILIATE_ZOHO"),
    "pipedrive": os.getenv("AFFILIATE_PIPEDRIVE"),
    "salesforce": os.getenv("AFFILIATE_SALESFORCE"),
    "copper": os.getenv("AFFILIATE_COPPER"),
    "keap": os.getenv("AFFILIATE_KEAP"),
    "nimble": os.getenv("AFFILIATE_NIMBLE"),
    "close": os.getenv("AFFILIATE_CLOSE"),

    # ── Email Marketing ───────────────────────────────────────
    "klaviyo": os.getenv("AFFILIATE_KLAVIYO"),
    "activecampaign": os.getenv("AFFILIATE_ACTIVECAMPAIGN"),
    "getresponse": os.getenv("AFFILIATE_GETRESPONSE"),
    "brevo": os.getenv("AFFILIATE_BREVO"),
    "constantcontact": os.getenv("AFFILIATE_CONSTANTCONTACT"),
    "drip": os.getenv("AFFILIATE_DRIP"),
    "mailerlite": os.getenv("AFFILIATE_MAILERLITE"),

    # ── Project Management ────────────────────────────────────
    "monday": os.getenv("AFFILIATE_MONDAY"),
    "notion": os.getenv("AFFILIATE_NOTION"),
    "asana": os.getenv("AFFILIATE_ASANA"),
    "clickup": os.getenv("AFFILIATE_CLICKUP"),
    "wrike": os.getenv("AFFILIATE_WRIKE"),
    "smartsheet": os.getenv("AFFILIATE_SMARTSHEET"),
    "teamwork": os.getenv("AFFILIATE_TEAMWORK"),
    "basecamp": os.getenv("AFFILIATE_BASECAMP"),
    "hive": os.getenv("AFFILIATE_HIVE"),
    "todoist": os.getenv("AFFILIATE_TODOIST"),

    # ── SEO Tools ─────────────────────────────────────────────
    "semrush": os.getenv("AFFILIATE_SEMRUSH"),
    "ahrefs": os.getenv("AFFILIATE_AHREFS"),
    "moz": os.getenv("AFFILIATE_MOZ"),
    "mangools": os.getenv("AFFILIATE_MANGOOLS"),
    "serpstat": os.getenv("AFFILIATE_SERPSTAT"),
    "seranking": os.getenv("AFFILIATE_SERANKING"),
    "spyfu": os.getenv("AFFILIATE_SPYFU"),
    "ubersuggest": os.getenv("AFFILIATE_UBERSUGGEST"),

    # ── Business Automation ───────────────────────────────────
    "zapier": os.getenv("AFFILIATE_ZAPIER"),
    "make": os.getenv("AFFILIATE_MAKE"),
    "n8n": os.getenv("AFFILIATE_N8N"),
    "pabbly": os.getenv("AFFILIATE_PABBLY"),
    "integrately": os.getenv("AFFILIATE_INTEGRATELY"),

    # ── AI Tools ─────────────────────────────────────────────
    "grammarly": os.getenv("AFFILIATE_GRAMMARLY"),
    "jasper": os.getenv("AFFILIATE_JASPER"),
    "copyai": os.getenv("AFFILIATE_COPYAI"),
    "writesonic": os.getenv("AFFILIATE_WRITESONIC"),
    "surferseo": os.getenv("AFFILIATE_SURFERSEO"),
    "frase": os.getenv("AFFILIATE_FRASE"),
    "descript": os.getenv("AFFILIATE_DESCRIPT"),
    "canva": os.getenv("AFFILIATE_CANVA"),

    # ── Finance ───────────────────────────────────────────────
    "quickbooks": os.getenv("AFFILIATE_QUICKBOOKS"),
    "freshbooks": os.getenv("AFFILIATE_FRESHBOOKS"),
    "xero": os.getenv("AFFILIATE_XERO"),
    "wave": os.getenv("AFFILIATE_WAVE"),
    "sage": os.getenv("AFFILIATE_SAGE"),
    "bench": os.getenv("AFFILIATE_BENCH"),
    "melio": os.getenv("AFFILIATE_MELIO"),
    "patriot": os.getenv("AFFILIATE_PATRIOT"),

    # ── Website Builders & Landing Pages ─────────────────────
    "webflow": os.getenv("AFFILIATE_WEBFLOW"),
    "unbounce": os.getenv("AFFILIATE_UNBOUNCE"),
    "instapage": os.getenv("AFFILIATE_INSTAPAGE"),
    "swipepages": os.getenv("AFFILIATE_SWIPEPAGES"),
    "elementor": os.getenv("AFFILIATE_ELEMENTOR"),
    "divi": os.getenv("AFFILIATE_DIVI"),
    "squarespace": os.getenv("AFFILIATE_SQUARESPACE"),
    "carrd": os.getenv("AFFILIATE_CARRD"),

    # ── Form Builders ─────────────────────────────────────────
    "jotform": os.getenv("AFFILIATE_JOTFORM"),
    "typeform": os.getenv("AFFILIATE_TYPEFORM"),
    "paperform": os.getenv("AFFILIATE_PAPERFORM"),
    "cognitoforms": os.getenv("AFFILIATE_COGNITOFORMS"),
    "123formbuilder": os.getenv("AFFILIATE_123FORMBUILDER"),
}

SITE_NAME = "Equinoxen Media"
SITE_URL = "https://equinoxen.com"
CURRENT_YEAR = datetime.now().year

# Category IDs from WordPress
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

# Pinterest Board IDs
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

# ─── API CREDENTIALS ──────────────────────────────────────────
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_ORGANIZATION_ID = os.getenv("LINKEDIN_ORGANIZATION_ID")

PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")

X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_KEY_SECRET = os.getenv("X_CONSUMER_KEY_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

DEVTO_API_KEY = os.getenv("DEVTO_API_KEY")
INDEXNOW_KEY = os.getenv("INDEXNOW_KEY")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google-service-account.json")

# ─── PINTEREST BOARD CATEGORIES ───────────────────────────────
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

# ─── LINKEDIN DAILY GATE ──────────────────────────────────────
def _linkedin_posted_today() -> bool:
    flag_file = ".linkedin_posted_date"
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(flag_file):
        return open(flag_file).read().strip() == today
    return False

def _mark_linkedin_posted():
    with open(".linkedin_posted_date", "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))

def _is_linkedin_window() -> bool:
    """Post to LinkedIn during the 10am-12pm Pacific window"""
    pacific = datetime.now(zoneinfo.ZoneInfo("America/Los_Angeles"))
    return 10 <= pacific.hour <= 12

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

    image_asset = None
    if image_url:
        try:
            print("   🖼️  Uploading image to LinkedIn...")
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
        post_body = {
            "author": f"urn:li:organization:{LINKEDIN_ORGANIZATION_ID}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "IMAGE",
                    "media": [{"status": "READY", "media": image_asset, "title": {"text": title}}]
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
    else:
        post_body = {
            "author": f"urn:li:organization:{LINKEDIN_ORGANIZATION_ID}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "ARTICLE",
                    "media": [{"status": "READY", "originalUrl": post_url, "title": {"text": title}}]
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
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

        tweet = f"{title[:200]}... {post_url} #SaaS #BusinessTools"
        if len(tweet) > 280:
            tweet = f"{title[:180]}... {post_url}"

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

        sorted_params = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
            for k, v in sorted(oauth_params.items())
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
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
            json={"text": tweet}
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
        "is_ai_generated": True,
        "media_source": {
            "source_type": "image_url",
            "url": image_url if image_url else "https://equinoxen.com/wp-content/uploads/equinoxen-default.jpg"
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


# ─── DEV.TO ───────────────────────────────────────────────────
def generate_devto_summary(title, keyword, article_html, canonical_url, excerpt=None):
    """Generate a Dev.to-friendly Markdown summary of the article."""
    print("   ✍️  Generating Dev.to summary...")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    if excerpt:
        excerpt_for_prompt = excerpt
    else:
        clean_text = re.sub(r'<[^>]+>', ' ', article_html)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        excerpt_for_prompt = clean_text[:1500]

    prompt = f"""Write a Dev.to post that teases this article without reproducing it fully.

Article title: {title}
Primary keyword: {keyword}
Article excerpt: {excerpt_for_prompt}
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
            messages=[{"role": "user", "content": prompt}]
        )
        body = message.content[0].text.strip()
        print(f"   ✅ Dev.to summary generated ({len(body)} chars)")
        return body
    except Exception as e:
        print(f"   ⚠️  Dev.to summary error: {e}")
        return (
            f"## {title}\n\n"
            f"Looking for the best {keyword}? We broke it all down in our latest independent review.\n\n"
            f"**👉 Read the full breakdown: [{title}]({canonical_url})**\n\n"
            f"---\nTAGS: saas, software, productivity, reviews"
        )


def post_to_devto(title, keyword, article_html, canonical_url, cover_image_url=None, excerpt=None):
    """Publish a teaser article to Dev.to with canonical_url pointing back to Equinoxen."""
    if not DEVTO_API_KEY:
        print("   ⚠️  DEVTO_API_KEY missing — skipping Dev.to")
        return False

    if not canonical_url:
        print("   ⚠️  Dev.to skipped — no canonical URL")
        return False

    print("   📤 Posting to Dev.to...")

    markdown_body = generate_devto_summary(
        title, keyword, article_html, canonical_url, excerpt=excerpt
    )

    if not markdown_body or len(markdown_body) < 50:
        print(f"   ⚠️  Dev.to skipped — markdown body too short")
        return False

    tags = ["saas", "software", "productivity", "reviews"]
    lines = markdown_body.strip().splitlines()
    for i, line in enumerate(lines):
        if line.strip().upper().startswith("TAGS:"):
            raw_tags = line.split(":", 1)[1]
            parsed = [t.strip().lower().replace(" ", "") for t in raw_tags.split(",")]
            parsed = [t for t in parsed if t][:4]
            if parsed:
                tags = parsed
            markdown_body = "\n".join(
                l for l in lines[:i] if l.strip() != "---"
            ).strip()
            break

    article_payload = {
        "article": {
            "title": title,
            "published": True,
            "body_markdown": markdown_body,
            "canonical_url": canonical_url,
            "tags": tags,
        }
    }

    if cover_image_url:
        article_payload["article"]["main_image"] = cover_image_url

    try:
        response = requests.post(
            "https://dev.to/api/articles",
            headers={"api-key": DEVTO_API_KEY, "Content-Type": "application/json"},
            json=article_payload,
            timeout=30
        )

        if response.status_code in [200, 201]:
            data = response.json()
            devto_url = data.get("url", "")
            print(f"   ✅ Dev.to posted successfully")
            print(f"   🔗 Dev.to URL: {devto_url}")
            return True
        else:
            print(f"   ❌ Dev.to failed: {response.status_code} — {response.text[:300]}")
            return False

    except Exception as e:
        print(f"   ❌ Dev.to error: {e}")
        return False


# ─── SOCIAL ORCHESTRATOR ──────────────────────────────────────
def post_to_social(title, excerpt, post_url, category_id=1, image_url=None,
                   pinterest_image_url=None, article_html=None, keyword=None):
    print("\n📱 Posting to social media...")
    time.sleep(2)

    if _is_linkedin_window() and not _linkedin_posted_today():
        post_to_linkedin(title, excerpt, post_url, image_url=image_url)
        _mark_linkedin_posted()
    elif _linkedin_posted_today():
        print("   ⏭️  LinkedIn — already posted today")
    else:
        print("   ⏭️  LinkedIn — outside posting window (10am-12pm Pacific)")
    time.sleep(2)

    post_to_x(title, post_url)
    time.sleep(2)

    if article_html and keyword and post_url:
        post_to_devto(
            title=title,
            keyword=keyword,
            article_html=article_html,
            canonical_url=post_url,
            cover_image_url=image_url,
            excerpt=excerpt,
        )
        time.sleep(2)
    else:
        print("   ⏭️  Dev.to — missing article_html or keyword, skipping")

    # ── PINTEREST DISABLED — API pending approval ─────────────
    # board_id = get_pinterest_board(category_id)
    # post_to_pinterest(title, excerpt, post_url, board_id, pinterest_image_url or image_url)

    print("   📱 Social posting complete")


# ─── PUBLISHED POSTS TRACKER ──────────────────────────────────
PUBLISHED_TRACKER = "published_posts.json"

def load_published_posts():
    if os.path.exists(PUBLISHED_TRACKER):
        with open(PUBLISHED_TRACKER, 'r') as f:
            return json.load(f)
    return {"slugs": [], "titles": [], "keywords": []}

def save_published_post(title, slug, keyword, post_id, post_url, comparison_key=None):
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
    if comparison_key:
        tracker["comparison_keys"] = tracker.get("comparison_keys", [])
        tracker["comparison_keys"].append(comparison_key)
    with open(PUBLISHED_TRACKER, 'w') as f:
        json.dump(tracker, f, indent=2)
    print(f"   📝 Tracked: {title}")

def is_already_published(title, keyword, slug):
    tracker = load_published_posts()
    if slug in tracker.get("slugs", []):
        return True, "slug"
    if keyword.lower() in tracker.get("keywords", []):
        return True, "keyword"
    if title.lower() in tracker.get("titles", []):
        return True, "title"
    return False, None

def list_published_posts():
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
    list_published_posts()

def clean_html_response(text):
    text = text.strip()
    if text.startswith('```html'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    return text.strip()

def get_published_urls():
    tracker = load_published_posts()
    posts = tracker.get("posts", [])
    return [{"title": p["title"], "url": p["post_url"], "keyword": p["keyword"]} for p in posts if p.get("post_url")]

def normalize_comparison_key(keyword, programs):
    if programs and len(programs) >= 2:
        normalized = sorted(p.lower().strip() for p in programs[:2])
        return "+".join(normalized)
    return re.sub(r'\b(20\d{2}|review|comparison|vs)\b', '', keyword.lower()).strip()

# ─── SUBMIT TO INDEXNOW ───────────────────────────────────────
def submit_to_indexnow(post_url):
    try:
        payload = {
            "host": "equinoxen.com",
            "key": INDEXNOW_KEY,
            "keyLocation": f"https://equinoxen.com/{INDEXNOW_KEY}.txt",
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

# ─── SUBMIT TO GOOGLE INDEXING API ───────────────────────────
def submit_to_google(post_url):
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/indexing"]
        )
        service = build("indexing", "v3", credentials=credentials)
        response = service.urlNotifications().publish(
            body={"url": post_url, "type": "URL_UPDATED"}
        ).execute()
        submitted_url = response.get("urlNotificationMetadata", {}).get("url", "unknown")
        print(f"   ✅ Google Indexing API submitted: {submitted_url}")
    except FileNotFoundError:
        print(f"   ⚠️  Service account file not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")
    except Exception as e:
        print(f"   ⚠️  Google Indexing API error: {e}")

# ─── STEP 1: LOAD INTELLIGENCE REPORT ────────────────────────
def load_latest_intelligence():
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
    title = opportunity.get('title', '')
    keyword = opportunity.get('keyword', '')
    content_type = opportunity.get('type', 'review')
    programs = opportunity.get('programs', [])

    print(f"\n✍️  Generating article: {title}")
    print(f"   Keyword: {keyword}")
    print(f"   Type: {content_type}")

    affiliate_info = []
    for program in programs:
        program_lower = program.lower().replace(" ", "").replace(".", "").replace("-", "")
        for key, link in AFFILIATE_LINKS.items():
            key_clean = key.replace(" ", "").replace(".", "").replace("-", "")
            if key_clean in program_lower and link:
                affiliate_info.append(f"{program}: {link}")

    affiliate_str = "\n".join(affiliate_info) if affiliate_info else "Use placeholder [AFFILIATE_LINK] where needed"

    published_posts = get_published_urls()
    internal_links_str = "\n".join(
        f"- {p['title']}: {p['url']}" for p in published_posts
    ) if published_posts else "None yet"

    if content_type == "review":
        prompt = build_review_prompt(title, keyword, programs, affiliate_str, internal_links_str)
    elif content_type == "comparison":
        prompt = build_comparison_prompt(title, keyword, programs, affiliate_str, internal_links_str)
    else:
        prompt = build_buying_guide_prompt(title, keyword, programs, affiliate_str, internal_links_str)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )
        content = message.content[0].text
        content = clean_html_response(content)
        print(f"   ✅ Article generated ({len(content)} characters)")
        return content
    except Exception as e:
        print(f"   ❌ Generation error: {e}")
        return None

# ─── REVIEW ARTICLE PROMPT ────────────────────────────────────
def build_review_prompt(title, keyword, programs, affiliate_links, internal_links_str):
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

INTERNAL LINKING:
Where naturally relevant, link to these existing articles on the site:
{internal_links_str}
Use descriptive anchor text matching the linked article's topic.
Add 2-3 internal links maximum — only where genuinely relevant, never forced.

Write the complete article now in HTML format:"""

# ─── COMPARISON ARTICLE PROMPT ────────────────────────────────
def build_comparison_prompt(title, keyword, programs, affiliate_links, internal_links_str):
    product1 = programs[0] if len(programs) > 0 else "Product A"
    product2 = programs[1] if len(programs) > 1 else "Product B"

    return f"""You are an expert SaaS reviewer writing for {SITE_NAME}, an independent
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

INTERNAL LINKING:
Where naturally relevant, link to these existing articles on the site:
{internal_links_str}
Use descriptive anchor text matching the linked article's topic.
Add 2-3 internal links maximum — only where genuinely relevant, never forced.

Write the complete article now in HTML:"""

# ─── BUYING GUIDE PROMPT ──────────────────────────────────────
def build_buying_guide_prompt(title, keyword, programs, affiliate_links, internal_links_str):
    return f"""You are an expert SaaS reviewer writing for {SITE_NAME}, an independent
software review publication. Write a comprehensive, SEO-optimized buying guide article.

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

INTERNAL LINKING:
Where naturally relevant, link to these existing articles on the site:
{internal_links_str}
Use descriptive anchor text matching the linked article's topic.
Add 2-3 internal links maximum — only where genuinely relevant, never forced.

Write the complete article now in HTML:"""

# ─── STEP 3: GENERATE SEO METADATA ───────────────────────────
def generate_seo_metadata(title, keyword, article_content):
    print("   🔍 Generating SEO metadata...")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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
    keyword_lower = keyword.lower()

    category_map = {
        # ── CRM ──────────────────────────────────────────────
        "crm": CATEGORIES.get("crm", 1),
        "salesforce": CATEGORIES.get("crm", 1),
        "hubspot": CATEGORIES.get("crm", 1),
        "zoho": CATEGORIES.get("crm", 1),
        "pipedrive": CATEGORIES.get("crm", 1),
        "copper": CATEGORIES.get("crm", 1),
        "keap": CATEGORIES.get("crm", 1),
        "nimble": CATEGORIES.get("crm", 1),
        "close crm": CATEGORIES.get("crm", 1),

        # ── Email Marketing ───────────────────────────────────
        "email": CATEGORIES.get("email_marketing", 1),
        "mailchimp": CATEGORIES.get("email_marketing", 1),
        "klaviyo": CATEGORIES.get("email_marketing", 1),
        "omnisend": CATEGORIES.get("email_marketing", 1),
        "convertkit": CATEGORIES.get("email_marketing", 1),
        "newsletter": CATEGORIES.get("email_marketing", 1),
        "activecampaign": CATEGORIES.get("email_marketing", 1),
        "getresponse": CATEGORIES.get("email_marketing", 1),
        "brevo": CATEGORIES.get("email_marketing", 1),
        "sendinblue": CATEGORIES.get("email_marketing", 1),
        "constant contact": CATEGORIES.get("email_marketing", 1),
        "drip": CATEGORIES.get("email_marketing", 1),
        "mailerlite": CATEGORIES.get("email_marketing", 1),

        # ── SEO Tools ─────────────────────────────────────────
        "seo": CATEGORIES.get("seo_tools", 1),
        "semrush": CATEGORIES.get("seo_tools", 1),
        "ahrefs": CATEGORIES.get("seo_tools", 1),
        "keyword": CATEGORIES.get("seo_tools", 1),
        "backlink": CATEGORIES.get("seo_tools", 1),
        "rank": CATEGORIES.get("seo_tools", 1),
        "moz": CATEGORIES.get("seo_tools", 1),
        "mangools": CATEGORIES.get("seo_tools", 1),
        "serpstat": CATEGORIES.get("seo_tools", 1),
        "se ranking": CATEGORIES.get("seo_tools", 1),
        "spyfu": CATEGORIES.get("seo_tools", 1),
        "ubersuggest": CATEGORIES.get("seo_tools", 1),
        "surfer": CATEGORIES.get("seo_tools", 1),
        "frase": CATEGORIES.get("seo_tools", 1),

        # ── Project Management ────────────────────────────────
        "project": CATEGORIES.get("project_management", 1),
        "monday": CATEGORIES.get("project_management", 1),
        "notion": CATEGORIES.get("project_management", 1),
        "asana": CATEGORIES.get("project_management", 1),
        "clickup": CATEGORIES.get("project_management", 1),
        "trello": CATEGORIES.get("project_management", 1),
        "task": CATEGORIES.get("project_management", 1),
        "wrike": CATEGORIES.get("project_management", 1),
        "smartsheet": CATEGORIES.get("project_management", 1),
        "teamwork": CATEGORIES.get("project_management", 1),
        "basecamp": CATEGORIES.get("project_management", 1),
        "hive": CATEGORIES.get("project_management", 1),
        "todoist": CATEGORIES.get("project_management", 1),

        # ── Business Automation ───────────────────────────────
        "automation": CATEGORIES.get("business_automation", 1),
        "zapier": CATEGORIES.get("business_automation", 1),
        "make": CATEGORIES.get("business_automation", 1),
        "workflow": CATEGORIES.get("business_automation", 1),
        "integrate": CATEGORIES.get("business_automation", 1),
        "n8n": CATEGORIES.get("business_automation", 1),
        "pabbly": CATEGORIES.get("business_automation", 1),
        "integrately": CATEGORIES.get("business_automation", 1),
        "jotform": CATEGORIES.get("business_automation", 1),
        "typeform": CATEGORIES.get("business_automation", 1),
        "paperform": CATEGORIES.get("business_automation", 1),
        "form builder": CATEGORIES.get("business_automation", 1),
        "online form": CATEGORIES.get("business_automation", 1),

        # ── AI Tools ─────────────────────────────────────────
        "ai": CATEGORIES.get("ai_tools", 1),
        "artificial intelligence": CATEGORIES.get("ai_tools", 1),
        "chatgpt": CATEGORIES.get("ai_tools", 1),
        "jasper": CATEGORIES.get("ai_tools", 1),
        "grammarly": CATEGORIES.get("ai_tools", 1),
        "copy.ai": CATEGORIES.get("ai_tools", 1),
        "copyai": CATEGORIES.get("ai_tools", 1),
        "writesonic": CATEGORIES.get("ai_tools", 1),
        "descript": CATEGORIES.get("ai_tools", 1),
        "canva": CATEGORIES.get("ai_tools", 1),

        # ── Finance ───────────────────────────────────────────
        "accounting": CATEGORIES.get("finance", 1),
        "quickbooks": CATEGORIES.get("finance", 1),
        "freshbooks": CATEGORIES.get("finance", 1),
        "xero": CATEGORIES.get("finance", 1),
        "invoice": CATEGORIES.get("finance", 1),
        "bookkeeping": CATEGORIES.get("finance", 1),
        "payroll": CATEGORIES.get("finance", 1),
        "finance": CATEGORIES.get("finance", 1),
        "wave": CATEGORIES.get("finance", 1),
        "sage": CATEGORIES.get("finance", 1),
        "bench": CATEGORIES.get("finance", 1),
        "melio": CATEGORIES.get("finance", 1),
        "patriot": CATEGORIES.get("finance", 1),

        # ── Website Builders ──────────────────────────────────
        "landing page": CATEGORIES.get("website_builders", 1),
        "webflow": CATEGORIES.get("website_builders", 1),
        "unbounce": CATEGORIES.get("website_builders", 1),
        "leadpages": CATEGORIES.get("website_builders", 1),
        "website builder": CATEGORIES.get("website_builders", 1),
        "wix": CATEGORIES.get("website_builders", 1),
        "instapage": CATEGORIES.get("website_builders", 1),
        "swipe pages": CATEGORIES.get("website_builders", 1),
        "elementor": CATEGORIES.get("website_builders", 1),
        "divi": CATEGORIES.get("website_builders", 1),
        "squarespace": CATEGORIES.get("website_builders", 1),
        "carrd": CATEGORIES.get("website_builders", 1),
    }

    for key, cat_id in category_map.items():
        if key in keyword_lower:
            return cat_id

    for program in programs:
        program_lower = program.lower()
        for key, cat_id in category_map.items():
            if key in program_lower:
                return cat_id

    return CATEGORIES.get("general", 1)

# ─── STEP 4.1: CREATE IMAGE ───────────────────────────────────
def get_featured_image_unsplash(keyword):
    access_key = UNSPLASH_ACCESS_KEY
    if not access_key:
        print("   ⚠️  No UNSPLASH_ACCESS_KEY — skipping featured image")
        return None

    try:
        search_term = keyword.replace('-', ' ')
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": f"{search_term} software technology",
                "per_page": 5,
                "orientation": "landscape",
                "content_filter": "high"
            },
            headers={"Authorization": f"Client-ID {access_key}"}
        )
        if response.status_code != 200:
            return None
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None
        photo = results[0]
        image_url = photo["urls"]["regular"]
        photographer = photo["user"]["name"]
        print(f"   📸 Found image by {photographer}")
        return image_url
    except Exception as e:
        print(f"   ⚠️  Unsplash error: {e}")
        return None


def upload_image_to_wordpress(image_url, title, alt_text=""):
    try:
        print(f"   📤 Uploading featured image...")
        img_response = requests.get(image_url, timeout=30)
        if img_response.status_code != 200:
            return None

        filename = title.lower()
        filename = ''.join(c if c.isalnum() or c == '-' else '-' for c in filename)
        filename = f"{filename[:50]}.jpg"

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
                time.sleep(1)
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
    try:
        import openai
        import io
        from PIL import Image

        openai_key = OPENAI_API_KEY
        if not openai_key:
            print("   ⚠️  No OPENAI_API_KEY — skipping AI image generation")
            return None, None

        client = openai.OpenAI(api_key=openai_key)
        print(f"   🎨 Generating {orientation} AI image for: {title}")

        color_hints = {
            # ── CRM & Sales ──────────────────────────────────────────
            "hubspot": "orange accents",
            "zoho": "red accents",
            "pipedrive": "green accents",
            "salesforce": "blue accents",
            "copper": "copper and bronze accents",
            "keap": "green accents",
            "nimble": "blue accents",
            "close": "black and white accents",

            # ── Email Marketing ───────────────────────────────────────
            "klaviyo": "green accents",
            "activecampaign": "blue accents",
            "getresponse": "blue and green accents",
            "brevo": "blue accents",
            "constantcontact": "blue and yellow accents",
            "drip": "black and orange accents",
            "mailerlite": "green and yellow accents",

            # ── Project Management ────────────────────────────────────
            "monday": "vibrant red and yellow accents",
            "notion": "black and white minimal accents",
            "asana": "coral pink accents",
            "clickup": "purple accents",
            "wrike": "green accents",
            "smartsheet": "blue and orange accents",
            "teamwork": "pink accents",
            "basecamp": "green accents",
            "hive": "orange accents",
            "todoist": "red accents",

            # ── SEO Tools ─────────────────────────────────────────────
            "semrush": "orange and blue accents",
            "ahrefs": "blue and orange accents",
            "moz": "blue accents",
            "mangools": "purple accents",
            "serpstat": "blue and green accents",
            "seranking": "green accents",
            "spyfu": "green accents",
            "ubersuggest": "orange accents",
            "surferseo": "blue and teal accents",
            "frase": "purple and blue accents",

            # ── Business Automation ───────────────────────────────────
            "zapier": "orange accents",
            "make": "purple accents",
            "n8n": "red accents",
            "pabbly": "blue accents",
            "integrately": "orange and blue accents",

            # ── AI Tools ─────────────────────────────────────────────
            "grammarly": "green accents",
            "jasper": "purple and pink accents",
            "copyai": "blue and purple accents",
            "writesonic": "blue and purple accents",
            "descript": "green and teal accents",
            "canva": "purple and turquoise accents",

            # ── Finance ───────────────────────────────────────────────
            "quickbooks": "green accents",
            "freshbooks": "teal accents",
            "xero": "blue accents",
            "wave": "blue and teal accents",
            "sage": "green accents",
            "bench": "green and navy accents",
            "melio": "blue accents",
            "patriot": "red and blue accents",

            # ── Website Builders & Landing Pages ─────────────────────
            "webflow": "blue accents",
            "unbounce": "purple and teal accents",
            "instapage": "orange accents",
            "swipepages": "blue and orange accents",
            "elementor": "red accents",
            "divi": "purple accents",
            "squarespace": "black and white accents",
            "carrd": "blue accents",

            # ── Form Builders ─────────────────────────────────────────
            "jotform": "orange and purple accents",
            "typeform": "pink and purple accents",
            "paperform": "teal and purple accents",
            "cognitoforms": "blue accents",
            "123formbuilder": "orange accents",
        }

        accent_colors = []
        if programs:
            for program in programs:
                for key, color in color_hints.items():
                    if key in program.lower() and color not in accent_colors:
                        accent_colors.append(color)

        color_instruction = f"Subtle {', '.join(accent_colors)} incorporated into the design" if accent_colors else "Eclipse Gold accents"

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
    try:
        print(f"   🎨 Generating AI featured images...")
        base_filename = keyword.lower().replace(' ', '-')[:50]

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
        pinterest_image_url = None

        return landscape_id, wordpress_image_url, pinterest_image_url

    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return None, None, None

def upload_single_image(img_data, filename, content_type, alt_text=""):
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
            if alt_text and media_id:
                time.sleep(1)
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

            if post_id and focus_keyword:
                try:
                    requests.post(
                        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                        json={"rank_math_focus_keyword": focus_keyword},
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

# ─── STEP 7: CLEANUP OLD FILES ────────────────────────────────
def cleanup_old_files():
    reports = sorted(glob.glob("intelligence_report_*.json"))
    for old_report in reports[:-7]:
        os.remove(old_report)
        print(f"   🧹 Removed old report: {old_report}")

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
    published_count = 0
    opp_index = 0

    while published_count < num_articles and opp_index < len(opportunities):
        opp = opportunities[opp_index]
        opp_index += 1

        print(f"\n{'='*60}")
        print(f"  ARTICLE {published_count + 1} of {num_articles} (opportunity {opp_index} of {len(opportunities)})")
        print(f"{'='*60}")

        title = opp.get('title', '')
        keyword = opp.get('keyword', '')
        test_slug = keyword.lower().replace(' ', '-')

        # ── CHECK FOR DUPLICATE COMPARISON (order-independent) ───
        comparison_key = normalize_comparison_key(keyword, opp.get('programs', []))
        tracker = load_published_posts()
        if comparison_key in tracker.get("comparison_keys", []):
            print(f"⏭️  Skipping — comparison already covered: {comparison_key}")
            continue

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
        pinterest_image_url = None
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
                post_url,
                comparison_key=comparison_key
            )
            published_count += 1

        # ── POST TO SOCIAL MEDIA ─────────────────────────────────
        if post_id and not publish_as_draft:
            post_to_social(
                title,
                metadata.get("excerpt", ""),
                post_url,
                category_id=category_id,
                image_url=image_url,
                pinterest_image_url=pinterest_image_url,
                article_html=article_content,
                keyword=keyword,
            )

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

        # ── SUBMIT TO INDEXNOW & GOOGLE ───────────────────────────
        if post_id and post_url:
            submit_to_indexnow(post_url)
            submit_to_google(post_url)

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
        show_published()
    else:
        run_pipeline(
            num_articles=1,
            publish_as_draft=False,
            publish_to_wp=True
        )
