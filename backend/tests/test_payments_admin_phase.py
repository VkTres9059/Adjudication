"""
Test Suite for Phase A/B/C Features:
- Payment Center (ACH/virtual card/check, batches, reversals, adjustments, reconciliation)
- Admin Portal (users, portal roles, TPA onboarding, system overview, traceability)
- Audit Logs (enhanced with filters)
- Plan Versioning
- Rx Rules Engine
- Enrollment Tier Auto-Adjust
- EOB/EOP PDF generation
- IDR Tracking
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@fletchflow.com"
TEST_PASSWORD = "Demo123!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    # API returns access_token, not token
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


@pytest.fixture(scope="module")
def test_claim_id(api_client):
    """Get or create a test claim for payment tests."""
    # First try to get an existing approved claim
    response = api_client.get(f"{BASE_URL}/api/claims", params={"claim_status": "approved", "limit": 1})
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0]["id"]
    
    # If no approved claim, get any claim
    response = api_client.get(f"{BASE_URL}/api/claims", params={"limit": 1})
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0]["id"]
    
    return None


@pytest.fixture(scope="module")
def test_group_id(api_client):
    """Get an existing group ID for tests."""
    response = api_client.get(f"{BASE_URL}/api/groups")
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0]["id"]
    return None


@pytest.fixture(scope="module")
def test_plan_id(api_client):
    """Get an existing plan ID for tests."""
    response = api_client.get(f"{BASE_URL}/api/plans")
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0]["id"]
    return None


# ============ PAYMENT CENTER TESTS ============

class TestPaymentSummary:
    """Test GET /api/payments/summary"""
    
    def test_payment_summary_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/payments/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "by_method" in data
        assert "by_status" in data
        assert "total_payments" in data
        assert "total_amount" in data
        assert isinstance(data["total_payments"], int)
        assert isinstance(data["total_amount"], (int, float))
        print(f"Payment summary: {data['total_payments']} payments, ${data['total_amount']}")


class TestPaymentsList:
    """Test GET /api/payments"""
    
    def test_list_payments_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/payments")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} payments")
    
    def test_list_payments_with_filters(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/payments", params={"status": "pending", "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPaymentBatches:
    """Test payment batch endpoints"""
    
    def test_list_batches_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/payments/batches")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} payment batches")
    
    def test_create_batch_no_approved_claims(self, api_client):
        """Test batch creation - may fail if no approved claims without payments."""
        response = api_client.post(f"{BASE_URL}/api/payments/batch", json={
            "payment_method": "ach",
            "funding_source": "aso",
            "description": "Test batch"
        })
        # Either 200 (batch created) or 400 (no approved claims)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "payment_count" in data
            print(f"Batch created: {data['payment_count']} payments")
        else:
            print(f"No approved claims for batch: {response.json().get('detail')}")


class TestPaymentReconciliation:
    """Test GET /api/payments/reconciliation"""
    
    def test_reconciliation_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/payments/reconciliation")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "claims" in data
        assert "payments" in data
        assert "discrepancy" in data
        assert "total_billed" in data["claims"]
        assert "total_paid" in data["claims"]
        print(f"Reconciliation: Claims paid ${data['claims']['total_paid']}, Payments ${data['payments']['total_disbursed']}, Discrepancy ${data['discrepancy']}")


class TestPaymentAdjustments:
    """Test payment adjustments endpoints"""
    
    def test_list_adjustments_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/payments/adjustments")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} adjustments")


# ============ ADMIN PORTAL TESTS ============

class TestAdminPortalRoles:
    """Test GET /api/admin/portal-roles"""
    
    def test_portal_roles_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/admin/portal-roles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict)
        assert "admin" in data
        assert "tpa_admin" in data
        assert "mgu_admin" in data
        assert "carrier_viewer" in data
        assert "analytics_viewer" in data
        print(f"Portal roles: {list(data.keys())}")


class TestAdminUsers:
    """Test admin user endpoints"""
    
    def test_list_users_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} users")
    
    def test_create_user_and_verify(self, api_client):
        """Test creating a user via admin endpoint."""
        unique_email = f"TEST_user_{uuid.uuid4().hex[:8]}@test.com"
        response = api_client.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Test User Admin",
            "role": "reviewer",
            "portal_role": "analytics_viewer"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["email"] == unique_email
        assert data["name"] == "Test User Admin"
        assert data["portal_role"] == "analytics_viewer"
        assert "id" in data
        print(f"Created user: {data['email']} with portal role {data['portal_role']}")
        
        # Verify user appears in list
        list_response = api_client.get(f"{BASE_URL}/api/admin/users")
        users = list_response.json()
        user_emails = [u["email"] for u in users]
        assert unique_email in user_emails, "Created user not found in list"


class TestAdminTPAs:
    """Test TPA management endpoints"""
    
    def test_list_tpas_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/admin/tpas")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} TPAs")
    
    def test_onboard_tpa_and_verify(self, api_client):
        """Test TPA onboarding."""
        unique_tax_id = f"TEST-{uuid.uuid4().hex[:8]}"
        response = api_client.post(f"{BASE_URL}/api/admin/tpas", json={
            "name": "Test TPA Inc",
            "tax_id": unique_tax_id,
            "contact_name": "John Doe",
            "contact_email": "john@testtpa.com",
            "contact_phone": "555-1234",
            "data_feed_type": "edi_834_837"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["name"] == "Test TPA Inc"
        assert data["tax_id"] == unique_tax_id
        assert data["status"] == "active"
        assert "id" in data
        print(f"Onboarded TPA: {data['name']} (Tax ID: {data['tax_id']})")


class TestAdminSystemOverview:
    """Test GET /api/admin/system-overview"""
    
    def test_system_overview_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/admin/system-overview")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "users" in data
        assert "groups" in data
        assert "plans" in data
        assert "members" in data
        assert "claims" in data
        assert "tpas" in data
        assert "payments" in data
        assert "recent_activity" in data
        print(f"System overview: {data['users']['total']} users, {data['groups']} groups, {data['claims']} claims")


class TestAdminTraceability:
    """Test GET /api/admin/traceability/{claim_id}"""
    
    def test_traceability_returns_200(self, api_client, test_claim_id):
        if not test_claim_id:
            pytest.skip("No test claim available")
        
        response = api_client.get(f"{BASE_URL}/api/admin/traceability/{test_claim_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "claim" in data
        assert "member" in data
        assert "plan" in data
        assert "group" in data
        assert "payment" in data
        assert "audit_trail" in data
        print(f"Traceability chain: Claim {data['claim']['claim_number']} -> Member {data['member']['member_id'] if data['member'] else 'N/A'}")
    
    def test_traceability_not_found(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/admin/traceability/nonexistent-claim-id")
        assert response.status_code == 404


# ============ AUDIT LOG TESTS ============

class TestAuditLogs:
    """Test audit log endpoints"""
    
    def test_list_audit_logs_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/audit-logs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)
        print(f"Found {data['total']} audit log entries")
    
    def test_audit_logs_with_filters(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/audit-logs", params={"action": "login", "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
    
    def test_audit_summary_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/audit-logs/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_events" in data
        assert "by_action" in data
        assert isinstance(data["by_action"], list)
        print(f"Audit summary: {data['total_events']} total events, {len(data['by_action'])} action types")


# ============ PLAN VERSIONING TESTS ============

class TestPlanVersions:
    """Test plan version history endpoints"""
    
    def test_plan_versions_returns_200(self, api_client, test_plan_id):
        if not test_plan_id:
            pytest.skip("No test plan available")
        
        response = api_client.get(f"{BASE_URL}/api/plans/{test_plan_id}/versions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "plan_id" in data
        assert "current_version" in data
        assert "versions" in data
        print(f"Plan {test_plan_id[:8]} has {len(data['versions'])} versions, current: v{data['current_version']}")


# ============ RX RULES TESTS ============

class TestRxRules:
    """Test Rx rules endpoints"""
    
    def test_rx_rules_template_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/plans/rx-rules/template")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict)
        print(f"Rx rules template keys: {list(data.keys())}")
    
    def test_rx_classify_drug(self, api_client):
        response = api_client.post(f"{BASE_URL}/api/plans/rx-rules/classify", params={
            "hcpcs_code": "J3490",
            "drug_name": "Ozempic"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tier" in data or "classification" in data or "drug_name" in data
        print(f"Drug classification result: {data}")


# ============ ENROLLMENT TIER AUTO-ADJUST TESTS ============

class TestEnrollmentTierAutoAdjust:
    """Test POST /api/groups/{group_id}/auto-adjust-tiers"""
    
    def test_auto_adjust_tiers_returns_200(self, api_client, test_group_id):
        if not test_group_id:
            pytest.skip("No test group available")
        
        response = api_client.post(f"{BASE_URL}/api/groups/{test_group_id}/auto-adjust-tiers")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "group_id" in data
        assert "adjustments" in data
        assert "total_adjusted" in data
        print(f"Auto-adjust tiers: {data['total_adjusted']} members adjusted")


# ============ EOB/EOP PDF TESTS ============

class TestEOBEOPPdf:
    """Test EOB/EOP PDF generation endpoints"""
    
    def test_eob_pdf_returns_pdf(self, api_client, test_claim_id):
        if not test_claim_id:
            pytest.skip("No test claim available")
        
        response = api_client.get(f"{BASE_URL}/api/claims/{test_claim_id}/eob.pdf")
        # Should return 200 with PDF or 404 if claim not found
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"
            assert len(response.content) > 0
            print(f"EOB PDF generated: {len(response.content)} bytes")
    
    def test_eop_pdf_returns_pdf(self, api_client, test_claim_id):
        if not test_claim_id:
            pytest.skip("No test claim available")
        
        response = api_client.get(f"{BASE_URL}/api/claims/{test_claim_id}/eop.pdf")
        # Should return 200 with PDF or 404 if claim not found
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"
            assert len(response.content) > 0
            print(f"EOP PDF generated: {len(response.content)} bytes")


# ============ IDR TRACKING TESTS ============

class TestIDRTracking:
    """Test PUT /api/claims/{claim_id}/idr"""
    
    def test_idr_update_returns_200(self, api_client, test_claim_id):
        if not test_claim_id:
            pytest.skip("No test claim available")
        
        idr_case = f"IDR-TEST-{uuid.uuid4().hex[:8]}"
        response = api_client.put(f"{BASE_URL}/api/claims/{test_claim_id}/idr", params={
            "idr_case_number": idr_case,
            "idr_status": "pending",
            "notes": "Test IDR case"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["claim_id"] == test_claim_id
        assert data["idr_case_number"] == idr_case
        assert data["idr_status"] == "pending"
        print(f"IDR tracking updated: Case {idr_case}")


# ============ PAYMENT CREATE AND REVERSE TESTS ============

class TestPaymentCreateAndReverse:
    """Test payment creation and reversal flow"""
    
    def test_create_payment_for_approved_claim(self, api_client):
        """Test creating a payment for an approved claim."""
        # First get an approved claim without a payment
        claims_response = api_client.get(f"{BASE_URL}/api/claims", params={"claim_status": "approved", "limit": 50})
        if claims_response.status_code != 200:
            pytest.skip("Could not fetch claims")
        
        claims = claims_response.json()
        # Find a claim without payment_id
        eligible_claim = None
        for claim in claims:
            if not claim.get("payment_id") and claim.get("total_paid", 0) > 0:
                eligible_claim = claim
                break
        
        if not eligible_claim:
            pytest.skip("No approved claim without payment found")
        
        # Try to create payment
        response = api_client.post(f"{BASE_URL}/api/payments", json={
            "claim_id": eligible_claim["id"],
            "payment_method": "ach",
            "payee_name": "Test Provider",
            "notes": "Test payment"
        })
        
        # Either 200 (created) or 400 (duplicate or not payable)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["claim_id"] == eligible_claim["id"]
            assert data["status"] == "pending"
            print(f"Payment created: {data['id'][:8]} for ${data['amount']}")
            return data["id"]
        else:
            print(f"Payment creation blocked: {response.json().get('detail')}")
            return None


class TestPaymentReversal:
    """Test payment reversal"""
    
    def test_reverse_payment_not_found(self, api_client):
        """Test reversing a non-existent payment."""
        response = api_client.post(f"{BASE_URL}/api/payments/reverse", json={
            "payment_id": "nonexistent-payment-id",
            "reason": "Test reversal"
        })
        assert response.status_code == 404


class TestPaymentAdjust:
    """Test payment adjustment"""
    
    def test_adjust_claim_not_found(self, api_client):
        """Test adjusting a non-existent claim."""
        response = api_client.post(f"{BASE_URL}/api/payments/adjust", json={
            "claim_id": "nonexistent-claim-id",
            "adjustment_type": "decrease",
            "amount": 100,
            "reason": "Test adjustment"
        })
        assert response.status_code == 404
    
    def test_adjust_claim_decrease(self, api_client, test_claim_id):
        """Test decreasing payment on a claim."""
        if not test_claim_id:
            pytest.skip("No test claim available")
        
        response = api_client.post(f"{BASE_URL}/api/payments/adjust", json={
            "claim_id": test_claim_id,
            "adjustment_type": "decrease",
            "amount": 10.00,
            "reason": "Test decrease adjustment",
            "notes": "Testing"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["adjustment_type"] == "decrease"
        assert data["adjustment_amount"] < 0  # Decrease is negative
        print(f"Adjustment created: {data['adjustment_type']} ${data['adjustment_amount']}")


# ============ USER ACCESS UPDATE TEST ============

class TestUserAccessUpdate:
    """Test PUT /api/admin/users/{id}/access"""
    
    def test_update_user_access(self, api_client):
        """Test updating user portal access."""
        # First create a test user
        unique_email = f"TEST_access_{uuid.uuid4().hex[:8]}@test.com"
        create_response = api_client.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Access Test User",
            "role": "reviewer",
            "portal_role": "analytics_viewer"
        })
        
        if create_response.status_code != 200:
            pytest.skip("Could not create test user")
        
        user_id = create_response.json()["id"]
        
        # Update access
        response = api_client.put(f"{BASE_URL}/api/admin/users/{user_id}/access", json={
            "user_id": user_id,
            "portal_role": "tpa_admin",
            "group_ids": [],
            "active": True
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["portal_role"] == "tpa_admin"
        print(f"User access updated: {data['email']} -> {data['portal_role']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
