from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional
import os
import json
import subprocess
import asyncio
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from emergentintegrations.llm.chat import LlmChat, UserMessage
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import tempfile
import base64
from playwright.async_api import async_playwright
import time

# Set Playwright browser path
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'

# Set Chrome path for Lighthouse
os.environ['CHROME_PATH'] = '/pw-browsers/chromium-1091/chrome-linux/chrome'

app = FastAPI(title="AI-Powered SEO Tool", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
client = AsyncIOMotorClient(MONGO_URL)
db = client.seo_tool

# Environment variables
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyApJd6nf2WFYow_O2K4EFVH2j5WD6ktF6U')

class URLAnalysisRequest(BaseModel):
    url: HttpUrl

class CompetitorAnalysisRequest(BaseModel):
    primary_url: HttpUrl
    competitor_urls: List[HttpUrl]

class SEOContentTemplateRequest(BaseModel):
    url: HttpUrl
    target_keywords: List[str]
    content_type: str = "article"  # article, blog, product, landing

class SEOAnalysisResponse(BaseModel):
    id: str
    url: str
    lighthouse_score: Dict[str, Any]
    screenshots: List[Dict[str, str]]
    ai_suggestions: Dict[str, Any]  # Changed from str to Dict for structured suggestions
    keywords: List[str]
    backlinks: List[str]
    performance_metrics: Dict[str, Any]
    performance_issues: List[str]  # New field for specific issues
    seo_issues: List[str]  # New field for specific issues
    accessibility_issues: List[str]  # New field for specific issues
    best_practices_issues: List[str]  # New field for specific issues
    created_at: datetime

class CompetitorAnalysisResponse(BaseModel):
    id: str
    primary_url: str
    competitor_data: List[Dict[str, Any]]
    comparison_insights: Dict[str, Any]
    competitive_keywords: List[str]
    content_gaps: List[str]
    created_at: datetime

class SEOContentTemplateResponse(BaseModel):
    id: str
    url: str
    content_template: Dict[str, Any]
    keyword_strategy: Dict[str, Any]
    content_outline: Dict[str, Any]
    created_at: datetime

@app.get("/")
async def root():
    return {"message": "AI-Powered SEO Tool API"}

@app.post("/api/analyze", response_model=SEOAnalysisResponse)
async def analyze_website(request: URLAnalysisRequest):
    """
    Comprehensive website analysis including:
    - Lighthouse performance analysis
    - Responsive screenshots
    - AI-powered suggestions
    - Keywords analysis
    - Backlinks analysis
    """
    try:
        url = str(request.url)
        analysis_id = str(uuid.uuid4())
        
        # Run all analyses in parallel
        lighthouse_task = asyncio.create_task(run_lighthouse_analysis(url))
        screenshots_task = asyncio.create_task(generate_responsive_screenshots(url))
        keywords_task = asyncio.create_task(analyze_keywords(url))
        backlinks_task = asyncio.create_task(analyze_backlinks(url))
        
        # Wait for all analyses to complete
        lighthouse_score = await lighthouse_task
        screenshots = await screenshots_task
        keywords = await keywords_task
        backlinks = await backlinks_task
        
        # Extract specific issues from lighthouse data
        performance_issues = extract_performance_issues(lighthouse_score)
        seo_issues = extract_seo_issues(lighthouse_score)
        accessibility_issues = extract_accessibility_issues(lighthouse_score)
        best_practices_issues = extract_best_practices_issues(lighthouse_score)
        
        # Generate structured AI suggestions based on all collected data
        ai_suggestions = await generate_structured_ai_suggestions(
            url, lighthouse_score, keywords, backlinks, 
            performance_issues, seo_issues, accessibility_issues, best_practices_issues
        )
        
        # Calculate performance metrics
        performance_metrics = calculate_performance_metrics(lighthouse_score, len(keywords), len(backlinks))
        
        # Store analysis results
        analysis_result = {
            "_id": analysis_id,
            "url": url,
            "lighthouse_score": lighthouse_score,
            "screenshots": screenshots,
            "ai_suggestions": ai_suggestions,
            "keywords": keywords,
            "backlinks": backlinks,
            "performance_metrics": performance_metrics,
            "performance_issues": performance_issues,
            "seo_issues": seo_issues,
            "accessibility_issues": accessibility_issues,
            "best_practices_issues": best_practices_issues,
            "created_at": datetime.utcnow()
        }
        
        await db.analyses.insert_one(analysis_result)
        
        return SEOAnalysisResponse(
            id=analysis_id,
            url=url,
            lighthouse_score=lighthouse_score,
            screenshots=screenshots,
            ai_suggestions=ai_suggestions,
            keywords=keywords,
            backlinks=backlinks,
            performance_metrics=performance_metrics,
            performance_issues=performance_issues,
            seo_issues=seo_issues,
            accessibility_issues=accessibility_issues,
            best_practices_issues=best_practices_issues,
            created_at=analysis_result["created_at"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

async def run_lighthouse_analysis(url: str) -> Dict[str, Any]:
    """Run Lighthouse analysis on the provided URL"""
    try:
        # Create a temporary file for lighthouse output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        # Run lighthouse with better configuration for containerized environment
        cmd = [
            'lighthouse',
            url,
            '--output=json',
            '--output-path=' + temp_file,
            '--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage --disable-gpu --remote-debugging-port=9222',
            '--preset=perf',
            '--max-wait-for-fcp=15000',
            '--max-wait-for-load=35000',
            '--throttling-method=simulate',
            '--disable-storage-reset'
        ]
        
        print(f"Running lighthouse analysis for: {url}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Set a reasonable timeout for lighthouse
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
        except asyncio.TimeoutError:
            process.kill()
            print(f"Lighthouse analysis timed out for {url}")
            raise Exception("Lighthouse analysis timed out")
        
        if process.returncode != 0:
            print(f"Lighthouse failed with return code {process.returncode}")
            print(f"STDERR: {stderr.decode()}")
            print(f"STDOUT: {stdout.decode()}")
            raise Exception(f"Lighthouse analysis failed: {stderr.decode()}")
        
        # Read the lighthouse results
        try:
            with open(temp_file, 'r') as f:
                lighthouse_data = json.load(f)
        except Exception as e:
            print(f"Failed to read lighthouse results: {str(e)}")
            raise Exception(f"Failed to read lighthouse results: {str(e)}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # Extract key metrics
        categories = lighthouse_data.get('categories', {})
        audits = lighthouse_data.get('audits', {})
        
        print(f"✅ Lighthouse analysis completed successfully for {url}")
        print(f"Performance: {categories.get('performance', {}).get('score', 0)}")
        print(f"SEO: {categories.get('seo', {}).get('score', 0)}")
        
        return {
            "performance": categories.get('performance', {}).get('score', 0),
            "accessibility": categories.get('accessibility', {}).get('score', 0),
            "best_practices": categories.get('best-practices', {}).get('score', 0),
            "seo": categories.get('seo', {}).get('score', 0),
            "categories": categories,
            "audits": audits
        }
        
    except Exception as e:
        print(f"Lighthouse analysis failed: {str(e)}")
        
        # Instead of returning mock data, try a simplified lighthouse run
        try:
            print("Attempting simplified lighthouse analysis...")
            
            # Try a simpler lighthouse command optimized for containerized environment
            simple_cmd = [
                'lighthouse',
                url,
                '--output=json',
                '--output-path=' + temp_file,
                '--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage --disable-gpu --disable-web-security --disable-features=VizDisplayCompositor',
                '--only-categories=performance,seo,accessibility,best-practices',
                '--skip-audits=screenshot-thumbnails,final-screenshot,uses-http2,uses-long-cache-ttl,uses-optimized-images',
                '--preset=perf',
                '--throttling-method=simulate',
                '--max-wait-for-fcp=10000',
                '--max-wait-for-load=25000'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *simple_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45.0)
            
            if process.returncode == 0:
                with open(temp_file, 'r') as f:
                    lighthouse_data = json.load(f)
                
                categories = lighthouse_data.get('categories', {})
                audits = lighthouse_data.get('audits', {})
                
                print(f"✅ Simplified lighthouse analysis completed for {url}")
                
                return {
                    "performance": categories.get('performance', {}).get('score', 0),
                    "accessibility": categories.get('accessibility', {}).get('score', 0),
                    "best_practices": categories.get('best-practices', {}).get('score', 0),
                    "seo": categories.get('seo', {}).get('score', 0),
                    "categories": categories,
                    "audits": audits
                }
            
        except Exception as simple_error:
            print(f"Simplified lighthouse also failed: {str(simple_error)}")
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # As absolute last resort, try to get basic page metrics using a different approach
        try:
            print("Attempting basic performance analysis...")
            return await get_basic_page_metrics(url)
        except Exception as basic_error:
            print(f"Basic analysis also failed: {str(basic_error)}")
            
            # Only return mock data as absolute last resort
            print("⚠️ Using fallback data - all lighthouse methods failed")
            return {
                "performance": 0.5,  # Lower fallback scores to indicate issues
                "accessibility": 0.7,
                "best_practices": 0.6,
                "seo": 0.5,
                "categories": {
                    "performance": {"score": 0.5, "title": "Performance (Fallback)"},
                    "accessibility": {"score": 0.7, "title": "Accessibility (Fallback)"},
                    "best-practices": {"score": 0.6, "title": "Best Practices (Fallback)"},
                    "seo": {"score": 0.5, "title": "SEO (Fallback)"}
                },
                "audits": {
                    "first-contentful-paint": {"numericValue": 3000, "title": "First Contentful Paint (Estimated)"},
                    "speed-index": {"numericValue": 4000, "title": "Speed Index (Estimated)"},
                    "largest-contentful-paint": {"numericValue": 5000, "title": "Largest Contentful Paint (Estimated)"}
                },
                "error": "Lighthouse analysis unavailable - using estimated values"
            }

async def get_basic_page_metrics(url: str) -> Dict[str, Any]:
    """Get basic page performance metrics using Playwright"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Start timing
            start_time = time.time()
            
            # Navigate to page and measure basic timing
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Get page metrics
            load_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Get basic page information
            title = await page.title()
            meta_description = await page.get_attribute('meta[name="description"]', 'content') or ""
            
            # Check for some basic SEO elements
            h1_count = await page.locator('h1').count()
            img_without_alt = await page.locator('img:not([alt])').count()
            
            # Check for HTTPS
            is_https = url.startswith('https://')
            
            await browser.close()
            
            # Calculate basic scores based on metrics
            performance_score = max(0, min(1, (5000 - load_time) / 5000))  # Better if load time < 5s
            seo_score = 1.0
            if not title:
                seo_score -= 0.3
            if not meta_description:
                seo_score -= 0.2
            if h1_count == 0:
                seo_score -= 0.2
            if h1_count > 1:
                seo_score -= 0.1
                
            accessibility_score = max(0, 1 - (img_without_alt * 0.1))  # Reduce for missing alt text
            best_practices_score = 0.9 if is_https else 0.5
            
            print(f"✅ Basic page analysis completed for {url}")
            print(f"Load time: {load_time:.0f}ms")
            print(f"Performance score: {performance_score:.2f}")
            print(f"SEO score: {seo_score:.2f}")
            
            return {
                "performance": performance_score,
                "accessibility": accessibility_score,
                "best_practices": best_practices_score,
                "seo": seo_score,
                "categories": {
                    "performance": {"score": performance_score, "title": "Performance (Basic Analysis)"},
                    "accessibility": {"score": accessibility_score, "title": "Accessibility (Basic Analysis)"},
                    "best-practices": {"score": best_practices_score, "title": "Best Practices (Basic Analysis)"},
                    "seo": {"score": seo_score, "title": "SEO (Basic Analysis)"}
                },
                "audits": {
                    "first-contentful-paint": {"numericValue": load_time * 0.6, "title": "First Contentful Paint (Estimated)"},
                    "speed-index": {"numericValue": load_time * 0.8, "title": "Speed Index (Estimated)"},
                    "largest-contentful-paint": {"numericValue": load_time * 0.9, "title": "Largest Contentful Paint (Estimated)"}
                },
                "method": "basic_analysis"
            }
            
    except Exception as e:
        print(f"Basic page metrics failed: {str(e)}")
        raise e

async def generate_responsive_screenshots(url: str) -> List[Dict[str, str]]:
    """Generate screenshots for different screen sizes"""
    try:
        screenshots = []
        
        # Screen sizes to test
        screen_sizes = [
            {"name": "Mobile", "width": 375, "height": 667},
            {"name": "Tablet", "width": 768, "height": 1024},
            {"name": "Laptop", "width": 1366, "height": 768},
            {"name": "Desktop", "width": 1920, "height": 1080}
        ]
        
        try:
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    
                    for size in screen_sizes:
                        try:
                            await page.set_viewport_size({"width": size["width"], "height": size["height"]})
                            await page.goto(url, wait_until="networkidle", timeout=30000)
                            
                            # Take screenshot
                            screenshot = await page.screenshot(full_page=False)
                            screenshot_base64 = base64.b64encode(screenshot).decode()
                            
                            screenshots.append({
                                "device": size["name"],
                                "width": str(size["width"]),
                                "height": str(size["height"]),
                                "screenshot": f"data:image/png;base64,{screenshot_base64}"
                            })
                            
                        except Exception as e:
                            print(f"Screenshot failed for {size['name']}: {str(e)}")
                            screenshots.append({
                                "device": size["name"],
                                "width": str(size["width"]),
                                "height": str(size["height"]),
                                "screenshot": "",
                                "error": str(e)
                            })
                    
                    await browser.close()
                except Exception as browser_error:
                    print(f"Browser launch failed: {str(browser_error)}")
                    # Generate mock screenshots if browser launch fails
                    for size in screen_sizes:
                        screenshots.append({
                            "device": size["name"],
                            "width": str(size["width"]),
                            "height": str(size["height"]),
                            "screenshot": "",
                            "error": f"Browser launch failed: {str(browser_error)}"
                        })
        except Exception as playwright_error:
            print(f"Screenshot generation failed: {str(playwright_error)}")
            # Generate mock screenshots if Playwright fails
            for size in screen_sizes:
                screenshots.append({
                    "device": size["name"],
                    "width": str(size["width"]),
                    "height": str(size["height"]),
                    "screenshot": "",
                    "error": f"Playwright error: {str(playwright_error)}"
                })
        
        return screenshots
        
    except Exception as e:
        print(f"Screenshot generation failed: {str(e)}")
        return []

async def analyze_keywords(url: str) -> List[str]:
    """Analyze keywords from the webpage"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text content
        text_content = soup.get_text()
        
        # Extract title and meta description
        title = soup.find('title')
        title_text = title.get_text() if title else ""
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_desc_text = meta_desc.get('content', '') if meta_desc else ""
        
        # Extract keywords from content
        all_text = f"{title_text} {meta_desc_text} {text_content}"
        
        # Simple keyword extraction (remove common words)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
        
        # Remove common stop words
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        
        keywords = [word for word in words if word not in stop_words]
        
        # Count frequency and return top keywords
        keyword_freq = {}
        for keyword in keywords:
            keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
        
        # Sort by frequency and return top 20
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [keyword for keyword, freq in sorted_keywords[:20]]
        
    except Exception as e:
        print(f"Keyword analysis failed: {str(e)}")
        return []

async def analyze_backlinks(url: str) -> List[str]:
    """Analyze potential backlinks (simplified version)"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract all external links
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http') and not urlparse(url).netloc in href:
                links.append(href)
        
        # Remove duplicates and return first 10
        unique_links = list(set(links))[:10]
        
        return unique_links
        
    except Exception as e:
        print(f"Backlink analysis failed: {str(e)}")
        return []

def extract_performance_issues(lighthouse_score: Dict[str, Any]) -> List[str]:
    """Extract specific performance issues from lighthouse data"""
    issues = []
    audits = lighthouse_score.get('audits', {})
    
    # Check First Contentful Paint
    fcp = audits.get('first-contentful-paint', {})
    if fcp.get('numericValue', 0) > 2000:
        issues.append(f"First Contentful Paint is slow ({fcp.get('numericValue', 0)}ms)")
    
    # Check Largest Contentful Paint
    lcp = audits.get('largest-contentful-paint', {})
    if lcp.get('numericValue', 0) > 2500:
        issues.append(f"Largest Contentful Paint is slow ({lcp.get('numericValue', 0)}ms)")
    
    # Check Speed Index
    si = audits.get('speed-index', {})
    if si.get('numericValue', 0) > 3000:
        issues.append(f"Speed Index is slow ({si.get('numericValue', 0)}ms)")
    
    # Check Cumulative Layout Shift
    cls = audits.get('cumulative-layout-shift', {})
    if cls.get('numericValue', 0) > 0.1:
        issues.append(f"Cumulative Layout Shift is high ({cls.get('numericValue', 0)})")
    
    # Check unused CSS
    unused_css = audits.get('unused-css-rules', {})
    if unused_css.get('details', {}).get('overallSavingsBytes', 0) > 10000:
        issues.append("Unused CSS detected - remove unused styles")
    
    # Check image optimization
    image_optimization = audits.get('uses-optimized-images', {})
    if image_optimization.get('score', 1) < 0.8:
        issues.append("Images are not optimized - compress and serve in modern formats")
    
    return issues

def extract_seo_issues(lighthouse_score: Dict[str, Any]) -> List[str]:
    """Extract specific SEO issues from lighthouse data"""
    issues = []
    audits = lighthouse_score.get('audits', {})
    
    # Check meta description
    meta_desc = audits.get('meta-description', {})
    if meta_desc.get('score', 1) < 1:
        issues.append("Missing or poor meta description")
    
    # Check title tag
    title_tag = audits.get('document-title', {})
    if title_tag.get('score', 1) < 1:
        issues.append("Missing or poor title tag")
    
    # Check headings
    headings = audits.get('heading-order', {})
    if headings.get('score', 1) < 1:
        issues.append("Heading elements are not in sequentially-descending order")
    
    # Check alt text
    alt_text = audits.get('image-alt', {})
    if alt_text.get('score', 1) < 1:
        issues.append("Images missing alt text")
    
    # Check robots.txt
    robots = audits.get('robots-txt', {})
    if robots.get('score', 1) < 1:
        issues.append("robots.txt issues detected")
    
    # Check hreflang
    hreflang = audits.get('hreflang', {})
    if hreflang.get('score', 1) < 1:
        issues.append("hreflang links are not valid")
    
    return issues

def extract_accessibility_issues(lighthouse_score: Dict[str, Any]) -> List[str]:
    """Extract specific accessibility issues from lighthouse data"""
    issues = []
    audits = lighthouse_score.get('audits', {})
    
    # Check color contrast
    color_contrast = audits.get('color-contrast', {})
    if color_contrast.get('score', 1) < 1:
        issues.append("Background and foreground colors do not have sufficient contrast ratio")
    
    # Check aria labels
    aria_labels = audits.get('aria-required-attr', {})
    if aria_labels.get('score', 1) < 1:
        issues.append("ARIA attributes are missing or invalid")
    
    # Check form labels
    form_labels = audits.get('label', {})
    if form_labels.get('score', 1) < 1:
        issues.append("Form elements do not have associated labels")
    
    # Check keyboard navigation
    keyboard_nav = audits.get('keyboard-traps', {})
    if keyboard_nav.get('score', 1) < 1:
        issues.append("Keyboard navigation issues detected")
    
    # Check focus order
    focus_order = audits.get('focus-traps', {})
    if focus_order.get('score', 1) < 1:
        issues.append("Focus is not trapped within modal dialogs")
    
    return issues

def extract_best_practices_issues(lighthouse_score: Dict[str, Any]) -> List[str]:
    """Extract specific best practices issues from lighthouse data"""
    issues = []
    audits = lighthouse_score.get('audits', {})
    
    # Check HTTPS
    https = audits.get('is-on-https', {})
    if https.get('score', 1) < 1:
        issues.append("Page is not served over HTTPS")
    
    # Check JavaScript errors
    js_errors = audits.get('errors-in-console', {})
    if js_errors.get('score', 1) < 1:
        issues.append("JavaScript errors detected in console")
    
    # Check deprecated APIs
    deprecated_apis = audits.get('deprecations', {})
    if deprecated_apis.get('score', 1) < 1:
        issues.append("Uses deprecated APIs")
    
    # Check content security policy
    csp = audits.get('csp-xss', {})
    if csp.get('score', 1) < 1:
        issues.append("Content Security Policy missing or ineffective")
    
    return issues

async def generate_structured_ai_suggestions(url: str, lighthouse_score: Dict[str, Any], keywords: List[str], backlinks: List[str], performance_issues: List[str], seo_issues: List[str], accessibility_issues: List[str], best_practices_issues: List[str]) -> Dict[str, Any]:
    """Generate structured AI suggestions for each metric"""
    try:
        if not GEMINI_API_KEY:
            return {
                "performance": {"suggestions": ["AI suggestions unavailable: Gemini API key not configured"], "priority": "high"},
                "seo": {"suggestions": ["AI suggestions unavailable: Gemini API key not configured"], "priority": "high"},
                "accessibility": {"suggestions": ["AI suggestions unavailable: Gemini API key not configured"], "priority": "medium"},
                "best_practices": {"suggestions": ["AI suggestions unavailable: Gemini API key not configured"], "priority": "medium"}
            }
        
        # Create Gemini chat instance
        chat = LlmChat(
            api_key=GEMINI_API_KEY,
            session_id=f"seo_analysis_{uuid.uuid4()}",
            system_message="You are an expert SEO consultant and web performance specialist. Provide specific, actionable recommendations for each metric category."
        ).with_model("gemini", "gemini-2.0-flash")
        
        # Generate suggestions for each metric
        suggestions = {}
        
        # Performance suggestions
        performance_prompt = f"""
        Analyze the performance issues for {url} and provide specific actionable recommendations:
        
        Current Performance Score: {lighthouse_score.get('performance', 0):.2f}
        
        Identified Issues:
        {chr(10).join(performance_issues) if performance_issues else "No specific issues identified"}
        
        Performance Metrics:
        - First Contentful Paint: {lighthouse_score.get('audits', {}).get('first-contentful-paint', {}).get('numericValue', 0)}ms
        - Speed Index: {lighthouse_score.get('audits', {}).get('speed-index', {}).get('numericValue', 0)}ms
        - Largest Contentful Paint: {lighthouse_score.get('audits', {}).get('largest-contentful-paint', {}).get('numericValue', 0)}ms
        
        Provide 3-5 specific, actionable recommendations to improve performance. Focus on technical solutions.
        """
        
        performance_response = await chat.send_message(UserMessage(text=performance_prompt))
        suggestions["performance"] = {
            "suggestions": [suggestion.strip() for suggestion in performance_response.split('\n') if suggestion.strip() and not suggestion.strip().startswith('#')],
            "priority": "high" if lighthouse_score.get('performance', 0) < 0.7 else "medium",
            "current_score": lighthouse_score.get('performance', 0),
            "issues": performance_issues
        }
        
        # SEO suggestions
        seo_prompt = f"""
        Analyze the SEO issues for {url} and provide specific actionable recommendations:
        
        Current SEO Score: {lighthouse_score.get('seo', 0):.2f}
        
        Identified Issues:
        {chr(10).join(seo_issues) if seo_issues else "No specific issues identified"}
        
        Top Keywords Found: {', '.join(keywords[:10])}
        External Links: {len(backlinks)} found
        
        Provide 3-5 specific, actionable SEO recommendations. Include keyword optimization strategies.
        """
        
        seo_response = await chat.send_message(UserMessage(text=seo_prompt))
        suggestions["seo"] = {
            "suggestions": [suggestion.strip() for suggestion in seo_response.split('\n') if suggestion.strip() and not suggestion.strip().startswith('#')],
            "priority": "high" if lighthouse_score.get('seo', 0) < 0.8 else "medium",
            "current_score": lighthouse_score.get('seo', 0),
            "issues": seo_issues
        }
        
        # Accessibility suggestions
        accessibility_prompt = f"""
        Analyze the accessibility issues for {url} and provide specific actionable recommendations:
        
        Current Accessibility Score: {lighthouse_score.get('accessibility', 0):.2f}
        
        Identified Issues:
        {chr(10).join(accessibility_issues) if accessibility_issues else "No specific issues identified"}
        
        Provide 3-5 specific, actionable accessibility recommendations to improve user experience for all users.
        """
        
        accessibility_response = await chat.send_message(UserMessage(text=accessibility_prompt))
        suggestions["accessibility"] = {
            "suggestions": [suggestion.strip() for suggestion in accessibility_response.split('\n') if suggestion.strip() and not suggestion.strip().startswith('#')],
            "priority": "medium" if lighthouse_score.get('accessibility', 0) < 0.8 else "low",
            "current_score": lighthouse_score.get('accessibility', 0),
            "issues": accessibility_issues
        }
        
        # Best Practices suggestions
        best_practices_prompt = f"""
        Analyze the best practices issues for {url} and provide specific actionable recommendations:
        
        Current Best Practices Score: {lighthouse_score.get('best_practices', 0):.2f}
        
        Identified Issues:
        {chr(10).join(best_practices_issues) if best_practices_issues else "No specific issues identified"}
        
        Provide 3-5 specific, actionable recommendations to improve web development best practices.
        """
        
        best_practices_response = await chat.send_message(UserMessage(text=best_practices_prompt))
        suggestions["best_practices"] = {
            "suggestions": [suggestion.strip() for suggestion in best_practices_response.split('\n') if suggestion.strip() and not suggestion.strip().startswith('#')],
            "priority": "medium" if lighthouse_score.get('best_practices', 0) < 0.8 else "low",
            "current_score": lighthouse_score.get('best_practices', 0),
            "issues": best_practices_issues
        }
        
        return suggestions
        
    except Exception as e:
        print(f"Structured AI suggestions generation failed: {str(e)}")
        return {
            "performance": {"suggestions": [f"AI suggestions unavailable: {str(e)}"], "priority": "high"},
            "seo": {"suggestions": [f"AI suggestions unavailable: {str(e)}"], "priority": "high"},
            "accessibility": {"suggestions": [f"AI suggestions unavailable: {str(e)}"], "priority": "medium"},
            "best_practices": {"suggestions": [f"AI suggestions unavailable: {str(e)}"], "priority": "medium"}
        }

async def generate_ai_suggestions(url: str, lighthouse_score: Dict[str, Any], keywords: List[str], backlinks: List[str]) -> str:
    """Generate AI-powered SEO suggestions using Gemini"""
    try:
        if not GEMINI_API_KEY:
            return "AI suggestions unavailable: Gemini API key not configured"
        
        # Create Gemini chat instance
        chat = LlmChat(
            api_key=GEMINI_API_KEY,
            session_id=f"seo_analysis_{uuid.uuid4()}",
            system_message="You are an expert SEO consultant. Analyze the provided website data and provide actionable SEO recommendations to improve search engine rankings and user experience."
        ).with_model("gemini", "gemini-2.0-flash")
        
        # Prepare analysis data
        analysis_data = {
            "url": url,
            "lighthouse_scores": {
                "Performance": lighthouse_score.get('performance', 0),
                "Accessibility": lighthouse_score.get('accessibility', 0),
                "Best Practices": lighthouse_score.get('best_practices', 0),
                "SEO": lighthouse_score.get('seo', 0)
            },
            "top_keywords": keywords[:10],
            "external_links": backlinks[:5],
            "performance_metrics": {
                "first_contentful_paint": lighthouse_score.get('audits', {}).get('first-contentful-paint', {}).get('numericValue', 0),
                "speed_index": lighthouse_score.get('audits', {}).get('speed-index', {}).get('numericValue', 0),
                "largest_contentful_paint": lighthouse_score.get('audits', {}).get('largest-contentful-paint', {}).get('numericValue', 0)
            }
        }
        
        prompt = f"""
        Analyze the following website SEO data and provide specific, actionable recommendations:

        Website: {url}

        Lighthouse Scores:
        - Performance: {analysis_data['lighthouse_scores']['Performance']:.2f}
        - Accessibility: {analysis_data['lighthouse_scores']['Accessibility']:.2f}
        - Best Practices: {analysis_data['lighthouse_scores']['Best Practices']:.2f}
        - SEO: {analysis_data['lighthouse_scores']['SEO']:.2f}

        Top Keywords Found: {', '.join(keywords[:10])}

        Performance Metrics:
        - First Contentful Paint: {analysis_data['performance_metrics']['first_contentful_paint']}ms
        - Speed Index: {analysis_data['performance_metrics']['speed_index']}ms
        - Largest Contentful Paint: {analysis_data['performance_metrics']['largest_contentful_paint']}ms

        External Links: {len(backlinks)} found

        Please provide:
        1. Priority areas for improvement
        2. Specific technical recommendations
        3. Content optimization suggestions
        4. Performance improvement strategies
        5. SEO best practices to implement

        Focus on actionable recommendations that can be implemented immediately.
        """
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response
        
    except Exception as e:
        print(f"AI suggestions generation failed: {str(e)}")
        return f"AI suggestions unavailable: {str(e)}"

def calculate_performance_metrics(lighthouse_score: Dict[str, Any], keywords_count: int, backlinks_count: int) -> Dict[str, Any]:
    """Calculate overall performance metrics"""
    
    # Calculate overall score
    scores = [
        lighthouse_score.get('performance', 0),
        lighthouse_score.get('accessibility', 0),
        lighthouse_score.get('best_practices', 0),
        lighthouse_score.get('seo', 0)
    ]
    
    overall_score = sum(scores) / len(scores) if scores else 0
    
    # Performance grade
    if overall_score >= 0.9:
        grade = "A"
    elif overall_score >= 0.75:
        grade = "B"
    elif overall_score >= 0.6:
        grade = "C"
    elif overall_score >= 0.4:
        grade = "D"
    else:
        grade = "F"
    
    return {
        "overall_score": round(overall_score, 2),
        "grade": grade,
        "keywords_found": keywords_count,
        "backlinks_found": backlinks_count,
        "performance_score": lighthouse_score.get('performance', 0),
        "accessibility_score": lighthouse_score.get('accessibility', 0),
        "best_practices_score": lighthouse_score.get('best_practices', 0),
        "seo_score": lighthouse_score.get('seo', 0)
    }

@app.post("/api/competitor-analysis", response_model=CompetitorAnalysisResponse)
async def analyze_competitors(request: CompetitorAnalysisRequest):
    """
    Analyze competitors and provide comparative insights
    """
    try:
        primary_url = str(request.primary_url)
        competitor_urls = [str(url) for url in request.competitor_urls]
        analysis_id = str(uuid.uuid4())
        
        # Analyze primary site
        primary_analysis = await analyze_single_site_for_comparison(primary_url)
        
        # Analyze competitors
        competitor_data = []
        for competitor_url in competitor_urls:
            competitor_analysis = await analyze_single_site_for_comparison(competitor_url)
            competitor_data.append(competitor_analysis)
        
        # Generate competitive insights
        comparison_insights = await generate_competitive_insights(primary_analysis, competitor_data)
        
        # Extract competitive keywords
        competitive_keywords = extract_competitive_keywords(primary_analysis, competitor_data)
        
        # Identify content gaps
        content_gaps = identify_content_gaps(primary_analysis, competitor_data)
        
        # Store results
        result = {
            "_id": analysis_id,
            "primary_url": primary_url,
            "competitor_data": competitor_data,
            "comparison_insights": comparison_insights,
            "competitive_keywords": competitive_keywords,
            "content_gaps": content_gaps,
            "created_at": datetime.utcnow()
        }
        
        await db.competitor_analyses.insert_one(result)
        
        return CompetitorAnalysisResponse(
            id=analysis_id,
            primary_url=primary_url,
            competitor_data=competitor_data,
            comparison_insights=comparison_insights,
            competitive_keywords=competitive_keywords,
            content_gaps=content_gaps,
            created_at=result["created_at"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Competitor analysis failed: {str(e)}")

@app.post("/api/seo-content-template", response_model=SEOContentTemplateResponse)
async def generate_seo_content_template(request: SEOContentTemplateRequest):
    """
    Generate SEO content template similar to SEMrush
    """
    try:
        url = str(request.url)
        target_keywords = request.target_keywords
        content_type = request.content_type
        template_id = str(uuid.uuid4())
        
        # Analyze the current page
        current_analysis = await analyze_single_site_for_comparison(url)
        
        # Generate content template
        content_template = await generate_content_template(url, target_keywords, content_type, current_analysis)
        
        # Generate keyword strategy
        keyword_strategy = await generate_keyword_strategy(target_keywords, current_analysis)
        
        # Generate content outline
        content_outline = await generate_content_outline(url, target_keywords, content_type)
        
        # Store results
        result = {
            "_id": template_id,
            "url": url,
            "content_template": content_template,
            "keyword_strategy": keyword_strategy,
            "content_outline": content_outline,
            "created_at": datetime.utcnow()
        }
        
        await db.content_templates.insert_one(result)
        
        return SEOContentTemplateResponse(
            id=template_id,
            url=url,
            content_template=content_template,
            keyword_strategy=keyword_strategy,
            content_outline=content_outline,
            created_at=result["created_at"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content template generation failed: {str(e)}")

async def analyze_single_site_for_comparison(url: str) -> Dict[str, Any]:
    """Analyze a single site for competitive comparison"""
    try:
        # Run basic analysis
        keywords = await analyze_keywords(url)
        backlinks = await analyze_backlinks(url)
        
        # Get basic page info
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('title')
        title_text = title.get_text() if title else ""
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_desc_text = meta_desc.get('content', '') if meta_desc else ""
        
        # Get headings
        headings = {
            'h1': [h.get_text().strip() for h in soup.find_all('h1')],
            'h2': [h.get_text().strip() for h in soup.find_all('h2')],
            'h3': [h.get_text().strip() for h in soup.find_all('h3')]
        }
        
        return {
            "url": url,
            "title": title_text,
            "meta_description": meta_desc_text,
            "keywords": keywords,
            "backlinks": backlinks,
            "headings": headings,
            "word_count": len(soup.get_text().split()),
            "internal_links": len([link for link in soup.find_all('a', href=True) if not link['href'].startswith('http')])
        }
        
    except Exception as e:
        print(f"Site analysis failed for {url}: {str(e)}")
        return {
            "url": url,
            "title": "",
            "meta_description": "",
            "keywords": [],
            "backlinks": [],
            "headings": {"h1": [], "h2": [], "h3": []},
            "word_count": 0,
            "internal_links": 0,
            "error": str(e)
        }

async def generate_competitive_insights(primary_analysis: Dict[str, Any], competitor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate competitive insights using AI"""
    try:
        if not GEMINI_API_KEY:
            return {"insights": ["AI insights unavailable: Gemini API key not configured"]}
        
        chat = LlmChat(
            api_key=GEMINI_API_KEY,
            session_id=f"competitive_analysis_{uuid.uuid4()}",
            system_message="You are a competitive analysis expert. Provide actionable insights based on comparative data."
        ).with_model("gemini", "gemini-2.0-flash")
        
        # Prepare comparison data
        comparison_data = f"""
        Primary Site: {primary_analysis['url']}
        - Title: {primary_analysis['title']}
        - Meta Description: {primary_analysis['meta_description']}
        - Keywords: {len(primary_analysis['keywords'])} found
        - Backlinks: {len(primary_analysis['backlinks'])} found
        - Word Count: {primary_analysis['word_count']}
        - H1 tags: {len(primary_analysis['headings']['h1'])}
        
        Competitors:
        """
        
        for i, competitor in enumerate(competitor_data, 1):
            comparison_data += f"""
        Competitor {i}: {competitor['url']}
        - Title: {competitor['title']}
        - Meta Description: {competitor['meta_description']}
        - Keywords: {len(competitor['keywords'])} found
        - Backlinks: {len(competitor['backlinks'])} found
        - Word Count: {competitor['word_count']}
        - H1 tags: {len(competitor['headings']['h1'])}
        """
        
        prompt = f"""
        Analyze the following competitive data and provide actionable insights:

        {comparison_data}

        Provide specific recommendations for:
        1. Content gaps and opportunities
        2. Keyword strategy improvements
        3. Technical SEO advantages competitors have
        4. Content length and structure recommendations
        5. Link building opportunities

        Focus on actionable insights that can be implemented immediately.
        """
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        return {
            "insights": [insight.strip() for insight in response.split('\n') if insight.strip() and not insight.strip().startswith('#')],
            "competitor_count": len(competitor_data),
            "analysis_date": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Competitive insights generation failed: {str(e)}")
        return {"insights": [f"AI insights unavailable: {str(e)}"]}

def extract_competitive_keywords(primary_analysis: Dict[str, Any], competitor_data: List[Dict[str, Any]]) -> List[str]:
    """Extract competitive keywords that competitors are using but primary site is not"""
    try:
        primary_keywords = set(primary_analysis['keywords'])
        competitor_keywords = set()
        
        for competitor in competitor_data:
            competitor_keywords.update(competitor['keywords'])
        
        # Find keywords competitors have but primary site doesn't
        competitive_keywords = list(competitor_keywords - primary_keywords)
        
        return competitive_keywords[:20]  # Return top 20
        
    except Exception as e:
        print(f"Competitive keywords extraction failed: {str(e)}")
        return []

def identify_content_gaps(primary_analysis: Dict[str, Any], competitor_data: List[Dict[str, Any]]) -> List[str]:
    """Identify content gaps based on competitor analysis"""
    try:
        gaps = []
        
        # Check word count
        primary_word_count = primary_analysis['word_count']
        avg_competitor_word_count = sum(c['word_count'] for c in competitor_data) / len(competitor_data)
        
        if primary_word_count < avg_competitor_word_count:
            gaps.append(f"Content length gap: Your page has {primary_word_count} words vs competitor average of {avg_competitor_word_count:.0f} words")
        
        # Check heading structure
        primary_h1_count = len(primary_analysis['headings']['h1'])
        primary_h2_count = len(primary_analysis['headings']['h2'])
        
        if primary_h1_count == 0:
            gaps.append("Missing H1 tag - critical for SEO")
        if primary_h2_count < 3:
            gaps.append("Few H2 tags - consider adding more section headings")
        
        # Check meta description
        if not primary_analysis['meta_description']:
            gaps.append("Missing meta description")
        
        return gaps
        
    except Exception as e:
        print(f"Content gaps identification failed: {str(e)}")
        return []

async def generate_content_template(url: str, target_keywords: List[str], content_type: str, current_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate content template similar to SEMrush"""
    try:
        if not GEMINI_API_KEY:
            return {"template": "AI template unavailable: Gemini API key not configured"}
        
        chat = LlmChat(
            api_key=GEMINI_API_KEY,
            session_id=f"content_template_{uuid.uuid4()}",
            system_message="You are an expert content strategist. Create detailed content templates for SEO optimization."
        ).with_model("gemini", "gemini-2.0-flash")
        
        prompt = f"""
        Create a comprehensive content template for {content_type} optimization:

        Target URL: {url}
        Target Keywords: {', '.join(target_keywords)}
        Content Type: {content_type}
        
        Current Analysis:
        - Title: {current_analysis['title']}
        - Meta Description: {current_analysis['meta_description']}
        - Current Word Count: {current_analysis['word_count']}
        
        Provide a detailed template including:
        1. Recommended title structure with target keywords
        2. Meta description template
        3. Content structure with H1, H2, H3 recommendations
        4. Keyword density and placement guidelines
        5. Content length recommendations
        6. Internal linking strategy
        7. Call-to-action placement
        8. Technical SEO elements to include
        
        Format as a detailed guide that can be followed step by step.
        """
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        return {
            "template": response,
            "target_keywords": target_keywords,
            "content_type": content_type,
            "recommended_length": "1500-2500 words" if content_type == "article" else "800-1200 words",
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Content template generation failed: {str(e)}")
        return {"template": f"Template generation failed: {str(e)}"}

async def generate_keyword_strategy(target_keywords: List[str], current_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate keyword strategy recommendations"""
    try:
        if not GEMINI_API_KEY:
            return {"strategy": "AI strategy unavailable: Gemini API key not configured"}
        
        chat = LlmChat(
            api_key=GEMINI_API_KEY,
            session_id=f"keyword_strategy_{uuid.uuid4()}",
            system_message="You are an SEO keyword strategy expert. Provide detailed keyword optimization strategies."
        ).with_model("gemini", "gemini-2.0-flash")
        
        prompt = f"""
        Create a comprehensive keyword strategy:

        Target Keywords: {', '.join(target_keywords)}
        Current Page Keywords: {', '.join(current_analysis['keywords'][:10])}
        
        Provide:
        1. Primary keyword selection and placement
        2. Secondary keyword opportunities
        3. Long-tail keyword suggestions
        4. Keyword density recommendations
        5. LSI (Latent Semantic Indexing) keywords
        6. Keyword mapping for different content sections
        7. Seasonal keyword opportunities
        8. Local SEO keywords (if applicable)
        
        Focus on actionable, specific recommendations.
        """
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        return {
            "strategy": response,
            "primary_keywords": target_keywords[:3],
            "secondary_keywords": target_keywords[3:],
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Keyword strategy generation failed: {str(e)}")
        return {"strategy": f"Strategy generation failed: {str(e)}"}

async def generate_content_outline(url: str, target_keywords: List[str], content_type: str) -> Dict[str, Any]:
    """Generate detailed content outline"""
    try:
        if not GEMINI_API_KEY:
            return {"outline": "AI outline unavailable: Gemini API key not configured"}
        
        chat = LlmChat(
            api_key=GEMINI_API_KEY,
            session_id=f"content_outline_{uuid.uuid4()}",
            system_message="You are a content strategist specialized in creating SEO-optimized content outlines."
        ).with_model("gemini", "gemini-2.0-flash")
        
        prompt = f"""
        Create a detailed content outline for {content_type}:

        Target URL: {url}
        Target Keywords: {', '.join(target_keywords)}
        Content Type: {content_type}
        
        Create a comprehensive outline with:
        1. Introduction section (with primary keyword)
        2. Main content sections (5-7 sections)
        3. Subheadings for each section
        4. Key points to cover in each section
        5. Keyword placement recommendations
        6. Internal linking opportunities
        7. Conclusion section
        8. Call-to-action recommendations
        
        Format as a structured outline that can be followed by content writers.
        """
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        return {
            "outline": response,
            "target_keywords": target_keywords,
            "content_type": content_type,
            "estimated_sections": 7,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Content outline generation failed: {str(e)}")
        return {"outline": f"Outline generation failed: {str(e)}"}

@app.get("/api/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get analysis results by ID"""
    try:
        result = await db.analyses.find_one({"_id": analysis_id})
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analyses")
async def get_all_analyses():
    """Get all analysis results"""
    try:
        analyses = []
        async for analysis in db.analyses.find().sort("created_at", -1).limit(50):
            analyses.append(analysis)
        return analyses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)