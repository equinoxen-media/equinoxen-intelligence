import os
import sys
import requests
import json
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WORDPRESS_USERNAME")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_ORGANIZATION_ID = os.getenv("LINKEDIN_ORGANIZATION_ID")


def get_post_from_wordpress(post_id):
    """Fetch a published post from WordPress by ID"""
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            auth=(WP_USER, WP_PASS)
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Could not fetch post {post_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching post: {e}")
        return None


def get_image_url(media_id):
    """Fetch image URL from WordPress media library"""
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            auth=(WP_USER, WP_PASS)
        )
        if response.status_code == 200:
            return response.json().get("source_url")
        return None
    except Exception as e:
        print(f"⚠️  Could not fetch image: {e}")
        return None


def download_image(image_url):
    """Download image from URL and return bytes"""
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            return response.content, response.headers.get("Content-Type", "image/jpeg")
        return None, None
    except Exception as e:
        print(f"⚠️  Could not download image: {e}")
        return None, None


def register_image_with_linkedin(image_data, content_type):
    """Register an image upload with LinkedIn and get upload URL"""
    try:
        headers = {
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        # Step 1 — Initialize upload
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

        if register_response.status_code != 200:
            print(f"⚠️  LinkedIn image registration failed: {register_response.status_code}")
            print(f"   {register_response.text[:200]}")
            return None

        register_data = register_response.json()
        upload_url = register_data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset = register_data["value"]["asset"]

        # Step 2 — Upload the image bytes
        upload_response = requests.put(
            upload_url,
            data=image_data,
            headers={"Content-Type": content_type}
        )

        if upload_response.status_code in [200, 201]:
            print(f"   ✅ Image uploaded to LinkedIn — Asset: {asset}")
            return asset
        else:
            print(f"⚠️  LinkedIn image upload failed: {upload_response.status_code}")
            return None

    except Exception as e:
        print(f"⚠️  LinkedIn image upload error: {e}")
        return None


def post_to_linkedin_with_image(title, excerpt, post_url, image_asset=None):
    """Post article to LinkedIn company page with optional image"""
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_ORGANIZATION_ID:
        print("❌ LinkedIn credentials missing")
        return False

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    post_text = f"{title}\n\n{excerpt}\n\nRead the full article 👇\n{post_url}"

    if image_asset:
        # Post with image
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
        # Post as article link without image
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


def share_to_linkedin(post_id):
    """Fetch a WordPress post and share it to LinkedIn with image"""
    print(f"\n📡 Fetching post ID {post_id} from WordPress...")

    post = get_post_from_wordpress(post_id)
    if not post:
        return

    import re

    title = post.get("title", {}).get("rendered", "")
    excerpt = re.sub(r'<[^>]+>', '', post.get("excerpt", {}).get("rendered", "")).strip()
    post_url = post.get("link", "")
    featured_media_id = post.get("featured_media")

    print(f"   📄 Title: {title}")
    print(f"   🔗 URL: {post_url}")
    print(f"   📝 Excerpt: {excerpt[:100]}...")

    # Try to get and upload featured image
    image_asset = None
    if featured_media_id:
        print(f"\n🖼️  Fetching featured image (Media ID: {featured_media_id})...")
        image_url = get_image_url(featured_media_id)

        if image_url:
            print(f"   📸 Image URL: {image_url}")
            image_data, content_type = download_image(image_url)

            if image_data:
                print(f"   📤 Uploading image to LinkedIn...")
                image_asset = register_image_with_linkedin(image_data, content_type)
        else:
            print("   ⚠️  No featured image found")
    else:
        print("   ⚠️  No featured image set on this post")

    # Post to LinkedIn
    print(f"\n📤 Posting to LinkedIn...")
    if image_asset:
        print("   📸 Posting with image")
    else:
        print("   🔗 Posting as article link (no image)")

    post_to_linkedin_with_image(title, excerpt, post_url, image_asset)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 post_linkedin.py <post_id>")
        print("Example: python3 post_linkedin.py 255")
        print("\nTo find post ID: WordPress admin → Posts → hover over post title → check URL for post=XXX")
        sys.exit(1)

    post_id = sys.argv[1]
    share_to_linkedin(post_id)
