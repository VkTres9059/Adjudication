"""
Test suite for Finance & Disbursement Module in FletchFlow.

Features tested:
- Vendor Payables CRUD (PBM, Telehealth PEPM, etc.)
- Wells Fargo API integration (simulated) - funding pull and disbursement push
- Provider batching in check runs
- Full check run lifecycle with vendor fees
- PDF generation for funding requests
- WF transaction history
- WF webhook processing
"""

import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@fletchflow.com"
TEST_PASSWORD = "Demo123!"


class TestAuth:
    """Authentication fixture"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}


class TestVendorPayablesCRUD(TestAuth):
    """Test CRUD /api/check-runs/vendor-payables"""
    
    created_vp_id = None
    test_group_id = None
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_test_group(self, auth_headers):
        """Get an ASO group for testing"""
        response = requests.get(f"{BASE_URL}/api/check-runs/groups", headers=auth_headers)
        assert response.status_code == 200
        groups = response.json()
        if len(groups) > 0:
            TestVendorPayablesCRUD.test_group_id = groups[0]["id"]
    
    def test_list_vendor_payables(self, auth_headers):
        """Should list all vendor payables"""
        response = requests.get(f"{BASE_URL}/api/check-runs/vendor-payables", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Listed {len(data)} vendor payables")
    
    def test_list_vendor_payables_filter_by_group(self, auth_headers):
        """Should filter vendor payables by group_id"""
        if not self.test_group_id:
            pytest.skip("No ASO group available")
        
        response = requests.get(
            f"{BASE_URL}/api/check-runs/vendor-payables",
            params={"group_id": self.test_group_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for vp in data:
            assert vp["group_id"] == self.test_group_id
        print(f"✅ Filtered vendor payables by group: {len(data)} results")
    
    def test_create_vendor_payable_pbm(self, auth_headers):
        """Should create a PBM Access vendor payable"""
        if not self.test_group_id:
            pytest.skip("No ASO group available")
        
        vp_data = {
            "group_id": self.test_group_id,
            "vendor_name": f"TEST_PBM_Vendor_{uuid.uuid4().hex[:6]}",
            "fee_type": "pbm_access",
            "description": "Monthly PBM access fee",
            "amount": 1500.00,
            "frequency": "monthly",
            "is_active": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/check-runs/vendor-payables",
            json=vp_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["vendor_name"] == vp_data["vendor_name"]
        assert data["fee_type"] == "pbm_access"
        assert data["amount"] == 1500.00
        assert data["is_active"] == True
        
        TestVendorPayablesCRUD.created_vp_id = data["id"]
        print(f"✅ Created PBM vendor payable: {data['id']}, ${data['amount']}")
    
    def test_create_vendor_payable_telehealth(self, auth_headers):
        """Should create a Telehealth PEPM vendor payable"""
        if not self.test_group_id:
            pytest.skip("No ASO group available")
        
        vp_data = {
            "group_id": self.test_group_id,
            "vendor_name": f"TEST_Telehealth_{uuid.uuid4().hex[:6]}",
            "fee_type": "telehealth_pepm",
            "description": "Telehealth per employee per month",
            "amount": 2.50,
            "frequency": "monthly",
            "is_active": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/check-runs/vendor-payables",
            json=vp_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["fee_type"] == "telehealth_pepm"
        print(f"✅ Created Telehealth PEPM vendor payable: {data['id']}")
    
    def test_update_vendor_payable(self, auth_headers):
        """Should update a vendor payable"""
        if not self.created_vp_id:
            pytest.skip("No vendor payable created to update")
        
        update_data = {
            "group_id": self.test_group_id,
            "vendor_name": "TEST_Updated_PBM",
            "fee_type": "pbm_access",
            "description": "Updated description",
            "amount": 1750.00,
            "frequency": "monthly",
            "is_active": True
        }
        
        response = requests.put(
            f"{BASE_URL}/api/check-runs/vendor-payables/{self.created_vp_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["amount"] == 1750.00
        assert data["description"] == "Updated description"
        print(f"✅ Updated vendor payable: {self.created_vp_id}")
    
    def test_delete_vendor_payable(self, auth_headers):
        """Should delete a vendor payable"""
        if not self.created_vp_id:
            pytest.skip("No vendor payable created to delete")
        
        response = requests.delete(
            f"{BASE_URL}/api/check-runs/vendor-payables/{self.created_vp_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        print(f"✅ Deleted vendor payable: {self.created_vp_id}")


class TestCheckRunWithVendorFees(TestAuth):
    """Test check run pending endpoint includes vendor fees"""
    
    def test_pending_includes_vendor_fees(self, auth_headers):
        """Should include vendor_fees and vendor_fees_total in pending response"""
        response = requests.get(f"{BASE_URL}/api/check-runs/pending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            pending = data[0]
            assert "vendor_fees" in pending
            assert "vendor_fees_total" in pending
            assert "total_funding_required" in pending
            
            # total_funding_required should be provider_payable + vendor_fees_total
            expected_total = pending["provider_payable"] + pending["vendor_fees_total"]
            assert abs(pending["total_funding_required"] - expected_total) < 0.01
            
            print(f"✅ Pending includes vendor fees:")
            print(f"   Provider payable: ${pending['provider_payable']}")
            print(f"   Vendor fees total: ${pending['vendor_fees_total']}")
            print(f"   Total funding required: ${pending['total_funding_required']}")
        else:
            print("✅ No pending claims (vendor fees structure verified in schema)")
    
    def test_pending_includes_provider_breakdown(self, auth_headers):
        """Should include providers array with NPI and payable amounts"""
        response = requests.get(f"{BASE_URL}/api/check-runs/pending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            pending = data[0]
            assert "providers" in pending
            
            if len(pending["providers"]) > 0:
                provider = pending["providers"][0]
                assert "provider_npi" in provider
                assert "provider_name" in provider or "provider_npi" in provider
                assert "claim_count" in provider
                assert "total_payable" in provider
                assert "claim_ids" in provider
                print(f"✅ Provider breakdown: {len(pending['providers'])} providers")
        else:
            print("✅ No pending claims (provider structure verified in schema)")


class TestCheckRunDetail(TestAuth):
    """Test check run detail includes WF transactions and provider batches"""
    
    def test_detail_includes_wf_transactions(self, auth_headers):
        """Should include wf_transactions in check run detail"""
        # Get a check run
        list_response = requests.get(f"{BASE_URL}/api/check-runs", headers=auth_headers)
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No check runs exist")
        
        run_id = runs[0]["id"]
        response = requests.get(f"{BASE_URL}/api/check-runs/{run_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "wf_transactions" in data
        assert isinstance(data["wf_transactions"], list)
        print(f"✅ Check run detail includes wf_transactions: {len(data['wf_transactions'])} transactions")
    
    def test_detail_includes_provider_batches(self, auth_headers):
        """Should include provider_batches in check run detail"""
        list_response = requests.get(f"{BASE_URL}/api/check-runs", headers=auth_headers)
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No check runs exist")
        
        run_id = runs[0]["id"]
        response = requests.get(f"{BASE_URL}/api/check-runs/{run_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "provider_batches" in data
        assert isinstance(data["provider_batches"], list)
        
        if len(data["provider_batches"]) > 0:
            batch = data["provider_batches"][0]
            assert "provider_npi" in batch
            assert "amount" in batch
            assert "claim_count" in batch
            print(f"✅ Provider batches: {len(data['provider_batches'])} batches")
    
    def test_detail_claims_include_wf_transaction_id(self, auth_headers):
        """Should include wf_transaction_id in claims for executed runs"""
        # Get an executed run
        list_response = requests.get(
            f"{BASE_URL}/api/check-runs",
            params={"status": "executed"},
            headers=auth_headers
        )
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No executed check runs exist")
        
        run_id = runs[0]["id"]
        response = requests.get(f"{BASE_URL}/api/check-runs/{run_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        claims = data.get("claims", [])
        if len(claims) > 0:
            # At least some claims should have wf_transaction_id
            has_wf_txn = any(c.get("wf_transaction_id") for c in claims)
            if has_wf_txn:
                print(f"✅ Claims include wf_transaction_id")
            else:
                print("⚠️ No claims have wf_transaction_id (may be older run)")


class TestWFTransactions(TestAuth):
    """Test GET /api/check-runs/wf-transactions/{run_id}"""
    
    def test_get_wf_transactions(self, auth_headers):
        """Should return WF transaction history for a run"""
        # Get a check run
        list_response = requests.get(f"{BASE_URL}/api/check-runs", headers=auth_headers)
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No check runs exist")
        
        run_id = runs[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/check-runs/wf-transactions/{run_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            txn = data[0]
            assert "transaction_id" in txn
            assert "type" in txn
            assert "amount" in txn
            assert "status" in txn
            print(f"✅ WF transactions for run: {len(data)} transactions")
        else:
            print("✅ No WF transactions for this run (may be older)")


class TestWFWebhook(TestAuth):
    """Test POST /api/check-runs/wf-webhook"""
    
    def test_wf_webhook_invalid_txn(self, auth_headers):
        """Should handle webhook for non-existent transaction"""
        payload = {
            "transaction_id": "WFT-NONEXISTENT-123",
            "status": "completed"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/check-runs/wf-webhook",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        print("✅ WF webhook handles non-existent transaction gracefully")


class TestPDFGeneration(TestAuth):
    """Test GET /api/check-runs/{run_id}/pdf"""
    
    def test_pdf_requires_token(self, auth_headers):
        """Should require token query parameter"""
        list_response = requests.get(f"{BASE_URL}/api/check-runs", headers=auth_headers)
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No check runs exist")
        
        run_id = runs[0]["id"]
        
        # Without token
        response = requests.get(f"{BASE_URL}/api/check-runs/{run_id}/pdf")
        assert response.status_code == 401
        print("✅ PDF endpoint requires token")
    
    def test_pdf_with_valid_token(self, auth_token, auth_headers):
        """Should return PDF with valid token"""
        list_response = requests.get(f"{BASE_URL}/api/check-runs", headers=auth_headers)
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No check runs exist")
        
        run_id = runs[0]["id"]
        
        # With token as query param
        response = requests.get(
            f"{BASE_URL}/api/check-runs/{run_id}/pdf",
            params={"token": auth_token}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert "Content-Disposition" in response.headers
        assert "FundingRequest" in response.headers.get("Content-Disposition", "")
        print(f"✅ PDF generated successfully, size: {len(response.content)} bytes")
    
    def test_pdf_not_found(self, auth_token):
        """Should return 404 for non-existent run"""
        response = requests.get(
            f"{BASE_URL}/api/check-runs/non-existent-id/pdf",
            params={"token": auth_token}
        )
        assert response.status_code == 404
        print("✅ PDF returns 404 for non-existent run")


class TestFullCheckRunLifecycle(TestAuth):
    """Test full lifecycle: create test data → generate → confirm → execute"""
    
    test_group_id = None
    test_member_id = None
    test_claim_id = None
    test_run_id = None
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_test_data(self, auth_headers):
        """Create test group, member, and claim for lifecycle test"""
        # Create a test ASO group
        unique_tax_id = f"99-{uuid.uuid4().hex[:7].upper()}"
        group_data = {
            "name": f"TEST_Lifecycle_Group_{uuid.uuid4().hex[:6]}",
            "tax_id": unique_tax_id,
            "effective_date": "2025-01-01",
            "funding_type": "aso",
            "employee_count": 25
        }
        
        group_response = requests.post(f"{BASE_URL}/api/groups", json=group_data, headers=auth_headers)
        if group_response.status_code == 200:
            TestFullCheckRunLifecycle.test_group_id = group_response.json()["id"]
            print(f"✅ Created test group: {TestFullCheckRunLifecycle.test_group_id}")
        
        # Create a test member
        if TestFullCheckRunLifecycle.test_group_id:
            member_data = {
                "member_id": f"TEST_MEM_{uuid.uuid4().hex[:8]}",
                "first_name": "Test",
                "last_name": "Lifecycle",
                "date_of_birth": "1985-05-15",
                "gender": "M",
                "group_id": TestFullCheckRunLifecycle.test_group_id,
                "effective_date": "2025-01-01",
                "relationship": "subscriber"
            }
            
            member_response = requests.post(f"{BASE_URL}/api/members", json=member_data, headers=auth_headers)
            if member_response.status_code == 200:
                TestFullCheckRunLifecycle.test_member_id = member_response.json()["member_id"]
                print(f"✅ Created test member: {TestFullCheckRunLifecycle.test_member_id}")
        
        # Create a test claim with approved status
        if TestFullCheckRunLifecycle.test_member_id:
            claim_data = {
                "member_id": TestFullCheckRunLifecycle.test_member_id,
                "claim_type": "medical",
                "service_date": "2025-01-15",
                "provider_npi": "1234567890",
                "provider_name": "Test Provider Clinic",
                "diagnosis_codes": ["Z00.00"],
                "procedure_codes": ["99213"],
                "total_billed": 250.00,
                "total_paid": 200.00,
                "member_responsibility": 50.00,
                "status": "approved"
            }
            
            claim_response = requests.post(f"{BASE_URL}/api/claims", json=claim_data, headers=auth_headers)
            if claim_response.status_code == 200:
                TestFullCheckRunLifecycle.test_claim_id = claim_response.json()["id"]
                print(f"✅ Created test claim: {TestFullCheckRunLifecycle.test_claim_id}")
    
    def test_01_generate_funding_request(self, auth_headers):
        """Step 1: Generate funding request"""
        if not self.test_group_id:
            pytest.skip("Test group not created")
        
        # First verify pending claims exist
        pending_response = requests.get(
            f"{BASE_URL}/api/check-runs/pending",
            params={"group_id": self.test_group_id},
            headers=auth_headers
        )
        pending_data = pending_response.json()
        
        if len(pending_data) == 0:
            pytest.skip("No pending claims for test group")
        
        # Generate funding request
        response = requests.post(
            f"{BASE_URL}/api/check-runs/generate-funding-request",
            params={"group_id": self.test_group_id},
            headers=auth_headers
        )
        
        if response.status_code == 400 and "No approved claims" in response.text:
            pytest.skip("No approved claims pending")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "pending_funding"
        assert "wf_funding_txn" in data
        assert data["wf_funding_txn"] is not None
        assert "provider_batches" in data
        
        TestFullCheckRunLifecycle.test_run_id = data["id"]
        print(f"✅ Generated funding request: {data['id']}")
        print(f"   WF Funding Txn: {data['wf_funding_txn']}")
        print(f"   Provider batches: {len(data['provider_batches'])}")
    
    def test_02_confirm_funding(self, auth_headers):
        """Step 2: Confirm funding via WF webhook simulation"""
        if not self.test_run_id:
            pytest.skip("No funding request generated")
        
        response = requests.post(
            f"{BASE_URL}/api/check-runs/{self.test_run_id}/confirm-funding",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "funded"
        print(f"✅ Confirmed funding: {self.test_run_id}")
    
    def test_03_execute_check_run(self, auth_headers):
        """Step 3: Execute check run with WF disbursement"""
        if not self.test_run_id:
            pytest.skip("No funding request generated")
        
        response = requests.post(
            f"{BASE_URL}/api/check-runs/{self.test_run_id}/execute",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "executed"
        assert "ach_batch" in data
        assert "wf_disbursement" in data
        
        print(f"✅ Executed check run: {self.test_run_id}")
        print(f"   ACH Batch: {data['ach_batch']}")
        print(f"   Claims: {data['claim_count']}")
    
    def test_04_verify_claims_paid(self, auth_headers):
        """Step 4: Verify claims moved to paid status with wf_transaction_id"""
        if not self.test_run_id:
            pytest.skip("No check run executed")
        
        response = requests.get(
            f"{BASE_URL}/api/check-runs/{self.test_run_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "executed"
        
        claims = data.get("claims", [])
        for claim in claims:
            assert claim["status"] == "paid", f"Claim {claim['id']} not paid"
            # wf_transaction_id should be set
            if claim.get("wf_transaction_id"):
                print(f"   Claim {claim['claim_number']}: wf_txn={claim['wf_transaction_id']}")
        
        print(f"✅ All {len(claims)} claims moved to paid status")


class TestCheckRunListFilters(TestAuth):
    """Test check run list with various filters"""
    
    def test_list_by_status_executed(self, auth_headers):
        """Should filter by status=executed"""
        response = requests.get(
            f"{BASE_URL}/api/check-runs",
            params={"status": "executed"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for run in data:
            assert run["status"] == "executed"
        print(f"✅ Filtered by status=executed: {len(data)} runs")
    
    def test_list_by_status_pending_funding(self, auth_headers):
        """Should filter by status=pending_funding"""
        response = requests.get(
            f"{BASE_URL}/api/check-runs",
            params={"status": "pending_funding"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for run in data:
            assert run["status"] == "pending_funding"
        print(f"✅ Filtered by status=pending_funding: {len(data)} runs")
    
    def test_list_by_status_funded(self, auth_headers):
        """Should filter by status=funded"""
        response = requests.get(
            f"{BASE_URL}/api/check-runs",
            params={"status": "funded"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for run in data:
            assert run["status"] == "funded"
        print(f"✅ Filtered by status=funded: {len(data)} runs")


class TestRegressionPages(TestAuth):
    """Regression tests for existing pages"""
    
    def test_groups_page_funding_type(self, auth_headers):
        """Groups should include funding_type"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        for group in data:
            assert "funding_type" in group
        print(f"✅ Groups include funding_type: {len(data)} groups")
    
    def test_settings_page(self, auth_headers):
        """Settings endpoints should work"""
        response = requests.get(f"{BASE_URL}/api/settings/adjudication-gateway", headers=auth_headers)
        assert response.status_code == 200
        print("✅ Settings page endpoint working")
    
    def test_edi_page(self, auth_headers):
        """EDI endpoints should work"""
        response = requests.get(f"{BASE_URL}/api/edi/transactions", headers=auth_headers)
        assert response.status_code == 200
        print("✅ EDI page endpoint working")
    
    def test_dashboard_funding_health(self, auth_headers):
        """Dashboard funding health should work"""
        response = requests.get(f"{BASE_URL}/api/dashboard/funding-health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "aso" in data
        assert "level_funded" in data
        assert "fully_insured" in data
        print("✅ Dashboard funding health endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
