"""
FletchFlow - Preventive Services API Tests
Tests for ACA-compliant preventive coverage module including:
- Preventive service catalog (63 codes across 7 categories)
- Search functionality
- Analytics and utilization tracking
- Abuse detection
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@fletchflow.com"
TEST_PASSWORD = "Demo123!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestPreventiveCategories:
    """Test preventive service categories endpoint."""
    
    def test_get_categories_returns_7_categories(self, auth_headers):
        """GET /api/preventive/categories should return 7 categories."""
        response = requests.get(f"{BASE_URL}/api/preventive/categories", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert len(data) == 7, f"Expected 7 categories, got {len(data)}"
        
        # Verify expected categories exist
        expected_categories = [
            "Wellness Visit",
            "Immunization",
            "Cancer Screening",
            "Preventive Screening",
            "Women's Preventive",
            "Pediatric Preventive",
            "Behavioral Counseling"
        ]
        for cat in expected_categories:
            assert cat in data, f"Missing category: {cat}"
            assert "count" in data[cat], f"Category {cat} missing count"
            assert "subcategories" in data[cat], f"Category {cat} missing subcategories"
    
    def test_wellness_visit_has_14_services(self, auth_headers):
        """Wellness Visit category should have 14 services."""
        response = requests.get(f"{BASE_URL}/api/preventive/categories", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["Wellness Visit"]["count"] == 14, f"Expected 14 Wellness Visit services, got {data['Wellness Visit']['count']}"
    
    def test_immunization_has_15_services(self, auth_headers):
        """Immunization category should have 15 services."""
        response = requests.get(f"{BASE_URL}/api/preventive/categories", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["Immunization"]["count"] == 15, f"Expected 15 Immunization services, got {data['Immunization']['count']}"
    
    def test_cancer_screening_has_11_services(self, auth_headers):
        """Cancer Screening category should have 11 services."""
        response = requests.get(f"{BASE_URL}/api/preventive/categories", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["Cancer Screening"]["count"] == 11, f"Expected 11 Cancer Screening services, got {data['Cancer Screening']['count']}"


class TestPreventiveSearch:
    """Test preventive service search functionality."""
    
    def test_search_99395_returns_wellness_visit(self, auth_headers):
        """Search for 99395 should return wellness visit code."""
        response = requests.get(f"{BASE_URL}/api/preventive/search", 
                               params={"q": "99395"}, 
                               headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        assert len(data["results"]) >= 1, "Expected at least 1 result for 99395"
        
        # Verify the result is a wellness visit
        result = data["results"][0]
        assert result["code"] == "99395"
        assert result["category"] == "Wellness Visit"
        assert "Preventive visit" in result["description"]
    
    def test_search_mammogram_returns_cancer_screening(self, auth_headers):
        """Search for 'mammogram' should return cancer screening codes."""
        response = requests.get(f"{BASE_URL}/api/preventive/search", 
                               params={"q": "mammogram"}, 
                               headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert len(data["results"]) >= 2, f"Expected at least 2 mammogram results, got {len(data['results'])}"
        
        # Verify results are cancer screening
        for result in data["results"]:
            assert result["category"] == "Cancer Screening"
            assert result["subcategory"] == "Mammogram"
    
    def test_search_colonoscopy_returns_results(self, auth_headers):
        """Search for 'colonoscopy' should return results."""
        response = requests.get(f"{BASE_URL}/api/preventive/search", 
                               params={"q": "colonoscopy"}, 
                               headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert len(data["results"]) >= 1, "Expected at least 1 colonoscopy result"
        
        # Verify results are cancer screening
        for result in data["results"]:
            assert result["category"] == "Cancer Screening"
            assert result["subcategory"] == "Colonoscopy"
    
    def test_search_hpv_returns_immunization(self, auth_headers):
        """Search for 'HPV' should return immunization code."""
        response = requests.get(f"{BASE_URL}/api/preventive/search", 
                               params={"q": "HPV"}, 
                               headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert len(data["results"]) >= 1, "Expected at least 1 HPV result"
        
        result = data["results"][0]
        assert result["category"] == "Immunization"


class TestPreventiveAnalytics:
    """Test preventive analytics endpoint."""
    
    def test_analytics_returns_total_codes_63(self, auth_headers):
        """Analytics should return total_preventive_codes: 63."""
        response = requests.get(f"{BASE_URL}/api/preventive/analytics", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_preventive_codes" in data
        assert data["total_preventive_codes"] == 63, f"Expected 63 codes, got {data['total_preventive_codes']}"
    
    def test_analytics_returns_utilization_metrics(self, auth_headers):
        """Analytics should return utilization metrics."""
        response = requests.get(f"{BASE_URL}/api/preventive/analytics", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all expected fields exist
        expected_fields = [
            "total_preventive_services",
            "members_with_preventive",
            "total_active_members",
            "compliance_rate",
            "preventive_pmpm",
            "total_preventive_paid",
            "claims_with_preventive",
            "category_breakdown",
            "total_preventive_codes"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


class TestPreventiveAbuseDetection:
    """Test preventive abuse detection endpoint."""
    
    def test_abuse_detection_returns_flags(self, auth_headers):
        """Abuse detection should return flags array (may be empty)."""
        response = requests.get(f"{BASE_URL}/api/preventive/abuse-detection", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "flags" in data
        assert isinstance(data["flags"], list)


class TestPreventiveServices:
    """Test preventive services listing endpoint."""
    
    def test_list_all_services_returns_63(self, auth_headers):
        """List all services should return 63 codes."""
        response = requests.get(f"{BASE_URL}/api/preventive/services", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] == 63, f"Expected 63 services, got {data['count']}"
    
    def test_list_services_by_category_wellness(self, auth_headers):
        """List services by Wellness Visit category should return 14."""
        response = requests.get(f"{BASE_URL}/api/preventive/services", 
                               params={"category": "Wellness Visit"},
                               headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 14, f"Expected 14 Wellness Visit services, got {data['count']}"
    
    def test_list_services_by_category_immunization(self, auth_headers):
        """List services by Immunization category should return 15."""
        response = requests.get(f"{BASE_URL}/api/preventive/services", 
                               params={"category": "Immunization"},
                               headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 15, f"Expected 15 Immunization services, got {data['count']}"


class TestExistingEndpointsStillWork:
    """Verify existing endpoints still work after preventive module addition."""
    
    def test_dashboard_metrics(self, auth_headers):
        """Dashboard metrics should still work."""
        response = requests.get(f"{BASE_URL}/api/dashboard/metrics", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_claims" in data
        assert "pending_claims" in data
    
    def test_claims_list(self, auth_headers):
        """Claims list should still work."""
        response = requests.get(f"{BASE_URL}/api/claims", headers=auth_headers)
        assert response.status_code == 200
    
    def test_plans_list(self, auth_headers):
        """Plans list should still work."""
        response = requests.get(f"{BASE_URL}/api/plans", headers=auth_headers)
        assert response.status_code == 200
    
    def test_prior_auth_list(self, auth_headers):
        """Prior auth list should still work."""
        response = requests.get(f"{BASE_URL}/api/prior-auth", headers=auth_headers)
        assert response.status_code == 200
    
    def test_network_summary(self, auth_headers):
        """Network summary should still work."""
        response = requests.get(f"{BASE_URL}/api/network/summary", headers=auth_headers)
        assert response.status_code == 200
    
    def test_code_database_stats(self, auth_headers):
        """Code database stats should still work."""
        response = requests.get(f"{BASE_URL}/api/code-database/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["grand_total"] == 377


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
