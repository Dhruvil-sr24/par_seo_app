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
                    return success, response.json()
                except:
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
    
    def check_ai_suggestions(self, analysis_result):
        """Check if AI suggestions are working properly"""
        print("\n🔍 Checking AI suggestions...")
        
        ai_suggestions = analysis_result.get("ai_suggestions", "")
        
        if not ai_suggestions:
            print("❌ Failed - No AI suggestions found")
            self.test_results["AI Suggestions"] = {
                "status": "FAILED",
                "error": "No AI suggestions found"
            }
            return False
            
        if "Gemini API key not configured" in ai_suggestions:
            print("❌ Failed - Gemini API key issue: " + ai_suggestions)
            self.test_results["AI Suggestions"] = {
                "status": "FAILED",
                "error": "Gemini API key not configured"
            }
            return False
            
        # Check if it looks like actual AI-generated content
        if len(ai_suggestions) > 100:
            print("✅ Passed - AI suggestions generated successfully")
            print(f"AI Suggestions preview: {ai_suggestions[:100]}...")
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
        
        # Check if screenshots have actual image data
        valid_screenshots = 0
        for screenshot in screenshots:
            if screenshot.get("screenshot", "").startswith("data:image"):
                valid_screenshots += 1
                
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
                "status": "PASSED"
            }
            return True
        else:
            print("❌ Failed - Too many missing screenshots")
            self.test_results["Screenshots"] = {
                "status": "FAILED",
                "error": f"Only {valid_screenshots}/{len(screenshots)} screenshots were valid"
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
            if result["status"] == "FAILED" and "error" in result:
                print(f"  Error: {result['error']}")
        print("="*50)

def main():
    # Use the backend URL from frontend's .env file
    backend_url = "https://555bd5fc-b652-4fea-9ad7-f48d697cb8d3.preview.emergentagent.com"
    print(f"Testing backend API at: {backend_url}")
    
    # Initialize tester
    tester = SEOToolAPITester(backend_url)
    
    # Test root endpoint
    tester.test_root_endpoint()
    
    # Test getting all analyses
    success, analyses = tester.test_get_analyses()
    
    # Test analyze endpoint with example.com
    success, analysis_result = tester.test_analyze_website()
    
    # Check if analysis was successful
    if success and analysis_result:
        # Check if AI suggestions are working
        tester.tests_run += 1
        tester.check_ai_suggestions(analysis_result)
        
        # Check if screenshots are being generated
        tester.tests_run += 1
        tester.check_screenshots(analysis_result)
        
        # Test getting analysis by ID
        if "id" in analysis_result:
            analysis_id = analysis_result["id"]
            tester.test_get_analysis_by_id(analysis_id)
    
    # Print summary
    tester.print_summary()
    
    # Save detailed results to a file for reference
    with open('api_test_results.json', 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "tests_run": tester.tests_run,
            "tests_passed": tester.tests_passed,
            "results": tester.test_results,
            "analysis_sample": analysis_result if success else None
        }, f, indent=2, default=str)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    main()