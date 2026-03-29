import requests
import sys
import json
from datetime import datetime, timedelta

class ClaimsAPITester:
    def __init__(self, base_url="https://plan-config-engine.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.plan_id = None
        self.member_id = None
        self.claim_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - {name}")
                try:
                    return success, response.json() if response.content else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_register_admin(self):
        """Test admin user registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        email = f"admin_{timestamp}@test.com"
        
        success, response = self.run_test(
            "Admin Registration",
            "POST",
            "auth/register",
            200,
            data={
                "email": email,
                "password": "AdminPass123!",
                "name": "Test Admin",
                "role": "admin"
            }
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   Admin registered: {email}")
            
            # Save credentials for future testing
            with open('/app/memory/test_credentials.md', 'w') as f:
                f.write("# Test Credentials\n")
                f.write("# Agent writes here when creating/modifying auth credentials (admin accounts, test users).\n")
                f.write("# Testing agent reads this before auth tests. Fork/continuation agents read on startup.\n\n")
                f.write(f"## Admin User\n")
                f.write(f"Email: {email}\n")
                f.write(f"Password: AdminPass123!\n")
                f.write(f"Role: admin\n")
                f.write(f"Created: {datetime.now().isoformat()}\n")
            
            return True
        return False

    def test_login(self, email, password):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            return True
        return False

    def test_get_me(self):
        """Test get current user"""
        return self.run_test("Get Current User", "GET", "auth/me", 200)

    def test_dashboard_metrics(self):
        """Test dashboard metrics"""
        return self.run_test("Dashboard Metrics", "GET", "dashboard/metrics", 200)

    def test_create_plan(self):
        """Test creating a benefit plan"""
        plan_data = {
            "name": "Test Medical Plan",
            "plan_type": "medical",
            "group_id": "GRP001",
            "effective_date": "2024-01-01",
            "termination_date": None,
            "deductible_individual": 1000,
            "deductible_family": 2000,
            "oop_max_individual": 5000,
            "oop_max_family": 10000,
            "network_type": "PPO",
            "reimbursement_method": "fee_schedule",
            "benefits": [
                {
                    "service_category": "office_visit",
                    "covered": True,
                    "copay": 25,
                    "coinsurance": 0.2,
                    "deductible_applies": False,
                    "code_range": "99213"
                }
            ],
            "tier_type": "employee_only",
            "exclusions": []
        }
        
        success, response = self.run_test(
            "Create Benefit Plan",
            "POST",
            "plans",
            200,
            data=plan_data
        )
        
        if success and 'id' in response:
            self.plan_id = response['id']
            print(f"   Plan created: {self.plan_id}")
            return True
        return False

    def test_list_plans(self):
        """Test listing plans"""
        return self.run_test("List Plans", "GET", "plans", 200)

    def test_create_member(self):
        """Test creating a member"""
        if not self.plan_id:
            print("❌ Cannot create member - no plan ID available")
            return False
            
        member_data = {
            "member_id": "MBR001",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "gender": "M",
            "group_id": "GRP001",
            "plan_id": self.plan_id,
            "effective_date": "2024-01-01",
            "relationship": "subscriber"
        }
        
        success, response = self.run_test(
            "Create Member",
            "POST",
            "members",
            200,
            data=member_data
        )
        
        if success and 'member_id' in response:
            self.member_id = response['member_id']
            print(f"   Member created: {self.member_id}")
            return True
        return False

    def test_list_members(self):
        """Test listing members"""
        return self.run_test("List Members", "GET", "members", 200)

    def test_create_claim(self):
        """Test creating a claim"""
        if not self.member_id:
            print("❌ Cannot create claim - no member ID available")
            return False
            
        claim_data = {
            "member_id": self.member_id,
            "provider_npi": "1234567890",
            "provider_name": "Test Medical Center",
            "claim_type": "medical",
            "service_date_from": "2024-01-15",
            "service_date_to": "2024-01-15",
            "total_billed": 150.00,
            "diagnosis_codes": ["Z00.00"],
            "service_lines": [
                {
                    "line_number": 1,
                    "cpt_code": "99213",
                    "units": 1,
                    "billed_amount": 150.00,
                    "service_date": "2024-01-15"
                }
            ]
        }
        
        success, response = self.run_test(
            "Create Claim",
            "POST",
            "claims",
            200,
            data=claim_data
        )
        
        if success and 'id' in response:
            self.claim_id = response['id']
            print(f"   Claim created: {response.get('claim_number')}")
            return True
        return False

    def test_create_duplicate_claim(self):
        """Test creating a duplicate claim to verify detection"""
        if not self.member_id:
            print("❌ Cannot create duplicate claim - no member ID available")
            return False
            
        # Create identical claim to trigger duplicate detection
        claim_data = {
            "member_id": self.member_id,
            "provider_npi": "1234567890",
            "provider_name": "Test Medical Center",
            "claim_type": "medical",
            "service_date_from": "2024-01-15",
            "service_date_to": "2024-01-15",
            "total_billed": 150.00,
            "diagnosis_codes": ["Z00.00"],
            "service_lines": [
                {
                    "line_number": 1,
                    "cpt_code": "99213",
                    "units": 1,
                    "billed_amount": 150.00,
                    "service_date": "2024-01-15"
                }
            ]
        }
        
        success, response = self.run_test(
            "Create Duplicate Claim",
            "POST",
            "claims",
            200,
            data=claim_data
        )
        
        if success:
            status = response.get('status')
            duplicate_info = response.get('duplicate_info')
            print(f"   Claim status: {status}")
            if duplicate_info:
                print(f"   Duplicate detected: {duplicate_info.get('duplicate_type')}")
            return True
        return False

    def test_list_claims(self):
        """Test listing claims"""
        return self.run_test("List Claims", "GET", "claims", 200)

    def test_get_claim_detail(self):
        """Test getting claim details"""
        if not self.claim_id:
            print("❌ Cannot get claim detail - no claim ID available")
            return False
            
        return self.run_test("Get Claim Detail", "GET", f"claims/{self.claim_id}", 200)

    def test_list_duplicates(self):
        """Test listing duplicate alerts"""
        return self.run_test("List Duplicate Alerts", "GET", "duplicates", 200)

    def test_claims_by_status(self):
        """Test dashboard claims by status"""
        return self.run_test("Claims by Status", "GET", "dashboard/claims-by-status", 200)

    def test_claims_by_type(self):
        """Test dashboard claims by type"""
        return self.run_test("Claims by Type", "GET", "dashboard/claims-by-type", 200)

    def test_fee_schedule_stats(self):
        """Test fee schedule statistics"""
        success, response = self.run_test("Fee Schedule Stats", "GET", "fee-schedule/stats", 200)
        
        if success:
            total_codes = response.get('total_cpt_codes', 0)
            total_localities = response.get('total_localities', 0)
            conversion_factor = response.get('conversion_factor_2024', 0)
            
            print(f"   CPT Codes: {total_codes}")
            print(f"   GPCI Localities: {total_localities}")
            print(f"   2024 Conversion Factor: ${conversion_factor}")
            
            # Verify expected counts
            if total_codes == 189:
                print("✅ CPT code count matches expected (189)")
            else:
                print(f"⚠️  CPT code count mismatch - expected 189, got {total_codes}")
                
            if total_localities == 87:
                print("✅ GPCI localities count matches expected (87)")
            else:
                print(f"⚠️  GPCI localities count mismatch - expected 87, got {total_localities}")
                
        return success

    def test_search_cpt_99213(self):
        """Test searching for CPT code 99213"""
        success, response = self.run_test("Search CPT 99213", "GET", "cpt-codes/search?q=99213&limit=10", 200)
        
        if success:
            results = response.get('results', [])
            print(f"   Found {len(results)} results")
            
            # Look for exact match
            exact_match = None
            for result in results:
                if result.get('code') == '99213':
                    exact_match = result
                    break
                    
            if exact_match:
                print(f"✅ Found CPT 99213: {exact_match.get('description', 'No description')}")
                print(f"   Category: {exact_match.get('category')}")
                print(f"   Work RVU: {exact_match.get('work_rvu')}")
                print(f"   Total RVU: {exact_match.get('total_rvu')}")
                return True
            else:
                print("❌ CPT 99213 not found in search results")
                return False
                
        return success

    def test_cpt_code_detail_99213(self):
        """Test getting detailed information for CPT 99213"""
        return self.run_test("CPT 99213 Details", "GET", "cpt-codes/99213", 200)

    def test_calculate_medicare_rate_99213(self):
        """Test calculating Medicare rate for CPT 99213"""
        success, response = self.run_test("Calculate Rate CPT 99213", "GET", "fee-schedule/rate?cpt_code=99213&locality=00000", 200)
        
        if success:
            medicare_rate = response.get('medicare_rate')
            locality_name = response.get('locality_name')
            work_rvu = response.get('work_rvu')
            total_rvu = response.get('total_rvu')
            
            print(f"   Medicare Rate: ${medicare_rate}")
            print(f"   Locality: {locality_name}")
            print(f"   Work RVU: {work_rvu}")
            print(f"   Total RVU: {total_rvu}")
            
        return success

    def test_list_gpci_localities(self):
        """Test listing GPCI localities"""
        success, response = self.run_test("List GPCI Localities", "GET", "fee-schedule/localities", 200)
        
        if success:
            localities = response.get('localities', [])
            count = response.get('count', 0)
            
            print(f"   Found {count} localities")
            
            # Check for national locality
            national = None
            for loc in localities:
                if loc.get('code') == '00000':
                    national = loc
                    break
                    
            if national:
                print(f"✅ Found National locality: {national.get('name')}")
                print(f"   Work GPCI: {national.get('work_gpci')}")
                print(f"   PE GPCI: {national.get('pe_gpci')}")
                print(f"   MP GPCI: {national.get('mp_gpci')}")
                
        return success

    def test_cpt_categories(self):
        """Test getting CPT codes by category"""
        categories = ["E%2FM", "Surgery", "Radiology", "Pathology%2FLab", "Medicine", "Anesthesia", "HCPCS"]
        category_names = ["E/M", "Surgery", "Radiology", "Pathology/Lab", "Medicine", "Anesthesia", "HCPCS"]
        
        for i, category in enumerate(categories):
            success, response = self.run_test(f"CPT Category {category_names[i]}", "GET", f"cpt-codes/category/{category}", 200)
            
            if success:
                codes = response.get('codes', [])
                count = response.get('count', 0)
                print(f"   {category_names[i]}: {count} codes")
            else:
                return False
                
        return True

    def test_create_member(self):
        """Test creating a member"""
        if not self.plan_id:
            print("❌ Cannot create member - no plan ID available")
            return False
            
        # Use timestamp to make member ID unique
        timestamp = datetime.now().strftime('%H%M%S')
        member_id = f"MBR{timestamp}"
            
        member_data = {
            "member_id": member_id,
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "gender": "M",
            "group_id": "GRP001",
            "plan_id": self.plan_id,
            "effective_date": "2024-01-01",
            "relationship": "subscriber"
        }
        
        success, response = self.run_test(
            "Create Member",
            "POST",
            "members",
            200,
            data=member_data
        )
        
        if success and 'member_id' in response:
            self.member_id = response['member_id']
            print(f"   Member created: {self.member_id}")
            return True
        return False

    def test_login_demo_user(self):
        """Test login with demo@javelina.com"""
        success, response = self.run_test(
            "Demo User Login",
            "POST",
            "auth/login",
            200,
            data={"email": "demo@javelina.com", "password": "Demo123!"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            user_role = response['user']['role']
            print(f"   Demo user logged in with role: {user_role}")
            return True
        return False

def main():
    print("🚀 Starting Claims Adjudication System API Tests")
    print("=" * 60)
    
    tester = ClaimsAPITester()
    
    # Test sequence - focusing on Fee Schedule functionality
    tests = [
        ("Health Check", tester.test_health_check),
        ("Demo User Login", tester.test_login_demo_user),
        ("Get Current User", tester.test_get_me),
        ("Dashboard Metrics", tester.test_dashboard_metrics),
        ("Fee Schedule Stats", tester.test_fee_schedule_stats),
        ("Search CPT 99213", tester.test_search_cpt_99213),
        ("CPT 99213 Details", tester.test_cpt_code_detail_99213),
        ("Calculate Rate CPT 99213", tester.test_calculate_medicare_rate_99213),
        ("List GPCI Localities", tester.test_list_gpci_localities),
        ("CPT Categories", tester.test_cpt_categories),
        ("Create Benefit Plan", tester.test_create_plan),
        ("Create Member", tester.test_create_member),
        ("Create Claim with 99213", tester.test_create_claim),
        ("List Claims", tester.test_list_claims),
        ("Get Claim Detail", tester.test_get_claim_detail),
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            tester.tests_run += 1
    
    # Print results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())