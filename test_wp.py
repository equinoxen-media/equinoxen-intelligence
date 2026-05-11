import requests
import os
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WORDPRESS_USERNAME")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD")

print(f"Testing connection to: {WP_URL}")
print(f"Username: {WP_USER}")
print(f"Password set: {bool(WP_PASS)}")

# Test authentication
response = requests.get(
    f"{WP_URL}/wp-json/wp/v2/users/me",
    auth=(WP_USER, WP_PASS)
)

print(f"\nStatus code: {response.status_code}")

if response.status_code == 200:
    user = response.json()
    print(f"✅ Connected as: {user.get('name')}")
    print(f"   Role: {user.get('roles', [])}")
    print(f"   Can create posts: {'edit_posts' in user.get('capabilities', {})}")
else:
    print(f"❌ Authentication failed")
    print(f"   Response: {response.text[:300]}")
