#!/usr/bin/env python3
"""
Maritime News Scraper for Daily Port Opportunities
Scans global maritime news sources for products/tech to sell to Israeli ports
"""

import requests
from bs4 import BeautifulSoup
import feedparser
import json
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urljoin
import time

# CRITICAL PRIORITY - Sulfur + Dust/Environmental (בעיית זיהום מי הים!)
CRITICAL_KEYWORDS = [
    'sulfur dust', 'dust suppression', 'dust control sulfur',
    'environmental protection port', 'sea pollution', 'marine pollution',
    'enclosed conveyor', 'cargo containment', 'rapid discharge',
    'air quality monitoring', 'dust emission', 'sulfur handling system'
]

# PRIMARY KEYWORDS - Sulfur (בראש המייל!)
PRIMARY_KEYWORDS = [
    'sulfur', 'sulphur', 'sulfur handling', 'sulfur discharge',
    'sulfur unloading', 'sulfur storage', 'bulk sulfur',
    'gypsum', 'dust control', 'environmental protection'
]

# SECONDARY - Other equipment
SECONDARY_KEYWORDS = [
    'conveyor system', 'bulk cargo', 'discharge equipment',
    'port equipment', 'unloading system', 'handling technology',
    'automation', 'IoT sensor', 'monitoring system',
    'environmental compliance', 'air quality', 'emissions control',
    'crane', 'loader', 'hopper', 'storage facility',
    'breakbulk', 'general cargo', 'bagging system'
]

KEYWORDS = CRITICAL_KEYWORDS + PRIMARY_KEYWORDS + SECONDARY_KEYWORDS

SOURCES = {
    'Maritime Executive': 'https://www.maritimeexecutive.com/feed',
    'JOC': 'https://www.joc.com/rss/port-terminals.xml',
    'TradeWinds': 'https://www.tradewindsnews.com/rss',
    'ShippingNews': 'https://www.shippingnews.net/feed',
    'Port Technology': 'https://www.porttechnology.org/feed',
}

SCRAPE_SOURCES = [
    'https://www.maritimeexecutive.com',
    'https://www.joc.com/port-terminals',
]

def normalize_keyword(text):
    """Convert text to lowercase for comparison"""
    return text.lower()

def is_critical_article(title, description=''):
    """Check if article is CRITICAL - Sulfur + Environmental/Dust control"""
    text = normalize_keyword(f"{title} {description}")
    has_sulfur = any(keyword in text for keyword in PRIMARY_KEYWORDS)
    has_critical = any(keyword in text for keyword in CRITICAL_KEYWORDS)
    return has_sulfur and has_critical

def is_sulfur_article(title, description=''):
    """Check if article is about sulfur handling"""
    text = normalize_keyword(f"{title} {description}")
    return any(keyword in text for keyword in PRIMARY_KEYWORDS)

def is_relevant(title, description=''):
    """Check if article is relevant to our search"""
    text = normalize_keyword(f"{title} {description}")
    return any(keyword in text for keyword in KEYWORDS)

def fetch_rss_feeds():
    """Fetch and parse RSS feeds"""
    articles = []
    
    for source_name, feed_url in SOURCES.items():
        try:
            print(f"Fetching {source_name}...")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:20]:  # Get last 20 articles
                title = entry.get('title', '')
                description = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '')
                published = entry.get('published', '')
                
                if is_relevant(title, description):
                    articles.append({
                        'source': source_name,
                        'title': title,
                        'description': description[:300],
                        'link': link,
                        'published': published,
                        'timestamp': datetime.now().isoformat()
                    })
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")
            continue
    
    return articles

