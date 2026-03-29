"""
FletchFlow Group Management & MEC 1 Plan Template - Backend API Tests
Tests for: Group CRUD, Stop-Loss Config, SFTP Config, Pulse Analytics, MEC 1 Template, Plan Attachment
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
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestGroupsList:
    """Group listing endpoint tests"""
    
    def test_groups_list_returns_array(self, auth_headers):
        """API: GET /api/groups returns list of groups"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Groups list returned {len(data)} groups")
    
    def test_groups_list_contains_acme(self, auth_headers):
        """API: GET /api/groups contains Acme Manufacturing group"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        acme = next((g for g in data if "Acme" in g.get("name", "")), None)
        assert acme is not None, "Acme Manufacturing group not found"
        assert acme.get("tax_id") == "12-3456789"
        print(f"✅ Found Acme Manufacturing group: Tax ID {acme.get('tax_id')}")


class TestGroupDetail:
    """Group detail endpoint tests"""
    
    def test_get_group_by_id(self, auth_headers):
        """API: GET /api/groups/{id} returns group with attached_plans and member_count"""
        # First get the list to find Acme's ID
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        assert response.status_code == 200
        groups = response.json()
        acme = next((g for g in groups if "Acme" in g.get("name", "")), None)
        assert acme is not None, "Acme Manufacturing group not found"
        
        # Get group detail
        group_id = acme.get("id")
        response = requests.get(f"{BASE_URL}/api/groups/{group_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "attached_plans" in data
        assert "member_count" in data
        assert isinstance(data.get("attached_plans"), list)
        assert isinstance(data.get("member_count"), int)
        print(f"✅ Group detail: {data.get('name')}, {len(data.get('attached_plans', []))} plans, {data.get('member_count')} members")
    
    def test_group_has_stop_loss_config(self, auth_headers):
        """Group detail includes stop-loss configuration"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        groups = response.json()
        acme = next((g for g in groups if "Acme" in g.get("name", "")), None)
        
        group_id = acme.get("id")
        response = requests.get(f"{BASE_URL}/api/groups/{group_id}", headers=auth_headers)
        data = response.json()
        
        stop_loss = data.get("stop_loss")
        assert stop_loss is not None, "Stop-loss config missing"
        assert stop_loss.get("specific_deductible") == 75000
        assert stop_loss.get("aggregate_attachment_point") == 500000
        print(f"✅ Stop-loss config: Specific ${stop_loss.get('specific_deductible'):,}, Aggregate ${stop_loss.get('aggregate_attachment_point'):,}")
    
    def test_group_has_sftp_config(self, auth_headers):
        """Group detail includes SFTP scheduler configuration"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        groups = response.json()
        acme = next((g for g in groups if "Acme" in g.get("name", "")), None)
        
        group_id = acme.get("id")
        response = requests.get(f"{BASE_URL}/api/groups/{group_id}", headers=auth_headers)
        data = response.json()
        
        sftp = data.get("sftp_config")
        assert sftp is not None, "SFTP config missing"
        assert sftp.get("host") == "sftp.acme.com"
        assert sftp.get("schedule") == "daily"
        assert "834" in sftp.get("file_types", [])
        assert "835" in sftp.get("file_types", [])
        print(f"✅ SFTP config: {sftp.get('host')}, {sftp.get('schedule')}, files: {sftp.get('file_types')}")


class TestGroupPulseAnalytics:
    """Group Pulse analytics endpoint tests"""
    
    def test_pulse_analytics_returns_data(self, auth_headers):
        """API: GET /api/groups/{id}/pulse returns Pulse analytics"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        groups = response.json()
        acme = next((g for g in groups if "Acme" in g.get("name", "")), None)
        
        group_id = acme.get("id")
        response = requests.get(f"{BASE_URL}/api/groups/{group_id}/pulse", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify Pulse analytics structure
        assert "member_count" in data
        assert "total_claims" in data
        assert "total_paid" in data
        assert "pmpm" in data
        assert "stop_loss" in data
        print(f"✅ Pulse analytics: {data.get('member_count')} members, {data.get('total_claims')} claims, PMPM ${data.get('pmpm')}")
    
    def test_pulse_stop_loss_surplus(self, auth_headers):
        """Pulse analytics includes stop-loss surplus bucket"""
        response = requests.get(f"{BASE_URL}/api/groups", headers=auth_headers)
        groups = response.json()
        acme = next((g for g in groups if "Acme" in g.get("name", "")), None)
        
        group_id = acme.get("id")
        response = requests.get(f"{BASE_URL}/api/groups/{group_id}/pulse", headers=auth_headers)
        data = response.json()
        
        stop_loss = data.get("stop_loss", {})
        assert "surplus_bucket" in stop_loss
        assert "utilization_pct" in stop_loss
        assert "total_paid_ytd" in stop_loss
        print(f"✅ Stop-loss surplus: ${stop_loss.get('surplus_bucket'):,.2f}, utilization {stop_loss.get('utilization_pct')}%")


class TestMEC1PlanTemplate:
    """MEC 1 Plan Template endpoint tests"""
    
    def test_create_mec1_plan(self, auth_headers):
        """API: POST /api/plans/template/mec-1 creates MEC 1 plan with 22 benefits and 30 exclusions"""
        # Create a test group first
        test_group_name = f"TEST_MEC1_Group_{uuid.uuid4().hex[:8]}"
        group_response = requests.post(f"{BASE_URL}/api/groups", headers=auth_headers, json={
            "name": test_group_name,
            "tax_id": f"99-{uuid.uuid4().hex[:7]}",
            "effective_date": "2025-01-01",
            "employee_count": 50
        })
        assert group_response.status_code == 200
        group_id = group_response.json().get("id")
        
        # Create MEC 1 plan
        response = requests.post(
            f"{BASE_URL}/api/plans/template/mec-1?group_id={group_id}&plan_name=MEC%201%20-%20Test",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify MEC 1 plan structure
        assert data.get("plan_template") == "mec_1"
        assert data.get("preventive_design") == "aca_strict"
        assert data.get("deductible_individual") == 0
        assert data.get("oop_max_individual") == 0
        assert data.get("preauth_penalty_pct") == 50.0
        assert data.get("non_network_reimbursement") == "reference_based"
        
        # Verify 22 benefit categories
        benefits = data.get("benefits", [])
        assert len(benefits) == 22, f"Expected 22 benefits, got {len(benefits)}"
        
        # Verify 10 covered preventive categories
        covered = [b for b in benefits if b.get("covered") == True]
        assert len(covered) == 10, f"Expected 10 covered benefits, got {len(covered)}"
        
        # Verify 12 not-covered categories
        not_covered = [b for b in benefits if b.get("covered") == False]
        assert len(not_covered) == 12, f"Expected 12 not-covered benefits, got {len(not_covered)}"
        
        # Verify 30 exclusions
        exclusions = data.get("exclusions", [])
        assert len(exclusions) == 30, f"Expected 30 exclusions, got {len(exclusions)}"
        
        print(f"✅ MEC 1 plan created: {len(benefits)} benefits (10 covered, 12 not-covered), {len(exclusions)} exclusions")
        
        # Cleanup - delete test group (plan will remain but that's ok)
        # Note: No delete endpoint for groups, so we leave it


class TestPlanAttachment:
    """Plan attachment to group tests"""
    
    def test_attach_plan_to_group(self, auth_headers):
        """API: POST /api/groups/{id}/attach-plan attaches a plan"""
        # Create a test group
        test_group_name = f"TEST_Attach_Group_{uuid.uuid4().hex[:8]}"
        group_response = requests.post(f"{BASE_URL}/api/groups", headers=auth_headers, json={
            "name": test_group_name,
            "tax_id": f"88-{uuid.uuid4().hex[:7]}",
            "effective_date": "2025-01-01",
            "employee_count": 25
        })
        assert group_response.status_code == 200
        group_id = group_response.json().get("id")
        
        # Get an existing plan
        plans_response = requests.get(f"{BASE_URL}/api/plans", headers=auth_headers)
        plans = plans_response.json()
        if len(plans) == 0:
            pytest.skip("No plans available to attach")
        
        plan_id = plans[0].get("id")
        
        # Attach plan
        response = requests.post(
            f"{BASE_URL}/api/groups/{group_id}/attach-plan?plan_id={plan_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "Plan attached"
        assert data.get("group_id") == group_id
        assert data.get("plan_id") == plan_id
        
        # Verify plan is attached
        group_detail = requests.get(f"{BASE_URL}/api/groups/{group_id}", headers=auth_headers)
        attached_plans = group_detail.json().get("attached_plans", [])
        attached_ids = [p.get("id") for p in attached_plans]
        assert plan_id in attached_ids
        
        print(f"✅ Plan attached successfully to group")


class TestStopLossUpdate:
    """Stop-loss configuration update tests"""
    
    def test_update_stop_loss_config(self, auth_headers):
        """API: PUT /api/groups/{id}/stop-loss updates stop-loss config"""
        # Create a test group
        test_group_name = f"TEST_StopLoss_Group_{uuid.uuid4().hex[:8]}"
        group_response = requests.post(f"{BASE_URL}/api/groups", headers=auth_headers, json={
            "name": test_group_name,
            "tax_id": f"77-{uuid.uuid4().hex[:7]}",
            "effective_date": "2025-01-01",
            "employee_count": 100
        })
        assert group_response.status_code == 200
        group_id = group_response.json().get("id")
        
        # Update stop-loss
        stop_loss_config = {
            "specific_deductible": 100000,
            "aggregate_attachment_point": 750000,
            "aggregate_factor": 125.0,
            "contract_period": "12_month",
            "laser_deductibles": []
        }
        response = requests.put(
            f"{BASE_URL}/api/groups/{group_id}/stop-loss",
            headers=auth_headers,
            json=stop_loss_config
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "Stop-loss updated"
        assert data.get("stop_loss", {}).get("specific_deductible") == 100000
        assert data.get("stop_loss", {}).get("aggregate_attachment_point") == 750000
        
        print(f"✅ Stop-loss config updated: Specific $100K, Aggregate $750K")


class TestSFTPUpdate:
    """SFTP configuration update tests"""
    
    def test_update_sftp_config(self, auth_headers):
        """API: PUT /api/groups/{id}/sftp updates SFTP config"""
        # Create a test group
        test_group_name = f"TEST_SFTP_Group_{uuid.uuid4().hex[:8]}"
        group_response = requests.post(f"{BASE_URL}/api/groups", headers=auth_headers, json={
            "name": test_group_name,
            "tax_id": f"66-{uuid.uuid4().hex[:7]}",
            "effective_date": "2025-01-01",
            "employee_count": 75
        })
        assert group_response.status_code == 200
        group_id = group_response.json().get("id")
        
        # Update SFTP config
        sftp_config = {
            "host": "sftp.testcompany.com",
            "port": 22,
            "username": "testuser",
            "directory": "/uploads",
            "schedule": "weekly",
            "file_types": ["834", "835"],
            "enabled": True
        }
        response = requests.put(
            f"{BASE_URL}/api/groups/{group_id}/sftp",
            headers=auth_headers,
            json=sftp_config
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "SFTP config updated"
        assert data.get("sftp_config", {}).get("host") == "sftp.testcompany.com"
        assert data.get("sftp_config", {}).get("schedule") == "weekly"
        assert data.get("sftp_config", {}).get("enabled") == True
        
        print(f"✅ SFTP config updated: {sftp_config.get('host')}, {sftp_config.get('schedule')}")


class TestGroupCreate:
    """Group creation tests"""
    
    def test_create_group_with_all_fields(self, auth_headers):
        """Create a new group with all fields including stop-loss and SFTP"""
        test_group_name = f"TEST_Full_Group_{uuid.uuid4().hex[:8]}"
        group_data = {
            "name": test_group_name,
            "tax_id": f"55-{uuid.uuid4().hex[:7]}",
            "effective_date": "2025-01-01",
            "termination_date": None,
            "contact_name": "John Doe",
            "contact_email": "john@test.com",
            "contact_phone": "555-123-4567",
            "address": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "sic_code": "3599",
            "employee_count": 150,
            "stop_loss": {
                "specific_deductible": 50000,
                "aggregate_attachment_point": 400000,
                "aggregate_factor": 125.0,
                "contract_period": "12_month",
                "laser_deductibles": []
            },
            "sftp_config": {
                "host": "sftp.newgroup.com",
                "port": 22,
                "username": "newuser",
                "directory": "/data",
                "schedule": "daily",
                "file_types": ["834", "835"],
                "enabled": True
            },
            "plan_ids": []
        }
        
        response = requests.post(f"{BASE_URL}/api/groups", headers=auth_headers, json=group_data)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("name") == test_group_name
        assert data.get("status") == "active"
        assert data.get("stop_loss", {}).get("specific_deductible") == 50000
        assert data.get("sftp_config", {}).get("enabled") == True
        
        print(f"✅ Group created: {test_group_name}, stop-loss and SFTP configured")


class TestExistingEndpointsStillWork:
    """Verify existing endpoints still work after Group Management addition"""
    
    def test_dashboard_metrics_still_works(self, auth_headers):
        """Dashboard metrics endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/dashboard/metrics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_claims" in data
        print(f"✅ Dashboard metrics still works: {data.get('total_claims')} claims")
    
    def test_plans_list_still_works(self, auth_headers):
        """Plans list endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/plans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Plans list still works: {len(data)} plans")
    
    def test_claims_list_still_works(self, auth_headers):
        """Claims list endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/claims", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Claims list still works: {len(data)} claims")
    
    def test_preventive_services_still_works(self, auth_headers):
        """Preventive services endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/preventive/services", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # API returns {count: N, results: [...]}
        assert "results" in data or isinstance(data, list)
        count = data.get("count", len(data)) if isinstance(data, dict) else len(data)
        print(f"✅ Preventive services still works: {count} services")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
