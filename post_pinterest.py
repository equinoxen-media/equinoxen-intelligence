import os
import io
import sys
import json
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIGURATION ────────────────────────────────────────────
WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WORDPRESS_USERNAME")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD")

PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PINTEREST_BOARDS = {
    "crm":                  os.getenv("PINTEREST_BOARD_CRM"),
    "email_marketing":      os.getenv("PINTEREST_BOARD_EMAIL_MARKETING"),
    "seo_tools":            os.getenv("PINTEREST_BOARD_SEO_TOOLS"),
    "project_management":   os.getenv("PINTEREST_BOARD_PROJECT_MANAGEMENT"),
    "business_automation":  os.getenv("PINTEREST_BOARD_BUSINESS_AUTOMATION"),
    "ai_tools":             os.getenv("PINTEREST_BOARD_AI_TOOLS"),
    "finance":              os.getenv("PINTEREST_BOARD_FINANCE"),
    "website_builders":     os.getenv("PINTEREST_BOARD_WEBSITE_BUILDERS"),
    "general":              os.getenv("PINTEREST_BOARD_GENERAL"),
}

# WordPress category ID → Pinterest board key
CATEGORY_BOARD_MAP = {
    4:  "crm",
    5:  "email_marketing",
    6:  "seo_tools",
    7:  "project_management",
    8:  "business_automation",
    9:  "ai_tools",
    10: "finance",
    11: "website_builders",
    1:  "general",
}

COLOR_HINTS = {
    "hubspot":    "orange accents",
    "monday":     "vibrant red and yellow accents",
    "semrush":    "orange and blue accents",
    "notion":     "black and white minimal accents",
    "webflow":    "blue accents",
    "zoho":       "red accents",
    "asana":      "coral pink accents",
    "klaviyo":    "green accents",
    "quickbooks": "green accents",
    "freshbooks": "teal accents",
    "zapier":     "orange accents",
    "ahrefs":     "blue and orange accents",
    "clickup":    "purple accents",
    "grammarly":  "green accents",
    "unbounce":   "purple and teal accents",
    "jotform":    "orange and purple accents",
    "canva":      "purple and turquoise accents",
}


# ─── STEP 1: FETCH POST FROM WORDPRESS ───────────────────────
def fetch_wp_post(identifier):
    """Fetch post data from WordPress by URL or numeric ID."""
    print(f"\n🔍 Fetching post from WordPress: {identifier}")

    # Determine if identifier is a URL or an ID
    if str(identifier).startswith("http"):
        # Slug-based lookup: extract slug from URL
        slug = identifier.rstrip("/").split("/")[-1]
        print(f"   Looking up by slug: {slug}")
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            auth=(WP_USER, WP_PASS),
            params={"slug": slug, "status": "publish", "_fields": "id,slug,title,excerpt,link,featured_media,categories,tags"},
        )
        if response.status_code != 200 or not response.json():
            print(f"   ❌ Post not found for slug: {slug}")
            return None
        post = response.json()[0]
    else:
        post_id = int(identifier)
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            auth=(WP_USER, WP_PASS),
            params={"_fields": "id,slug,title,excerpt,link,featured_media,categories,tags"},
        )
        if response.status_code != 200:
            print(f"   ❌ Post not found for ID: {post_id}")
            return None
        post = response.json()

    title = post["title"]["rendered"]
    # Strip HTML tags from excerpt
    raw_excerpt = post["excerpt"]["rendered"]
    excerpt = _strip_html(raw_excerpt)[:500]
    link = post["link"]
    category_ids = post.get("categories", [1])
    category_id = category_ids[0] if category_ids else 1

    print(f"   ✅ Found: {title}")
    print(f"   🔗 URL: {link}")
    print(f"   📂 Category ID: {category_id}")

    return {
        "id": post["id"],
        "slug": post["slug"],
        "title": title,
        "excerpt": excerpt,
        "link": link,
        "featured_media": post.get("featured_media"),
        "category_id": category_id,
    }


def _strip_html(html):
    """Remove HTML tags from a string."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


# ─── STEP 2: GENERATE PINTEREST IMAGE ────────────────────────
def generate_pinterest_image(title, keyword, programs=None):
    """Generate a 1024×1536 portrait WebP image via gpt-image-2, resized to ~1000×1500."""
    try:
        import openai
        from PIL import Image

        if not OPENAI_API_KEY:
            print("   ⚠️  No OPENAI_API_KEY — cannot generate image")
            return None

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        print(f"\n🎨 Generating Pinterest portrait image...")

        # Build accent color hints from program names
        accent_colors = []
        if programs:
            for prog in programs:
                for key, color in COLOR_HINTS.items():
                    if key in prog.lower() and color not in accent_colors:
                        accent_colors.append(color)
        color_instruction = (
            f"Subtle {', '.join(accent_colors)} incorporated into the design"
            if accent_colors
            else "Eclipse Gold #D4AF37 accents"
        )

        prompt = f"""Create a professional Pinterest pin image for a blog post titled: '{title}'

