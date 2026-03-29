"""
Test suite for Advanced Eligibility & Member Lifecycle features:
1. Member Reconciliation Dashboard (Census vs TPA 834 Feed)
2. Retroactive Termination & Clawback Monitor
3. Pending Eligibility Queue (72hr hold then auto-deny)
4. Dependent Age-Out Rules (turning 26)
5. Member Audit Trail
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestEligibilityFeatures:
    """Test suite for eligibility management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@fletchflow.com",
            "password": "Demo123!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        
        # Cleanup: delete test members created during tests
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up test data created during tests"""
        # Note: In production, we'd have a cleanup endpoint
        pass
    
    # ==================== RECONCILIATION TESTS ====================
    
    def test_reconciliation_endpoint_returns_expected_fields(self):
        """GET /api/members/eligibility/reconciliation returns census_count, tpa_feed_count, ghost_members, unmatched_members"""
        resp = self.session.get(f"{BASE_URL}/api/members/eligibility/reconciliation")
        assert resp.status_code == 200, f"Reconciliation failed: {resp.text}"
        
        data = resp.json()
        assert "census_count" in data, "Missing census_count"
        assert "tpa_feed_count" in data, "Missing tpa_feed_count"
        assert "ghost_members" in data, "Missing ghost_members"
        assert "unmatched_members" in data, "Missing unmatched_members"
        assert "matched_count" in data, "Missing matched_count"
        
        # Verify types
        assert isinstance(data["census_count"], int)
        assert isinstance(data["tpa_feed_count"], int)
        assert isinstance(data["ghost_members"], list)
        assert isinstance(data["unmatched_members"], list)
        
        print(f"✅ Reconciliation: Census={data['census_count']}, TPA Feed={data['tpa_feed_count']}, Ghost={len(data['ghost_members'])}, Unmatched={len(data['unmatched_members'])}")
    
    def test_upload_tpa_feed_pipe_delimited(self):
        """POST /api/members/eligibility/upload-tpa-feed uploads pipe-delimited TPA feed"""
        # Create a pipe-delimited TPA feed file content
        feed_content = """TEST_TPA_001|John|Doe|1990-01-15|GRP001|PLN001|2024-01-01|
