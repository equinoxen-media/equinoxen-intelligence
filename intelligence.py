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

# ─── LAYER 1: GOOGLE KEYWORDS VIA SERPAPI ───────────────────────
def get_keyword_opportunities(niche):
    """Use SerpAPI to find real keyword opportunities by searching Google"""
    print(f"\n📈 Finding keywords for: {niche}")
    
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        print("  ⚠️  No SERPAPI_KEY — skipping")
        return []
    
    results = []
    
    # Search variations that reveal buyer intent
    searches = [
        f"best {niche} 2026",
        f"{niche} review",
        f"{niche} comparison",
        f"{niche} alternative",
    ]
    
#    for search_query in searches[:2]:  # Limit to 2 per niche to save credits
    for search_query in searches[:1]:  # Limit to 1 per niche to save credits
        try:
            params = {
                "engine": "google",
                "q": search_query,
                "location": "United States",
                "gl": "us",
                "hl": "en",
                "num": 10,
                "api_key": serpapi_key
            }
            
            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"  ⚠️  SerpAPI error: {response.status_code}")
                continue
            
            data = response.json()
            
            # Extract related searches — gold for content ideas
            related_searches = data.get("related_searches", [])
            for item in related_searches[:5]:
                query = item.get("query", "")
                if query:
                    results.append({
                        'keyword': query,
                        'type': 'related_search',
                        'value': 100,
                        'niche': niche,
                        'source': 'serpapi_related',
                        'search_query': search_query
                    })
            
            # Extract People Also Ask — great for FAQ content
            paa = data.get("related_questions", [])
            for item in paa[:3]:
                question = item.get("question", "")
                if question:
                    results.append({
                        'keyword': question,
                        'type': 'people_also_ask',
                        'value': 80,
                        'niche': niche,
                        'source': 'serpapi_paa',
                        'search_query': search_query
                    })
            
            # Extract organic result titles for competitor analysis
            organic = data.get("organic_results", [])
            for item in organic[:3]:
                title = item.get("title", "")
                if title and any(word in title.lower() for word in ['best', 'review', 'vs', 'alternative', 'comparison']):
                    results.append({
                        'keyword': title,
                        'type': 'competitor_title',
                        'value': 60,
                        'niche': niche,
                        'source': 'serpapi_organic',
                        'search_query': search_query
                    })
            
            print(f"  Found {len(results)} keywords for '{search_query}'")
            time.sleep(2)
            
        except Exception as e:
            print(f"  ⚠️  Error for '{search_query}': {e}")
            continue
    
    return results

