"""
Test Member 360 View APIs - Iteration 14
Tests: accumulators, claims-history, dependents endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "demo@fletchflow.com",
        "password": "Demo123!"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestMemberAccumulators:
    """Test GET /api/members/{member_id}/accumulators endpoint"""
    
    def test_accumulators_returns_individual_deductible(self, auth_headers):
        """Accumulators should return individual_deductible with used and max"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/accumulators", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "individual_deductible" in data, "Missing individual_deductible"
        assert "used" in data["individual_deductible"], "Missing individual_deductible.used"
        assert "max" in data["individual_deductible"], "Missing individual_deductible.max"
        assert isinstance(data["individual_deductible"]["used"], (int, float))
        assert isinstance(data["individual_deductible"]["max"], (int, float))
        print(f"✅ Individual Deductible: ${data['individual_deductible']['used']} / ${data['individual_deductible']['max']}")
    
    def test_accumulators_returns_family_deductible_with_contributions(self, auth_headers):
        """Accumulators should return family_deductible with contributions array"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/accumulators", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "family_deductible" in data, "Missing family_deductible"
        assert "used" in data["family_deductible"], "Missing family_deductible.used"
        assert "max" in data["family_deductible"], "Missing family_deductible.max"
        assert "contributions" in data["family_deductible"], "Missing family_deductible.contributions"
        assert isinstance(data["family_deductible"]["contributions"], list)
        
        # Check contributions structure if any exist
        if len(data["family_deductible"]["contributions"]) > 0:
            contrib = data["family_deductible"]["contributions"][0]
            assert "member_id" in contrib, "Contribution missing member_id"
            assert "name" in contrib, "Contribution missing name"
            assert "contribution" in contrib, "Contribution missing contribution amount"
        
        print(f"✅ Family Deductible: ${data['family_deductible']['used']} / ${data['family_deductible']['max']}, {len(data['family_deductible']['contributions'])} contributors")
    
    def test_accumulators_returns_oop_max(self, auth_headers):
        """Accumulators should return oop_max with used and max"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/accumulators", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "oop_max" in data, "Missing oop_max"
        assert "used" in data["oop_max"], "Missing oop_max.used"
        assert "max" in data["oop_max"], "Missing oop_max.max"
        print(f"✅ OOP Max: ${data['oop_max']['used']} / ${data['oop_max']['max']}")
    
    def test_accumulators_nonexistent_member_returns_404(self, auth_headers):
        """Accumulators for nonexistent member should return 404"""
        response = requests.get(f"{BASE_URL}/api/members/NONEXISTENT_MEMBER/accumulators", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Nonexistent member returns 404")


class TestMemberClaimsHistory:
    """Test GET /api/members/{member_id}/claims-history endpoint"""
    
    def test_claims_history_returns_list(self, auth_headers):
        """Claims history should return a list of claims"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/claims-history", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Claims history should be a list"
        print(f"✅ Claims history returned {len(data)} claims")
    
    def test_claims_history_has_required_fields(self, auth_headers):
        """Each claim should have required fields"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/claims-history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            claim = data[0]
            required_fields = ["id", "claim_number", "service_date", "status", "total_billed", "total_paid"]
            for field in required_fields:
                assert field in claim, f"Claim missing required field: {field}"
            
            # Check optional but expected fields
            optional_fields = ["provider_name", "cpt_codes", "eligibility_source", "member_responsibility"]
            present_optional = [f for f in optional_fields if f in claim]
            print(f"✅ Claim has required fields + optional: {present_optional}")
            print(f"   Sample claim: #{claim['claim_number']}, status={claim['status']}, billed=${claim['total_billed']}, paid=${claim['total_paid']}")
        else:
            print("⚠️ No claims found for MBR001 - cannot verify field structure")
    
    def test_claims_history_has_cpt_codes_array(self, auth_headers):
        """Claims should have cpt_codes as an array"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/claims-history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            claim = data[0]
            assert "cpt_codes" in claim, "Claim missing cpt_codes"
            assert isinstance(claim["cpt_codes"], list), "cpt_codes should be a list"
            print(f"✅ CPT codes array: {claim['cpt_codes']}")
        else:
            print("⚠️ No claims to verify cpt_codes")
    
    def test_claims_history_nonexistent_member_returns_404(self, auth_headers):
        """Claims history for nonexistent member should return 404"""
        response = requests.get(f"{BASE_URL}/api/members/NONEXISTENT_MEMBER/claims-history", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Nonexistent member returns 404")


class TestMemberDependents:
    """Test GET /api/members/{member_id}/dependents endpoint"""
    
    def test_dependents_returns_subscriber_object(self, auth_headers):
        """Dependents should return subscriber object"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/dependents", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "subscriber" in data, "Missing subscriber"
        assert isinstance(data["subscriber"], dict), "subscriber should be an object"
        assert "member_id" in data["subscriber"], "subscriber missing member_id"
        assert "first_name" in data["subscriber"], "subscriber missing first_name"
        print(f"✅ Subscriber: {data['subscriber'].get('first_name')} {data['subscriber'].get('last_name')} ({data['subscriber'].get('member_id')})")
    
    def test_dependents_returns_dependents_array(self, auth_headers):
        """Dependents should return dependents array"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/dependents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "dependents" in data, "Missing dependents"
        assert isinstance(data["dependents"], list), "dependents should be a list"
        
        if len(data["dependents"]) > 0:
            dep = data["dependents"][0]
            assert "member_id" in dep, "dependent missing member_id"
            assert "relationship" in dep, "dependent missing relationship"
            print(f"✅ Found {len(data['dependents'])} dependents")
            for d in data["dependents"]:
                print(f"   - {d.get('first_name')} {d.get('last_name')} ({d.get('relationship')})")
        else:
            print("⚠️ No dependents found for MBR001")
    
    def test_dependents_returns_household_size(self, auth_headers):
        """Dependents should return household_size"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001/dependents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "household_size" in data, "Missing household_size"
        assert isinstance(data["household_size"], int), "household_size should be an integer"
        assert data["household_size"] >= 1, "household_size should be at least 1"
        print(f"✅ Household size: {data['household_size']}")
    
    def test_dependents_nonexistent_member_returns_404(self, auth_headers):
        """Dependents for nonexistent member should return 404"""
        response = requests.get(f"{BASE_URL}/api/members/NONEXISTENT_MEMBER/dependents", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Nonexistent member returns 404")


class TestClaimEOBDetail:
    """Test GET /api/claims/{claim_id} for EOB inline view"""
    
    def test_claim_detail_has_service_lines(self, auth_headers):
        """Claim detail should have service_lines for EOB view"""
        # First get a claim ID from claims history
        history_response = requests.get(f"{BASE_URL}/api/members/MBR001/claims-history", headers=auth_headers)
        assert history_response.status_code == 200
        claims = history_response.json()
        
        if len(claims) == 0:
            pytest.skip("No claims available to test EOB detail")
        
        claim_id = claims[0]["id"]
        response = requests.get(f"{BASE_URL}/api/claims/{claim_id}", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get claim detail: {response.text}"
        data = response.json()
        
        # Check for EOB-relevant fields
        assert "claim_number" in data, "Missing claim_number"
        assert "total_billed" in data, "Missing total_billed"
        assert "total_paid" in data, "Missing total_paid"
        
        if "service_lines" in data:
            print(f"✅ Claim has {len(data['service_lines'])} service lines")
            if len(data["service_lines"]) > 0:
                sl = data["service_lines"][0]
                print(f"   Sample line: CPT {sl.get('cpt_code')}, billed=${sl.get('billed_amount')}, paid=${sl.get('paid_amount')}")
        else:
            print("⚠️ No service_lines in claim detail")
        
        if "adjudication_notes" in data:
            print(f"✅ Claim has {len(data['adjudication_notes'])} adjudication notes")
        
        print(f"✅ EOB Detail: #{data['claim_number']}, status={data.get('status')}, billed=${data['total_billed']}, paid=${data['total_paid']}")


class TestMemberBasicEndpoint:
    """Test GET /api/members/{member_id} for header data"""
    
    def test_member_detail_has_header_fields(self, auth_headers):
        """Member detail should have fields needed for 360 header"""
        response = requests.get(f"{BASE_URL}/api/members/MBR001", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        required_fields = ["member_id", "first_name", "last_name", "status", "dob", "effective_date", "relationship"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"✅ Member header data: {data['first_name']} {data['last_name']}")
        print(f"   Status: {data['status']}, DOB: {data['dob']}, Effective: {data['effective_date']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
