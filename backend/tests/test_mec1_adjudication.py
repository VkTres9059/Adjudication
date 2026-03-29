"""
MEC 1 Plan Auto-Adjudication Tests
Tests for:
- Preventive claims auto-approved at $0 member cost
- Non-preventive claims auto-denied with 'Not a Covered Benefit'
- Group pulse analytics with MEC financials
- Fixed Cost vs Claims report endpoint
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@fletchflow.com"
TEST_PASSWORD = "Demo123!"

# Known MEC group from seed data
ACME_GROUP_ID = "98a51eee-6fd7-4259-9b0d-ae3864ab8a5b"


class TestMEC1Adjudication:
    """Tests for MEC 1 Plan auto-adjudication logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("access_token")
        assert token, "No access_token in login response"
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get MEC 1 plan ID from Acme Manufacturing group
        group_response = self.session.get(f"{BASE_URL}/api/groups/{ACME_GROUP_ID}")
        assert group_response.status_code == 200, f"Failed to get group: {group_response.text}"
        
        group_data = group_response.json()
        self.mec_plan_id = None
        for plan in group_data.get("attached_plans", []):
            if plan.get("plan_template") == "mec_1":
                self.mec_plan_id = plan["id"]
                break
        
        assert self.mec_plan_id, "No MEC 1 plan found attached to Acme Manufacturing"
        
        # Create a test member linked to MEC 1 plan
        # DOB set to make member 35 years old (within 99385 age range 18-39)
        self.test_member_id = f"TEST_MEC_{uuid.uuid4().hex[:8]}"
        member_payload = {
            "member_id": self.test_member_id,
            "first_name": "Test",
            "last_name": "MEC Member",
            "dob": "1991-05-15",  # ~35 years old in 2026
            "gender": "M",
            "ssn_last4": "9999",
            "group_id": ACME_GROUP_ID,
            "plan_id": self.mec_plan_id,
            "effective_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "termination_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "relationship": "subscriber",
            "address": {
                "street": "123 Test St",
                "city": "Phoenix",
                "state": "AZ",
                "zip_code": "85001"
            }
        }
        
        member_response = self.session.post(f"{BASE_URL}/api/members", json=member_payload)
        assert member_response.status_code in [200, 201], f"Failed to create test member: {member_response.text}"
        
        yield
        
        # Cleanup - delete test member (if endpoint exists)
        # self.session.delete(f"{BASE_URL}/api/members/{self.test_member_id}")
    
    def test_preventive_claim_auto_approved_zero_cost(self):
        """
        Test: POST /api/claims with preventive CPT code (99385 with Z00.00) 
        on MEC 1 member should auto-adjudicate to 'approved' with $0 member responsibility
        """
        service_date = datetime.now().strftime("%Y-%m-%d")
        claim_payload = {
            "member_id": self.test_member_id,
            "provider_npi": "1234567890",
            "provider_name": "Test Wellness Clinic",
            "claim_type": "medical",
            "service_date_from": service_date,
            "service_date_to": service_date,
            "diagnosis_codes": ["Z00.00"],  # Wellness visit diagnosis
            "service_lines": [
                {
                    "line_number": 1,
                    "cpt_code": "99385",  # Preventive wellness visit (18-39 years)
                    "billed_amount": 250.00,
                    "units": 1,
                    "modifier": "",
                    "diagnosis_codes": ["Z00.00"],
                    "service_date": service_date
                }
            ],
            "total_billed": 250.00
        }
        
        response = self.session.post(f"{BASE_URL}/api/claims", json=claim_payload)
        assert response.status_code in [200, 201], f"Claim creation failed: {response.text}"
        
        claim_data = response.json()
        
        # Verify auto-adjudication to approved
        assert claim_data.get("status") == "approved", f"Expected 'approved' status, got: {claim_data.get('status')}"
        
        # Verify $0 member responsibility
        assert claim_data.get("member_responsibility", 0) == 0, f"Expected $0 member responsibility, got: {claim_data.get('member_responsibility')}"
        
        # Verify adjudication notes mention preventive
        notes = claim_data.get("adjudication_notes", [])
        has_preventive_note = any("PREVENTIVE" in str(note).upper() for note in notes)
        assert has_preventive_note, f"Expected preventive service note in adjudication_notes: {notes}"
        
        print(f"✅ Preventive claim auto-approved with $0 member cost. Claim ID: {claim_data.get('id')}")
    
    def test_non_preventive_claim_auto_denied(self):
        """
        Test: POST /api/claims with NON-preventive CPT code (99213 - office visit)
        on MEC 1 member should auto-adjudicate to 'denied' with 'Not a Covered Benefit'
        """
        service_date = datetime.now().strftime("%Y-%m-%d")
        claim_payload = {
            "member_id": self.test_member_id,
            "provider_npi": "1234567890",
            "provider_name": "Test Medical Office",
            "claim_type": "medical",
            "service_date_from": service_date,
            "service_date_to": service_date,
            "diagnosis_codes": ["J06.9"],  # Acute upper respiratory infection (non-preventive)
            "service_lines": [
                {
                    "line_number": 1,
                    "cpt_code": "99213",  # Office visit - established patient (non-preventive)
                    "billed_amount": 150.00,
                    "units": 1,
                    "modifier": "",
                    "diagnosis_codes": ["J06.9"],
                    "service_date": service_date
                }
            ],
            "total_billed": 150.00
        }
        
        response = self.session.post(f"{BASE_URL}/api/claims", json=claim_payload)
        assert response.status_code in [200, 201], f"Claim creation failed: {response.text}"
        
        claim_data = response.json()
        
        # Verify auto-adjudication to denied
        assert claim_data.get("status") == "denied", f"Expected 'denied' status, got: {claim_data.get('status')}"
        
        # Verify denial reason contains 'Not a Covered Benefit'
        notes = claim_data.get("adjudication_notes", [])
        notes_str = " ".join(str(n) for n in notes)
        assert "Not a Covered Benefit" in notes_str or "MEC 1" in notes_str, \
            f"Expected 'Not a Covered Benefit' in denial notes: {notes}"
        
        # Verify member responsibility equals billed amount
        assert claim_data.get("member_responsibility", 0) == 150.00, \
            f"Expected member responsibility of $150, got: {claim_data.get('member_responsibility')}"
        
        print(f"✅ Non-preventive claim auto-denied with 'Not a Covered Benefit'. Claim ID: {claim_data.get('id')}")
    
    def test_mec_group_pulse_analytics(self):
        """
        Test: GET /api/groups/{id}/pulse for MEC group should return:
        - is_mec=true
        - total_premium and mgu_fees in stop_loss section
        """
        response = self.session.get(f"{BASE_URL}/api/groups/{ACME_GROUP_ID}/pulse")
        assert response.status_code == 200, f"Pulse analytics failed: {response.text}"
        
        pulse_data = response.json()
        
        # Verify is_mec flag
        assert pulse_data.get("is_mec") == True, f"Expected is_mec=true, got: {pulse_data.get('is_mec')}"
        
        # Verify stop_loss section contains MEC financials
        stop_loss = pulse_data.get("stop_loss", {})
        assert "total_premium" in stop_loss, f"Expected total_premium in stop_loss: {stop_loss}"
        assert "mgu_fees" in stop_loss, f"Expected mgu_fees in stop_loss: {stop_loss}"
        assert "surplus_bucket" in stop_loss, f"Expected surplus_bucket in stop_loss: {stop_loss}"
        
        print(f"✅ MEC group pulse analytics returns is_mec=true with financials")
        print(f"   Total Premium: ${stop_loss.get('total_premium', 0):,.2f}")
        print(f"   MGU Fees: ${stop_loss.get('mgu_fees', 0):,.2f}")
        print(f"   Surplus: ${stop_loss.get('surplus_bucket', 0):,.2f}")
    
    def test_fixed_cost_vs_claims_report(self):
        """
        Test: GET /api/reports/fixed-cost-vs-claims should return array with:
        - is_mec flag
        - total_premium, mgu_fees, claims_paid, surplus, margin_pct
        """
        response = self.session.get(f"{BASE_URL}/api/reports/fixed-cost-vs-claims")
        assert response.status_code == 200, f"Fixed cost report failed: {response.text}"
        
        report_data = response.json()
        assert isinstance(report_data, list), f"Expected list response, got: {type(report_data)}"
        
        # Find Acme Manufacturing in report
        acme_row = None
        for row in report_data:
            if row.get("group_id") == ACME_GROUP_ID:
                acme_row = row
                break
        
        assert acme_row, f"Acme Manufacturing not found in report: {report_data}"
        
        # Verify required fields
        required_fields = ["is_mec", "total_premium", "mgu_fees", "claims_paid", "surplus", "margin_pct"]
        for field in required_fields:
            assert field in acme_row, f"Missing field '{field}' in report row: {acme_row}"
        
        # Verify is_mec flag for Acme
        assert acme_row.get("is_mec") == True, f"Expected is_mec=true for Acme, got: {acme_row.get('is_mec')}"
        
        print(f"✅ Fixed Cost vs Claims report returns correct data structure")
        print(f"   Acme Manufacturing: is_mec={acme_row.get('is_mec')}, margin={acme_row.get('margin_pct')}%")
    
    def test_group_detail_has_mec_plan(self):
        """
        Test: GET /api/groups/{id} returns attached MEC 1 plan with plan_template='mec_1'
        """
        response = self.session.get(f"{BASE_URL}/api/groups/{ACME_GROUP_ID}")
        assert response.status_code == 200, f"Group detail failed: {response.text}"
        
        group_data = response.json()
        attached_plans = group_data.get("attached_plans", [])
        
        mec_plan = None
        for plan in attached_plans:
            if plan.get("plan_template") == "mec_1":
                mec_plan = plan
                break
        
        assert mec_plan, f"No MEC 1 plan found in attached_plans: {attached_plans}"
        
        print(f"✅ Group detail shows MEC 1 plan: {mec_plan.get('name')}")