# ─── LAYER 1.2: GOOGLE AUTOCOMPLETE ───────────────────────
def get_google_autocomplete(niche):
    """Get keyword ideas from Google Autocomplete - completely free"""
    print(f"\n🔍 Google Autocomplete for: {niche}")
    
    results = []
    
    # Different search patterns
    prefixes = [
        f"best {niche}",
        f"{niche} review",
        f"{niche} vs",
        f"{niche} alternative",
        f"cheap {niche}",
        f"{niche} for small business",
        f"top {niche}",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for prefix in prefixes[:4]:
        try:
            response = requests.get(
                "https://suggestqueries.google.com/complete/search",
                params={
                    "client": "firefox",
                    "q": prefix,
                    "hl": "en",
                    "gl": "us"
                },
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                suggestions = response.json()
                if len(suggestions) > 1:
                    for suggestion in suggestions[1][:5]:
                        results.append({
                            'keyword': suggestion,
                            'type': 'autocomplete',
                            'value': 90,
                            'niche': niche,
                            'source': 'google_autocomplete'
                        })
            
            time.sleep(1)
            
        except Exception as e:
            continue
    
    print(f"  Found {len(results)} autocomplete suggestions")
    return results

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

# ─── LAYER 3: CHECK KEYWORD COMPETITION  VIA SERPAPI ──────────────────────
def check_keyword_competition(keyword):
    """Check how competitive a keyword is using SerpAPI"""
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        return "unknown"
    
    try:
        params = {
            "engine": "google",
            "q": keyword,
            "api_key": serpapi_key,
            "num": 10
        }
        
        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=30
        )
        
        if response.status_code != 200:
            return "unknown"
        
        data = response.json()
        ads = data.get("ads", [])
        organic = data.get("organic_results", [])
        
        # More ads = more commercial intent = worth targeting
        if len(ads) >= 4:
            return "high_commercial"
        elif len(ads) >= 1:
            return "medium_commercial"
        else:
            return "low_commercial"
            
    except:
        return "unknown"

# ─── LAYER 3.5: TRACK KEYWORKS PUBLISHED ─────────────────────────────────
def load_published_keywords():
    """Load already published keywords to avoid repetition"""
    tracker_path = os.path.join(os.path.dirname(__file__), 'published_posts.json')
    if os.path.exists(tracker_path):
        with open(tracker_path, 'r') as f:
            tracker = json.load(f)
            return tracker.get('keywords', [])
    return []

# ─── LAYER 4: CLAUDE ANALYSIS ─────────────────────────────────
def analyze_opportunities(trends_data, reddit_data, published_keywords=None):
    current_year = datetime.now().year
    """Use Claude to identify best content opportunities"""
    print("\n🤖 Analyzing opportunities with Claude...")
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("  ❌ No ANTHROPIC_API_KEY found in .env")
        return []
    
    # Check competition for top trend keywords
    print("  🔍 Checking keyword competition...")
#    for item in trends_data[:20]: 
    for item in trends_data[:5]: #limit to 5 for SERPAPI Limit
        keyword = item.get('keyword', '')
        if keyword:
            competition = check_keyword_competition(keyword)
            item['competition'] = competition
            time.sleep(1)
    
    client = anthropic.Anthropic(api_key=anthropic_key)
    
    trends_summary = json.dumps(trends_data[:30], indent=2) if trends_data else "No trends data available"
    
    reddit_summary = json.dumps([{
        'title': p['title'],
        'subreddit': p['subreddit'],
        'relevance': p['relevance'],
        'score': p.get('score', 0),
        'pain_points': p.get('pain_points', [])
    } for p in sorted(reddit_data, key=lambda x: x.get('relevance', 0), reverse=True)[:40]], indent=2)
    
    published_str = json.dumps(published_keywords[-30:]) if published_keywords else "[]"
    
    prompt = f"""You are an expert SaaS affiliate content strategist for Equinoxen Media,
an independent SaaS review and comparison website targeting business owners,
marketers and entrepreneurs.

CRITICAL: Today is {datetime.now().strftime('%B %d, %Y')}. 
The current year is {current_year}.
ALL article titles MUST use {current_year} — never use 2024, 2023 or any past year.

DIVERSITY REQUIREMENTS — MANDATORY:
- Return exactly 10 opportunities spread across ALL these categories
- Maximum 2 opportunities per category:
  CRM, Email Marketing, SEO Tools, Project Management,
  Business Automation, AI Tools, Finance, Website Builders
- Do not recommend the same software twice across the 10 opportunities
- Vary the software featured — do not default to the biggest names only
- Include at least 2 comparison articles (Product A vs Product B format)
- Include at least 2 buying guides
- Include at least 3 individual product reviews
- Feature lesser known alternatives alongside market leaders

ALREADY PUBLISHED — DO NOT REPEAT THESE KEYWORDS:
{published_str}

SCORING GUIDANCE:
- Prefer keywords with low or medium competition over high competition
- Weight Reddit posts with higher relevance scores more heavily
- Prioritize topics appearing in BOTH keyword data AND Reddit discussions
- High commercial intent signals: best, review, alternative, vs, top, comparison
- Favor lesser known software alternatives that have affiliate programs

GOOGLE TRENDS AND KEYWORD DATA (includes competition level):
{trends_summary}

REDDIT PAIN POINTS (sorted by relevance score):
{reddit_summary}

For each opportunity identify:
1. A compelling SEO optimized article title using {current_year} where relevant
2. Primary target keyword — exact phrase a buyer would search, 3-6 words,
   no year in the keyword, examples: "hubspot crm review", 
   "best crm for small business", "monday vs asana"
3. Content type: review, comparison, or buying_guide
4. Affiliate programs to target from this list:
   HubSpot, Monday.com, Semrush, Notion, Webflow, Jotform, 
   Zoho, Unbounce, Klaviyo, Asana, ClickUp, Ahrefs,
   QuickBooks, FreshBooks, Zapier, Canva, Grammarly
5. Why this opportunity is strong right now
6. Urgency score 1-10

Rules for good opportunities:
- High commercial intent keywords (best, review, alternative, vs, comparison)
- Prefer low/medium competition keywords over high competition
- Products with affiliate programs paying 20%+ commission
- Topics appearing in both keyword trends AND Reddit discussions get priority
- Avoid overly broad topics — be specific
- Mix of review, comparison and buying_guide types
- The keyword must appear verbatim in the article title

Formatting Rules
- If suggesting a buying guide or listicle, cap the number in the title at 5 (e.g. "5 Best..." not "10 Best...") as content will only cover 5 options
- Never include (), [], or | characters in titles
- Never use the words: Honest, Comprehensive, Ultimate, In-Depth, Definitive — these are AI writing signals

Return ONLY a valid JSON array. No markdown. No explanation:
[{{"title":"...{current_year}...","keyword":"...","type":"review","programs":["HubSpot"],"why":"...","urgency":8}}]"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=3000,  # Increased from 2000
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
    print("  EQUINOXEN MEDIA — INTELLIGENCE LAYER v3")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Keywords: Google Autocomplete (free) + SerpAPI")
    print("  Reddit: RSS feeds (no API needed)")
    print("=" * 60)
    
    all_trends = []
    all_reddit = []
    
    # Phase 1 — Keyword Research
    print("\n📊 PHASE 1: Keyword Research")
    print("-" * 40)
    
    day = datetime.now().weekday()
    start = (day * 2) % len(NICHES)
    todays_niches = NICHES[start:start+4] if start + 4 <= len(NICHES) else NICHES[start:] + NICHES[:4-(len(NICHES)-start)]
    for niche in todays_niches:
        # Always use free autocomplete
        autocomplete = get_google_autocomplete(niche)
        all_trends.extend(autocomplete)
        
        # Use SerpAPI if available
        if os.getenv("SERPAPI_KEY"):
            serpapi = get_keyword_opportunities(niche)
            all_trends.extend(serpapi)
        else:
            print("\n⚠️  Skipping keyword research — no SERPAPI_KEY")
        time.sleep(3)
    print(f"\n  ✅ Total keywords: {len(all_trends)}")
    
    # Phase 2 — Reddit via RSS
    print("\n💬 PHASE 2: Reddit RSS Analysis")
    print("-" * 40)
    for sub in SUBREDDITS:
        posts = get_reddit_via_rss(sub)
        all_reddit.extend(posts)
        time.sleep(3)
    
    print(f"\n  ✅ Total Reddit posts: {len(all_reddit)}")
    
    # Phase 3 — Claude Analysis
    print("\n🧠 PHASE 3: AI Opportunity Analysis")
    print("-" * 40)
    published_keywords = load_published_keywords()
    opportunities = analyze_opportunities(all_trends, all_reddit, published_keywords)
    
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
