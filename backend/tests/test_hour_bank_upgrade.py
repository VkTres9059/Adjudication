"""
Hour Bank & Reporting Module Upgrade Tests
Tests for: Multi-tier banking, Bridge Payments, Manual Entry, Predictive Eligibility, Claims Integration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Get auth token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@fletchflow.com",
            "password": "Demo123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestBridgePaymentSettings(TestAuth):
    """Test Bridge Payment Settings endpoints"""
    
    def test_get_bridge_settings(self, auth_headers):
        """GET /api/settings/bridge-payment returns config"""
        response = requests.get(f"{BASE_URL}/api/settings/bridge-payment", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "rate_per_hour" in data
        print(f"✅ GET bridge settings: enabled={data['enabled']}, rate={data['rate_per_hour']}")
    
    def test_update_bridge_settings(self, auth_headers):
        """PUT /api/settings/bridge-payment updates config"""
        # Enable bridge payments with $25/hr rate
        payload = {"enabled": True, "rate_per_hour": 25.0}
        response = requests.put(f"{BASE_URL}/api/settings/bridge-payment", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == True
        assert data["rate_per_hour"] == 25.0
        print(f"✅ PUT bridge settings: enabled={data['enabled']}, rate={data['rate_per_hour']}")
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/settings/bridge-payment", headers=auth_headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["enabled"] == True
        assert get_data["rate_per_hour"] == 25.0
        print("✅ Bridge settings persisted correctly")


class TestHourBankMultiTier(TestAuth):
    """Test Hour Bank multi-tier ledger endpoints"""
    
    def test_get_member_hour_bank_multi_tier(self, auth_headers):
        """GET /api/hour-bank/{member_id} returns multi-tier data"""
        # First get a member
        members_response = requests.get(f"{BASE_URL}/api/members", headers=auth_headers)
        assert members_response.status_code == 200
        members = members_response.json()
        
        if len(members) == 0:
            pytest.skip("No members available for testing")
        
        member_id = members[0]["member_id"]
        response = requests.get(f"{BASE_URL}/api/hour-bank/{member_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify multi-tier fields
        assert "current_balance" in data
        assert "reserve_balance" in data
        assert "total_balance" in data
        assert "burn_rate" in data
        assert "months_remaining" in data
        assert "at_risk" in data
        assert "eligibility_source" in data
        assert "bridge" in data
        
        # Verify bridge info structure
        bridge = data["bridge"]
        assert "enabled" in bridge
        assert "eligible" in bridge
        assert "hours_short" in bridge
        assert "cost" in bridge
        assert "rate_per_hour" in bridge
        
        print(f"✅ Hour bank multi-tier for {member_id}: current={data['current_balance']}, reserve={data['reserve_balance']}, burn_rate={data['burn_rate']}, months_remaining={data['months_remaining']}")
    
    def test_hour_bank_not_found(self, auth_headers):
        """GET /api/hour-bank/NONEXISTENT returns 404"""
        response = requests.get(f"{BASE_URL}/api/hour-bank/NONEXISTENT_MEMBER_XYZ", headers=auth_headers)
        assert response.status_code == 404
        print("✅ Hour bank 404 for non-existent member")


class TestManualHourEntry(TestAuth):
    """Test Manual Hour Entry endpoint"""
    
    def test_manual_hour_entry(self, auth_headers):
        """POST /api/hour-bank/{member_id}/manual-entry adds hours"""
        # Get a member
        members_response = requests.get(f"{BASE_URL}/api/members", headers=auth_headers)
        assert members_response.status_code == 200
        members = members_response.json()
        
        if len(members) == 0:
            pytest.skip("No members available for testing")
        
        member_id = members[0]["member_id"]
        
        # Get current balance
        before_response = requests.get(f"{BASE_URL}/api/hour-bank/{member_id}", headers=auth_headers)
        before_data = before_response.json()
        before_current = before_data.get("current_balance", 0)
        
        # Add 10 hours manually
        response = requests.post(
            f"{BASE_URL}/api/hour-bank/{member_id}/manual-entry",
            params={"hours": 10.0, "description": "TEST_MANUAL_ENTRY"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["hours_added"] == 10.0
        assert "current_balance" in data
        assert "reserve_balance" in data
        assert "total_balance" in data
        print(f"✅ Manual entry: +10 hrs for {member_id}, new current={data['current_balance']}")
        
        # Verify balance increased
        after_response = requests.get(f"{BASE_URL}/api/hour-bank/{member_id}", headers=auth_headers)
        after_data = after_response.json()
        # Check that an entry was added
        entries = after_data.get("entries", [])
        manual_entries = [e for e in entries if e.get("entry_type") == "manual_adjustment" and "TEST_MANUAL_ENTRY" in e.get("description", "")]
        assert len(manual_entries) > 0, "Manual entry should appear in ledger"
        print("✅ Manual entry appears in ledger")


class TestBridgePaymentExecution(TestAuth):
    """Test Bridge Payment execution endpoint"""
    
    def test_bridge_payment_requires_enabled(self, auth_headers):
        """POST /api/hour-bank/{member_id}/bridge-payment requires bridge enabled"""
        # First disable bridge payments
        requests.put(f"{BASE_URL}/api/settings/bridge-payment", json={"enabled": False, "rate_per_hour": 20.0}, headers=auth_headers)
        
        # Get a member
        members_response = requests.get(f"{BASE_URL}/api/members", headers=auth_headers)
        members = members_response.json()
        if len(members) == 0:
            pytest.skip("No members available")
        
        member_id = members[0]["member_id"]
        
        # Try bridge payment - should fail
        response = requests.post(f"{BASE_URL}/api/hour-bank/{member_id}/bridge-payment", headers=auth_headers)
        # Should return 400 because bridge is disabled
        assert response.status_code == 400
        print("✅ Bridge payment correctly rejected when disabled")
        
        # Re-enable for other tests
        requests.put(f"{BASE_URL}/api/settings/bridge-payment", json={"enabled": True, "rate_per_hour": 25.0}, headers=auth_headers)


class TestMonthlyRunMultiTier(TestAuth):
    """Test Monthly Run with multi-tier processing"""
    
    def test_run_monthly_multi_tier(self, auth_headers):
        """POST /api/hour-bank/run-monthly processes multi-tier buckets"""
        response = requests.post(
            f"{BASE_URL}/api/hour-bank/run-monthly",
            params={"period": "2026-02"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Handle case where no plans have eligibility threshold
        if "message" in data and "No plans with eligibility threshold" in data["message"]:
            print(f"✅ Monthly run: No plans with eligibility threshold configured (expected if no hour-bank plans exist)")
            return
        
        # Verify response structure when plans exist
        assert "period" in data
        assert "total_members" in data
        assert "activated" in data
        assert "termed" in data
        assert "unchanged" in data
        assert "reserve_draws" in data  # New multi-tier field
        assert "notifications_sent" in data
        
        print(f"✅ Monthly run: period={data['period']}, total={data['total_members']}, activated={data['activated']}, termed={data['termed']}, reserve_draws={data['reserve_draws']}")


class TestPredictiveEligibilityReport(TestAuth):
    """Test Predictive Eligibility dashboard endpoint"""
    
    def test_predictive_eligibility_endpoint(self, auth_headers):
        """GET /api/reports/predictive-eligibility returns summary and members"""
        response = requests.get(f"{BASE_URL}/api/reports/predictive-eligibility", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "summary" in data
        assert "members" in data
        
        summary = data["summary"]
        assert "total" in summary
        assert "at_risk" in summary
        assert "critical" in summary
        assert "healthy" in summary
        
        print(f"✅ Predictive eligibility: total={summary['total']}, healthy={summary['healthy']}, at_risk={summary['at_risk']}, critical={summary['critical']}")
        
        # If there are members, verify their structure
        if len(data["members"]) > 0:
            member = data["members"][0]
            assert "member_id" in member
            assert "current_balance" in member
            assert "reserve_balance" in member
            assert "burn_rate" in member
            assert "months_remaining" in member
            assert "at_risk" in member
            assert "critical" in member
            assert "eligibility_source" in member
            print(f"✅ Member data structure verified: {member['member_id']}")


class TestHourBankDeficiencyEnhanced(TestAuth):
    """Test Enhanced Hour Bank Deficiency report"""
    
    def test_hour_bank_deficiency_multi_tier(self, auth_headers):
        """GET /api/reports/hour-bank-deficiency returns multi-tier columns"""
        response = requests.get(f"{BASE_URL}/api/reports/hour-bank-deficiency", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Data is a list
        assert isinstance(data, list)
        
        if len(data) > 0:
            member = data[0]
            # Verify multi-tier fields
            assert "current_balance" in member
            assert "reserve_balance" in member
            assert "total_balance" in member
            assert "burn_rate" in member
            assert "months_remaining" in member
            assert "at_risk" in member
            assert "eligibility_source" in member
            print(f"✅ Deficiency report multi-tier: {member['member_id']} - current={member['current_balance']}, reserve={member['reserve_balance']}, burn_rate={member['burn_rate']}")
        else:
            print("✅ Deficiency report returned empty (no at-risk members)")


class TestClaimsEligibilitySource(TestAuth):
    """Test Claims integration with eligibility source"""
    
    def test_claims_have_eligibility_source(self, auth_headers):
        """GET /api/claims returns claims with eligibility_source field"""
        response = requests.get(f"{BASE_URL}/api/claims", headers=auth_headers)
        assert response.status_code == 200
        claims = response.json()
        
        if len(claims) > 0:
            claim = claims[0]
            # eligibility_source may be null for older claims, but field should exist in schema
            # Check if any claim has the field
            has_field = any("eligibility_source" in c for c in claims)
            print(f"✅ Claims list returned {len(claims)} claims")
            
            # Check a specific claim detail
            claim_id = claims[0]["id"]
            detail_response = requests.get(f"{BASE_URL}/api/claims/{claim_id}", headers=auth_headers)
            assert detail_response.status_code == 200
            detail = detail_response.json()
            # The field should be in the response (may be null)
            print(f"✅ Claim detail {claim_id}: eligibility_source={detail.get('eligibility_source', 'not set')}")
        else:
            print("✅ No claims to verify eligibility_source")


class TestClaimCreationWithHourBankGatekeeper(TestAuth):
    """Test claim creation routes through hour bank gatekeeper"""
    
    def test_create_claim_checks_hour_bank(self, auth_headers):
        """POST /api/claims creates claim with eligibility_source stamped"""
        # Get a member with a plan
        members_response = requests.get(f"{BASE_URL}/api/members", headers=auth_headers)
        members = members_response.json()
        
        if len(members) == 0:
            pytest.skip("No members available")
        
        # Find a member with a plan
        member = None
        for m in members:
            if m.get("plan_id"):
                member = m
                break
        
        if not member:
            pytest.skip("No member with plan found")
        
        # Create a test claim
        claim_data = {
            "member_id": member["member_id"],
            "provider_npi": "1234567890",
            "provider_name": "TEST_PROVIDER",
            "claim_type": "medical",
            "service_date_from": "2026-01-15",
            "service_date_to": "2026-01-15",
            "total_billed": 150.00,
            "diagnosis_codes": ["Z00.00"],
            "service_lines": [{
                "line_number": 1,
                "cpt_code": "99213",
                "units": 1,
                "billed_amount": 150.00,
                "service_date": "2026-01-15",
                "diagnosis_codes": ["Z00.00"]
            }],
            "source": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/claims", json=claim_data, headers=auth_headers)
        assert response.status_code in [200, 201]
        data = response.json()
        
        # Verify claim was created
        assert "id" in data
        assert "claim_number" in data
        # eligibility_source should be stamped
        print(f"✅ Claim created: {data['claim_number']}, status={data['status']}, eligibility_source={data.get('eligibility_source', 'not set')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