class TestGroupCreationWithFinancials:
    """Tests for group creation with total_premium and mgu_fees fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        self.created_group_ids = []
        yield
        
        # Cleanup created groups
        for group_id in self.created_group_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/groups/{group_id}")
            except:
                pass
    
    def test_create_group_with_financials(self):
        """
        Test: POST /api/groups with total_premium and mgu_fees fields
        """
        group_payload = {
            "name": f"TEST_MEC_Financials_{uuid.uuid4().hex[:6]}",
            "tax_id": f"99-{uuid.uuid4().hex[:7]}",
            "effective_date": datetime.now().strftime("%Y-%m-%d"),
            "contact_name": "Test Contact",
            "contact_email": "test@example.com",
            "employee_count": 50,
            "total_premium": 250000.00,
            "mgu_fees": 25000.00,
            "stop_loss": {
                "specific_deductible": 50000,
                "aggregate_attachment_point": 300000,
                "aggregate_factor": 125,
                "contract_period": "12_month"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/groups", json=group_payload)
        assert response.status_code in [200, 201], f"Group creation failed: {response.text}"
        
        group_data = response.json()
        self.created_group_ids.append(group_data.get("id"))
        
        # Verify financials are saved
        assert group_data.get("total_premium") == 250000.00, \
            f"Expected total_premium=250000, got: {group_data.get('total_premium')}"
        assert group_data.get("mgu_fees") == 25000.00, \
            f"Expected mgu_fees=25000, got: {group_data.get('mgu_fees')}"
        
        print(f"✅ Group created with financials: premium=${group_data.get('total_premium'):,.2f}, fees=${group_data.get('mgu_fees'):,.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
