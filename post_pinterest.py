import os
import io
import sys
import json
import base64
import requests
import anthropic
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIGURATION ────────────────────────────────────────────
WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WORDPRESS_USERNAME")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD")

PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

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


# ─── STEP 1.5: GENERATE SHORT PIN TITLE ──────────────────────
def generate_pin_title(title, keyword):
    """
    Distill the full (often dramatic/long) article title into a short,
    scannable pin title for the image overlay. Backfill-only equivalent
    of the pin_title field content_pipeline.py now generates for new posts.
    """
    print("   ✍️  Generating pin title...")

    fallback = keyword.title()
    if len(fallback) > 45:
        fallback = fallback[:45].rsplit(' ', 1)[0]

    if not ANTHROPIC_API_KEY:
        print("   ⚠️  No ANTHROPIC_API_KEY — using keyword fallback for pin title")
        return fallback

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Article title: {title}
Primary keyword: {keyword}

Distill this into a short, scannable Pinterest pin title. Strip filler words
like "Ultimate", "Complete", "Honest Review", "In-Depth", and the year.
Prefer a direct comparison or plain product/keyword phrasing
(e.g. "HubSpot vs Salesforce" or "Best CRM for Small Teams").
Max 45 characters. No punctuation at the end. No quotes around it.

Return ONLY the short title text, nothing else."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
        pin_title = message.content[0].text.strip().strip('"').strip("'")
        if not pin_title or len(pin_title) > 60:
            return fallback
        print(f"   ✅ Pin title: {pin_title}")
        return pin_title
    except Exception as e:
        print(f"   ⚠️  Pin title generation error: {e} — using keyword fallback")
        return fallback


# ─── STEP 2: GENERATE PINTEREST IMAGE ────────────────────────
def generate_pinterest_image(title, keyword, programs=None):
    """Generate a 1024×1536 portrait WebP background image via gpt-image-2."""
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
- High contrast, visually striking, scroll-stopping on Pinterest
- Keep the top 25% of the composition visually calm and low-detail (soft gradient
  or open space) — a title banner will be added there afterward"""

        response = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            size="1024x1536",
            quality="medium",
            n=1,
        )

        image_data = base64.b64decode(response.data[0].b64_json)

        img = Image.open(io.BytesIO(image_data))
        webp_buffer = io.BytesIO()
        img.save(webp_buffer, format="WEBP", quality=85, method=6)
        webp_buffer.seek(0)
        final_bytes = webp_buffer.getvalue()

        print(f"   ✅ Background generated ({len(final_bytes) // 1024} KB)")
        return final_bytes

    except ImportError as e:
        print(f"   ❌ Missing library: {e} — install openai and Pillow")
        return None
    except Exception as e:
        print(f"   ❌ Image generation error: {e}")
        return None


# ─── STEP 2.5: OVERLAY PIN TITLE ON IMAGE ────────────────────
def _load_font(size, bold=True):
    from PIL import ImageFont
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ) if bold else (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    """Greedy word-wrap that fits within max_width using actual glyph measurements."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def add_pinterest_title_overlay(image_bytes, pin_title, max_lines=4):
    """
    Overlay the short pin title as crisp, legible text in a gradient
    banner at the top of the generated background. Returns webp bytes.
    """
    from PIL import Image, ImageDraw

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    W, H = img.size

    side_margin = int(W * 0.08)
    max_text_width = W - (side_margin * 2)

    font_size = int(W * 0.09)
    font = _load_font(font_size)
    draw_tmp = ImageDraw.Draw(img)
    display_title = pin_title.strip()

    lines = _wrap_text(draw_tmp, display_title, font, max_text_width)
    while len(lines) > max_lines and font_size > int(W * 0.045):
        font_size -= 4
        font = _load_font(font_size)
        lines = _wrap_text(draw_tmp, display_title, font, max_text_width)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;: ") + "…"

    line_bbox = draw_tmp.textbbox((0, 0), "Ag", font=font)
    line_height = int((line_bbox[3] - line_bbox[1]) * 1.35)
    top_pad = int(H * 0.06)
    bottom_pad = int(H * 0.05)
    banner_h = top_pad + (line_height * len(lines)) + bottom_pad

    banner = Image.new("RGBA", (W, banner_h), (0, 0, 0, 0))
    for y in range(banner_h):
        t = 1 - (y / max(1, banner_h - 1))
        alpha = int(200 * (t ** 0.6))
        banner.paste((8, 8, 8, alpha), (0, y, W, y + 1))

    draw = ImageDraw.Draw(banner)
    y_cursor = top_pad
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2
        draw.text((x + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 160))
        draw.text((x, y_cursor), line, font=font, fill=(255, 255, 255, 255))
        y_cursor += line_height

    draw.rectangle([(side_margin, banner_h - int(H * 0.015)),
                     (W - side_margin, banner_h - int(H * 0.015) + 3)],
                    fill=(212, 175, 55, 255))

    img.alpha_composite(banner, (0, 0))

    out = io.BytesIO()
    img.convert("RGB").save(out, format="WEBP", quality=85, method=6)
    return out.getvalue()


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

