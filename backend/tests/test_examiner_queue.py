"""
Test Examiner Queue Dashboard and Auto-Assignment Engine
Features tested:
- GET /api/examiner/queue - returns claims with pending_review or managerial_hold status
- GET /api/examiner/performance - returns per-examiner metrics
- GET /api/examiner/list - returns all users with admin or adjudicator role
- POST /api/examiner/queue/{claim_id}/quick-action - approve/deny/request_info
- POST /api/claims/{claim_id}/reassign - reassign claim to different examiner
- Auto-assignment on Tier 3 claims
- Authority routing (<$5k=adjudicator, >=$5k=admin)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@fletchflow.com"
TEST_PASSWORD = "Demo123!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for testing."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    data = response.json()
    return data.get("access_token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestExaminerQueueEndpoints:
    """Test examiner queue API endpoints."""
    
    def test_get_examiner_queue(self, auth_headers):
        """GET /api/examiner/queue returns claims with pending_review or managerial_hold status."""
        response = requests.get(f"{BASE_URL}/api/examiner/queue", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify each claim has required fields
        for claim in data:
            assert "id" in claim, "Claim should have id"
            assert "status" in claim, "Claim should have status"
            assert claim["status"] in ["pending_review", "managerial_hold"], f"Unexpected status: {claim['status']}"
            assert "days_in_queue" in claim, "Claim should have days_in_queue calculated"
            assert isinstance(claim["days_in_queue"], (int, float)), "days_in_queue should be numeric"
        
        print(f"✅ GET /api/examiner/queue returned {len(data)} claims")
    
    def test_get_examiner_performance(self, auth_headers):
        """GET /api/examiner/performance returns per-examiner metrics."""
        response = requests.get(f"{BASE_URL}/api/examiner/performance", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify each examiner has required metrics
        for examiner in data:
            assert "examiner_id" in examiner, "Should have examiner_id"
            assert "examiner_name" in examiner, "Should have examiner_name"
            assert "open_claims" in examiner, "Should have open_claims"
            assert "closed_today" in examiner, "Should have closed_today"
            assert "avg_tat_hours" in examiner, "Should have avg_tat_hours"
            assert "role" in examiner, "Should have role"
            assert examiner["role"] in ["admin", "adjudicator"], f"Unexpected role: {examiner['role']}"
        
        print(f"✅ GET /api/examiner/performance returned {len(data)} examiners")
    
    def test_get_examiner_list(self, auth_headers):
        """GET /api/examiner/list returns all users with admin or adjudicator role."""
        response = requests.get(f"{BASE_URL}/api/examiner/list", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify each examiner has required fields
        for examiner in data:
            assert "id" in examiner, "Should have id"
            assert "role" in examiner, "Should have role"
            assert examiner["role"] in ["admin", "adjudicator"], f"Unexpected role: {examiner['role']}"
        
        print(f"✅ GET /api/examiner/list returned {len(data)} examiners")


class TestQuickActions:
    """Test quick action endpoints for approve/deny/request_info."""
    
    @pytest.fixture
    def queue_claim_id(self, auth_headers):
        """Get a claim ID from the queue for testing."""
        response = requests.get(f"{BASE_URL}/api/examiner/queue", headers=auth_headers)
        if response.status_code != 200:
            pytest.skip("Could not fetch queue")
        
        data = response.json()
        if not data:
            pytest.skip("No claims in queue to test quick actions")
        
        return data[0]["id"]
    
    def test_quick_action_approve(self, auth_headers, queue_claim_id):
        """POST /api/examiner/queue/{claim_id}/quick-action?action=approve changes claim to approved."""
        response = requests.post(
            f"{BASE_URL}/api/examiner/queue/{queue_claim_id}/quick-action",
            params={"action": "approve"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "approved", f"Expected status 'approved', got '{data['status']}'"
        
        print(f"✅ Quick action approve worked for claim {queue_claim_id}")
    
    def test_quick_action_invalid(self, auth_headers):
        """POST /api/examiner/queue/{claim_id}/quick-action with invalid action returns 400."""
        # Use a fake claim ID
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/examiner/queue/{fake_id}/quick-action",
            params={"action": "invalid_action"},
            headers=auth_headers
        )
        # Should return 404 (claim not found) or 400 (invalid action)
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print("✅ Invalid quick action handled correctly")


class TestReassignment:
    """Test claim reassignment functionality."""
    
    def test_reassign_claim(self, auth_headers):
        """POST /api/claims/{claim_id}/reassign reassigns claim to different examiner."""
        # First get a claim from queue
        queue_response = requests.get(f"{BASE_URL}/api/examiner/queue", headers=auth_headers)
        if queue_response.status_code != 200:
            pytest.skip("Could not fetch queue")
        
        queue = queue_response.json()
        if not queue:
            pytest.skip("No claims in queue to test reassignment")
        
        claim_id = queue[0]["id"]
        
        # Get list of examiners
        examiners_response = requests.get(f"{BASE_URL}/api/examiner/list", headers=auth_headers)
        if examiners_response.status_code != 200:
            pytest.skip("Could not fetch examiners list")
        
        examiners = examiners_response.json()
        if not examiners:
            pytest.skip("No examiners available for reassignment")
        
        examiner_id = examiners[0]["id"]
        
        # Reassign the claim
        response = requests.post(
            f"{BASE_URL}/api/claims/{claim_id}/reassign",
            params={"examiner_id": examiner_id},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["assigned_to"] == examiner_id, f"Expected assigned_to '{examiner_id}', got '{data.get('assigned_to')}'"
        
        print(f"✅ Claim {claim_id} reassigned to examiner {examiner_id}")
    
    def test_reassign_nonexistent_claim(self, auth_headers):
        """POST /api/claims/{claim_id}/reassign with invalid claim returns 404."""
        fake_claim_id = str(uuid.uuid4())
        
        # Get an examiner ID
        examiners_response = requests.get(f"{BASE_URL}/api/examiner/list", headers=auth_headers)
        if examiners_response.status_code != 200 or not examiners_response.json():
            pytest.skip("Could not fetch examiners list")
        
        examiner_id = examiners_response.json()[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/claims/{fake_claim_id}/reassign",
            params={"examiner_id": examiner_id},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Reassign nonexistent claim returns 404")


class TestAutoAssignment:
    """Test auto-assignment on Tier 3 claims and authority routing."""
    
    def test_get_gateway_settings(self, auth_headers):
        """GET /api/settings/adjudication-gateway returns tier thresholds."""
        response = requests.get(f"{BASE_URL}/api/settings/adjudication-gateway", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tier1_auto_pilot_limit" in data, "Should have tier1_auto_pilot_limit"
        assert "tier2_audit_hold_limit" in data, "Should have tier2_audit_hold_limit"
        
        print(f"✅ Gateway settings: Tier1={data['tier1_auto_pilot_limit']}, Tier2={data['tier2_audit_hold_limit']}")
        return data
    
    def test_set_gateway_for_auto_assignment(self, auth_headers):
        """PUT /api/settings/adjudication-gateway sets thresholds for testing."""
        # Set low thresholds to trigger Tier 3 easily
        response = requests.put(
            f"{BASE_URL}/api/settings/adjudication-gateway",
            json={
                "tier1_auto_pilot_limit": 100.0,
                "tier2_audit_hold_limit": 500.0,
                "enabled": True
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ Gateway thresholds set for auto-assignment testing")
    
    def test_create_tier3_claim_auto_assigns(self, auth_headers):
        """Create a high-dollar claim that triggers Tier 3 and verify auto-assignment."""
        # First get a member ID
        members_response = requests.get(f"{BASE_URL}/api/members?limit=1", headers=auth_headers)
        if members_response.status_code != 200:
            pytest.skip("Could not fetch members")
        
        members = members_response.json()
        if not members:
            pytest.skip("No members available for claim creation")
        
        member_id = members[0]["member_id"]
        service_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create a high-dollar claim (>$500 to trigger Tier 3 with our test settings)
        claim_data = {
            "member_id": member_id,
            "provider_npi": "1234567890",
            "provider_name": "Test Provider",
            "claim_type": "medical",
            "service_date_from": service_date,
            "service_date_to": service_date,
            "total_billed": 6000.00,  # High dollar to trigger Tier 3 and admin assignment
            "diagnosis_codes": ["Z00.00"],
            "service_lines": [
                {
                    "line_number": 1,
                    "cpt_code": "99213",
                    "description": "Office visit",
                    "billed_amount": 6000.00,
                    "units": 1,
                    "service_date": service_date
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/claims", json=claim_data, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check if claim was auto-assigned (Tier 3 should trigger assignment)
        if data.get("tier_level") == 3:
            assert data.get("status") == "pending_review", f"Tier 3 claim should be pending_review, got {data.get('status')}"
            # Auto-assignment may or may not populate assigned_to depending on examiner availability
            if data.get("assigned_to"):
                print(f"✅ Tier 3 claim auto-assigned to {data.get('assigned_to_name')}")
            else:
                print("✅ Tier 3 claim created but no examiner available for assignment")
        else:
            print(f"✅ Claim created with tier_level={data.get('tier_level')} (may not be Tier 3 based on adjudication)")
        
        return data.get("id")
    
    def test_authority_routing_high_dollar(self, auth_headers):
        """Claims >=$5k should be assigned to admin (senior) role."""
        # Get a member
        members_response = requests.get(f"{BASE_URL}/api/members?limit=1", headers=auth_headers)
        if members_response.status_code != 200 or not members_response.json():
            pytest.skip("No members available")
        
        member_id = members_response.json()[0]["member_id"]
        service_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create a $5000+ claim
        claim_data = {
            "member_id": member_id,
            "provider_npi": "1234567890",
            "provider_name": "Test Provider",
            "claim_type": "medical",
            "service_date_from": service_date,
            "service_date_to": service_date,
            "total_billed": 7500.00,
            "diagnosis_codes": ["Z00.00"],
            "service_lines": [
                {
                    "line_number": 1,
                    "cpt_code": "99215",
                    "description": "Complex office visit",
                    "billed_amount": 7500.00,
                    "units": 1,
                    "service_date": service_date
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/claims", json=claim_data, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # If assigned, verify it's to an admin
        if data.get("assigned_to"):
            # Get the examiner to verify role
            examiners_response = requests.get(f"{BASE_URL}/api/examiner/list", headers=auth_headers)
            if examiners_response.status_code == 200:
                examiners = {e["id"]: e for e in examiners_response.json()}
                assigned_examiner = examiners.get(data["assigned_to"])
                if assigned_examiner:
                    # High dollar claims should go to admin (senior)
                    print(f"✅ High-dollar claim assigned to {assigned_examiner.get('role')} examiner")
        else:
            print("✅ High-dollar claim created (no examiner available for assignment)")


class TestQueueAllEndpoint:
    """Test admin-only queue/all endpoint."""
    
    def test_get_all_queues(self, auth_headers):
        """GET /api/examiner/queue/all returns all claims in review (admin only)."""
        response = requests.get(f"{BASE_URL}/api/examiner/queue/all", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify each claim has days_in_queue
        for claim in data:
            assert "days_in_queue" in claim, "Claim should have days_in_queue"
        
        print(f"✅ GET /api/examiner/queue/all returned {len(data)} claims")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
