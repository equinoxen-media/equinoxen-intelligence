import os
import json
import time
import requests
import feedparser
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import anthropic

# Load credentials
load_dotenv()

# ─── CONFIGURATION ────────────────────────────────────────────
NICHES = [
    "CRM software",
    "email marketing software",
    "project management software",
    "SEO tools",
    "business automation software",
    "accounting software",
    "AI productivity tools",
    "landing page builder",
]

SUBREDDITS = [
    "entrepreneur",
    "smallbusiness",
    "SaaS",
    "marketing",
    "productivity",
    "startups",
    "digitalnomad",
    "freelance",
]

PAIN_POINT_KEYWORDS = [
    'recommend', 'alternative', 'looking for', 'best tool',
    'which software', 'need help', 'frustrated', 'switch from',
    'better than', 'replace', 'comparison', 'vs ', 'review',
    'anyone use', 'thoughts on', 'worth it', 'pricing',
    'too expensive', 'free alternative', 'open source',
    'best crm', 'best email', 'best project', 'help choosing',
    'which tool', 'recommendation', 'suggestions', 'advice',
]

# ─── LAYER 1: GOOGLE TRENDS VIA SERPAPI ───────────────────────
def get_trending_topics_serpapi(niche):
    """Get trending topics via SerpAPI - handles rate limits automatically"""
    print(f"\n📈 Checking trends for: {niche}")
    
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        print("  ⚠️  No SERPAPI_KEY found in .env - skipping trends")
        return []
    
    try:
        params = {
            "engine": "google_trends",
            "q": niche,
            "date": "now 7-d",
            "geo": "US",
            "api_key": serpapi_key
        }
        
        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"  ⚠️  SerpAPI error: {response.status_code}")
            return []
        
        data = response.json()
        trending = []
        
        # Get related queries
        related = data.get("related_queries", {})
        rising = related.get("rising", [])
        top = related.get("top", [])
        
        for item in rising[:5]:
            trending.append({
                'keyword': item.get('query', ''),
                'type': 'rising',
                'value': item.get('value', 0),
                'niche': niche,
                'source': 'google_trends'
            })
        
        for item in top[:5]:
            trending.append({
                'keyword': item.get('query', ''),
                'type': 'top',
                'value': item.get('value', 0),
                'niche': niche,
                'source': 'google_trends'
            })
        
        print(f"  Found {len(trending)} trending keywords")
        time.sleep(3)
        return trending
        
    except Exception as e:
        print(f"  ⚠️  SerpAPI error: {e}")
        return []

# ─── LAYER 2: REDDIT VIA RSS (NO API NEEDED) ──────────────────
def get_reddit_via_rss(subreddit_name, limit=25):
    """Get Reddit posts via RSS - zero credentials needed"""
    print(f"\n🔍 Scanning r/{subreddit_name} via RSS...")
    
    pain_points = []
    
    # Try hot and new feeds
    feed_urls = [
        f"https://www.reddit.com/r/{subreddit_name}/hot.rss",
        f"https://www.reddit.com/r/{subreddit_name}/new.rss",
    ]
    
    headers = {
        'User-Agent': 'EquinoxenMedia/1.0 (content research; equinoxen.com)'
    }
    
    seen_titles = set()
    
    for feed_url in feed_urls:
        try:
            response = requests.get(
                feed_url,
                headers=headers,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"  ⚠️  RSS error {response.status_code} for {feed_url}")
                continue
            
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:limit]:
                title = entry.get('title', '')
                
                # Skip duplicates
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                
                title_lower = title.lower()
                
                # Score by keyword relevance
                score = sum(
                    1 for kw in PAIN_POINT_KEYWORDS 
                    if kw in title_lower
                )
                
                if score >= 1:
                    pain_points.append({
                        'title': title,
                        'link': entry.get('link', ''),
                        'relevance': score,
                        'subreddit': subreddit_name,
                        'source': 'reddit_rss'
                    })
            
            time.sleep(2)
            
        except Exception as e:
            print(f"  ⚠️  RSS error for r/{subreddit_name}: {e}")
            continue
    
    # Sort by relevance
    pain_points.sort(key=lambda x: x['relevance'], reverse=True)
    top_posts = pain_points[:10]
    
    print(f"  Found {len(top_posts)} relevant posts")
    return top_posts

# ─── LAYER 3: KEYWORD SEARCH VIA SERPAPI ──────────────────────
def get_keyword_data(keyword):
    """Get search volume and competition data for a keyword"""
    
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        return {}
    
    try:
        params = {
            "engine": "google",
            "q": keyword,
            "location": "United States",
            "api_key": serpapi_key,
            "num": 10
        }
        
        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=30
        )
        
        if response.status_code != 200:
            return {}
        
        data = response.json()
        
        # Check organic results count as competition signal
        organic = data.get("organic_results", [])
        ads = data.get("ads", [])
        
        return {
            'keyword': keyword,
            'organic_results': len(organic),
            'has_ads': len(ads) > 0,
            'competition': 'high' if len(ads) > 3 else 'medium' if len(ads) > 0 else 'low'
        }
        
    except Exception as e:
        return {}

