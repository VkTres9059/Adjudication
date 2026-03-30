"""
Test Claims Adjudication Fields - P0 Bug Fix Verification
Tests that ClaimResponse model correctly returns all adjudication fields:
- data_tier, tier_label, plan_version, cob_applied, stop_loss_flag, 
- precert_penalty_applied, payment_ready, network_status, idr_case_number, idr_status
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@fletchflow.com"
TEST_PASSWORD = "Demo123!"


class TestClaimsAdjudicationFields:
    """Test that claims API returns all adjudication fields after P0 fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
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
        
    def test_list_claims_returns_adjudication_fields(self):
        """GET /api/claims - Verify list endpoint returns claims with adjudication fields"""
        response = self.session.get(f"{BASE_URL}/api/claims?limit=10")
        assert response.status_code == 200, f"Failed to list claims: {response.text}"
        
        claims = response.json()
        assert isinstance(claims, list), "Response should be a list"
        
        if len(claims) > 0:
            claim = claims[0]
            print(f"\n=== Sample Claim from List ===")
            print(f"Claim ID: {claim.get('id')}")
            print(f"Claim Number: {claim.get('claim_number')}")
            print(f"Status: {claim.get('status')}")
            
            # Check adjudication fields are present in response (can be None but must exist)
            adjudication_fields = [
                'data_tier', 'tier_label', 'plan_version', 'cob_applied',
                'stop_loss_flag', 'precert_penalty_applied', 'payment_ready',
                'network_status', 'idr_case_number', 'idr_status'
            ]
            
            for field in adjudication_fields:
                assert field in claim, f"Field '{field}' missing from claim response"
                print(f"  {field}: {claim.get(field)}")
            
            print(f"\n✓ All adjudication fields present in list response")
        else:
            print("No claims found - will create one to test")
            
    def test_get_single_claim_returns_adjudication_fields(self):
        """GET /api/claims/{claim_id} - Verify single claim retrieval includes adjudication fields"""
        # First get a claim ID
        list_response = self.session.get(f"{BASE_URL}/api/claims?limit=1")
        assert list_response.status_code == 200
        claims = list_response.json()
        
        if len(claims) == 0:
            pytest.skip("No claims available to test")
            
        claim_id = claims[0]['id']
        
        # Get single claim
        response = self.session.get(f"{BASE_URL}/api/claims/{claim_id}")
        assert response.status_code == 200, f"Failed to get claim: {response.text}"
        
        claim = response.json()
        print(f"\n=== Single Claim Details ===")
        print(f"Claim ID: {claim.get('id')}")
        print(f"Claim Number: {claim.get('claim_number')}")
        print(f"Status: {claim.get('status')}")
        
        # Verify all adjudication fields
        adjudication_fields = [
            'data_tier', 'tier_label', 'plan_version', 'cob_applied',
            'stop_loss_flag', 'precert_penalty_applied', 'payment_ready',
            'network_status', 'idr_case_number', 'idr_status'
        ]
        
        for field in adjudication_fields:
            assert field in claim, f"Field '{field}' missing from single claim response"
            print(f"  {field}: {claim.get(field)}")
            
        print(f"\n✓ All adjudication fields present in single claim response")
        
    def test_create_claim_returns_adjudication_fields(self):
        """POST /api/claims - Verify newly created claims return ALL adjudication fields"""
        # Get a member to use
        members_response = self.session.get(f"{BASE_URL}/api/members?limit=1")
        assert members_response.status_code == 200
        members = members_response.json()
        
        if len(members) == 0:
            pytest.skip("No members available to create claim")
            
        member_id = members[0]['member_id']
        
        # Create a new claim
        claim_data = {
            "member_id": member_id,
            "provider_npi": "1234567890",
            "provider_name": "Test Provider - Adjudication Fields Test",
            "claim_type": "medical",
            "service_date_from": "2025-01-15",
            "service_date_to": "2025-01-15",
            "total_billed": 150.00,
            "diagnosis_codes": ["Z00.00"],
            "service_lines": [
                {
                    "line_number": 1,
                    "cpt_code": "99213",
                    "units": 1,
                    "billed_amount": 150.00,
                    "service_date": "2025-01-15",
                    "diagnosis_codes": ["Z00.00"]
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/claims", json=claim_data)
        assert response.status_code == 200, f"Failed to create claim: {response.text}"
        
        claim = response.json()
        print(f"\n=== Newly Created Claim ===")
        print(f"Claim ID: {claim.get('id')}")
        print(f"Claim Number: {claim.get('claim_number')}")
        print(f"Status: {claim.get('status')}")
        print(f"Total Billed: ${claim.get('total_billed')}")
        print(f"Total Paid: ${claim.get('total_paid')}")
        
        # Verify all adjudication fields are present
        adjudication_fields = [
            'data_tier', 'tier_label', 'plan_version', 'cob_applied',
            'stop_loss_flag', 'precert_penalty_applied', 'payment_ready',
            'network_status', 'idr_case_number', 'idr_status'
        ]
        
        print(f"\n--- Adjudication Fields ---")
        for field in adjudication_fields:
            assert field in claim, f"Field '{field}' missing from created claim response"
            value = claim.get(field)
            print(f"  {field}: {value}")
            
        # Verify data_tier is populated for adjudicated claims
        if claim.get('status') in ['approved', 'denied']:
            assert claim.get('data_tier') is not None, "data_tier should be populated for adjudicated claims"
            assert claim.get('tier_label') is not None, "tier_label should be populated for adjudicated claims"
            print(f"\n✓ data_tier={claim.get('data_tier')}, tier_label={claim.get('tier_label')}")
            
        print(f"\n✓ All adjudication fields present in created claim response")
        
        # Store claim_id for cleanup
        self.created_claim_id = claim.get('id')
        
    def test_adjudicate_claim_returns_updated_fields(self):
        """POST /api/claims/{claim_id}/adjudicate - Verify adjudication action returns updated fields"""
        # Get a pending claim
        list_response = self.session.get(f"{BASE_URL}/api/claims?status=pending&limit=1")
        if list_response.status_code != 200 or len(list_response.json()) == 0:
            # Try pended claims
            list_response = self.session.get(f"{BASE_URL}/api/claims?status=pended&limit=1")
            
        if list_response.status_code != 200 or len(list_response.json()) == 0:
            # Create a claim to adjudicate
            members_response = self.session.get(f"{BASE_URL}/api/members?limit=1")
            if members_response.status_code != 200 or len(members_response.json()) == 0:
                pytest.skip("No members available to create claim for adjudication test")
                
            member_id = members_response.json()[0]['member_id']
            
            claim_data = {
                "member_id": member_id,
                "provider_npi": "1234567890",
                "provider_name": "Test Provider - Adjudication Test",
                "claim_type": "medical",
                "service_date_from": "2025-01-15",
                "service_date_to": "2025-01-15",
                "total_billed": 200.00,
                "diagnosis_codes": ["Z00.00"],
                "service_lines": [
                    {
                        "line_number": 1,
                        "cpt_code": "99214",
                        "units": 1,
                        "billed_amount": 200.00,
                        "service_date": "2025-01-15",
                        "diagnosis_codes": ["Z00.00"]
                    }
                ]
            }
            
            create_response = self.session.post(f"{BASE_URL}/api/claims", json=claim_data)
            assert create_response.status_code == 200, f"Failed to create claim: {create_response.text}"
            claim_id = create_response.json()['id']
        else:
            claim_id = list_response.json()[0]['id']
            
        # Adjudicate the claim
        adjudicate_response = self.session.post(
            f"{BASE_URL}/api/claims/{claim_id}/adjudicate",
            json={"action": "approve", "notes": "Test adjudication for P0 fix verification"}
        )
        assert adjudicate_response.status_code == 200, f"Failed to adjudicate claim: {adjudicate_response.text}"
        
        claim = adjudicate_response.json()
        print(f"\n=== Adjudicated Claim ===")
        print(f"Claim ID: {claim.get('id')}")
        print(f"Claim Number: {claim.get('claim_number')}")
        print(f"Status: {claim.get('status')}")
        
        # Verify all adjudication fields
        adjudication_fields = [
            'data_tier', 'tier_label', 'plan_version', 'cob_applied',
            'stop_loss_flag', 'precert_penalty_applied', 'payment_ready',
            'network_status', 'idr_case_number', 'idr_status'
        ]
        
        print(f"\n--- Adjudication Fields After Adjudicate Action ---")
        for field in adjudication_fields:
            assert field in claim, f"Field '{field}' missing from adjudicated claim response"
            value = claim.get(field)
            print(f"  {field}: {value}")
            
        print(f"\n✓ All adjudication fields present in adjudicated claim response")


class TestBatchClaimsAdjudicationFields:
    """Test batch claim processing returns adjudication fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
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
        
    def test_batch_claims_endpoint(self):
        """POST /api/claims/batch - Batch claim processing returns results"""
        # Get a member
        members_response = self.session.get(f"{BASE_URL}/api/members?limit=1")
        assert members_response.status_code == 200
        members = members_response.json()
        
        if len(members) == 0:
            pytest.skip("No members available for batch test")
            
        member_id = members[0]['member_id']
        
        # Create batch request
        batch_data = {
            "claims": [
                {
                    "member_id": member_id,
                    "provider_npi": "1234567890",
                    "provider_name": "Batch Test Provider 1",
                    "claim_type": "medical",
                    "service_date_from": "2025-01-15",
                    "service_date_to": "2025-01-15",
                    "total_billed": 100.00,
                    "diagnosis_codes": ["Z00.00"],
                    "service_lines": [
                        {
                            "line_number": 1,
                            "cpt_code": "99212",
                            "units": 1,
                            "billed_amount": 100.00,
                            "service_date": "2025-01-15",
                            "diagnosis_codes": ["Z00.00"]
                        }
                    ]
                }
            ],
            "auto_adjudicate": True,
            "locality_code": "00000"
        }
        
        response = self.session.post(f"{BASE_URL}/api/claims/batch", json=batch_data)
        assert response.status_code == 200, f"Batch processing failed: {response.text}"
        
        result = response.json()
        print(f"\n=== Batch Processing Result ===")
        print(f"Total: {result.get('total')}")
        print(f"Created: {result.get('created')}")
        print(f"Adjudicated: {result.get('adjudicated')}")
        print(f"Errors: {result.get('errors')}")
        print(f"Claim IDs: {result.get('claim_ids')}")
        
        assert result.get('created') >= 1, "At least one claim should be created"
        
        # Verify the created claim has adjudication fields
        if result.get('claim_ids') and len(result.get('claim_ids')) > 0:
            claim_id = result['claim_ids'][0]
            claim_response = self.session.get(f"{BASE_URL}/api/claims/{claim_id}")
            assert claim_response.status_code == 200
            
            claim = claim_response.json()
            adjudication_fields = [
                'data_tier', 'tier_label', 'plan_version', 'cob_applied',
                'stop_loss_flag', 'precert_penalty_applied', 'payment_ready',
                'network_status', 'idr_case_number', 'idr_status'
            ]
            
            print(f"\n--- Batch Claim Adjudication Fields ---")
            for field in adjudication_fields:
                assert field in claim, f"Field '{field}' missing from batch claim"
                print(f"  {field}: {claim.get(field)}")
                
            print(f"\n✓ Batch claim has all adjudication fields")


class TestAIAgentAndRxClassification:
    """Test AI Agent and Rx Classification endpoints still functional"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
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
        
    def test_ai_agent_chat(self):
        """POST /api/ai-agent/chat - AI Provider Agent still functional"""
        chat_data = {
            "message": "What is the status of claims for member MBR001?",
            "provider_tax_id": "123456789"
        }
        
        response = self.session.post(f"{BASE_URL}/api/ai-agent/chat", json=chat_data)
        assert response.status_code == 200, f"AI Agent chat failed: {response.text}"
        
        result = response.json()
        print(f"\n=== AI Agent Response ===")
        print(f"Session ID: {result.get('session_id')}")
        print(f"Response: {result.get('response', '')[:200]}...")
        
        assert 'response' in result, "AI Agent should return a response"
        assert 'session_id' in result, "AI Agent should return a session_id"
        
        print(f"\n✓ AI Agent chat endpoint functional")
        
    def test_rx_classification(self):
        """POST /api/plans/rx-rules/classify - Rx classification endpoint still functional"""
        # Test with a known drug code
        response = self.session.get(f"{BASE_URL}/api/plans/rx-rules/classify?hcpcs_code=J3490")
        assert response.status_code == 200, f"Rx classification failed: {response.text}"
        
        result = response.json()
        print(f"\n=== Rx Classification Result ===")
        print(f"HCPCS Code: J3490")
        print(f"Drug Name: {result.get('drug_name')}")
        print(f"Tier: {result.get('tier')}")
        print(f"Tier Label: {result.get('tier_label')}")
        print(f"Is GLP-1: {result.get('is_glp1')}")
        
        assert 'tier' in result, "Rx classification should return tier"
        
        print(f"\n✓ Rx classification endpoint functional")


class TestClaimStatusVariations:
    """Test adjudication fields for different claim statuses"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
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
        
    def test_approved_claims_have_adjudication_fields(self):
        """Verify approved claims have adjudication fields populated"""
        response = self.session.get(f"{BASE_URL}/api/claims?status=approved&limit=5")
        assert response.status_code == 200
        
        claims = response.json()
        print(f"\n=== Approved Claims Adjudication Fields ===")
        print(f"Found {len(claims)} approved claims")
        
        for claim in claims[:3]:  # Check first 3
            print(f"\nClaim {claim.get('claim_number')}:")
            print(f"  data_tier: {claim.get('data_tier')}")
            print(f"  tier_label: {claim.get('tier_label')}")
            print(f"  plan_version: {claim.get('plan_version')}")
            print(f"  network_status: {claim.get('network_status')}")
            print(f"  cob_applied: {claim.get('cob_applied')}")
            print(f"  stop_loss_flag: {claim.get('stop_loss_flag')}")
            print(f"  precert_penalty_applied: {claim.get('precert_penalty_applied')}")
            print(f"  payment_ready: {claim.get('payment_ready')}")
            
            # Verify fields exist
            assert 'data_tier' in claim
            assert 'tier_label' in claim
            assert 'plan_version' in claim
            
        print(f"\n✓ Approved claims have adjudication fields")
        
    def test_denied_claims_have_adjudication_fields(self):
        """Verify denied claims have adjudication fields"""
        response = self.session.get(f"{BASE_URL}/api/claims?status=denied&limit=5")
        assert response.status_code == 200
        
        claims = response.json()
        print(f"\n=== Denied Claims Adjudication Fields ===")
        print(f"Found {len(claims)} denied claims")
        
        for claim in claims[:3]:
            print(f"\nClaim {claim.get('claim_number')}:")
            print(f"  data_tier: {claim.get('data_tier')}")
            print(f"  tier_label: {claim.get('tier_label')}")
            
            assert 'data_tier' in claim
            assert 'tier_label' in claim
            
        print(f"\n✓ Denied claims have adjudication fields")
        
    def test_duplicate_claims_have_adjudication_fields(self):
        """Verify duplicate claims have adjudication fields"""
        response = self.session.get(f"{BASE_URL}/api/claims?status=duplicate&limit=5")
        assert response.status_code == 200
        
        claims = response.json()
        print(f"\n=== Duplicate Claims Adjudication Fields ===")
        print(f"Found {len(claims)} duplicate claims")
        
        for claim in claims[:3]:
            print(f"\nClaim {claim.get('claim_number')}:")
            print(f"  data_tier: {claim.get('data_tier')}")
            print(f"  tier_label: {claim.get('tier_label')}")
            
            assert 'data_tier' in claim
            assert 'tier_label' in claim
            
        print(f"\n✓ Duplicate claims have adjudication fields")
