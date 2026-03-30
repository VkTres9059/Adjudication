"""
Test suite for ASO Check Run Module, Level Funded Claims Bucket, Toggleable Funding Types,
and Funding Health Dashboard features.

Features tested:
- Check Run endpoints (groups, pending, generate-funding-request, confirm-funding, execute, list, get)
- Groups with funding_type field (aso, level_funded, fully_insured)
- Level Funded reserve fund tracking
- Dashboard funding health widget
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@fletchflow.com"
TEST_PASSWORD = "Demo123!"

# Known test data from context
ACME_GROUP_ID = "98a51eee-6fd7-4259-9b0d-ae3864ab8a5b"  # ASO group
BETA_GROUP_ID = "f4881478-6450-4d77-ac18-340385dfecbf"  # Level Funded group


class TestAuth:
    """Authentication tests"""
    
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


class TestCheckRunGroups(TestAuth):
    """Test GET /api/check-runs/groups — List ASO groups"""
    
    def test_list_aso_groups(self, auth_headers):
        """Should return list of ASO groups eligible for check runs"""
        response = requests.get(f"{BASE_URL}/api/check-runs/groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify structure of returned groups
        if len(data) > 0:
            group = data[0]
            assert "id" in group
            assert "name" in group
            assert "funding_type" in group
            assert group["funding_type"] == "aso"
            print(f"✅ Found {len(data)} ASO groups")
    
    def test_aso_groups_only_returns_aso_type(self, auth_headers):
        """Should only return groups with funding_type=aso"""
        response = requests.get(f"{BASE_URL}/api/check-runs/groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        for group in data:
            assert group.get("funding_type") == "aso", f"Non-ASO group returned: {group}"
        print(f"✅ All {len(data)} groups have funding_type=aso")


class TestCheckRunPending(TestAuth):
    """Test GET /api/check-runs/pending — Aggregate approved claims per ASO group"""
    
    def test_get_pending_all_groups(self, auth_headers):
        """Should return pending claims aggregated by ASO group"""
        response = requests.get(f"{BASE_URL}/api/check-runs/pending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            pending = data[0]
            assert "group_id" in pending
            assert "group_name" in pending
            assert "claim_count" in pending
            assert "total_billed" in pending
            assert "total_paid" in pending
            assert "provider_payable" in pending
            assert "claim_ids" in pending
            assert "members" in pending
            print(f"✅ Found {len(data)} groups with pending claims")
    
    def test_get_pending_with_group_filter(self, auth_headers):
        """Should filter pending claims by group_id"""
        response = requests.get(
            f"{BASE_URL}/api/check-runs/pending",
            params={"group_id": ACME_GROUP_ID},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # If there are results, they should all be for the specified group
        for pending in data:
            assert pending["group_id"] == ACME_GROUP_ID
        print(f"✅ Filtered pending claims for Acme Manufacturing: {len(data)} results")


class TestCheckRunLifecycle(TestAuth):
    """Test full check run lifecycle: generate → confirm → execute"""
    
    def test_generate_funding_request(self, auth_headers):
        """Should generate a funding request for an ASO group"""
        # First check if there are pending claims for Acme
        pending_response = requests.get(
            f"{BASE_URL}/api/check-runs/pending",
            params={"group_id": ACME_GROUP_ID},
            headers=auth_headers
        )
        pending_data = pending_response.json()
        
        if len(pending_data) == 0:
            pytest.skip("No pending claims for Acme Manufacturing to generate funding request")
        
        # Generate funding request
        response = requests.post(
            f"{BASE_URL}/api/check-runs/generate-funding-request",
            params={"group_id": ACME_GROUP_ID},
            headers=auth_headers
        )
        
        if response.status_code == 400 and "No approved claims" in response.text:
            pytest.skip("No approved claims pending for this group")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["group_id"] == ACME_GROUP_ID
        assert data["status"] == "pending_funding"
        assert "claim_count" in data
        assert "total_payable" in data
        assert "claim_ids" in data
        
        print(f"✅ Generated funding request: {data['id']}, {data['claim_count']} claims, ${data['total_payable']}")
        return data["id"]
    
    def test_generate_funding_request_invalid_group(self, auth_headers):
        """Should return 404 for non-existent group"""
        response = requests.post(
            f"{BASE_URL}/api/check-runs/generate-funding-request",
            params={"group_id": "non-existent-group-id"},
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✅ Returns 404 for non-existent group")


class TestCheckRunList(TestAuth):
    """Test GET /api/check-runs — List all check runs"""
    
    def test_list_all_check_runs(self, auth_headers):
        """Should return list of all check runs"""
        response = requests.get(f"{BASE_URL}/api/check-runs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            run = data[0]
            assert "id" in run
            assert "group_id" in run
            assert "group_name" in run
            assert "status" in run
            assert "claim_count" in run
            assert "total_payable" in run
            assert "created_at" in run
        print(f"✅ Found {len(data)} check runs")
    
    def test_list_check_runs_filter_by_group(self, auth_headers):
        """Should filter check runs by group_id"""
        response = requests.get(
            f"{BASE_URL}/api/check-runs",
            params={"group_id": ACME_GROUP_ID},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for run in data:
            assert run["group_id"] == ACME_GROUP_ID
        print(f"✅ Filtered check runs by group: {len(data)} results")
    
    def test_list_check_runs_filter_by_status(self, auth_headers):
        """Should filter check runs by status"""
        response = requests.get(
            f"{BASE_URL}/api/check-runs",
            params={"status": "pending_funding"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for run in data:
            assert run["status"] == "pending_funding"
        print(f"✅ Filtered check runs by status: {len(data)} pending_funding")


class TestCheckRunDetail(TestAuth):
    """Test GET /api/check-runs/{run_id} — Get check run detail"""
    
    def test_get_check_run_detail(self, auth_headers):
        """Should return check run detail with claims list"""
        # First get a check run ID
        list_response = requests.get(f"{BASE_URL}/api/check-runs", headers=auth_headers)
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No check runs exist to test detail endpoint")
        
        run_id = runs[0]["id"]
        response = requests.get(f"{BASE_URL}/api/check-runs/{run_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == run_id
        assert "claims" in data
        assert isinstance(data["claims"], list)
        print(f"✅ Got check run detail: {run_id}, {len(data['claims'])} claims")
    
    def test_get_check_run_not_found(self, auth_headers):
        """Should return 404 for non-existent check run"""
        response = requests.get(
            f"{BASE_URL}/api/check-runs/non-existent-run-id",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✅ Returns 404 for non-existent check run")


class TestGroupsFundingType(TestAuth):
    """Test POST /api/groups with funding_type field"""
    
    def test_create_group_with_aso_funding(self, auth_headers):
        """Should create group with funding_type=aso"""
        unique_tax_id = f"99-{uuid.uuid4().hex[:7].upper()}"
        group_data = {
            "name": f"TEST_ASO_Group_{uuid.uuid4().hex[:6]}",
            "tax_id": unique_tax_id,
            "effective_date": "2025-01-01",
            "funding_type": "aso",
            "employee_count": 50
        }
        
        response = requests.post(f"{BASE_URL}/api/groups", json=group_data, headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["funding_type"] == "aso"
        assert data["name"] == group_data["name"]
        print(f"✅ Created ASO group: {data['id']}")
        return data["id"]
    
    def test_create_group_with_level_funded(self, auth_headers):
        """Should create group with funding_type=level_funded and claims_fund_monthly"""
        unique_tax_id = f"99-{uuid.uuid4().hex[:7].upper()}"
        group_data = {
            "name": f"TEST_LF_Group_{uuid.uuid4().hex[:6]}",
            "tax_id": unique_tax_id,
            "effective_date": "2025-01-01",
            "funding_type": "level_funded",
            "claims_fund_monthly": 15000.00,
            "employee_count": 75
        }
        
        response = requests.post(f"{BASE_URL}/api/groups", json=group_data, headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["funding_type"] == "level_funded"
        assert data["claims_fund_monthly"] == 15000.00
        print(f"✅ Created Level Funded group: {data['id']}, monthly fund: ${data['claims_fund_monthly']}")
        return data["id"]
    
    def test_create_group_with_fully_insured(self, auth_headers):
        """Should create group with funding_type=fully_insured"""
        unique_tax_id = f"99-{uuid.uuid4().hex[:7].upper()}"
        group_data = {
            "name": f"TEST_FI_Group_{uuid.uuid4().hex[:6]}",
            "tax_id": unique_tax_id,
            "effective_date": "2025-01-01",
            "funding_type": "fully_insured",
            "employee_count": 100
        }
        
        response = requests.post(f"{BASE_URL}/api/groups", json=group_data, headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["funding_type"] == "fully_insured"
        print(f"✅ Created Fully Insured group: {data['id']}")
        return data["id"]


class TestReserveFund(TestAuth):
    """Test GET /api/groups/{id}/reserve-fund — Claims reserve fund for level-funded groups"""
    
    def test_get_reserve_fund_level_funded(self, auth_headers):
        """Should return reserve fund status for level-funded group"""
        response = requests.get(
            f"{BASE_URL}/api/groups/{BETA_GROUP_ID}/reserve-fund",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["group_id"] == BETA_GROUP_ID
        assert data["funding_type"] == "level_funded"
        assert "claims_fund_monthly" in data
        assert "months_active" in data
        assert "total_deposited" in data
        assert "total_claims_paid" in data
        assert "balance" in data
        assert "in_deficit" in data
        assert "needs_stop_loss_review" in data
        assert "monthly_breakdown" in data
        
        print(f"✅ Reserve fund for Beta LLC:")
        print(f"   Monthly deposit: ${data['claims_fund_monthly']}")
        print(f"   Months active: {data['months_active']}")
        print(f"   Total deposited: ${data['total_deposited']}")
        print(f"   Claims paid: ${data['total_claims_paid']}")
        print(f"   Balance: ${data['balance']}")
        print(f"   In deficit: {data['in_deficit']}")
    
    def test_reserve_fund_aso_group_returns_error(self, auth_headers):
        """Should return 400 for ASO group (reserve fund only for level-funded)"""
        response = requests.get(
            f"{BASE_URL}/api/groups/{ACME_GROUP_ID}/reserve-fund",
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "level-funded" in response.text.lower()
        print("✅ Returns 400 for ASO group (reserve fund only for level-funded)")
    
    def test_reserve_fund_monthly_breakdown(self, auth_headers):
        """Should include monthly breakdown in reserve fund response"""
        response = requests.get(
            f"{BASE_URL}/api/groups/{BETA_GROUP_ID}/reserve-fund",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        monthly = data.get("monthly_breakdown", [])
        assert isinstance(monthly, list)
        
        if len(monthly) > 0:
            month = monthly[0]
            assert "month" in month
            assert "deposited" in month
            assert "claims_paid" in month
            print(f"✅ Monthly breakdown has {len(monthly)} months")


class TestDashboardFundingHealth(TestAuth):
    """Test GET /api/dashboard/funding-health — Funding Health summary"""
    
    def test_get_funding_health(self, auth_headers):
        """Should return funding health summary across all groups"""
        response = requests.get(f"{BASE_URL}/api/dashboard/funding-health", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check ASO section
        assert "aso" in data
        assert "group_count" in data["aso"]
        assert "pending_funding" in data["aso"]
        assert "total_paid" in data["aso"]
        
        # Check Level Funded section
        assert "level_funded" in data
        assert "group_count" in data["level_funded"]
        assert "expected_fund" in data["level_funded"]
        assert "actual_claims" in data["level_funded"]
        assert "surplus" in data["level_funded"]
        assert "deficit_groups" in data["level_funded"]
        
        # Check Fully Insured section
        assert "fully_insured" in data
        assert "group_count" in data["fully_insured"]
        
        print(f"✅ Funding Health Summary:")
        print(f"   ASO: {data['aso']['group_count']} groups, pending: ${data['aso']['pending_funding']}, paid: ${data['aso']['total_paid']}")
        print(f"   Level Funded: {data['level_funded']['group_count']} groups, expected: ${data['level_funded']['expected_fund']}, actual: ${data['level_funded']['actual_claims']}, surplus: ${data['level_funded']['surplus']}")
        print(f"   Fully Insured: {data['fully_insured']['group_count']} groups")
    
    def test_funding_health_deficit_groups(self, auth_headers):
        """Should include deficit groups in level_funded section"""
        response = requests.get(f"{BASE_URL}/api/dashboard/funding-health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        deficit_groups = data["level_funded"].get("deficit_groups", [])
        assert isinstance(deficit_groups, list)
        
        if len(deficit_groups) > 0:
            dg = deficit_groups[0]
            assert "group_id" in dg
            assert "group_name" in dg
            assert "deficit" in dg
            print(f"✅ Found {len(deficit_groups)} deficit groups")
        else:
            print("✅ No deficit groups (all level-funded groups have surplus)")


class TestGroupsList(TestAuth):
    """Test GET /api/groups — Verify funding_type in groups list"""
    
    def test_groups_list_includes_funding_type(self, auth_headers):
        """Should include funding_type in groups list response"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check that funding_type is present
        for group in data:
            assert "funding_type" in group, f"Group {group.get('name')} missing funding_type"
        
        # Count by funding type
        aso_count = sum(1 for g in data if g.get("funding_type") == "aso")
        lf_count = sum(1 for g in data if g.get("funding_type") == "level_funded")
        fi_count = sum(1 for g in data if g.get("funding_type") == "fully_insured")
        
        print(f"✅ Groups by funding type: ASO={aso_count}, Level Funded={lf_count}, Fully Insured={fi_count}")