def scrape_maritime_sites():
    """Scrape content from maritime news sites"""
    articles = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for url in SCRAPE_SOURCES:
        try:
            print(f"Scraping {url}...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for article headlines
            articles_found = soup.find_all(['article', 'div'], class_=lambda x: x and 'article' in x.lower())
            
            for article in articles_found[:15]:
                title_elem = article.find(['h2', 'h3', 'h4', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', url)
                    if not link.startswith('http'):
                        link = urljoin(url, link)
                    
                    description_elem = article.find(['p', 'span'], class_=lambda x: x and any(d in (x or '').lower() for d in ['summary', 'excerpt', 'description']))
                    description = description_elem.get_text(strip=True)[:300] if description_elem else ''
                    
                    if is_relevant(title, description):
                        articles.append({
                            'source': url.split('//')[1].split('/')[0],
                            'title': title,
                            'description': description,
                            'link': link,
                            'published': datetime.now().isoformat(),
                            'timestamp': datetime.now().isoformat()
                        })
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            continue
        
        time.sleep(2)  # Be respectful
    
    return articles

def load_seen_articles():
    """Load previously sent articles to avoid duplicates"""
    seen_file = 'seen_articles.json'
    if os.path.exists(seen_file):
        try:
            with open(seen_file, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_seen_articles(articles):
    """Save articles to avoid re-sending"""
    seen_file = 'seen_articles.json'
    with open(seen_file, 'w') as f:
        json.dump(articles, f, indent=2)

def send_email(articles, recipient_email, smtp_password):
    """Send email with scraped articles - CRITICAL (Sulfur+Environmental) FIRST!"""
    
    if not articles:
        print("No relevant articles found.")
        return
    
    # Separate articles into 3 categories
    critical_articles = [a for a in articles if is_critical_article(a['title'], a['description'])]
    sulfur_articles = [a for a in articles if is_sulfur_article(a['title'], a['description']) and a not in critical_articles]
    other_articles = [a for a in articles if a not in critical_articles and a not in sulfur_articles]
    
    # Build email content
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; direction: rtl; color: #333; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
                .header h2 {{ margin: 0; color: #1a1a1a; }}
                .header p {{ margin: 5px 0; color: #666; }}
                
                .critical-section {{ background: #ffebee; border-left: 5px solid #c62828; padding: 20px; margin-bottom: 30px; border-radius: 4px; box-shadow: 0 2px 8px rgba(198,40,40,0.2); }}
                .critical-section h3 {{ color: #c62828; margin-top: 0; font-size: 18px; }}
                
                .sulfur-section {{ background: #fff3f3; border-left: 5px solid #d32f2f; padding: 20px; margin-bottom: 30px; border-radius: 4px; }}
                .sulfur-section h3 {{ color: #d32f2f; margin-top: 0; font-size: 18px; }}
                
                .article {{ 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    margin-bottom: 20px; 
                    background: #f9f9f9;
                    border-radius: 4px;
                }}
                .article.critical {{
                    border-left: 4px solid #c62828;
                    background: #fff5f5;
                }}
                .article.sulfur {{
                    border-left: 4px solid #ff6b6b;
                    background: #fff8f8;
                }}
                .article h3 {{ color: #1a5490; margin-top: 0; font-size: 16px; }}
                .article.critical h3 {{ color: #c62828; font-weight: bold; }}
                .article.sulfur h3 {{ color: #d32f2f; font-weight: bold; }}
                .source {{ color: #666; font-size: 12px; }}
                .link {{ color: #0066cc; text-decoration: none; }}
                .link:hover {{ text-decoration: underline; }}
                .timestamp {{ color: #999; font-size: 11px; }}
                .section-title {{ color: #666; font-size: 14px; margin-top: 30px; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
                .critical-badge {{ display: inline-block; background: #c62828; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px; margin-left: 10px; font-weight: bold; }}
                .sulfur-badge {{ display: inline-block; background: #d32f2f; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-left: 10px; font-weight: bold; }}
                .warning {{ color: #c62828; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📰 חדשות ימיות עולמיות</h2>
                <p><strong>הזדמנויות למכירה לנמלים</strong></p>
                <p>דוח יומי: {datetime.now().strftime('%d.%m.%Y')}</p>
                <p>סך הכל: {len(articles)} חדשות רלוונטיות</p>
            </div>
    """
    
    # CRITICAL ARTICLES - Top Priority! (Sulfur + Environmental/Dust)
    if critical_articles:
        html_content += f"""
            <div class="critical-section">
                <h3>🔴🌊 CRITICAL - בעיה זיהום מי הים! ({len(critical_articles)})</h3>
                <p class="warning">⚠️ פתרונות לבעיית הפיכת חומר אבקתי לים בזמן פריקת גופרית</p>
                <p>אלו החדשות החשובות ביותר:</p>
        """
        
        for article in critical_articles:
            html_content += f"""
                <div class="article critical">
                    <h3>{article['title']} <span class="critical-badge">🌊 CRITICAL</span></h3>
                    <p class="source">📍 מקור: {article['source']}</p>
                    <p>{article['description']}</p>
                    <a class="link" href="{article['link']}" target="_blank">🔗 קרא עוד →</a>
                    <p class="timestamp">{article['published']}</p>
                </div>
            """
        
        html_content += "</div>"
    
    # SULFUR ARTICLES - High Priority
    if sulfur_articles:
        html_content += f"""
            <div class="sulfur-section">
                <h3>🔴 חדשות גופרית ({len(sulfur_articles)})</h3>
                <p>פתרונות וטכנולוגיות נוספות לטיפול בגופרית:</p>
        """
        
        for article in sulfur_articles:
            html_content += f"""
                <div class="article sulfur">
                    <h3>{article['title']} <span class="sulfur-badge">🔴 SULFUR</span></h3>
                    <p class="source">📍 מקור: {article['source']}</p>
                    <p>{article['description']}</p>
                    <a class="link" href="{article['link']}" target="_blank">🔗 קרא עוד →</a>
                    <p class="timestamp">{article['published']}</p>
                </div>
            """
        
        html_content += "</div>"
    
    # OTHER ARTICLES
    if other_articles:
        html_content += f"""
            <div class="section-title">📦 חדשות נוספות ({len(other_articles)})</div>
        """
        
        for article in other_articles:
            html_content += f"""
                <div class="article">
                    <h3>{article['title']}</h3>
                    <p class="source">📍 מקור: {article['source']}</p>
                    <p>{article['description']}</p>
                    <a class="link" href="{article['link']}" target="_blank">🔗 קרא עוד →</a>
                    <p class="timestamp">{article['published']}</p>
                </div>
            """
    
    html_content += """
        </body>
    </html>
    """
    
    # Send via Gmail SMTP
    try:
        sender_email = "omri42000@gmail.com"
        
        msg = MIMEMultipart("alternative")
        subject = f"📦 Maritime Opportunities - {datetime.now().strftime('%d.%m.%Y')}"
        if critical_articles:
            subject = f"🔴🌊 CRITICAL - {len(critical_articles)} solutions! - {datetime.now().strftime('%d.%m.%Y')}"
        elif sulfur_articles:
            subject = f"🔴 {len(sulfur_articles)} SULFUR opportunities - {datetime.now().strftime('%d.%m.%Y')}"
        
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email
        
        msg.attach(MIMEText(html_content, "html"))
        
        # Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(sender_email, smtp_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        print(f"✅ Email sent to {recipient_email}")
        print(f"   - CRITICAL articles: {len(critical_articles)}")
        print(f"   - Sulfur articles: {len(sulfur_articles)}")
        print(f"   - Other articles: {len(other_articles)}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def main():
    """Main execution"""
    print("🚢 Starting Maritime News Scraper...")
    print(f"Timestamp: {datetime.now()}")
    
    # Get environment variables
    recipient_email = os.getenv('RECIPIENT_EMAIL', 'omri42000@gmail.com')
    smtp_password = os.getenv('GMAIL_PASSWORD')
    
    if not smtp_password:
        print("❌ GMAIL_APP_PASSWORD not set in environment")
        return
    
    # Load previously seen articles
    seen_articles = load_seen_articles()
    seen_titles = set(a['title'] for a in seen_articles)
    
    # Fetch articles
    print("\n📡 Fetching RSS feeds...")
    rss_articles = fetch_rss_feeds()
    
    print("🕷️ Scraping maritime sites...")
    scraped_articles = scrape_maritime_sites()
    
    all_articles = rss_articles + scraped_articles
    
    # Filter out duplicates
    new_articles = [a for a in all_articles if a['title'] not in seen_titles]
    
    # Remove old entries (keep last 100)
    all_seen = seen_articles + new_articles
    all_seen = all_seen[-100:]
    
    print(f"\n📊 Results:")
    print(f"  RSS articles found: {len(rss_articles)}")
    print(f"  Scraped articles found: {len(scraped_articles)}")
    print(f"  New relevant articles: {len(new_articles)}")
    
    if new_articles:
        # Send email
        send_email(new_articles, recipient_email, smtp_password)
        
        # Save to file for backup
        with open('latest_articles.json', 'w', encoding='utf-8') as f:
            json.dump(new_articles, f, ensure_ascii=False, indent=2)
    
    # Save seen articles
    save_seen_articles(all_seen)
    
    print("\n✅ Scraper completed successfully")

if __name__ == "__main__":
    main()
