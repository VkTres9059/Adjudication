"""
SFTP Scheduler Module Tests
Tests for:
- SFTP Connection CRUD (POST/GET/PUT/DELETE /api/sftp/connections)
- Password masking in GET response
- Connection testing (POST /api/sftp/connections/{id}/test, POST /api/sftp/connections/test-inline)
- SFTP Schedule CRUD (POST/GET/PUT/DELETE /api/sftp/schedules)
- Schedule toggle (PUT /api/sftp/schedules/{id}/toggle)
- Manual trigger (POST /api/sftp/schedules/{id}/run-now)
- Intake logs (GET /api/sftp/intake-logs)
- Export Data Engine (POST /api/edi/export-834, POST /api/edi/export-auth-feed, GET /api/edi/transmissions)
- Vendor CRUD (GET/POST /api/settings/vendors)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "demo@fletchflow.com",
        "password": "Demo123!"
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    pytest.skip("Authentication failed - skipping tests")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


# ═══════════════════════════════════════════════════════════════════════════
# SFTP CONNECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestSFTPConnections:
    """SFTP Connection CRUD tests."""
    
    created_connection_id = None
    
    def test_create_sftp_connection(self, auth_headers):
        """POST /api/sftp/connections - Create new SFTP connection."""
        payload = {
            "name": f"TEST_SFTP_Conn_{uuid.uuid4().hex[:8]}",
            "host": "sftp.test-server.com",
            "port": 22,
            "username": "test_user",
            "auth_type": "password",
            "password": "secret_password_123",
            "ssh_key": "",
            "base_path": "/outbound/test",
            "enabled": True
        }
        response = requests.post(f"{BASE_URL}/api/sftp/connections", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should contain 'id'"
        assert data["name"] == payload["name"], "Name should match"
        assert data["host"] == payload["host"], "Host should match"
        assert data["port"] == payload["port"], "Port should match"
        assert data["username"] == payload["username"], "Username should match"
        assert data["auth_type"] == payload["auth_type"], "Auth type should match"
        assert data["base_path"] == payload["base_path"], "Base path should match"
        
        # Password should be masked in response
        assert data["password"] == "••••••••", f"Password should be masked, got: {data['password']}"
        
        TestSFTPConnections.created_connection_id = data["id"]
        print(f"✅ Created SFTP connection: {data['id']}")
    
    def test_list_sftp_connections(self, auth_headers):
        """GET /api/sftp/connections - List all connections."""
        response = requests.get(f"{BASE_URL}/api/sftp/connections", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ Listed {len(data)} SFTP connections")
        
        # Verify password masking in list
        for conn in data:
            if conn.get("password"):
                assert conn["password"] == "••••••••", f"Password should be masked in list: {conn['password']}"
    
    def test_password_masking_in_get(self, auth_headers):
        """GET /api/sftp/connections - Verify password is masked as '••••••••'."""
        response = requests.get(f"{BASE_URL}/api/sftp/connections", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Find our test connection
        test_conn = next((c for c in data if c.get("id") == TestSFTPConnections.created_connection_id), None)
        
        if test_conn:
            assert test_conn["password"] == "••••••••", f"Password should be '••••••••', got: {test_conn['password']}"
            print("✅ Password correctly masked as '••••••••'")
        else:
            print("⚠️ Test connection not found in list, but masking verified on other connections")
    
    def test_update_sftp_connection(self, auth_headers):
        """PUT /api/sftp/connections/{id} - Update connection."""
        if not TestSFTPConnections.created_connection_id:
            pytest.skip("No connection created to update")
        
        conn_id = TestSFTPConnections.created_connection_id
        payload = {
            "name": f"TEST_SFTP_Updated_{uuid.uuid4().hex[:6]}",
            "host": "sftp.updated-server.com",
            "port": 2222,
            "username": "updated_user",
            "auth_type": "password",
            "password": "••••••••",  # Send masked value back - should preserve original
            "ssh_key": "",
            "base_path": "/updated/path",
            "enabled": True
        }
        response = requests.put(f"{BASE_URL}/api/sftp/connections/{conn_id}", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["host"] == "sftp.updated-server.com", "Host should be updated"
        assert data["port"] == 2222, "Port should be updated"
        assert data["base_path"] == "/updated/path", "Base path should be updated"
        print(f"✅ Updated SFTP connection: {conn_id}")
    
    def test_test_sftp_connection_saved(self, auth_headers):
        """POST /api/sftp/connections/{id}/test - Test saved connection (expected failure for fake host)."""
        if not TestSFTPConnections.created_connection_id:
            pytest.skip("No connection created to test")
        
        conn_id = TestSFTPConnections.created_connection_id
        response = requests.post(f"{BASE_URL}/api/sftp/connections/{conn_id}/test", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return proper error response structure
        assert "success" in data, "Response should have 'success' field"
        assert "message" in data, "Response should have 'message' field"
        
        # Expected to fail since it's a fake host
        assert data["success"] == False, "Connection to fake host should fail"
        assert len(data["message"]) > 0, "Should have error message"
        print(f"✅ Connection test returned expected failure: {data['message'][:50]}...")
    
    def test_test_inline_connection(self, auth_headers):
        """POST /api/sftp/connections/test-inline - Test connection without saving."""
        payload = {
            "name": "Inline Test",
            "host": "nonexistent.sftp.server.com",
            "port": 22,
            "username": "inline_user",
            "auth_type": "password",
            "password": "inline_pass",
            "ssh_key": "",
            "base_path": "/",
            "enabled": True
        }
        response = requests.post(f"{BASE_URL}/api/sftp/connections/test-inline", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "success" in data, "Response should have 'success' field"
        assert "message" in data, "Response should have 'message' field"
        
        # Expected to fail since it's a fake host
        assert data["success"] == False, "Inline test to fake host should fail"
        print(f"✅ Inline connection test returned expected failure: {data['message'][:50]}...")


# ═══════════════════════════════════════════════════════════════════════════
# SFTP SCHEDULE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestSFTPSchedules:
    """SFTP Schedule CRUD tests."""
    
    created_schedule_id = None
    
    def test_create_sftp_schedule(self, auth_headers):
        """POST /api/sftp/schedules - Create new schedule."""
        # First ensure we have a connection
        if not TestSFTPConnections.created_connection_id:
            # Create a connection first
            conn_payload = {
                "name": f"TEST_Conn_For_Schedule_{uuid.uuid4().hex[:6]}",
                "host": "sftp.schedule-test.com",
                "port": 22,
                "username": "sched_user",
                "auth_type": "password",
                "password": "sched_pass",
                "ssh_key": "",
                "base_path": "/",
                "enabled": True
            }
            conn_resp = requests.post(f"{BASE_URL}/api/sftp/connections", json=conn_payload, headers=auth_headers)
            if conn_resp.status_code == 200:
                TestSFTPConnections.created_connection_id = conn_resp.json()["id"]
        
        payload = {
            "name": f"TEST_Schedule_{uuid.uuid4().hex[:8]}",
            "connection_id": TestSFTPConnections.created_connection_id,
            "frequency": "daily",
            "time_of_day": "03:00",
            "day_of_week": "mon",
            "file_pattern": "*834*.edi",
            "route_type": "834",
            "enabled": True
        }
        response = requests.post(f"{BASE_URL}/api/sftp/schedules", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data, "Response should contain 'id'"
        assert data["name"] == payload["name"], "Name should match"
        assert data["connection_id"] == payload["connection_id"], "Connection ID should match"
        assert data["frequency"] == "daily", "Frequency should be daily"
        assert data["route_type"] == "834", "Route type should be 834"
        assert "connection_name" in data, "Should include connection_name"
        
        TestSFTPSchedules.created_schedule_id = data["id"]
        print(f"✅ Created SFTP schedule: {data['id']}")
    
    def test_list_sftp_schedules(self, auth_headers):
        """GET /api/sftp/schedules - List all schedules."""
        response = requests.get(f"{BASE_URL}/api/sftp/schedules", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ Listed {len(data)} SFTP schedules")
    
    def test_update_sftp_schedule(self, auth_headers):
        """PUT /api/sftp/schedules/{id} - Update schedule."""
        if not TestSFTPSchedules.created_schedule_id:
            pytest.skip("No schedule created to update")
        
        sched_id = TestSFTPSchedules.created_schedule_id
        payload = {
            "name": f"TEST_Schedule_Updated_{uuid.uuid4().hex[:6]}",
            "connection_id": TestSFTPConnections.created_connection_id,
            "frequency": "weekly",
            "time_of_day": "04:30",
            "day_of_week": "wed",
            "file_pattern": "*835*.edi",
            "route_type": "835",
            "enabled": True
        }
        response = requests.put(f"{BASE_URL}/api/sftp/schedules/{sched_id}", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["frequency"] == "weekly", "Frequency should be updated to weekly"
        assert data["route_type"] == "835", "Route type should be updated to 835"
        print(f"✅ Updated SFTP schedule: {sched_id}")
    
    def test_toggle_schedule(self, auth_headers):
        """PUT /api/sftp/schedules/{id}/toggle - Toggle enabled field."""
        if not TestSFTPSchedules.created_schedule_id:
            pytest.skip("No schedule created to toggle")
        
        sched_id = TestSFTPSchedules.created_schedule_id
        
        # First toggle
        response = requests.put(f"{BASE_URL}/api/sftp/schedules/{sched_id}/toggle", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "enabled" in data, "Response should have 'enabled' field"
        first_state = data["enabled"]
        print(f"✅ Toggled schedule to enabled={first_state}")
        
        # Second toggle - should flip
        response2 = requests.put(f"{BASE_URL}/api/sftp/schedules/{sched_id}/toggle", headers=auth_headers)
        data2 = response2.json()
        
        assert data2["enabled"] != first_state, "Toggle should flip the enabled state"
        print(f"✅ Toggled schedule again to enabled={data2['enabled']}")
    
    def test_run_schedule_now(self, auth_headers):
        """POST /api/sftp/schedules/{id}/run-now - Manual trigger."""
        if not TestSFTPSchedules.created_schedule_id:
            pytest.skip("No schedule created to trigger")
        
        sched_id = TestSFTPSchedules.created_schedule_id
        response = requests.post(f"{BASE_URL}/api/sftp/schedules/{sched_id}/run-now", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("status") == "triggered", f"Status should be 'triggered', got: {data.get('status')}"
        assert data.get("schedule_id") == sched_id, "Schedule ID should match"
        print(f"✅ Manually triggered schedule: {sched_id}")


# ═══════════════════════════════════════════════════════════════════════════
# INTAKE LOGS TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestIntakeLogs:
    """SFTP Intake Logs tests."""
    
    def test_list_intake_logs(self, auth_headers):
        """GET /api/sftp/intake-logs - List intake history."""
        response = requests.get(f"{BASE_URL}/api/sftp/intake-logs", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ Listed {len(data)} intake logs")
        
        # If there are logs, verify structure
        if len(data) > 0:
            log = data[0]
            expected_fields = ["id", "schedule_id", "status", "started_at"]
            for field in expected_fields:
                assert field in log, f"Log should have '{field}' field"
    
    def test_intake_logs_with_limit(self, auth_headers):
        """GET /api/sftp/intake-logs?limit=10 - Test limit parameter."""
        response = requests.get(f"{BASE_URL}/api/sftp/intake-logs", params={"limit": 10}, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) <= 10, "Should respect limit parameter"
        print(f"✅ Intake logs with limit=10 returned {len(data)} logs")


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT DATA ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestExportDataEngine:
    """Export 834 and Auth Feed tests."""
    
    def test_export_834_hipaa_format(self, auth_headers):
        """POST /api/edi/export-834 - Export 834 in HIPAA 5010 format."""
        response = requests.post(
            f"{BASE_URL}/api/edi/export-834",
            params={"format": "hipaa_5010"},
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "content" in data, "Response should have 'content'"
        assert "filename" in data, "Response should have 'filename'"
        assert "format" in data, "Response should have 'format'"
        assert "total_members" in data, "Response should have 'total_members'"
        assert "adds" in data, "Response should have 'adds'"
        assert "terms" in data, "Response should have 'terms'"
        
        assert data["format"] == "hipaa_5010", f"Format should be hipaa_5010, got: {data['format']}"
        
        # Verify X12 content structure
        content = data["content"]
        assert "ISA*" in content, "HIPAA 5010 should have ISA segment"
        assert "GS*BE" in content, "HIPAA 5010 should have GS*BE segment"
        assert "ST*834" in content, "HIPAA 5010 should have ST*834 segment"
        
        print(f"✅ Exported 834 HIPAA: {data['total_members']} members ({data['adds']} adds, {data['terms']} terms)")
    
    def test_export_834_csv_format(self, auth_headers):
        """POST /api/edi/export-834?format=csv - Export 834 in CSV format."""
        response = requests.post(
            f"{BASE_URL}/api/edi/export-834",
            params={"format": "csv"},
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["format"] == "csv", f"Format should be csv, got: {data['format']}"
        
        # Verify CSV content structure
        content = data["content"]
        assert "MemberID" in content, "CSV should have MemberID header"
        assert "FirstName" in content, "CSV should have FirstName header"
        assert "MaintenanceCode" in content, "CSV should have MaintenanceCode header"
        
        print(f"✅ Exported 834 CSV: {data['total_members']} members")
    
    def test_export_auth_feed_csv(self, auth_headers):
        """POST /api/edi/export-auth-feed - Export authorization feed."""
        response = requests.post(
            f"{BASE_URL}/api/edi/export-auth-feed",
            params={"format": "csv"},
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "content" in data, "Response should have 'content'"
        assert "filename" in data, "Response should have 'filename'"
        assert "format" in data, "Response should have 'format'"
        assert "auth_count" in data, "Response should have 'auth_count'"
        
        # Verify CSV header
        content = data["content"]
        assert "AuthID" in content, "CSV should have AuthID header"
        
        print(f"✅ Exported auth feed: {data['auth_count']} authorizations")
    
    def test_export_auth_feed_hipaa(self, auth_headers):
        """POST /api/edi/export-auth-feed?format=hipaa_5010 - Export auth in HIPAA format."""
        response = requests.post(
            f"{BASE_URL}/api/edi/export-auth-feed",
            params={"format": "hipaa_5010"},
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["format"] == "hipaa_5010"
        
        # Verify X12 278 structure
        content = data["content"]
        assert "ISA*" in content, "HIPAA should have ISA segment"
        assert "ST*278" in content, "HIPAA should have ST*278 segment"
        
        print(f"✅ Exported auth feed HIPAA: {data['auth_count']} authorizations")


# ═══════════════════════════════════════════════════════════════════════════
# TRANSMISSION LOG TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestTransmissionLog:
    """EDI Transmission Log tests."""
    
    def test_list_transmissions(self, auth_headers):
        """GET /api/edi/transmissions - List outbound feed history."""
        response = requests.get(f"{BASE_URL}/api/edi/transmissions", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ Listed {len(data)} transmissions")
        
        # Verify structure if there are transmissions
        if len(data) > 0:
            tx = data[0]
            expected_fields = ["id", "feed_type", "filename", "status", "record_count", "created_at"]
            for field in expected_fields:
                assert field in tx, f"Transmission should have '{field}' field"


# ═══════════════════════════════════════════════════════════════════════════
# VENDOR CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestVendorCRUD:
    """Feed Vendor CRUD tests."""
    
    created_vendor_id = None
    
    def test_list_vendors(self, auth_headers):
        """GET /api/settings/vendors - List all vendors."""
        response = requests.get(f"{BASE_URL}/api/settings/vendors", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ Listed {len(data)} vendors")
    
    def test_create_vendor(self, auth_headers):
        """POST /api/settings/vendors - Create new vendor."""
        payload = {
            "name": f"TEST_Vendor_{uuid.uuid4().hex[:8]}",
            "vendor_type": "pbm",
            "feed_types": ["834", "278"],
            "format": "hipaa_5010",
            "sftp_host": "sftp.test-vendor.com",
            "sftp_path": "/inbound",
            "enabled": True
        }
        response = requests.post(f"{BASE_URL}/api/settings/vendors", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data, "Response should have 'id'"
        assert data["name"] == payload["name"], "Name should match"
        assert data["vendor_type"] == "pbm", "Vendor type should match"
        assert "834" in data["feed_types"], "Feed types should include 834"
        
        TestVendorCRUD.created_vendor_id = data["id"]
        print(f"✅ Created vendor: {data['id']}")
    
    def test_update_vendor(self, auth_headers):
        """PUT /api/settings/vendors/{id} - Update vendor."""
        if not TestVendorCRUD.created_vendor_id:
            pytest.skip("No vendor created to update")
        
        vendor_id = TestVendorCRUD.created_vendor_id
        payload = {
            "name": f"TEST_Vendor_Updated_{uuid.uuid4().hex[:6]}",
            "vendor_type": "medical_tpa",
            "feed_types": ["834"],
            "format": "csv",
            "sftp_host": "sftp.updated-vendor.com",
            "sftp_path": "/updated",
            "enabled": False
        }
        response = requests.put(f"{BASE_URL}/api/settings/vendors/{vendor_id}", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["format"] == "csv", "Format should be updated to csv"
        assert data["enabled"] == False, "Enabled should be False"
        print(f"✅ Updated vendor: {vendor_id}")


# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP TESTS (run last)
# ═══════════════════════════════════════════════════════════════════════════

class TestCleanup:
    """Cleanup test data."""
    
    def test_delete_schedule(self, auth_headers):
        """DELETE /api/sftp/schedules/{id} - Delete test schedule."""
        if not TestSFTPSchedules.created_schedule_id:
            pytest.skip("No schedule to delete")
        
        sched_id = TestSFTPSchedules.created_schedule_id
        response = requests.delete(f"{BASE_URL}/api/sftp/schedules/{sched_id}", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "deleted"
        print(f"✅ Deleted schedule: {sched_id}")
    
    def test_delete_connection(self, auth_headers):
        """DELETE /api/sftp/connections/{id} - Delete test connection."""
        if not TestSFTPConnections.created_connection_id:
            pytest.skip("No connection to delete")
        
        conn_id = TestSFTPConnections.created_connection_id
        response = requests.delete(f"{BASE_URL}/api/sftp/connections/{conn_id}", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "deleted"
        print(f"✅ Deleted connection: {conn_id}")
    
    def test_delete_vendor(self, auth_headers):
        """DELETE /api/settings/vendors/{id} - Delete test vendor."""
        if not TestVendorCRUD.created_vendor_id:
            pytest.skip("No vendor to delete")
        
        vendor_id = TestVendorCRUD.created_vendor_id
        response = requests.delete(f"{BASE_URL}/api/settings/vendors/{vendor_id}", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "deleted"
        print(f"✅ Deleted vendor: {vendor_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
