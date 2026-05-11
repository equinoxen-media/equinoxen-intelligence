import requests
import os
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WORDPRESS_USERNAME")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD")

post = {
    "title": "API Test Post",
    "content": "This was created via API.",
    "status": "draft"
}

response = requests.post(
    f"{WP_URL}/wp-json/wp/v2/posts",
    auth=(WP_USER, WP_PASS),
    json=post
)

print(f"Status: {response.status_code}")
print(response.text)

