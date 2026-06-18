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

# Keywords we're looking for
KEYWORDS = [
    'sulfur', 'gypsum', 'cargo handling', 'discharge equipment',
    'port technology', 'automation', 'crane', 'conveyor',
    'environmental compliance', 'sustainability', 'IoT', 'AI',
    'maritime', 'shipping', 'container', 'terminal', 'logistics',
    'supply chain', 'port authority', 'harbor', 'breakbulk'
]

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
    """Send email with scraped articles"""
    
    if not articles:
        print("No relevant articles found.")
        return
    
    # Build email content
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; direction: rtl; }}
                .article {{ 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    margin-bottom: 20px; 
                    background: #f9f9f9;
                }}
                .article h3 {{ color: #1a5490; margin-top: 0; }}
                .source {{ color: #666; font-size: 12px; }}
                .link {{ color: #0066cc; text-decoration: none; }}
                .timestamp {{ color: #999; font-size: 11px; }}
            </style>
        </head>
        <body>
            <h2>📰 חדשות ימיות עולמיות - הזדמנויות למכירה לנמלים</h2>
            <p>דוח יומי: {datetime.now().strftime('%d.%m.%Y')}</p>
            <p>נמצאו {len(articles)} חדשות רלוונטיות:</p>
    """
    
    for article in articles:
        html_content += f"""
            <div class="article">
                <h3>{article['title']}</h3>
                <p class="source">מקור: {article['source']}</p>
                <p>{article['description']}</p>
                <a class="link" href="{article['link']}" target="_blank">קרא עוד →</a>
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
        msg["Subject"] = f"📦 Maritime Opportunities - {datetime.now().strftime('%d.%m.%Y')}"
        msg["From"] = sender_email
        msg["To"] = recipient_email
        
        msg.attach(MIMEText(html_content, "html"))
        
        # Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(sender_email, smtp_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        print(f"✅ Email sent to {recipient_email} with {len(articles)} articles")
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
