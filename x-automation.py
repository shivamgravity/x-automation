import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import logging
import json
from groq import Groq
import tweepy
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global API Configuration
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
TWITTER_API_KEY = "YOUR_TWITTER_API_KEY"
TWITTER_API_SECRET = "YOUR_TWITTER_API_SECRET"
TWITTER_ACCESS_TOKEN = "YOUR_TWITTER_ACCESS_TOKEN"
TWITTER_ACCESS_TOKEN_SECRET = "YOUR_TWITTER_ACCESS_TOKEN_SECRET"

class BlogToTwitterAutomation:
    def __init__(self):
        """
        Initialize the combined blog-to-Twitter automation system
        """
        # Initialize Groq client
        try:
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            logger.info("✅ Groq API configured")
        except Exception as e:
            logger.error(f"❌ Groq initialization failed: {e}")
            raise
        
        # Initialize Twitter client
        try:
            self.twitter_client = tweepy.Client(
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
            )
            
            # Test Twitter authentication
            me = self.twitter_client.get_me()
            logger.info(f"✅ Twitter authenticated as: @{me.data.username}")
            
        except Exception as e:
            logger.error(f"❌ Twitter authentication failed: {e}")
            raise

    def fetch_blog_content(self, url: str) -> Dict[str, str]:
        """
        Fetch and extract content from blog post URL
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            logger.info(f"🌐 Fetching content from: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = ""
            title_selectors = ['post-title entry-title'] # ['h1', 'title', '.post-title', '.entry-title', '.article-title']
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    title = title_element.get_text().strip()
                    break
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'comment']):
                element.decompose()
            
            # Extract main content - try different selectors
            content_selectors = ['post-body entry-content float-container']
            '''[
                'article', 'main', '.post-content', '.entry-content', 
                '.content', '.post', '.blog-post', '[role="main"]',
                '.article-body', '.post-body'
            ]'''
            
            content = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content = content_element.get_text(separator=' ', strip=True)
                    break
            
            # Fallback: get all paragraph text
            if not content:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content).strip()
            content = re.sub(r'[^\w\s.,!?;:()\-\'""]', '', content)  # Remove special characters
            
            logger.info(f"✅ Extracted content:")
            logger.info(f"   Title: {title[:80]}...")
            logger.info(f"   Content: {len(content)} characters")
            logger.info(f"   Word count: {len(content.split())} words")
            
            return {
                'title': title,
                'content': content,
                'url': url,
                'word_count': len(content.split())
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching blog content: {e}")
            return {}

    def create_tweets_manually(self, blog_data: Dict[str, str], num_tweets: int = 3) -> List[Dict]:
        """
        Fallback: Create tweets manually when ChatGPT is not available
        """
        title = blog_data.get('title', 'Blog Post')
        content = blog_data.get('content', '')
        url = blog_data.get('url', '')
        
        print(f"\n📝 MANUAL TWEET CREATION")
        print(f"Blog Title: {title}")
        print(f"Content Preview: {content[:200]}...")
        print(f"URL: {url}")
        
        tweets = []
        for i in range(num_tweets):
            print(f"\n--- Creating Tweet {i+1}/{num_tweets} ---")
            
            while True:
                tweet_content = input(f"Enter tweet {i+1} content: ").strip()
                if not tweet_content:
                    print("❌ Tweet content cannot be empty!")
                    continue
                
                hashtags = input(f"Enter hashtags for tweet {i+1} (optional): ").strip()
                
                # Ensure hashtags format
                if hashtags and not hashtags.startswith('#'):
                    hashtags = '#' + hashtags.replace(' ', ' #').replace('##', '#')
                
                total_length = len(tweet_content + ' ' + hashtags)
                
                if total_length <= 280:
                    tweets.append({
                        'content': tweet_content,
                        'hashtags': hashtags,
                        'length': total_length
                    })
                    print(f"✅ Tweet {i+1} created ({total_length}/280 chars)")
                    break
                else:
                    print(f"❌ Tweet too long ({total_length}/280 chars). Please shorten it.")
        
        return tweets

    def create_tweets_with_groq(self, blog_data: Dict[str, str], num_tweets: int = 3) -> List[Dict]:
        """
        Use Groq AI to create engaging tweets from blog content
        """
        try:
            title = blog_data.get('title', '')
            content = blog_data.get('content', '')
            url = blog_data.get('url', '')
            
            # Limit content length for API limits
            max_content_length = 4000
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
                logger.info(f"📝 Truncated content to {max_content_length} characters")
            
            system_prompt = """You are an expert social media manager who creates viral Twitter content. 
Your job is to analyze blog posts and create engaging, shareable tweets that will get high engagement.