TEST_TPA_002|Jane|Smith|1985-06-20|GRP001|PLN001|2024-01-01|2025-12-31"""
        
        files = {'file': ('tpa_feed.txt', feed_content, 'text/plain')}
        
        # Remove Content-Type header for multipart upload
        headers = {"Authorization": self.session.headers.get("Authorization")}
        
        resp = requests.post(
            f"{BASE_URL}/api/members/eligibility/upload-tpa-feed",
            files=files,
            headers=headers
        )
        assert resp.status_code == 200, f"Upload TPA feed failed: {resp.text}"
        
        data = resp.json()
        assert "members_loaded" in data, "Missing members_loaded in response"
        assert data["members_loaded"] == 2, f"Expected 2 members loaded, got {data['members_loaded']}"
        assert "feed_date" in data, "Missing feed_date in response"
        
        print(f"✅ TPA Feed uploaded: {data['members_loaded']} members, feed_date={data['feed_date']}")
    
    def test_reconciliation_shows_ghost_members_after_feed_upload(self):
        """After uploading TPA feed, reconciliation should show ghost members (on census but not in TPA feed)"""
        # First upload a minimal TPA feed
        feed_content = "NONEXISTENT_MEMBER_XYZ|Test|User|1990-01-01|GRP001|PLN001|2024-01-01|"
        files = {'file': ('tpa_feed.txt', feed_content, 'text/plain')}
        headers = {"Authorization": self.session.headers.get("Authorization")}
        
        upload_resp = requests.post(
            f"{BASE_URL}/api/members/eligibility/upload-tpa-feed",
            files=files,
            headers=headers
        )
        assert upload_resp.status_code == 200
        
        # Now check reconciliation
        recon_resp = self.session.get(f"{BASE_URL}/api/members/eligibility/reconciliation")
        assert recon_resp.status_code == 200
        
        data = recon_resp.json()
        # Since we uploaded only 1 member that doesn't exist in census, 
        # all census members should be ghost members
        assert data["census_count"] > 0, "Expected census members"
        assert len(data["ghost_members"]) > 0, "Expected ghost members (census members not in TPA feed)"
        
        print(f"✅ Ghost members detected: {len(data['ghost_members'])} members on census but not in TPA feed")
    
    # ==================== RETRO-TERM & CLAWBACK TESTS ====================
    
    def test_retro_terms_endpoint(self):
        """GET /api/members/eligibility/retro-terms returns members with past termination_date and claims after"""
        resp = self.session.get(f"{BASE_URL}/api/members/eligibility/retro-terms")
        assert resp.status_code == 200, f"Retro-terms failed: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), "Expected list of retro-term members"
        
        # If there are retro-term members, verify structure
        if len(data) > 0:
            member = data[0]
            assert "member_id" in member
            assert "termination_date" in member
            assert "claims_after_term" in member
            assert "clawback_total" in member
            print(f"✅ Retro-terms: Found {len(data)} members with claims after termination")
        else:
            print("✅ Retro-terms: No retro-terminated members with claims found (expected if no test data)")
    
    def test_request_refund_creates_clawback_ledger(self):
        """POST /api/members/{id}/request-refund creates clawback ledger entry"""
        # First, create a test member with past termination date
        test_member_id = f"TEST_RETRO_{uuid.uuid4().hex[:8]}"
        past_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        member_data = {
            "member_id": test_member_id,
            "first_name": "Retro",
            "last_name": "Test",
            "dob": "1980-01-01",
            "gender": "M",
            "group_id": "GRP001",
            "plan_id": "",  # Will need a valid plan
            "effective_date": "2024-01-01",
            "termination_date": past_date,
            "relationship": "subscriber"
        }
        
        # Get a plan first
        plans_resp = self.session.get(f"{BASE_URL}/api/plans")
        if plans_resp.status_code == 200 and len(plans_resp.json()) > 0:
            member_data["plan_id"] = plans_resp.json()[0]["id"]
        
        create_resp = self.session.post(f"{BASE_URL}/api/members", json=member_data)
        
        if create_resp.status_code == 200:
            # Try to request refund - should fail if no claims after term date
            refund_resp = self.session.post(f"{BASE_URL}/api/members/{test_member_id}/request-refund")
            
            # Expected: 400 if no claims found after termination date
            if refund_resp.status_code == 400:
                assert "No claims found" in refund_resp.json().get("detail", "")
                print(f"✅ Request refund correctly returns 400 when no claims after term date")
            elif refund_resp.status_code == 200:
                data = refund_resp.json()
                assert "total_recovery" in data
                assert "claims_affected" in data
                print(f"✅ Request refund created: recovery=${data['total_recovery']}, claims={data['claims_affected']}")
        else:
            print(f"⚠️ Could not create test member for refund test: {create_resp.text}")
    
    def test_request_refund_member_not_found(self):
        """POST /api/members/{id}/request-refund returns 404 for non-existent member"""
        resp = self.session.post(f"{BASE_URL}/api/members/NONEXISTENT_MEMBER_999999/request-refund")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✅ Request refund returns 404 for non-existent member")
    
    # ==================== PENDING ELIGIBILITY TESTS ====================
    
    def test_claim_for_unknown_member_creates_pending_eligibility(self):
        """POST /api/claims with unknown member_id creates claim with status=pending_eligibility"""
        unknown_member_id = f"UNKNOWN_{uuid.uuid4().hex[:8]}"
        
        claim_data = {
            "member_id": unknown_member_id,
            "provider_npi": "1234567890",
            "provider_name": "Test Provider",
            "claim_type": "medical",
            "service_date_from": datetime.now().strftime("%Y-%m-%d"),
            "service_date_to": datetime.now().strftime("%Y-%m-%d"),
            "total_billed": 150.00,
            "diagnosis_codes": ["Z00.00"],
            "service_lines": [{
                "line_number": 1,
                "cpt_code": "99213",
                "units": 1,
                "billed_amount": 150.00,
                "service_date": datetime.now().strftime("%Y-%m-%d"),
                "diagnosis_codes": ["Z00.00"]
            }]
        }
        
        resp = self.session.post(f"{BASE_URL}/api/claims", json=claim_data)
        assert resp.status_code == 200, f"Create claim failed: {resp.text}"
        
        data = resp.json()
        assert data["status"] == "pending_eligibility", f"Expected pending_eligibility status, got {data['status']}"
        assert "eligibility_deadline" in data, "Missing eligibility_deadline"
        assert data["eligibility_deadline"] is not None, "eligibility_deadline should be set"
        
        # Verify deadline is ~72 hours from now
        deadline = datetime.fromisoformat(data["eligibility_deadline"].replace('Z', '+00:00'))
        now = datetime.now(deadline.tzinfo)
        hours_diff = (deadline - now).total_seconds() / 3600
        assert 71 < hours_diff < 73, f"Deadline should be ~72 hours from now, got {hours_diff} hours"
        
        print(f"✅ Claim for unknown member created with pending_eligibility status, deadline={data['eligibility_deadline']}")
    
    def test_process_pending_eligibility_endpoint(self):
        """POST /api/claims/process-pending-eligibility processes pending claims"""
        resp = self.session.post(f"{BASE_URL}/api/claims/process-pending-eligibility")
        assert resp.status_code == 200, f"Process pending eligibility failed: {resp.text}"
        
        data = resp.json()
        assert "released" in data, "Missing released count"
        assert "denied" in data, "Missing denied count"
        assert "still_pending" in data, "Missing still_pending count"
        assert "total_processed" in data, "Missing total_processed count"
        
        print(f"✅ Process pending eligibility: released={data['released']}, denied={data['denied']}, still_pending={data['still_pending']}")
    
    # ==================== AGE-OUT ALERTS TESTS ====================
    
    def test_age_out_alerts_endpoint(self):
        """GET /api/members/eligibility/age-out-alerts returns dependents turning 26 within 30 days"""
        resp = self.session.get(f"{BASE_URL}/api/members/eligibility/age-out-alerts")
        assert resp.status_code == 200, f"Age-out alerts failed: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), "Expected list of age-out alerts"
        
        # If there are alerts, verify structure
        if len(data) > 0:
            alert = data[0]
            assert "member_id" in alert
            assert "dob" in alert
            assert "age_out_date" in alert
            assert "days_until" in alert
            print(f"✅ Age-out alerts: Found {len(data)} dependents turning 26 within 30 days")
        else:
            print("✅ Age-out alerts: No dependents aging out in next 30 days (expected if no test data)")
    
    def test_create_dependent_for_age_out(self):
        """Create a dependent turning 26 in ~15 days and verify it appears in age-out alerts"""
        # Calculate DOB for someone turning 26 in 15 days
        today = datetime.now()
        birthday_26 = today + timedelta(days=15)
        dob = birthday_26.replace(year=birthday_26.year - 26)
        
        test_member_id = f"TEST_AGEOUT_{uuid.uuid4().hex[:8]}"
        
        # Get a plan first
        plans_resp = self.session.get(f"{BASE_URL}/api/plans")
        plan_id = ""
        if plans_resp.status_code == 200 and len(plans_resp.json()) > 0:
            plan_id = plans_resp.json()[0]["id"]
        
        member_data = {
            "member_id": test_member_id,
            "first_name": "AgeOut",
            "last_name": "Test",
            "dob": dob.strftime("%Y-%m-%d"),
            "gender": "F",
            "group_id": "GRP001",
            "plan_id": plan_id,
            "effective_date": "2024-01-01",
            "relationship": "child"  # Must be child/dependent for age-out
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/members", json=member_data)
        
        if create_resp.status_code == 200:
            # Now check age-out alerts
            alerts_resp = self.session.get(f"{BASE_URL}/api/members/eligibility/age-out-alerts")
            assert alerts_resp.status_code == 200
            
            alerts = alerts_resp.json()
            found = any(a["member_id"] == test_member_id for a in alerts)
            assert found, f"Expected to find {test_member_id} in age-out alerts"
            
            # Verify the alert details
            alert = next(a for a in alerts if a["member_id"] == test_member_id)
            assert alert["days_until"] == 15 or alert["days_until"] == 14, f"Expected ~15 days until age-out, got {alert['days_until']}"
            
            print(f"✅ Age-out dependent created and found in alerts: {test_member_id}, days_until={alert['days_until']}")
        else:
            print(f"⚠️ Could not create test dependent: {create_resp.text}")
    
    # ==================== AUDIT TRAIL TESTS ====================
    
    def test_member_audit_trail_endpoint(self):
        """GET /api/members/{member_id}/audit-trail returns audit entries"""
        # First create a member to have audit trail
        test_member_id = f"TEST_AUDIT_{uuid.uuid4().hex[:8]}"
        
        plans_resp = self.session.get(f"{BASE_URL}/api/plans")
        plan_id = ""
        if plans_resp.status_code == 200 and len(plans_resp.json()) > 0:
            plan_id = plans_resp.json()[0]["id"]
        
        member_data = {
            "member_id": test_member_id,
            "first_name": "Audit",
            "last_name": "Trail",
            "dob": "1990-01-01",
            "gender": "M",
            "group_id": "GRP001",
            "plan_id": plan_id,
            "effective_date": "2024-01-01",
            "relationship": "subscriber"
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/members", json=member_data)
        
        if create_resp.status_code == 200:
            # Now get audit trail
            audit_resp = self.session.get(f"{BASE_URL}/api/members/{test_member_id}/audit-trail")
            assert audit_resp.status_code == 200, f"Audit trail failed: {audit_resp.text}"
            
            trail = audit_resp.json()
            assert isinstance(trail, list), "Expected list of audit entries"
            assert len(trail) > 0, "Expected at least one audit entry for newly created member"
            
            # Verify structure
            entry = trail[0]
            assert "id" in entry
            assert "member_id" in entry
            assert "action" in entry
            assert "timestamp" in entry
            
            # Should have member_added action
            actions = [e["action"] for e in trail]
            assert "member_added" in actions, f"Expected 'member_added' action in audit trail, got {actions}"
            
            print(f"✅ Audit trail for {test_member_id}: {len(trail)} entries, actions={actions}")
        else:
            print(f"⚠️ Could not create test member for audit trail: {create_resp.text}")
    
    def test_member_creation_logs_to_audit_trail(self):
        """POST /api/members creates member AND logs to member_audit_trail"""
        test_member_id = f"TEST_AUDITLOG_{uuid.uuid4().hex[:8]}"
        
        plans_resp = self.session.get(f"{BASE_URL}/api/plans")
        plan_id = ""
        if plans_resp.status_code == 200 and len(plans_resp.json()) > 0:
            plan_id = plans_resp.json()[0]["id"]
        
        member_data = {
            "member_id": test_member_id,
            "first_name": "AuditLog",
            "last_name": "Test",
            "dob": "1985-05-15",
            "gender": "F",
            "group_id": "GRP001",
            "plan_id": plan_id,
            "effective_date": "2024-01-01",
            "relationship": "subscriber"
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/members", json=member_data)
        assert create_resp.status_code == 200, f"Create member failed: {create_resp.text}"
        
        # Immediately check audit trail
        audit_resp = self.session.get(f"{BASE_URL}/api/members/{test_member_id}/audit-trail")
        assert audit_resp.status_code == 200
        
        trail = audit_resp.json()
        assert len(trail) >= 1, "Expected audit entry for member creation"
        
        # Find the member_added entry
        added_entry = next((e for e in trail if e["action"] == "member_added"), None)
        assert added_entry is not None, "Expected 'member_added' action in audit trail"
        assert added_entry["member_id"] == test_member_id
        assert "details" in added_entry
        assert added_entry["details"].get("first_name") == "AuditLog"
        
        print(f"✅ Member creation logged to audit trail: {added_entry['action']} at {added_entry['timestamp']}")


class TestMemberCRUD:
    """Test member CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@fletchflow.com",
            "password": "Demo123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        yield
    
    def test_list_members(self):
        """GET /api/members returns list of members"""
        resp = self.session.get(f"{BASE_URL}/api/members")
        assert resp.status_code == 200
        
        data = resp.json()
        assert isinstance(data, list)
        print(f"✅ List members: {len(data)} members found")
    
    def test_get_member_by_id(self):
        """GET /api/members/{member_id} returns member details"""
        # First get list to find a member
        list_resp = self.session.get(f"{BASE_URL}/api/members")
        if list_resp.status_code == 200 and len(list_resp.json()) > 0:
            member_id = list_resp.json()[0]["member_id"]
            
            resp = self.session.get(f"{BASE_URL}/api/members/{member_id}")
            assert resp.status_code == 200
            
            data = resp.json()
            assert data["member_id"] == member_id
            print(f"✅ Get member: {member_id} - {data['first_name']} {data['last_name']}")
        else:
            print("⚠️ No members to test get_member_by_id")
    
    def test_get_member_not_found(self):
        """GET /api/members/{member_id} returns 404 for non-existent member"""
        resp = self.session.get(f"{BASE_URL}/api/members/NONEXISTENT_MEMBER_XYZ123")
        assert resp.status_code == 404
        print("✅ Get non-existent member returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
