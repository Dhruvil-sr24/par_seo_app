import requests
import unittest
import time
import os
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
    
    # If analysis was successful, test getting it by ID
    if success and "id" in analysis_result:
        analysis_id = analysis_result["id"]
        tester.test_get_analysis_by_id(analysis_id)
    
    # Print summary
    tester.print_summary()
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    main()