Rules:
1. Each tweet should be unique and highlight different aspects
2. Make tweets engaging, actionable, and valuable
3. Use emojis strategically (1-2 per tweet)
4. Include 2-4 relevant hashtags per tweet
5. Keep total length under 270 characters (content + hashtags)
6. Make them sound conversational and authentic
7. Focus on insights, tips, or interesting takeaways

Always return valid JSON format."""

            user_prompt = f"""
Create {num_tweets} engaging Twitter posts from this blog post:

TITLE: {title}

CONTENT: {content}

URL: {url}

Return as JSON array with this exact format:
[
  {{"content": "Tweet text here (engaging, no hashtags)", "hashtags": "#Tag1 #Tag2 #Tag3"}},
  {{"content": "Second tweet text", "hashtags": "#Tag1 #Tag2"}},
  {{"content": "Third tweet text", "hashtags": "#Tag1 #Tag2 #Tag3"}}
]

Make each tweet compelling and different. Focus on actionable insights or interesting points from the blog.
"""

            logger.info("🤖 Generating tweets with Groq AI...")
            
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",  # Fast Groq model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.8,  # More creative
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.info(f"📥 Groq Response: {result_text[:200]}...")
            
            # Extract JSON from response (Groq might include extra text)
            json_start = result_text.find('[')
            json_end = result_text.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = result_text[json_start:json_end]
            else:
                json_text = result_text
            
            # Parse JSON response
            tweets_data = json.loads(json_text)
            
            # Handle both array and object formats
            if isinstance(tweets_data, dict) and 'tweets' in tweets_data:
                tweets = tweets_data['tweets']
            elif isinstance(tweets_data, list):
                tweets = tweets_data
            else:
                logger.error("❌ Unexpected response format from Groq")
                return []
            
            # Validate and clean tweets
            valid_tweets = []
            for i, tweet in enumerate(tweets):
                content = tweet.get('content', '').strip()
                hashtags = tweet.get('hashtags', '').strip()
                
                if not content:
                    continue
                
                # Ensure hashtags start with #
                if hashtags and not hashtags.startswith('#'):
                    hashtags = '#' + hashtags.replace(' ', ' #')
                
                total_length = len(content + ' ' + hashtags)
                
                if total_length <= 280:
                    valid_tweets.append({
                        'content': content,
                        'hashtags': hashtags,
                        'length': total_length
                    })
                    logger.info(f"✅ Tweet {i+1}: {content[:50]}... ({total_length} chars)")
                else:
                    logger.warning(f"⚠️  Tweet {i+1} too long ({total_length} chars), skipping")
            
            logger.info(f"✅ Generated {len(valid_tweets)} valid tweets")
            return valid_tweets
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing Groq JSON response: {e}")
            logger.error(f"Raw response: {result_text}")
            return []
        except Exception as e:
            logger.error(f"❌ Error with Groq: {e}")
            return []

    def preview_tweets(self, tweets: List[Dict]) -> None:
        """
        Preview generated tweets before posting
        """
        if not tweets:
            print("❌ No tweets to preview")
            return
        
        print(f"\n{'='*60}")
        print(f"📋 TWEET PREVIEW ({len(tweets)} tweets)")
        print(f"{'='*60}")
        
        for i, tweet in enumerate(tweets, 1):
            content = tweet.get('content', '')
            hashtags = tweet.get('hashtags', '')
            length = tweet.get('length', len(content + ' ' + hashtags))
            
            print(f"\n--- Tweet {i} ({length}/280 chars) ---")
            print(f"{content}")
            if hashtags:
                print(f"{hashtags}")
            print(f"{'-'*40}")

    def get_user_confirmation(self) -> bool:
        """
        Get user confirmation before posting tweets
        """
        while True:
            choice = input("\n❓ Do you want to post these tweets? (y/n/preview): ").lower().strip()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            elif choice in ['p', 'preview']:
                return 'preview'
            else:
                print("Please enter 'y' for yes, 'n' for no, or 'preview' to see tweets again.")

    def post_tweet(self, content: str, hashtags: str = "") -> Optional[Dict]:
        """
        Post a single tweet to Twitter
        """
        # Combine content and hashtags
        if hashtags and not content.endswith(' '):
            tweet_text = f"{content} {hashtags}"
        else:
            tweet_text = f"{content}{hashtags}"
        
        # Make sure it's not too long
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
        
        try:
            logger.info(f"📤 Posting: {tweet_text[:50]}...")
            response = self.twitter_client.create_tweet(text=tweet_text)
            
            if response.data:
                logger.info(f"✅ Tweet posted! ID: {response.data['id']}")
                return {
                    'success': True,
                    'id': response.data['id'],
                    'text': tweet_text,
                    'error': None
                }
            else:
                logger.error("❌ No response data received")
                return {
                    'success': False,
                    'id': None,
                    'text': tweet_text,
                    'error': 'No response data received'
                }
                
        except Exception as e:
            logger.error(f"❌ Error posting tweet: {e}")
            return {
                'success': False,
                'id': None,
                'text': tweet_text,
                'error': str(e)
            }

    def post_multiple_tweets(self, tweets: List[Dict], delay: int = 10) -> List[Dict]:
        """
        Post multiple tweets with delay between them and error reporting
        """
        results = []
        successful_posts = 0
        failed_posts = 0
        
        logger.info(f"🚀 Starting to post {len(tweets)} tweets...")
        
        for i, tweet in enumerate(tweets):
            content = tweet.get('content', '')
            hashtags = tweet.get('hashtags', '')
            
            if not content:
                logger.warning(f"⚠️  Skipping empty tweet {i+1}")
                results.append({
                    'success': False,
                    'id': None,
                    'text': '',
                    'error': 'Empty content'
                })
                failed_posts += 1
                continue
            
            print(f"\n📤 Posting tweet {i+1}/{len(tweets)}...")
            result = self.post_tweet(content, hashtags)
            results.append(result)
            
            if result['success']:
                successful_posts += 1
                print(f"✅ Tweet {i+1} posted successfully!")
            else:
                failed_posts += 1
                print(f"❌ Tweet {i+1} failed: {result['error']}")
            
            # Wait between tweets (except for the last one)
            if i < len(tweets) - 1:
                logger.info(f"⏰ Waiting {delay} seconds before next tweet...")
                time.sleep(delay)
        
        # Summary report
        print(f"\n{'='*50}")
        print(f"📊 POSTING SUMMARY")
        print(f"{'='*50}")
        print(f"✅ Successful: {successful_posts}")
        print(f"❌ Failed: {failed_posts}")
        print(f"📈 Success Rate: {(successful_posts/len(tweets)*100):.1f}%")
        
        if failed_posts > 0:
            print(f"\n❌ FAILED TWEETS:")
            for i, result in enumerate(results):
                if not result['success']:
                    print(f"   Tweet {i+1}: {result['error']}")
        
        return results

    def process_blog_to_twitter(self, url: str, num_tweets: int = 3, delay: int = 10) -> List[Dict]:
        """
        Complete pipeline: Blog URL → Tweet Generation → Manual Confirmation → Twitter Posting
        """
        logger.info(f"🚀 Starting complete blog-to-Twitter automation")
        logger.info(f"   URL: {url}")
        logger.info(f"   Target tweets: {num_tweets}")
        
        # Step 1: Fetch blog content
        print("📥 Step 1: Fetching blog content...")
        blog_data = self.fetch_blog_content(url)
        
        if not blog_data or not blog_data.get('content'):
            print("❌ Could not extract blog content")
            return []
        
        if len(blog_data['content']) < 100:
            print("⚠️  Very short content extracted, results may be poor")
        
        # Step 2: Generate tweets with ChatGPT
        print("\n🤖 Step 2: Generating tweets with ChatGPT...")
        tweets = self.create_tweets_with_groq(blog_data, num_tweets)
        
        if not tweets:
            print("❌ ChatGPT failed. Switching to manual tweet creation...")
            choice = input("Do you want to create tweets manually? (y/n): ").lower().strip()
            if choice in ['y', 'yes']:
                tweets = self.create_tweets_manually(blog_data, num_tweets)
            else:
                print("❌ No tweets generated")
                return []
        
        # Step 3: Add blog URL to last tweet (optional)
        if tweets and url:
            last_tweet = tweets[-1]
            url_text = f"\n\nRead more: {url}"
            
            if len(last_tweet['content'] + url_text + ' ' + last_tweet['hashtags']) <= 280:
                last_tweet['content'] += url_text
                last_tweet['length'] = len(last_tweet['content'] + ' ' + last_tweet['hashtags'])
        
        # Step 4: Preview and get confirmation
        while True:
            print("\n📋 Step 3: Tweet Preview")
            self.preview_tweets(tweets)
            
            confirmation = self.get_user_confirmation()
            
            if confirmation == True:
                # Step 5: Post tweets
                print("\n📤 Step 4: Posting tweets to Twitter...")
                results = self.post_multiple_tweets(tweets, delay)
                return results
            elif confirmation == False:
                print("❌ Tweet posting cancelled by user")
                return []
            else:  # preview
                continue  # Show preview again
        
        return []

# Usage example
if __name__ == "__main__":
    # Initialize the automation system
    try:
        automation = BlogToTwitterAutomation()
        
        # Process a blog post
        blog_url = input("Enter your blog post url: ")
        results = automation.process_blog_to_twitter(
            url=blog_url,
            num_tweets=4,
            delay=10  # seconds between tweets
        )
        
        print(f"\n🎉 Process completed! {len([r for r in results if r['success']])} tweets posted successfully.")
        
    except Exception as e:
        logger.error(f"❌ Automation failed: {e}")
        print(f"❌ Error: {e}")