class TestGroupDetail(TestAuth):
    """Test GET /api/groups/{id} — Verify funding_type in group detail"""
    
    def test_group_detail_includes_funding_type(self, auth_headers):
        """Should include funding_type in group detail response"""
        response = requests.get(f"{BASE_URL}/api/groups/{ACME_GROUP_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "funding_type" in data
        assert data["funding_type"] == "aso"
        print(f"✅ Acme Manufacturing funding_type: {data['funding_type']}")
    
    def test_level_funded_group_detail(self, auth_headers):
        """Should include claims_fund_monthly for level-funded group"""
        response = requests.get(f"{BASE_URL}/api/groups/{BETA_GROUP_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["funding_type"] == "level_funded"
        assert "claims_fund_monthly" in data
        print(f"✅ Beta LLC: funding_type={data['funding_type']}, claims_fund_monthly=${data.get('claims_fund_monthly', 0)}")


class TestCheckRunConfirmAndExecute(TestAuth):
    """Test confirm-funding and execute endpoints"""
    
    def test_confirm_funding_not_found(self, auth_headers):
        """Should return 404 for non-existent run"""
        response = requests.post(
            f"{BASE_URL}/api/check-runs/non-existent-id/confirm-funding",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✅ confirm-funding returns 404 for non-existent run")
    
    def test_execute_not_found(self, auth_headers):
        """Should return 404 for non-existent run"""
        response = requests.post(
            f"{BASE_URL}/api/check-runs/non-existent-id/execute",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✅ execute returns 404 for non-existent run")
    
    def test_confirm_funding_wrong_status(self, auth_headers):
        """Should return 400 if run is not in pending_funding status"""
        # Get a run that's already funded or executed
        list_response = requests.get(
            f"{BASE_URL}/api/check-runs",
            params={"status": "executed"},
            headers=auth_headers
        )
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No executed runs to test wrong status")
        
        run_id = runs[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/check-runs/{run_id}/confirm-funding",
            headers=auth_headers
        )
        assert response.status_code == 400
        print("✅ confirm-funding returns 400 for wrong status")
    
    def test_execute_wrong_status(self, auth_headers):
        """Should return 400 if run is not in funded status"""
        # Get a run that's pending_funding
        list_response = requests.get(
            f"{BASE_URL}/api/check-runs",
            params={"status": "pending_funding"},
            headers=auth_headers
        )
        runs = list_response.json()
        
        if len(runs) == 0:
            pytest.skip("No pending_funding runs to test wrong status")
        
        run_id = runs[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/check-runs/{run_id}/execute",
            headers=auth_headers
        )
        assert response.status_code == 400
        print("✅ execute returns 400 for wrong status (must be funded)")


class TestRegressionExistingEndpoints(TestAuth):
    """Regression tests for existing endpoints"""
    
    def test_dashboard_metrics(self, auth_headers):
        """Dashboard metrics should still work"""
        response = requests.get(f"{BASE_URL}/api/dashboard/metrics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_claims" in data
        assert "pending_claims" in data
        print("✅ Dashboard metrics endpoint working")
    
    def test_claims_list(self, auth_headers):
        """Claims list should still work"""
        response = requests.get(f"{BASE_URL}/api/claims", headers=auth_headers)
        assert response.status_code == 200
        print("✅ Claims list endpoint working")
    
    def test_members_list(self, auth_headers):
        """Members list should still work"""
        response = requests.get(f"{BASE_URL}/api/members", headers=auth_headers)
        assert response.status_code == 200
        print("✅ Members list endpoint working")
    
    def test_plans_list(self, auth_headers):
        """Plans list should still work"""
        response = requests.get(f"{BASE_URL}/api/plans", headers=auth_headers)
        assert response.status_code == 200
        print("✅ Plans list endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
