import requests
import unittest
import time
import os
import json
from datetime import datetime

class SEOToolAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = {}

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                self.test_results[name] = {
                    "status": "PASSED",
                    "response_code": response.status_code
                }
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results[name] = {
                    "status": "FAILED",
                    "response_code": response.status_code,
                    "error": f"Expected {expected_status}, got {response.status_code}"
                }
                try:
                    error_response = response.json()
                    print(f"Error response: {error_response}")
                    return success, error_response
                except:
                    print(f"Raw response: {response.text[:500]}")
                    return success, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results[name] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False, {}

    def test_root_endpoint(self):
        """Test the root endpoint"""
        return self.run_test(
            "Root Endpoint",
            "GET",
            "",
            200
        )

    def test_analyze_website(self, url="https://example.com"):
        """Test the analyze endpoint with a simple website"""
        print(f"Testing website analysis for: {url}")
        return self.run_test(
            "Analyze Website",
            "POST",
            "api/analyze",
            200,
            data={"url": url},
            timeout=120  # Longer timeout for analysis
        )
    
    def test_get_analyses(self):
        """Test getting all analyses"""
        return self.run_test(
            "Get All Analyses",
            "GET",
            "api/analyses",
            200
        )
    
    def test_get_analysis_by_id(self, analysis_id):
        """Test getting a specific analysis by ID"""
        return self.run_test(
            "Get Analysis by ID",
            "GET",
            f"api/analysis/{analysis_id}",
            200
        )
    
    def test_competitor_analysis(self, primary_url="https://example.com", competitor_urls=["https://example.org", "https://example.net"]):
        """Test the competitor analysis endpoint"""
        print(f"Testing competitor analysis for: {primary_url} vs {', '.join(competitor_urls)}")
        return self.run_test(
            "Competitor Analysis",
            "POST",
            "api/competitor-analysis",
            200,
            data={
                "primary_url": primary_url,
                "competitor_urls": competitor_urls
            },
            timeout=180  # Longer timeout for competitor analysis
        )
    
    def test_seo_content_template(self, url="https://example.com", target_keywords=["seo", "content", "marketing"], content_type="article"):
        """Test the SEO content template endpoint"""
        print(f"Testing SEO content template for: {url} with keywords: {', '.join(target_keywords)}")
        return self.run_test(
            "SEO Content Template",
            "POST",
            "api/seo-content-template",
            200,
            data={
                "url": url,
                "target_keywords": target_keywords,
                "content_type": content_type
            },
            timeout=120  # Longer timeout for content template generation
        )
    
    def check_structured_ai_suggestions(self, analysis_result):
        """Check if structured AI suggestions are working properly"""
        print("\n🔍 Checking structured AI suggestions...")
        
        ai_suggestions = analysis_result.get("ai_suggestions", {})
        
        if not ai_suggestions:
            print("❌ Failed - No AI suggestions found")
            self.test_results["Structured AI Suggestions"] = {
                "status": "FAILED",
                "error": "No AI suggestions found"
            }
            return False
        
        # Check if it's a dictionary (structured format)
        if not isinstance(ai_suggestions, dict):
            print("❌ Failed - AI suggestions are not in structured format (not a dictionary)")
            self.test_results["Structured AI Suggestions"] = {
                "status": "FAILED",
                "error": "AI suggestions are not in structured format"
            }
            return False
        
        # Check for required metrics
        required_metrics = ["performance", "seo", "accessibility", "best_practices"]
        missing_metrics = [metric for metric in required_metrics if metric not in ai_suggestions]
        
        if missing_metrics:
            print(f"❌ Failed - Missing metrics in AI suggestions: {', '.join(missing_metrics)}")
            self.test_results["Structured AI Suggestions"] = {
                "status": "FAILED",
                "error": f"Missing metrics: {', '.join(missing_metrics)}"
            }
            return False
        
        # Check structure of each metric
        valid_metrics = 0
        for metric in required_metrics:
            metric_data = ai_suggestions.get(metric, {})
            if not isinstance(metric_data, dict):
                print(f"❌ Metric '{metric}' is not properly structured")
                continue
                
            # Check for required fields in each metric
            if "suggestions" in metric_data and "priority" in metric_data and "issues" in metric_data:
                valid_metrics += 1
                print(f"✅ Metric '{metric}' is properly structured")
                # Print a sample suggestion
                if metric_data.get("suggestions"):
                    print(f"  Sample suggestion: {metric_data['suggestions'][0][:100]}...")
                print(f"  Priority: {metric_data.get('priority', 'unknown')}")
                print(f"  Issues count: {len(metric_data.get('issues', []))}")
            else:
                print(f"❌ Metric '{metric}' is missing required fields")
        
        if valid_metrics == len(required_metrics):
            print("✅ Passed - All metrics are properly structured")
            self.tests_passed += 1
            self.test_results["Structured AI Suggestions"] = {
                "status": "PASSED",
                "details": f"All {len(required_metrics)} metrics are properly structured"
            }
            return True
        else:
            print(f"❌ Failed - Only {valid_metrics}/{len(required_metrics)} metrics are properly structured")
            self.test_results["Structured AI Suggestions"] = {
                "status": "FAILED",
                "error": f"Only {valid_metrics}/{len(required_metrics)} metrics are properly structured"
            }
            return False
    
    def check_competitor_analysis(self, result):
        """Check if competitor analysis results are valid"""
        print("\n🔍 Checking competitor analysis results...")
        
        if not result:
            print("❌ Failed - No competitor analysis results found")
            self.test_results["Competitor Analysis Results"] = {
                "status": "FAILED",
                "error": "No competitor analysis results found"
            }
            return False
        
        # Check for required fields
        required_fields = ["primary_url", "competitor_data", "comparison_insights", "competitive_keywords", "content_gaps"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            print(f"❌ Failed - Missing fields in competitor analysis: {', '.join(missing_fields)}")
            self.test_results["Competitor Analysis Results"] = {
                "status": "FAILED",
                "error": f"Missing fields: {', '.join(missing_fields)}"
            }
            return False
        
        # Check competitor data
        competitor_data = result.get("competitor_data", [])
        if not competitor_data:
            print("❌ Failed - No competitor data found")
            self.test_results["Competitor Analysis Results"] = {
                "status": "FAILED",
                "error": "No competitor data found"
            }
            return False
        
        print(f"✅ Found data for {len(competitor_data)} competitors")
        
        # Check comparison insights
        comparison_insights = result.get("comparison_insights", {})
        if not comparison_insights or not comparison_insights.get("insights"):
            print("❌ Failed - No comparison insights found")
            self.test_results["Competitor Analysis Results"] = {
                "status": "FAILED",
                "error": "No comparison insights found"
            }
            return False
        
        print(f"✅ Found {len(comparison_insights.get('insights', []))} comparison insights")
        if comparison_insights.get("insights"):
            print(f"  Sample insight: {comparison_insights['insights'][0][:100]}...")
        
        # Check competitive keywords
        competitive_keywords = result.get("competitive_keywords", [])
        if not competitive_keywords:
            print("⚠️ Warning - No competitive keywords found")
        else:
            print(f"✅ Found {len(competitive_keywords)} competitive keywords")
            if competitive_keywords:
                print(f"  Sample keywords: {', '.join(competitive_keywords[:5])}")
        
        # Check content gaps
        content_gaps = result.get("content_gaps", [])
        if not content_gaps:
            print("⚠️ Warning - No content gaps found")
        else:
            print(f"✅ Found {len(content_gaps)} content gaps")
            if content_gaps:
                print(f"  Sample content gap: {content_gaps[0][:100]}...")
        
        # Overall check
        if comparison_insights.get("insights") and competitor_data:
            print("✅ Passed - Competitor analysis generated successfully")
            self.tests_passed += 1
            self.test_results["Competitor Analysis Results"] = {
                "status": "PASSED",
                "details": f"Analysis includes {len(competitor_data)} competitors and {len(comparison_insights.get('insights', []))} insights"
            }
            return True
        else:
            print("❌ Failed - Competitor analysis incomplete")
            self.test_results["Competitor Analysis Results"] = {
                "status": "FAILED",
                "error": "Competitor analysis incomplete or missing key components"
            }
            return False
    
    def check_seo_content_template(self, result):
        """Check if SEO content template results are valid"""
        print("\n🔍 Checking SEO content template results...")
        
        if not result:
            print("❌ Failed - No SEO content template results found")
            self.test_results["SEO Content Template Results"] = {
                "status": "FAILED",
                "error": "No SEO content template results found"
            }
            return False
        
        # Check for required fields
        required_fields = ["url", "content_template", "keyword_strategy", "content_outline"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            print(f"❌ Failed - Missing fields in SEO content template: {', '.join(missing_fields)}")
            self.test_results["SEO Content Template Results"] = {
                "status": "FAILED",
                "error": f"Missing fields: {', '.join(missing_fields)}"
            }
            return False
        
        # Check content template
        content_template = result.get("content_template", {})
        if not content_template or not content_template.get("template"):
            print("❌ Failed - No content template found")
            self.test_results["SEO Content Template Results"] = {
                "status": "FAILED",
                "error": "No content template found"
            }
            return False
        
        print("✅ Content template generated")
        print(f"  Template preview: {content_template.get('template', '')[:100]}...")
        
        # Check keyword strategy
        keyword_strategy = result.get("keyword_strategy", {})
        if not keyword_strategy or not keyword_strategy.get("strategy"):
            print("❌ Failed - No keyword strategy found")
            self.test_results["SEO Content Template Results"] = {
                "status": "FAILED",
                "error": "No keyword strategy found"
            }
            return False
        
        print("✅ Keyword strategy generated")
        print(f"  Strategy preview: {keyword_strategy.get('strategy', '')[:100]}...")
        
        # Check content outline
        content_outline = result.get("content_outline", {})
        if not content_outline or not content_outline.get("outline"):
            print("❌ Failed - No content outline found")
            self.test_results["SEO Content Template Results"] = {
                "status": "FAILED",
                "error": "No content outline found"
            }
            return False
        
        print("✅ Content outline generated")
        print(f"  Outline preview: {content_outline.get('outline', '')[:100]}...")
        
        # Overall check
        if (content_template.get("template") and 
            keyword_strategy.get("strategy") and 
            content_outline.get("outline")):
            print("✅ Passed - SEO content template generated successfully")
            self.tests_passed += 1
            self.test_results["SEO Content Template Results"] = {
                "status": "PASSED",
                "details": "Template, keyword strategy, and content outline all generated"
            }
            return True
        else:
            print("❌ Failed - SEO content template incomplete")
            self.test_results["SEO Content Template Results"] = {
                "status": "FAILED",
                "error": "SEO content template incomplete or missing key components"
            }
            return False
    
    def check_ai_suggestions(self, analysis_result):
        """Check if AI suggestions are working properly (legacy method)"""
        print("\n🔍 Checking AI suggestions...")
        
        ai_suggestions = analysis_result.get("ai_suggestions", "")
        
        if not ai_suggestions:
            print("❌ Failed - No AI suggestions found")
            self.test_results["AI Suggestions"] = {
                "status": "FAILED",
                "error": "No AI suggestions found"
            }
            return False
            
        if isinstance(ai_suggestions, dict):
            print("✅ AI suggestions are in structured format - using structured checker instead")
            return self.check_structured_ai_suggestions(analysis_result)
            
        if "Gemini API key not configured" in str(ai_suggestions):
            print("❌ Failed - Gemini API key issue: " + str(ai_suggestions))
            self.test_results["AI Suggestions"] = {
                "status": "FAILED",
                "error": "Gemini API key not configured"
            }
            return False
            
        if "AI suggestions unavailable" in str(ai_suggestions):
            print("❌ Failed - AI suggestions unavailable: " + str(ai_suggestions))
            self.test_results["AI Suggestions"] = {
                "status": "FAILED",
                "error": ai_suggestions
            }
            return False
            
        # Check if it looks like actual AI-generated content
        if len(str(ai_suggestions)) > 100:
            print("✅ Passed - AI suggestions generated successfully")
            print(f"AI Suggestions preview: {str(ai_suggestions)[:100]}...")
            self.tests_passed += 1
            self.test_results["AI Suggestions"] = {
                "status": "PASSED"
            }
            return True
        else:
            print("❌ Failed - AI suggestions too short or incomplete")
            self.test_results["AI Suggestions"] = {
                "status": "FAILED",
                "error": "AI suggestions too short or incomplete"
            }
            return False
    
    def check_screenshots(self, analysis_result):
        """Check if screenshots are being generated properly"""
        print("\n🔍 Checking responsive screenshots...")
        
        screenshots = analysis_result.get("screenshots", [])
        
        if not screenshots:
            print("❌ Failed - No screenshots found")
            self.test_results["Screenshots"] = {
                "status": "FAILED",
                "error": "No screenshots found"
            }
            return False
            
        # Check if we have screenshots for different devices
        devices = [s.get("device") for s in screenshots]
        print(f"Found screenshots for devices: {', '.join(devices)}")
        
        # Check for expected devices
        expected_devices = ["Mobile", "Tablet", "Laptop", "Desktop"]
        missing_devices = [device for device in expected_devices if device not in devices]
        if missing_devices:
            print(f"⚠️ Warning - Missing screenshots for devices: {', '.join(missing_devices)}")
        
        # Check if screenshots have actual image data
        valid_screenshots = 0
        for screenshot in screenshots:
            if screenshot.get("screenshot", "").startswith("data:image"):
                valid_screenshots += 1
            elif "error" in screenshot:
                print(f"⚠️ Screenshot error for {screenshot.get('device')}: {screenshot.get('error')}")
                
        if valid_screenshots == 0:
            print("❌ Failed - No valid screenshot data found")
            self.test_results["Screenshots"] = {
                "status": "FAILED",
                "error": "No valid screenshot data found"
            }
            return False
        
        success_rate = valid_screenshots / len(screenshots) if screenshots else 0
        print(f"Screenshot success rate: {valid_screenshots}/{len(screenshots)} ({success_rate*100:.1f}%)")
        
        if success_rate >= 0.5:  # At least half of the screenshots should be valid
            print("✅ Passed - Screenshots generated successfully")
            self.tests_passed += 1
            self.test_results["Screenshots"] = {
                "status": "PASSED",
                "details": f"Generated {valid_screenshots}/{len(screenshots)} screenshots"
            }
            return True
        else:
            print("❌ Failed - Too many missing screenshots")
            self.test_results["Screenshots"] = {
                "status": "FAILED",
                "error": f"Only {valid_screenshots}/{len(screenshots)} screenshots were valid"
            }
            return False
    
    def check_keywords_and_backlinks(self, analysis_result):
        """Check if keywords and backlinks analysis is working properly"""
        print("\n🔍 Checking keywords and backlinks analysis...")
        
        keywords = analysis_result.get("keywords", [])
        backlinks = analysis_result.get("backlinks", [])
        
        if not keywords:
            print("❌ Failed - No keywords found")
            self.test_results["Keywords Analysis"] = {
                "status": "FAILED",
                "error": "No keywords found"
            }
            keywords_success = False
        else:
            print(f"✅ Found {len(keywords)} keywords")
            if keywords:
                print(f"  Sample keywords: {', '.join(keywords[:5])}")
            self.tests_passed += 1
            self.test_results["Keywords Analysis"] = {
                "status": "PASSED",
                "details": f"Found {len(keywords)} keywords"
            }
            keywords_success = True
        
        if not backlinks:
            print("❌ Failed - No backlinks found")
            self.test_results["Backlinks Analysis"] = {
                "status": "FAILED",
                "error": "No backlinks found"
            }
            backlinks_success = False
        else:
            print(f"✅ Found {len(backlinks)} backlinks")
            if backlinks:
                print(f"  Sample backlinks: {backlinks[0]}")
            self.tests_passed += 1
            self.test_results["Backlinks Analysis"] = {
                "status": "PASSED",
                "details": f"Found {len(backlinks)} backlinks"
            }
            backlinks_success = True
        
        return keywords_success and backlinks_success
    
    def check_performance(self, start_time, end_time):
        """Check if the analysis completed in a reasonable time"""
        print("\n🔍 Checking performance...")
        
        duration = end_time - start_time
        print(f"Analysis completed in {duration:.2f} seconds")
        
        if duration < 120:  # Less than 2 minutes
            print("✅ Passed - Analysis completed in reasonable time")
            self.tests_passed += 1
            self.test_results["Performance"] = {
                "status": "PASSED",
                "duration": f"{duration:.2f} seconds"
            }
            return True
        else:
            print("❌ Failed - Analysis took too long")
            self.test_results["Performance"] = {
                "status": "FAILED",
                "error": f"Analysis took {duration:.2f} seconds (> 120 seconds)"
            }
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        for name, result in self.test_results.items():
            status = "✅ PASSED" if result["status"] == "PASSED" else "❌ FAILED"
            print(f"{status} - {name}")
            if result["status"] == "PASSED" and "details" in result:
                print(f"  Details: {result['details']}")
            if result["status"] == "FAILED" and "error" in result:
                print(f"  Error: {result['error']}")
        print("="*50)

def main():
    # Use the backend URL from frontend's .env file
    backend_url = "https://7df2e77d-798e-44be-b9ff-0eb61e396390.preview.emergentagent.com"
    print(f"Testing backend API at: {backend_url}")
    
    # Initialize tester
    tester = SEOToolAPITester(backend_url)
    
    # Test root endpoint
    tester.test_root_endpoint()
    
    # Test getting all analyses
    success, analyses = tester.test_get_analyses()
    
    # Test analyze endpoint with example.com
    print("\n===== Testing Main Analysis Endpoint =====")
    start_time = time.time()
    success, analysis_result = tester.test_analyze_website()
    end_time = time.time()
    
    # Check if analysis was successful
    if success and analysis_result:
        # Check if structured AI suggestions are working
        tester.tests_run += 1
        tester.check_structured_ai_suggestions(analysis_result)
        
        # Check if screenshots are being generated
        tester.tests_run += 1
        tester.check_screenshots(analysis_result)
        
        # Check keywords and backlinks analysis
        tester.tests_run += 1
        tester.check_keywords_and_backlinks(analysis_result)
        
        # Check performance
        tester.tests_run += 1
        tester.check_performance(start_time, end_time)
        
        # Test getting analysis by ID
        if "id" in analysis_result:
            analysis_id = analysis_result["id"]
            tester.test_get_analysis_by_id(analysis_id)
    else:
        print("\n❌ Analysis failed - Cannot perform additional checks")
    
    # Test competitor analysis endpoint
    print("\n===== Testing Competitor Analysis Endpoint =====")
    start_time = time.time()
    success, competitor_result = tester.test_competitor_analysis()
    end_time = time.time()
    
    if success and competitor_result:
        # Check competitor analysis results
        tester.tests_run += 1
        tester.check_competitor_analysis(competitor_result)
        
        # Check performance
        tester.tests_run += 1
        tester.check_performance(start_time, end_time)
    else:
        print("\n❌ Competitor analysis failed - Cannot perform additional checks")
    
    # Test SEO content template endpoint
    print("\n===== Testing SEO Content Template Endpoint =====")
    start_time = time.time()
    success, template_result = tester.test_seo_content_template()
    end_time = time.time()
    
    if success and template_result:
        # Check SEO content template results
        tester.tests_run += 1
        tester.check_seo_content_template(template_result)
        
        # Check performance
        tester.tests_run += 1
        tester.check_performance(start_time, end_time)
    else:
        print("\n❌ SEO content template failed - Cannot perform additional checks")
    
    # Print summary
    tester.print_summary()
    
    # Save detailed results to a file for reference
    with open('api_test_results.json', 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "tests_run": tester.tests_run,
            "tests_passed": tester.tests_passed,
            "results": tester.test_results,
            "analysis_sample": analysis_result if success else None,
            "competitor_sample": competitor_result if success else None,
            "template_sample": template_result if success else None
        }, f, indent=2, default=str)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    main()