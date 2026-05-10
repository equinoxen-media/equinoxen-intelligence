import requests
import os
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv("WORDPRESS_URL")
WP_USER = os.getenv("WORDPRESS_USERNAME")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD")

def get_categories():
    """Fetch all categories from WordPress"""
    
    url = f"{WP_URL}/wp-json/wp/v2/categories"
    
    try:
        response = requests.get(
            url,
            auth=(WP_USER, WP_PASS),
            params={"per_page": 100}
        )
        
        if response.status_code == 200:
            categories = response.json()
            
            print("\n📂 YOUR WORDPRESS CATEGORIES:")
            print("=" * 50)
            print(f"{'ID':<6} {'Name':<30} {'Slug':<25}")
            print("-" * 50)
            
            for cat in categories:
                print(f"{cat['id']:<6} {cat['name']:<30} {cat['slug']:<25}")
            
            print("\n📋 Copy these IDs into content_pipeline.py:")
            print("=" * 50)
            print("CATEGORIES = {")
            for cat in categories:
                key = cat['slug'].replace('-', '_')
                print(f'    "{key}": {cat["id"]},')
            print("}")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:200])
            
    except Exception as e:
        print(f"❌ Connection error: {e}")

get_categories()