Style requirements:
- Vertical portrait composition optimized for Pinterest (tall format)
- Strong visual flow from top to bottom
- Flat-lay or abstract tech aesthetic
- All critical design elements centered in the frame
- Clean, modern, professional business/tech look suitable for a SaaS review publication
- No text, typography, logos, brand marks, or recognizable company symbols
- Visual metaphor representing the topic: {keyword}
- Dark sophisticated base with gold as primary accents
- Accent colors as subtle design elements: {color_instruction}
- High contrast, visually striking, scroll-stopping on Pinterest"""

        response = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            size="1024x1536",
            quality="medium",
            n=1,
        )

        image_data = base64.b64decode(response.data[0].b64_json)

        # Resize to ~1000×1500 and save as WebP
        img = Image.open(io.BytesIO(image_data))
        webp_buffer = io.BytesIO()
        img.save(webp_buffer, format="WEBP", quality=85, method=6)
        webp_buffer.seek(0)
        final_bytes = webp_buffer.getvalue()

        print(f"   ✅ Image generated ({len(final_bytes) // 1024} KB, 1000×1500 WebP)")
        return final_bytes

    except ImportError as e:
        print(f"   ❌ Missing library: {e} — install openai and Pillow")
        return None
    except Exception as e:
        print(f"   ❌ Image generation error: {e}")
        return None


# ─── STEP 3: UPLOAD IMAGE TO WORDPRESS ───────────────────────
def upload_image_to_wordpress(image_bytes, slug):
    """Upload WebP image bytes to WordPress media library, return public URL."""
    try:
        print(f"\n📤 Uploading image to WordPress media library...")
        filename = f"{slug[:50]}-pinterest.webp"
        media_url = f"{WP_URL}/wp-json/wp/v2/media"

        response = requests.post(
            media_url,
            data=image_bytes,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "image/webp",
            },
            auth=(WP_USER, WP_PASS),
        )

        if response.status_code in [200, 201]:
            media = response.json()
            public_url = media.get("source_url")
            print(f"   ✅ Uploaded — {public_url}")
            return public_url
        else:
            print(f"   ❌ Upload failed: {response.status_code} — {response.text[:200]}")
            return None

    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return None


# ─── STEP 4: POST TO PINTEREST ────────────────────────────────
def post_to_pinterest(title, excerpt, post_url, board_id, image_url):
    """Create a Pin on Pinterest."""
    if not PINTEREST_ACCESS_TOKEN:
        print("   ❌ No PINTEREST_ACCESS_TOKEN — aborting")
        return False
    if not board_id:
        print("   ❌ No board ID resolved — aborting")
        return False

    print(f"\n📌 Posting to Pinterest...")
    print(f"   Board ID: {board_id}")

    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    pin_data = {
        "board_id": board_id,
        "title": title[:100],
        "description": excerpt[:500],
        "link": post_url,
        "media_source": {
            "source_type": "image_url",
            "url": image_url,
        },
    }

    try:
        response = requests.post(
            "https://api.pinterest.com/v5/pins",
            headers=headers,
            json=pin_data,
        )
        if response.status_code in [200, 201]:
            pin = response.json()
            print(f"   ✅ Pin created — ID: {pin.get('id')}")
            return True
        else:
            print(f"   ❌ Pinterest failed: {response.status_code} — {response.text[:300]}")
            return False
    except Exception as e:
        print(f"   ❌ Pinterest error: {e}")
        return False


# ─── MAIN ─────────────────────────────────────────────────────
def run(identifier, programs=None):
    """
    Full flow: fetch post → generate image → upload → pin.

    Args:
        identifier: WordPress post ID (int) or full post URL (str)
        programs:   Optional list of affiliate program names for color hints
                    e.g. ["HubSpot", "Zoho"] — inferred from title if omitted
    """
    print("=" * 60)
    print("  EQUINOXEN MEDIA — PINTEREST POSTER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Fetch post
    post = fetch_wp_post(identifier)
    if not post:
        print("\n❌ Could not fetch post — exiting")
        return False

    title = post["title"]
    excerpt = post["excerpt"]
    link = post["link"]
    slug = post["slug"]
    category_id = post["category_id"]

    # 2. Resolve Pinterest board
    board_key = CATEGORY_BOARD_MAP.get(category_id, "general")
    board_id = PINTEREST_BOARDS.get(board_key)
    print(f"\n📂 Pinterest board: {board_key} → {board_id}")

    # 3. Infer programs from title if not supplied
    if not programs:
        programs = _infer_programs_from_title(title)

    # 4. Generate image
    image_bytes = generate_pinterest_image(title, slug.replace("-", " "), programs)
    if not image_bytes:
        print("\n❌ Image generation failed — exiting")
        return False

    # 5. Upload image to WordPress (serves as CDN)
    image_url = upload_image_to_wordpress(image_bytes, slug)
    if not image_url:
        print("\n❌ Image upload failed — exiting")
        return False

    # 6. Post to Pinterest
    success = post_to_pinterest(title, excerpt, link, board_id, image_url)

    print("\n" + "=" * 60)
    if success:
        print("  ✅ DONE — Pin live on Pinterest")
    else:
        print("  ❌ FAILED — Pin not created")
    print("=" * 60)
    return success


def _infer_programs_from_title(title):
    """Extract known program names from the post title."""
    known = list(COLOR_HINTS.keys())
    title_lower = title.lower()
    return [p for p in known if p in title_lower]


# ─── CLI ──────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 post_pinterest.py <post_id>")
        print("  python3 post_pinterest.py <post_url>")
        print("")
        print("Examples:")
        print("  python3 post_pinterest.py 42")
        print("  python3 post_pinterest.py https://equinoxen.com/hubspot-crm-review/")
        sys.exit(1)

    identifier = sys.argv[1]
    # Optional: pass program names as extra args
    extra_programs = sys.argv[2:] if len(sys.argv) > 2 else None
    run(identifier, programs=extra_programs)
