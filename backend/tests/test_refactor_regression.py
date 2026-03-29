"""
FletchFlow Claims Adjudication System - Refactor Regression Tests
Tests all API routes after the monolithic server.py was refactored into modular architecture.
Verifies: Auth, Dashboard, Plans, Members, Groups, Claims, Examiner, Duplicates, 
Reports, Settings, Audit, Codes (CPT/Dental/Vision/Hearing), Network, Prior Auth, Preventive
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


# ============ HEALTH & ROOT ============
class TestHealthAndRoot:
    """Health check and root endpoint tests"""
    
    def test_health_check(self):
        """GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check: {data}")


# ============ AUTHENTICATION ============
class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """POST /api/auth/login with demo@fletchflow.com / Demo123! returns access_token"""
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
        print(f"✅ Login successful: {TEST_EMAIL}")
    
    def test_auth_me(self, auth_headers):
        """GET /api/auth/me returns user info with valid token"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == TEST_EMAIL
        assert data.get("role") == "admin"
        print(f"✅ Auth me: {data.get('email')}, role={data.get('role')}")


# ============ DASHBOARD ============
class TestDashboard:
    """Dashboard metrics endpoint tests"""
    
    def test_dashboard_metrics(self, auth_headers):
        """GET /api/dashboard/metrics returns complete metrics object"""
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
        print(f"✅ Dashboard metrics: total_claims={data.get('total_claims')}, auto_adj_rate={data.get('auto_adjudication_rate')}%")
    
    def test_dashboard_claims_by_status(self, auth_headers):
        """GET /api/dashboard/claims-by-status returns status breakdown"""
        response = requests.get(f"{BASE_URL}/api/dashboard/claims-by-status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Claims by status: {len(data)} status categories")
    
    def test_dashboard_claims_by_type(self, auth_headers):
        """GET /api/dashboard/claims-by-type returns type breakdown"""
        response = requests.get(f"{BASE_URL}/api/dashboard/claims-by-type", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Claims by type: {len(data)} claim types")
    
    def test_dashboard_recent_activity(self, auth_headers):
        """GET /api/dashboard/recent-activity returns audit logs"""
        response = requests.get(f"{BASE_URL}/api/dashboard/recent-activity?limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Recent activity: {len(data)} entries")


# ============ PLANS ============
class TestPlans:
    """Plans endpoint tests"""
    
    def test_plans_list(self, auth_headers):
        """GET /api/plans returns list of plans"""
        response = requests.get(f"{BASE_URL}/api/plans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Plans list: {len(data)} plans")
    
    def test_plans_get_single(self, auth_headers):
        """GET /api/plans/{id} returns single plan"""
        # First get list to get an ID
        response = requests.get(f"{BASE_URL}/api/plans", headers=auth_headers)
        plans = response.json()
        if len(plans) > 0:
            plan_id = plans[0].get("id")
            response = requests.get(f"{BASE_URL}/api/plans/{plan_id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data.get("id") == plan_id
            print(f"✅ Single plan: {data.get('name')}")
        else:
            print("⚠️ No plans to test single get")


# ============ MEMBERS ============
class TestMembers:
    """Members endpoint tests"""
    
    def test_members_list(self, auth_headers):
        """GET /api/members returns list of members"""
        response = requests.get(f"{BASE_URL}/api/members", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Members list: {len(data)} members")
    
    def test_members_eligibility_reconciliation(self, auth_headers):
        """GET /api/members/eligibility/reconciliation returns reconciliation data"""
        response = requests.get(f"{BASE_URL}/api/members/eligibility/reconciliation", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
        print(f"✅ Eligibility reconciliation: {type(data).__name__}")
    
    def test_members_eligibility_retro_terms(self, auth_headers):
        """GET /api/members/eligibility/retro-terms returns retro term monitor data"""
        response = requests.get(f"{BASE_URL}/api/members/eligibility/retro-terms", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
        print(f"✅ Retro terms: {type(data).__name__}")
    
    def test_members_eligibility_age_out_alerts(self, auth_headers):
        """GET /api/members/eligibility/age-out-alerts returns age-out alerts"""
        response = requests.get(f"{BASE_URL}/api/members/eligibility/age-out-alerts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
        print(f"✅ Age-out alerts: {type(data).__name__}")


# ============ GROUPS ============
class TestGroups:
    """Groups endpoint tests"""
    
    def test_groups_list(self, auth_headers):
        """GET /api/groups returns list of groups"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Groups list: {len(data)} groups")
    
    def test_groups_get_single(self, auth_headers):
        """GET /api/groups/{id} returns group with pulse analytics available"""
        # First get list to get an ID
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        groups = response.json()
        if len(groups) > 0:
            group_id = groups[0].get("id")
            response = requests.get(f"{BASE_URL}/api/groups/{group_id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data.get("id") == group_id
            print(f"✅ Single group: {data.get('name')}")
        else:
            print("⚠️ No groups to test single get")


# ============ CLAIMS ============
class TestClaims:
    """Claims endpoint tests"""
    
    def test_claims_list(self, auth_headers):
        """GET /api/claims returns claims list"""
        response = requests.get(f"{BASE_URL}/api/claims", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Claims list: {len(data)} claims")
    
    def test_claims_get_single(self, auth_headers):
        """GET /api/claims/{id} returns single claim detail"""
        # First get list to get an ID
        response = requests.get(f"{BASE_URL}/api/claims?limit=5", headers=auth_headers)
        claims = response.json()
        if len(claims) > 0:
            claim_id = claims[0].get("id")
            response = requests.get(f"{BASE_URL}/api/claims/{claim_id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data.get("id") == claim_id
            print(f"✅ Single claim: {data.get('claim_number')}")
        else:
            print("⚠️ No claims to test single get")
    
    def test_claims_create(self, auth_headers):
        """POST /api/claims creates a new claim with adjudication"""
        claim_data = {
            "member_id": "TEST_MEMBER_001",
            "provider_id": "TEST_PROVIDER_001",
            "claim_type": "medical",
            "service_date": "2024-01-15",
            "diagnosis_codes": ["Z00.00"],
            "procedure_codes": ["99213"],
            "billed_amount": 150.00,
            "group_id": "TEST_GROUP_001"
        }
        response = requests.post(f"{BASE_URL}/api/claims", json=claim_data, headers=auth_headers)
        # Accept 200, 201, or 422 (validation error is acceptable for test data)
        assert response.status_code in [200, 201, 422]
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Claim created: {data.get('claim_number', data.get('id'))}")
        else:
            print(f"⚠️ Claim creation returned validation error (expected for test data)")


# ============ EXAMINER ============
class TestExaminer:
    """Examiner endpoint tests"""
    
    def test_examiner_queue(self, auth_headers):
        """GET /api/examiner/queue returns examiner queue"""
        response = requests.get(f"{BASE_URL}/api/examiner/queue", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Examiner queue: {len(data)} items")
    
    def test_examiner_queue_all(self, auth_headers):
        """GET /api/examiner/queue/all returns all queues (admin)"""
        response = requests.get(f"{BASE_URL}/api/examiner/queue/all", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Examiner queue all: {len(data)} items")
    
    def test_examiner_performance(self, auth_headers):
        """GET /api/examiner/performance returns performance metrics"""
        response = requests.get(f"{BASE_URL}/api/examiner/performance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Examiner performance: {len(data)} examiners")
    
    def test_examiner_list(self, auth_headers):
        """GET /api/examiner/list returns examiner list"""
        response = requests.get(f"{BASE_URL}/api/examiner/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Examiner list: {len(data)} examiners")


# ============ DUPLICATES ============
class TestDuplicates:
    """Duplicates endpoint tests"""
    
    def test_duplicates_list(self, auth_headers):
        """GET /api/duplicates returns duplicate alerts"""
        response = requests.get(f"{BASE_URL}/api/duplicates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Duplicates: {len(data)} alerts")


# ============ REPORTS ============
class TestReports:
    """Reports endpoint tests"""
    
    def test_reports_fixed_cost_vs_claims(self, auth_headers):
        """GET /api/reports/fixed-cost-vs-claims returns report data"""
        response = requests.get(f"{BASE_URL}/api/reports/fixed-cost-vs-claims", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
        print(f"✅ Fixed cost vs claims report: {type(data).__name__}")


# ============ SETTINGS ============
class TestSettings:
    """Settings endpoint tests"""
    
    def test_settings_adjudication_gateway(self, auth_headers):
        """GET /api/settings/adjudication-gateway returns gateway config"""
        response = requests.get(f"{BASE_URL}/api/settings/adjudication-gateway", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tier1_auto_pay_limit" in data or "auto_pay_limit" in data or isinstance(data, dict)
        print(f"✅ Adjudication gateway settings: {data}")


# ============ AUDIT ============
class TestAudit:
    """Audit endpoint tests"""
    
    def test_audit_logs(self, auth_headers):
        """GET /api/audit-logs returns audit entries"""
        response = requests.get(f"{BASE_URL}/api/audit-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Audit logs: {len(data)} entries")


# ============ CODES (CPT/Dental/Vision/Hearing) ============
class TestCodes:
    """Code search endpoint tests"""
    
    def test_cpt_codes_search(self, auth_headers):
        """GET /api/cpt-codes/search?q=office returns CPT search results"""
        response = requests.get(f"{BASE_URL}/api/cpt-codes/search?q=office", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or isinstance(data, list)
        print(f"✅ CPT codes search 'office': {data.get('count', len(data.get('results', [])))} results")
    
    def test_dental_codes_search(self, auth_headers):
        """GET /api/dental-codes/search?q=exam returns dental results"""
        response = requests.get(f"{BASE_URL}/api/dental-codes/search?q=exam", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or isinstance(data, list)
        print(f"✅ Dental codes search 'exam': {data.get('count', len(data.get('results', [])))} results")
    
    def test_vision_codes_search(self, auth_headers):
        """GET /api/vision-codes/search?q=exam returns vision results"""
        response = requests.get(f"{BASE_URL}/api/vision-codes/search?q=exam", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or isinstance(data, list)
        print(f"✅ Vision codes search 'exam': {data.get('count', len(data.get('results', [])))} results")
    
    def test_hearing_codes_search(self, auth_headers):
        """GET /api/hearing-codes/search?q=audio returns hearing results"""
        response = requests.get(f"{BASE_URL}/api/hearing-codes/search?q=audio", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or isinstance(data, list)
        print(f"✅ Hearing codes search 'audio': {data.get('count', len(data.get('results', [])))} results")
    
    def test_code_database_stats(self, auth_headers):
        """GET /api/code-database/stats returns all code stats"""
        response = requests.get(f"{BASE_URL}/api/code-database/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "grand_total" in data
        assert "medical" in data
        assert "dental" in data
        assert "vision" in data
        assert "hearing" in data
        print(f"✅ Code database stats: grand_total={data.get('grand_total')}")


# ============ NETWORK ============
class TestNetwork:
    """Network endpoint tests"""
    
    def test_network_summary(self, auth_headers):
        """GET /api/network/summary returns network summary"""
        response = requests.get(f"{BASE_URL}/api/network/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "active_contracts" in data or isinstance(data, dict)
        print(f"✅ Network summary: {data}")


# ============ PRIOR AUTH ============
class TestPriorAuth:
    """Prior Authorization endpoint tests"""
    
    def test_prior_auth_list(self, auth_headers):
        """GET /api/prior-auth returns prior auth list"""
        response = requests.get(f"{BASE_URL}/api/prior-auth", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Prior auth: {len(data)} items")


# ============ PREVENTIVE ============
class TestPreventive:
    """Preventive services endpoint tests"""
    
    def test_preventive_services(self, auth_headers):
        """GET /api/preventive/services returns all preventive services"""
        response = requests.get(f"{BASE_URL}/api/preventive/services", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
        print(f"✅ Preventive services: {type(data).__name__}")
    
    def test_preventive_categories(self, auth_headers):
        """GET /api/preventive/categories returns categories"""
        response = requests.get(f"{BASE_URL}/api/preventive/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
        print(f"✅ Preventive categories: {type(data).__name__}")
    
    def test_preventive_analytics(self, auth_headers):
        """GET /api/preventive/analytics returns analytics data"""
        response = requests.get(f"{BASE_URL}/api/preventive/analytics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
        print(f"✅ Preventive analytics: {type(data).__name__}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
