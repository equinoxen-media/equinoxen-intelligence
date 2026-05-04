import os
import json
import time
import praw
import pandas as pd
from pytrends.request import TrendReq
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
    "marketing",
    "startups",
    "SaaS",
    "productivity",
    "digitalnomad",
    "freelance",
]

# ─── REDDIT SETUP ─────────────────────────────────────────────
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)

# ─── GOOGLE TRENDS SETUP ──────────────────────────────────────
pytrends = TrendReq(hl='en-US', tz=360)

# ─── LAYER 1: GOOGLE TRENDS ───────────────────────────────────
def get_trending_topics(niche):
    """Get trending searches for a niche from Google Trends"""
    print(f"\n📈 Checking Google Trends for: {niche}")
    try:
        pytrends.build_payload([niche], timeframe='now 7-d', geo='US')
        related_queries = pytrends.related_queries()
        
        results = []
        if niche in related_queries:
            rising = related_queries[niche].get('rising')
            top = related_queries[niche].get('top')
            
            if rising is not None and not rising.empty:
                for _, row in rising.head(5).iterrows():
                    results.append({
                        'keyword': row['query'],
                        'type': 'rising',
                        'value': row['value'],
                        'niche': niche
                    })
            
            if top is not None and not top.empty:
                for _, row in top.head(5).iterrows():
                    results.append({
                        'keyword': row['query'],
                        'type': 'top',
                        'value': row['value'],
                        'niche': niche
                    })
        
        time.sleep(2)  # Respect rate limits
        return results
    except Exception as e:
        print(f"  ⚠️  Trends error for {niche}: {e}")
        return []

# ─── LAYER 2: REDDIT PAIN POINTS ──────────────────────────────
def get_reddit_pain_points(subreddit_name, limit=25):
    """Find SaaS pain points from Reddit posts"""
    print(f"\n🔍 Scanning r/{subreddit_name}...")
    pain_points = []
    
    try:
        subreddit = reddit.subreddit(subreddit_name)
        
        # Check hot posts
        for post in subreddit.hot(limit=limit):
            score = 0
            keywords = [
                'recommend', 'alternative', 'looking for', 'best tool',
                'which software', 'need help', 'frustrated', 'switch from',
                'better than', 'replace', 'comparison', 'vs ', 'review',
                'anyone use', 'thoughts on', 'worth it', 'pricing',
                'too expensive', 'free alternative', 'open source'
            ]
            
            title_lower = post.title.lower()
            for kw in keywords:
                if kw in title_lower:
                    score += 1
            
            if score >= 1:
                pain_points.append({
                    'title': post.title,
                    'score': post.score,
                    'comments': post.num_comments,
                    'relevance': score,
                    'url': f"https://reddit.com{post.permalink}",
                    'subreddit': subreddit_name
                })
        
        # Sort by relevance and engagement
        pain_points.sort(key=lambda x: x['relevance'] * x['score'], reverse=True)
        return pain_points[:10]
        
    except Exception as e:
        print(f"  ⚠️  Reddit error for r/{subreddit_name}: {e}")
        return []

# ─── LAYER 3: CLAUDE ANALYSIS ─────────────────────────────────
def analyze_opportunities(trends_data, reddit_data):
    """Use Claude to identify the best content opportunities"""
    print("\n🤖 Analyzing opportunities with Claude...")
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Prepare data summary
    trends_summary = json.dumps(trends_data[:20], indent=2)
    reddit_summary = json.dumps(reddit_data[:20], indent=2)
    
    prompt = f"""You are an expert SaaS affiliate content strategist for Equinoxen Media, 
an independent SaaS review and comparison website.

Analyze these trending topics and Reddit pain points to identify the TOP 10 content 
opportunities for affiliate review articles.

GOOGLE TRENDS DATA:
{trends_summary}

REDDIT PAIN POINTS:
{reddit_summary}

For each opportunity provide:
1. Suggested article title (SEO optimized)
2. Target keyword (1-3 words, high commercial intent)
3. Content type (review/comparison/buying guide)
4. Estimated affiliate programs to target
5. Why this opportunity is strong right now
6. Urgency score (1-10)

Return ONLY a JSON array. No markdown. No explanation. Just raw JSON:
[{{"title":"...","keyword":"...","type":"...","programs":["..."],"why":"...","urgency":8}}]"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        # Clean up response
        response_text = response_text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        opportunities = json.loads(response_text)
        return opportunities
    except Exception as e:
        print(f"  ⚠️  Claude analysis error: {e}")
        return []

# ─── LAYER 4: SAVE RESULTS ────────────────────────────────────
def save_results(trends_data, reddit_data, opportunities):
    """Save all results to a JSON file"""
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
    print("  EQUINOXEN MEDIA — INTELLIGENCE LAYER")
    print(f"  Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_trends = []
    all_reddit = []
    
    # Collect Google Trends data
    print("\n📊 PHASE 1: Google Trends Analysis")
    print("-" * 40)
    for niche in NICHES[:4]:  # Start with 4 niches
        trends = get_trending_topics(niche)
        all_trends.extend(trends)
        print(f"  Found {len(trends)} trending keywords for {niche}")
    
    # Collect Reddit data
    print("\n💬 PHASE 2: Reddit Pain Point Analysis")
    print("-" * 40)
    for sub in SUBREDDITS[:4]:  # Start with 4 subreddits
        posts = get_reddit_pain_points(sub)
        all_reddit.extend(posts)
        print(f"  Found {len(posts)} relevant posts in r/{sub}")
    
    # Analyze with Claude
    print("\n🧠 PHASE 3: AI Opportunity Analysis")
    print("-" * 40)
    opportunities = analyze_opportunities(all_trends, all_reddit)
    
    # Display top opportunities
    print("\n🎯 TOP CONTENT OPPORTUNITIES:")
    print("=" * 60)
    for i, opp in enumerate(opportunities[:5], 1):
        print(f"\n{i}. {opp.get('title', 'N/A')}")
        print(f"   Keyword: {opp.get('keyword', 'N/A')}")
        print(f"   Type: {opp.get('type', 'N/A')}")
        print(f"   Programs: {', '.join(opp.get('programs', []))}")
        print(f"   Urgency: {opp.get('urgency', 'N/A')}/10")
        print(f"   Why: {opp.get('why', 'N/A')}")
    
    # Save everything
    filename = save_results(all_trends, all_reddit, opportunities)
    
    print("\n" + "=" * 60)
    print("  INTELLIGENCE RUN COMPLETE")
    print(f"  {len(all_trends)} trends + {len(all_reddit)} Reddit posts analyzed")
    print(f"  {len(opportunities)} content opportunities identified")
    print("=" * 60)
    
    return opportunities

if __name__ == "__main__":
    run_intelligence()
