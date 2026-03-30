import requests
import sys
import json
import time
from datetime import datetime

class ZappizoAPITester:
    def __init__(self, base_url="https://erp-prompt-engine.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_project_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}" if endpoint else f"{self.base_url}/api"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    else:
                        print(f"   Response: Large data object")
                except:
                    print(f"   Response: Non-JSON response")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text[:200]}")

            return success, response.json() if response.content else {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_create_project(self):
        """Test project creation"""
        test_data = {
            "name": f"Test ERP Project {datetime.now().strftime('%H%M%S')}",
            "prompt": "I want an ERP for a small manufacturing company with inventory management, sales tracking, and basic accounting features."
        }
        
        success, response = self.run_test(
            "Create Project",
            "POST",
            "projects",
            200,
            data=test_data
        )
        
        if success and 'id' in response:
            self.created_project_id = response['id']
            print(f"   Created project ID: {self.created_project_id}")
            
            # Verify project structure
            required_fields = ['id', 'name', 'prompt', 'status', 'pipeline', 'created_at', 'updated_at']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Warning: Missing fields in response: {missing_fields}")
            
            # Check pipeline structure
            if 'pipeline' in response:
                expected_stages = ["requirement_analysis", "requirement_gathering", "architecture",
                                 "json_transform", "frontend_generation", "backend_generation", "code_review"]
                pipeline = response['pipeline']
                missing_stages = [stage for stage in expected_stages if stage not in pipeline]
                if missing_stages:
                    print(f"⚠️  Warning: Missing pipeline stages: {missing_stages}")
                else:
                    print(f"✅ Pipeline structure complete with {len(expected_stages)} stages")
        
        return success

    def test_list_projects(self):
        """Test listing projects"""
        success, response = self.run_test(
            "List Projects",
            "GET",
            "projects",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   Found {len(response)} projects")
                if len(response) > 0:
                    # Check if our created project is in the list
                    if self.created_project_id:
                        project_found = any(p.get('id') == self.created_project_id for p in response)
                        if project_found:
                            print(f"✅ Created project found in list")
                        else:
                            print(f"⚠️  Created project not found in list")
            else:
                print(f"⚠️  Expected list, got {type(response)}")
        
        return success

    def test_get_project(self):
        """Test getting specific project"""
        if not self.created_project_id:
            print("⚠️  Skipping get project test - no project ID available")
            return False
            
        success, response = self.run_test(
            "Get Project",
            "GET",
            f"projects/{self.created_project_id}",
            200
        )
        
        if success:
            # Verify project data
            if response.get('id') == self.created_project_id:
                print(f"✅ Project data matches created project")
                print(f"   Status: {response.get('status', 'N/A')}")
                print(f"   Pipeline stages: {len(response.get('pipeline', {}))}")
            else:
                print(f"⚠️  Project ID mismatch")
        
        return success

    def test_get_existing_project(self):
        """Test getting the existing complete project"""
        existing_project_id = "fc4cc226-83b8-4d1e-aa38-3aab0182941e"
        
        success, response = self.run_test(
            "Get Existing Complete Project",
            "GET",
            f"projects/{existing_project_id}",
            200
        )
        
        if success:
            print(f"   Status: {response.get('status', 'N/A')}")
            print(f"   Name: {response.get('name', 'N/A')}")
            pipeline = response.get('pipeline', {})
            completed_stages = [stage for stage, data in pipeline.items() if data.get('status') == 'complete']
            print(f"   Completed stages: {len(completed_stages)}")
        
        return success

    def test_get_messages(self):
        """Test getting project messages"""
        if not self.created_project_id:
            print("⚠️  Skipping get messages test - no project ID available")
            return False
            
        success, response = self.run_test(
            "Get Project Messages",
            "GET",
            f"projects/{self.created_project_id}/messages",
            200
        )
        
        if success:
            if isinstance(response, list):
                print(f"   Found {len(response)} messages")
            else:
                print(f"⚠️  Expected list, got {type(response)}")
        
        return success

    def test_send_chat(self):
        """Test sending chat message"""
        if not self.created_project_id:
            print("⚠️  Skipping chat test - no project ID available")
            return False
            
        chat_data = {
            "message": "I want to add inventory tracking and basic sales management features."
        }
        
        success, response = self.run_test(
            "Send Chat Message",
            "POST",
            f"projects/{self.created_project_id}/chat",
            200,
            data=chat_data
        )
        
        if success:
            # Check response structure
            if 'response' in response:
                print(f"✅ Got AI response")
                print(f"   Status: {response.get('status', 'N/A')}")
                if 'analysis' in response:
                    print(f"✅ Analysis data included")
            else:
                print(f"⚠️  No response field in chat result")
        
        return success

    def test_pipeline_stage(self):
        """Test getting pipeline stage data"""
        existing_project_id = "fc4cc226-83b8-4d1e-aa38-3aab0182941e"
        
        # Test getting architecture stage from complete project
        success, response = self.run_test(
            "Get Pipeline Stage (Architecture)",
            "GET",
            f"projects/{existing_project_id}/pipeline/architecture",
            200
        )
        
        if success:
            if response.get('status') == 'complete':
                print(f"✅ Architecture stage is complete")
                if 'output' in response:
                    output = response['output']
                    if isinstance(output, dict):
                        modules = output.get('modules', [])
                        print(f"   Architecture has {len(modules)} modules")
                    else:
                        print(f"   Architecture output type: {type(output)}")
            else:
                print(f"   Architecture status: {response.get('status', 'N/A')}")
        
        return success

    def test_delete_project(self):
        """Test project deletion"""
        if not self.created_project_id:
            print("⚠️  Skipping delete test - no project ID available")
            return False
            
        success, response = self.run_test(
            "Delete Project",
            "DELETE",
            f"projects/{self.created_project_id}",
            200
        )
        
        if success:
            if response.get('status') == 'deleted':
                print(f"✅ Project deletion confirmed")
            else:
                print(f"⚠️  Unexpected delete response: {response}")
        
        return success

    def test_invalid_endpoints(self):
        """Test error handling for invalid endpoints"""
        print(f"\n🔍 Testing Error Handling...")
        
        # Test non-existent project
        success, response = self.run_test(
            "Get Non-existent Project",
            "GET",
            "projects/non-existent-id",
            404
        )
        
        # Test invalid pipeline stage
        existing_project_id = "fc4cc226-83b8-4d1e-aa38-3aab0182941e"
        success2, response2 = self.run_test(
            "Get Invalid Pipeline Stage",
            "GET",
            f"projects/{existing_project_id}/pipeline/invalid_stage",
            400
        )
        
        return success and success2

def main():
    print("🚀 Starting Zappizo API Testing...")
    print("=" * 60)
    
    tester = ZappizoAPITester()
    
    # Run all tests
    tests = [
        tester.test_root_endpoint,
        tester.test_create_project,
        tester.test_list_projects,
        tester.test_get_project,
        tester.test_get_existing_project,
        tester.test_get_messages,
        tester.test_send_chat,
        tester.test_pipeline_stage,
        tester.test_invalid_endpoints,
        tester.test_delete_project,  # Delete last to clean up
    ]
    
    for test in tests:
        try:
            test()
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Test Summary:")
    print(f"   Tests run: {tester.tests_run}")
    print(f"   Tests passed: {tester.tests_passed}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())