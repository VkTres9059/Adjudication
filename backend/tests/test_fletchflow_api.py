"""
FletchFlow Claims Adjudication System - Backend API Tests
Tests for: Authentication, Code Database (Medical/Dental/Vision/Hearing), 
Prior Auth, Network, Dashboard, Claims, Plans, Members
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@fletchflow.com"
TEST_PASSWORD = "Demo123!"
ALT_EMAIL = "demo@javelina.com"


class TestHealthAndRoot:
    """Health check and root endpoint tests"""
    
    def test_root_endpoint_returns_fletchflow_branding(self):
        """API: GET /api/ returns FletchFlow branding"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "FletchFlow" in data.get("message", "")
        assert data.get("version") == "1.0.0"
        print(f"✅ Root endpoint returns: {data}")
    
    def test_health_check(self):
        """API: GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check passed: {data}")


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_login_with_fletchflow_credentials(self):
        """Login with demo@fletchflow.com / Demo123! credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data.get("token_type") == "bearer"
        assert data.get("user", {}).get("email") == TEST_EMAIL
        assert data.get("user", {}).get("role") == "admin"
        print(f"✅ Login successful for {TEST_EMAIL}")
    
    def test_login_with_javelina_credentials(self):
        """Old credentials also work: demo@javelina.com / Demo123!"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ALT_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"✅ Login successful for {ALT_EMAIL}")
    
    def test_login_invalid_credentials(self):
        """Login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for authenticated tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestCodeDatabaseStats:
    """Code Database statistics tests"""
    
    def test_code_database_stats_grand_total(self, auth_headers):
        """API: GET /api/code-database/stats returns grand_total of 377"""
        response = requests.get(f"{BASE_URL}/api/code-database/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("grand_total") == 377
        assert data.get("medical", {}).get("total") == 189
        assert data.get("dental", {}).get("total") == 79
        assert data.get("vision", {}).get("total") == 44
        assert data.get("hearing", {}).get("total") == 65
        print(f"✅ Code database stats: grand_total={data.get('grand_total')}")


class TestDentalCodes:
    """Dental CDT code search tests"""
    
    def test_search_dental_code_d1110(self, auth_headers):
        """API: GET /api/dental-codes/search?q=D1110 returns results"""
        response = requests.get(f"{BASE_URL}/api/dental-codes/search?q=D1110", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        assert len(results) > 0
        # Verify D1110 is in results
        d1110 = next((r for r in results if r.get("code") == "D1110"), None)
        assert d1110 is not None
        assert "Prophylaxis" in d1110.get("description", "")
        assert d1110.get("category") == "Preventive"
        assert d1110.get("benefit_class") == "preventive"
        assert d1110.get("fee") == 105.0
        print(f"✅ Dental code D1110 found: {d1110.get('description')}")
    
    def test_search_dental_by_description(self, auth_headers):
        """Search dental codes by description"""
        response = requests.get(f"{BASE_URL}/api/dental-codes/search?q=prophylaxis", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("count", 0) > 0
        print(f"✅ Dental search 'prophylaxis' returned {data.get('count')} results")


class TestVisionCodes:
    """Vision code search tests"""
    
    def test_search_vision_code_92014(self, auth_headers):
        """API: GET /api/vision-codes/search?q=92014 returns results"""
        response = requests.get(f"{BASE_URL}/api/vision-codes/search?q=92014", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        assert len(results) > 0
        # Verify 92014 is in results
        v92014 = next((r for r in results if r.get("code") == "92014"), None)
        assert v92014 is not None
        assert "Ophthalmological" in v92014.get("description", "")
        assert v92014.get("category") == "Eye Exam"
        assert v92014.get("benefit_class") == "exam"
        assert v92014.get("fee") == 175.0
        print(f"✅ Vision code 92014 found: {v92014.get('description')}")
    
    def test_search_vision_by_description(self, auth_headers):
        """Search vision codes by description"""
        response = requests.get(f"{BASE_URL}/api/vision-codes/search?q=exam", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("count", 0) > 0
        print(f"✅ Vision search 'exam' returned {data.get('count')} results")


class TestHearingCodes:
    """Hearing code search tests"""
    
    def test_search_hearing_code_92557(self, auth_headers):
        """API: GET /api/hearing-codes/search?q=92557 returns results"""
        response = requests.get(f"{BASE_URL}/api/hearing-codes/search?q=92557", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        assert len(results) > 0
        # Verify 92557 is in results
        h92557 = next((r for r in results if r.get("code") == "92557"), None)
        assert h92557 is not None
        assert "audiometry" in h92557.get("description", "").lower()
        assert h92557.get("category") == "Audiometric Testing"
        assert h92557.get("benefit_class") == "diagnostic"
        assert h92557.get("fee") == 80.0
        print(f"✅ Hearing code 92557 found: {h92557.get('description')}")
    
    def test_search_hearing_by_description(self, auth_headers):
        """Search hearing codes by description"""
        response = requests.get(f"{BASE_URL}/api/hearing-codes/search?q=audiometry", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("count", 0) > 0
        print(f"✅ Hearing search 'audiometry' returned {data.get('count')} results")


class TestPriorAuth:
    """Prior Authorization endpoint tests"""
    
    def test_prior_auth_list_returns_empty_array(self, auth_headers):
        """API: GET /api/prior-auth returns empty array"""
        response = requests.get(f"{BASE_URL}/api/prior-auth", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Prior auth list returned {len(data)} items")


class TestNetwork:
    """Network management endpoint tests"""
    
    def test_network_summary_returns_data(self, auth_headers):
        """API: GET /api/network/summary returns summary data"""
        response = requests.get(f"{BASE_URL}/api/network/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "active_contracts" in data
        assert "total_claims_processed" in data
        assert "total_billed" in data
        assert "total_paid" in data
        assert "total_savings" in data
        assert "savings_percentage" in data
        print(f"✅ Network summary: {data.get('active_contracts')} contracts, {data.get('savings_percentage')}% savings")


class TestDashboard:
    """Dashboard metrics endpoint tests"""
    
    def test_dashboard_metrics(self, auth_headers):
        """Dashboard loads with metrics"""
        response = requests.get(f"{BASE_URL}/api/dashboard/metrics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_claims" in data
        assert "pending_claims" in data
        assert "approved_claims" in data
        assert "denied_claims" in data
        assert "duplicate_alerts" in data
        assert "total_paid" in data
        assert "auto_adjudication_rate" in data
        print(f"✅ Dashboard metrics: {data.get('total_claims')} total claims, {data.get('auto_adjudication_rate')}% auto-adj rate")
    
    def test_dashboard_claims_by_status(self, auth_headers):
        """Dashboard claims by status chart data"""
        response = requests.get(f"{BASE_URL}/api/dashboard/claims-by-status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Claims by status: {len(data)} status categories")
    
    def test_dashboard_claims_by_type(self, auth_headers):
        """Dashboard claims by type chart data"""
        response = requests.get(f"{BASE_URL}/api/dashboard/claims-by-type", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Claims by type: {len(data)} claim types")


class TestClaims:
    """Claims endpoint tests"""
    
    def test_claims_list(self, auth_headers):
        """Claims page loads - list claims"""
        response = requests.get(f"{BASE_URL}/api/claims", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Claims list: {len(data)} claims")


class TestPlans:
    """Plans endpoint tests"""
    
    def test_plans_list(self, auth_headers):
        """Plans page loads - list plans"""
        response = requests.get(f"{BASE_URL}/api/plans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Plans list: {len(data)} plans")


class TestMembers:
    """Members endpoint tests"""
    
    def test_members_list(self, auth_headers):
        """Members page loads - list members"""
        response = requests.get(f"{BASE_URL}/api/members", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Members list: {len(data)} members")


class TestFeeSchedule:
    """Fee Schedule endpoint tests"""
    
    def test_fee_schedule_stats(self, auth_headers):
        """Fee Schedule page loads - get stats"""
        response = requests.get(f"{BASE_URL}/api/fee-schedule/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("total_cpt_codes") == 189
        assert data.get("total_localities") == 87
        print(f"✅ Fee schedule stats: {data.get('total_cpt_codes')} CPT codes, {data.get('total_localities')} localities")


class TestDuplicates:
    """Duplicates endpoint tests"""
    
    def test_duplicates_list(self, auth_headers):
        """Duplicates page loads - list duplicate alerts"""
        response = requests.get(f"{BASE_URL}/api/duplicates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Duplicates list: {len(data)} alerts")


class TestMedicalCPTCodes:
    """Medical CPT code search tests"""
    
    def test_search_cpt_code_99213(self, auth_headers):
        """Search medical CPT codes"""
        response = requests.get(f"{BASE_URL}/api/cpt-codes/search?q=99213", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        assert len(results) > 0
        cpt99213 = next((r for r in results if r.get("code") == "99213"), None)
        assert cpt99213 is not None
        print(f"✅ CPT code 99213 found: {cpt99213.get('description')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