# ─── LAYER 4: CLAUDE ANALYSIS ─────────────────────────────────
def analyze_opportunities(trends_data, reddit_data):
    current_year = datetime.now().year
    """Use Claude to identify best content opportunities"""
    print("\n🤖 Analyzing opportunities with Claude...")
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("  ❌ No ANTHROPIC_API_KEY found in .env")
        return []
    
    client = anthropic.Anthropic(api_key=anthropic_key)
    
    # Prepare summaries
    trends_summary = json.dumps(trends_data[:20], indent=2) if trends_data else "No trends data available"
    
    reddit_summary = json.dumps([{
        'title': p['title'],
        'subreddit': p['subreddit'],
        'relevance': p['relevance']
    } for p in reddit_data[:30]], indent=2)
    
    prompt = f"""You are an expert SaaS affiliate content strategist for Equinoxen Media,
an independent SaaS review and comparison website targeting business owners,
marketers and entrepreneurs.

CRITICAL: Today is {datetime.now().strftime('%B %d, %Y')}. 
The current year is {current_year}.
ALL article titles MUST use {current_year} — never use 2024, 2023 or any past year.

Analyze these trending topics and Reddit pain points to identify the TOP 10
content opportunities for affiliate review articles.

GOOGLE TRENDS DATA:
{trends_summary}

REDDIT PAIN POINTS (from r/entrepreneur, r/smallbusiness, r/SaaS etc):
{reddit_summary}

For each opportunity identify:
1. A compelling SEO optimized article title using {current_year} where relevant
2. Primary target keyword (2-4 words, high commercial intent)
3. Content type: review, comparison, or buying_guide
4. Affiliate programs to target from this list:
   HubSpot, Monday.com, Semrush, Notion, Webflow, Jotform, 
   Zoho, Unbounce, Klaviyo, Asana, ClickUp, Ahrefs,
   QuickBooks, FreshBooks, Zapier, Canva, Grammarly
5. Why this opportunity is strong right now
6. Urgency score 1-10

Rules for good opportunities:
- High commercial intent keywords (best, review, alternative, vs, comparison)
- Products with affiliate programs paying 20%+ commission
- Topics with clear buyer intent from Reddit discussions
- Avoid overly broad topics — be specific

Return ONLY a valid JSON array. No markdown. No explanation:
[{{"title":"...{current_year}...","keyword":"...","type":"review","programs":["HubSpot"],"why":"...","urgency":8}}]"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text.strip()
        
        # Clean up response
        if '```' in response_text:
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        # Find JSON array
        start = response_text.find('[')
        end = response_text.rfind(']') + 1
        if start >= 0 and end > 0:
            response_text = response_text[start:end]
        
        opportunities = json.loads(response_text)
        print(f"  ✅ Found {len(opportunities)} opportunities")
        return opportunities
        
    except Exception as e:
        print(f"  ❌ Claude analysis error: {e}")
        return []

# ─── LAYER 5: SAVE RESULTS ────────────────────────────────────
def save_results(trends_data, reddit_data, opportunities):
    """Save all results to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "trends_keywords_found": len(trends_data),
            "reddit_posts_analyzed": len(reddit_data),
            "opportunities_identified": len(opportunities)
        },
        "top_opportunities": opportunities,
        "trends_data": trends_data,
        "reddit_data": reddit_data
    }
    
    filename = f"intelligence_report_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Report saved: {filename}")
    return filename

# ─── MAIN RUNNER ──────────────────────────────────────────────
def run_intelligence():
    print("=" * 60)
    print("  EQUINOXEN MEDIA — INTELLIGENCE LAYER v2")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Reddit: RSS feeds (no API needed)")
    print("  Trends: SerpAPI")
    print("=" * 60)
    
    all_trends = []
    all_reddit = []
    
    # Phase 1 — Google Trends via SerpAPI
    if os.getenv("SERPAPI_KEY"):
        print("\n📊 PHASE 1: Google Trends via SerpAPI")
        print("-" * 40)
        for niche in NICHES[:4]:
            trends = get_trending_topics_serpapi(niche)
            all_trends.extend(trends)
            time.sleep(3)
    else:
        print("\n⚠️  Skipping Google Trends — no SERPAPI_KEY in .env")
    
    # Phase 2 — Reddit via RSS
    print("\n💬 PHASE 2: Reddit RSS Analysis")
    print("-" * 40)
    for sub in SUBREDDITS:
        posts = get_reddit_via_rss(sub)
        all_reddit.extend(posts)
        time.sleep(3)
    
    # Phase 3 — Claude Analysis
    print("\n🧠 PHASE 3: AI Opportunity Analysis")
    print("-" * 40)
    opportunities = analyze_opportunities(all_trends, all_reddit)
    
    # Display results
    if opportunities:
        print("\n🎯 TOP CONTENT OPPORTUNITIES:")
        print("=" * 60)
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"\n{i}. {opp.get('title', 'N/A')}")
            print(f"   Keyword: {opp.get('keyword', 'N/A')}")
            print(f"   Type: {opp.get('type', 'N/A')}")
            print(f"   Programs: {', '.join(opp.get('programs', []))}")
            print(f"   Urgency: {opp.get('urgency', 'N/A')}/10")
            print(f"   Why: {opp.get('why', 'N/A')}")
    else:
        print("\n⚠️  No opportunities identified")
        print("   Check your ANTHROPIC_API_KEY in .env")
    
    # Save report
    filename = save_results(all_trends, all_reddit, opportunities)
    
    print("\n" + "=" * 60)
    print("  INTELLIGENCE RUN COMPLETE")
    print(f"  Trends: {len(all_trends)} keywords")
    print(f"  Reddit: {len(all_reddit)} posts analyzed")
    print(f"  Opportunities: {len(opportunities)} identified")
    print(f"  Report: {filename}")
    print("=" * 60)
    
    return opportunities

if __name__ == "__main__":
    run_intelligence()