def refresh_pinterest_token():
    """Refresh Pinterest access token and persist new tokens to .env."""
    refresh_token = os.getenv("PINTEREST_REFRESH_TOKEN")
    client_id = os.getenv("PINTEREST_CLIENT_ID")
    client_secret = os.getenv("PINTEREST_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        print("   ⚠️  Pinterest refresh credentials missing")
        return None

    credentials = f"{client_id}:{client_secret}"
    encoded_creds = base64.b64encode(credentials.encode()).decode()

    resp = requests.post(
        "https://api.pinterest.com/v5/oauth/token",
        headers={
            "Authorization": f"Basic {encoded_creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )

    if resp.status_code != 200:
        print(f"   ❌ Pinterest token refresh failed: {resp.status_code} — {resp.text[:200]}")
        return None

    data = resp.json()
    new_access = data.get("access_token")
    new_refresh = data.get("refresh_token")  # present only if Pinterest rotates it

    _update_env_file("PINTEREST_ACCESS_TOKEN", new_access)
    if new_refresh:
        _update_env_file("PINTEREST_REFRESH_TOKEN", new_refresh)

    print("   ✅ Pinterest token refreshed")
    return new_access


def _update_env_file(key, value, path=".env"):
    """Update a single key in the .env file, preserving everything else."""
    with open(path, "r") as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")

    with open(path, "w") as f:
        f.writelines(lines)

# ─── MAIN ─────────────────────────────────────────────────────
def run(identifier, programs=None):
    """
    Full flow: fetch post → generate image → overlay title → upload → pin.

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
    keyword = slug.replace("-", " ")

    # 2. Resolve Pinterest board
    board_key = CATEGORY_BOARD_MAP.get(category_id, "general")
    board_id = PINTEREST_BOARDS.get(board_key)
    print(f"\n📂 Pinterest board: {board_key} → {board_id}")

    # 3. Infer programs from title if not supplied
    if not programs:
        programs = _infer_programs_from_title(title)

    # 4. Generate short pin title for the overlay (old posts don't have one stored)
    pin_title = generate_pin_title(title, keyword)

    # 5. Generate background image
    image_bytes = generate_pinterest_image(title, keyword, programs)
    if not image_bytes:
        print("\n❌ Image generation failed — exiting")
        return False

    # 6. Overlay the pin title onto the background
    image_bytes = add_pinterest_title_overlay(image_bytes, pin_title)

    # 7. Upload image to WordPress (serves as CDN)
    image_url = upload_image_to_wordpress(image_bytes, slug)
    if not image_url:
        print("\n❌ Image upload failed — exiting")
        return False

    # 8. Before posting to Pinterest, refresh the token
    fresh_token = refresh_pinterest_token()
    if fresh_token:
        global PINTEREST_ACCESS_TOKEN
        PINTEREST_ACCESS_TOKEN = fresh_token

    # 9. Post to Pinterest
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
