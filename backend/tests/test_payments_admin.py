"""
Test suite for Phase A/B/C features:
- Payment & Check Run (summary, batch, reconciliation)
- Admin Portal (portal roles, system overview, TPA onboarding, traceability)
- Audit Logs (filtered logs, summary)
- Rx Rules (template, drug classification)
- Groups (auto-adjust tiers)
- Claims (EOB/EOP PDFs, IDR tracking)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Session-level auth to share across all tests
_auth_token = None
_auth_headers = None

def get_auth():
    global _auth_token, _auth_headers
    if _auth_token is None:
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@fletchflow.com",
            "password": "Demo123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        _auth_token = data.get("access_token") or data.get("token")
        _auth_headers = {"Authorization": f"Bearer {_auth_token}", "Content-Type": "application/json"}
    return _auth_headers


# ── Payment System Tests ──

def test_payment_summary_returns_structure():
    """GET /api/payments/summary - returns payment summary"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/payments/summary", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    # Verify structure
    assert "by_method" in data
    assert "by_status" in data
    assert "total_payments" in data
    assert "total_amount" in data
    
    # Verify types
    assert isinstance(data["total_payments"], int)
    assert isinstance(data["total_amount"], (int, float))
    print(f"✓ Payment summary: {data['total_payments']} payments, ${data['total_amount']:,.2f} total")


def test_create_payment_batch():
    """POST /api/payments/batch - creates payment batch for approved claims"""
    headers = get_auth()
    
    # First check if there are approved claims
    claims_resp = requests.get(f"{BASE_URL}/api/claims?claim_status=approved&limit=5", headers=headers)
    assert claims_resp.status_code == 200
    
    # Try to create batch
    response = requests.post(f"{BASE_URL}/api/payments/batch", headers=headers, json={
        "payment_method": "ach",
        "funding_source": "aso",
        "description": "Test batch from pytest"
    })
    
    # Either 200 (batch created) or 400 (no approved claims)
    assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}, {response.text}"
    
    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        assert "payment_count" in data
        assert "total_amount" in data
        assert data["payment_method"] == "ach"
        print(f"✓ Batch created: {data['payment_count']} payments, ${data['total_amount']:,.2f}")
    else:
        # 400 means no approved claims awaiting payment
        assert "No approved claims" in response.json().get("detail", "")
        print("✓ Batch endpoint working (no approved claims available)")


def test_reconciliation_returns_structure():
    """GET /api/payments/reconciliation - returns claims vs payments reconciliation"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/payments/reconciliation", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    # Verify structure
    assert "claims" in data
    assert "payments" in data
    assert "discrepancy" in data
    
    # Verify claims structure
    claims = data["claims"]
    assert "total_billed" in claims
    assert "total_allowed" in claims
    assert "total_paid" in claims
    assert "claim_count" in claims
    
    # Verify payments structure
    payments = data["payments"]
    assert "total_disbursed" in payments
    assert "payment_count" in payments
    
    print(f"✓ Reconciliation: Claims paid ${claims['total_paid']:,.2f}, Disbursed ${payments['total_disbursed']:,.2f}, Discrepancy ${data['discrepancy']:,.2f}")


# ── Admin Portal Tests ──

def test_portal_roles_returns_five_roles():
    """GET /api/admin/portal-roles - returns 5 portal roles"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/admin/portal-roles", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    # Should have 5 roles
    assert len(data) == 5, f"Expected 5 roles, got {len(data)}"
    
    expected_roles = ["admin", "tpa_admin", "mgu_admin", "carrier_viewer", "analytics_viewer"]
    for role in expected_roles:
        assert role in data, f"Missing role: {role}"
        assert "label" in data[role]
        assert "permissions" in data[role]
    
    print(f"✓ Portal roles: {list(data.keys())}")


def test_system_overview_returns_counts():
    """GET /api/admin/system-overview - returns system counts"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/admin/system-overview", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    # Verify all expected fields
    expected_fields = ["users", "groups", "plans", "members", "claims", "tpas", "payments"]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"
    
    # Users should have total and active
    assert "total" in data["users"]
    assert "active" in data["users"]
    
    # Recent activity
    assert "recent_activity" in data
    
    print(f"✓ System overview: {data['users']['total']} users, {data['groups']} groups, {data['claims']} claims")


def test_onboard_tpa():
    """POST /api/admin/tpas - onboards a TPA"""
    headers = get_auth()
    unique_tax_id = f"99-{uuid.uuid4().hex[:7].upper()}"
    
    response = requests.post(f"{BASE_URL}/api/admin/tpas", headers=headers, json={
        "name": f"TEST_TPA_{unique_tax_id}",
        "tax_id": unique_tax_id,
        "contact_name": "Test Contact",
        "contact_email": "test@tpa.com",
        "contact_phone": "555-1234",
        "data_feed_type": "edi_834_837",
        "group_ids": [],
        "notes": "Created by pytest"
    })
    
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    assert "id" in data
    assert data["name"].startswith("TEST_TPA_")
    assert data["tax_id"] == unique_tax_id
    assert data["status"] == "active"
    
    print(f"✓ TPA onboarded: {data['name']} (ID: {data['id'][:8]})")


def test_traceability_returns_chain():
    """GET /api/admin/traceability/{claim_id} - returns full lifecycle chain"""
    headers = get_auth()
    
    # First get a claim
    claims_resp = requests.get(f"{BASE_URL}/api/claims?limit=1", headers=headers)
    assert claims_resp.status_code == 200
    claims = claims_resp.json()
    
    if not claims:
        pytest.skip("No claims available for traceability test")
    
    claim_id = claims[0]["id"]
    
    response = requests.get(f"{BASE_URL}/api/admin/traceability/{claim_id}", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    # Verify chain structure
    assert "claim" in data
    assert "member" in data
    assert "plan" in data
    assert "group" in data
    assert "payment" in data
    assert "audit_trail" in data
    
    # Claim should have expected fields
    claim = data["claim"]
    assert "id" in claim
    assert "claim_number" in claim
    assert "status" in claim
    
    print(f"✓ Traceability for claim {claim['claim_number']}: Plan={data['plan']['name'] if data['plan'] else 'N/A'}, Group={data['group']['name'] if data['group'] else 'N/A'}")


# ── Audit Log Tests ──

def test_audit_logs_returns_structure():
    """GET /api/audit-logs - returns filtered audit logs"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/audit-logs?limit=10", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    assert "logs" in data
    assert "total" in data
    assert "limit" in data
    assert "skip" in data
    
    if data["logs"]:
        log = data["logs"][0]
        assert "id" in log
        assert "action" in log
        assert "timestamp" in log
    
    print(f"✓ Audit logs: {data['total']} total events, showing {len(data['logs'])}")


def test_audit_summary_returns_structure():
    """GET /api/audit-logs/summary - returns summary by action"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/audit-logs/summary", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    assert "total_events" in data
    assert "by_action" in data
    assert isinstance(data["by_action"], list)
    
    if data["by_action"]:
        action = data["by_action"][0]
        assert "action" in action
        assert "count" in action
        assert "last_occurrence" in action
    
    print(f"✓ Audit summary: {data['total_events']} total events, {len(data['by_action'])} action types")


# ── Rx Rules Tests ──

def test_rx_template_returns_structure():
    """GET /api/plans/rx-rules/template - returns Rx rules template with formulary tiers"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/plans/rx-rules/template", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    # Verify structure
    assert "enabled" in data
    assert "formulary_tiers" in data
    assert "glp1_policy" in data
    assert "mandatory_generic_substitution" in data
    
    # Verify formulary tiers
    tiers = data["formulary_tiers"]
    expected_tiers = ["tier1_generic", "tier2_preferred_brand", "tier3_non_preferred", "tier4_specialty", "tier5_preventive"]
    for tier in expected_tiers:
        assert tier in tiers, f"Missing tier: {tier}"
        assert "label" in tiers[tier]
        assert "copay" in tiers[tier]
    
    print(f"✓ Rx template: {len(tiers)} formulary tiers, GLP-1 policy: {data['glp1_policy']}")


def test_classify_glp1_drug():
    """GET /api/plans/rx-rules/classify?hcpcs_code=J3490 - classifies GLP-1 drug correctly"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/plans/rx-rules/classify?hcpcs_code=J3490", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    # J3490 is Ozempic (GLP-1)
    assert data["is_glp1"] == True, "J3490 should be classified as GLP-1"
    assert data["tier"] == "tier4_specialty"
    assert "Ozempic" in data["drug_name"]
    assert data["requires_prior_auth"] == True
    assert data["step_therapy_required"] == True
    
    print(f"✓ GLP-1 classification: {data['drug_name']} -> {data['tier_label']}")


def test_classify_generic_drug():
    """GET /api/plans/rx-rules/classify?drug_name=metformin - classifies generic drug"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/plans/rx-rules/classify?drug_name=metformin", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    assert data["tier"] == "tier1_generic"
    assert data["is_glp1"] == False
    
    print(f"✓ Generic classification: metformin -> {data['tier_label']}")


# ── Groups Auto-Adjust Tiers Tests ──

def test_auto_adjust_tiers():
    """POST /api/groups/{group_id}/auto-adjust-tiers - auto-adjusts enrollment tiers"""
    headers = get_auth()
    
    # First get a group
    groups_resp = requests.get(f"{BASE_URL}/api/groups?status=active", headers=headers)
    assert groups_resp.status_code == 200
    groups = groups_resp.json()
    
    if not groups:
        pytest.skip("No groups available for auto-adjust test")
    
    group_id = groups[0]["id"]
    
    response = requests.post(f"{BASE_URL}/api/groups/{group_id}/auto-adjust-tiers", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    assert "group_id" in data
    assert "adjustments" in data
    assert "total_adjusted" in data
    assert data["group_id"] == group_id
    
    print(f"✓ Auto-adjust tiers: {data['total_adjusted']} members adjusted")


# ── EOB/EOP PDF Tests ──

def test_eob_pdf_returns_pdf():
    """GET /api/claims/{claim_id}/eob.pdf - returns valid PDF"""
    headers = get_auth()
    
    # First get a claim
    claims_resp = requests.get(f"{BASE_URL}/api/claims?limit=1", headers=headers)
    assert claims_resp.status_code == 200
    claims = claims_resp.json()
    
    if not claims:
        pytest.skip("No claims available for EOB test")
    
    claim_id = claims[0]["id"]
    
    response = requests.get(f"{BASE_URL}/api/claims/{claim_id}/eob.pdf", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    
    # Verify PDF content type
    assert response.headers.get("content-type") == "application/pdf"
    
    # Verify PDF magic bytes
    assert response.content[:4] == b'%PDF', "Response is not a valid PDF"
    
    print(f"✓ EOB PDF generated: {len(response.content)} bytes")


def test_eop_pdf_returns_pdf():
    """GET /api/claims/{claim_id}/eop.pdf - returns valid PDF"""
    headers = get_auth()
    
    # First get a claim
    claims_resp = requests.get(f"{BASE_URL}/api/claims?limit=1", headers=headers)
    assert claims_resp.status_code == 200
    claims = claims_resp.json()
    
    if not claims:
        pytest.skip("No claims available for EOP test")
    
    claim_id = claims[0]["id"]
    
    response = requests.get(f"{BASE_URL}/api/claims/{claim_id}/eop.pdf", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    
    # Verify PDF content type
    assert response.headers.get("content-type") == "application/pdf"
    
    # Verify PDF magic bytes
    assert response.content[:4] == b'%PDF', "Response is not a valid PDF"
    
    print(f"✓ EOP PDF generated: {len(response.content)} bytes")


# ── IDR Tracking Tests ──

def test_update_idr_tracking():
    """PUT /api/claims/{claim_id}/idr - updates IDR tracking"""
    headers = get_auth()
    
    # First get a claim
    claims_resp = requests.get(f"{BASE_URL}/api/claims?limit=1", headers=headers)
    assert claims_resp.status_code == 200
    claims = claims_resp.json()
    
    if not claims:
        pytest.skip("No claims available for IDR test")
    
    claim_id = claims[0]["id"]
    idr_case = f"IDR-{uuid.uuid4().hex[:8].upper()}"
    
    response = requests.put(
        f"{BASE_URL}/api/claims/{claim_id}/idr",
        headers=headers,
        params={
            "idr_case_number": idr_case,
            "idr_status": "pending",
            "notes": "Test IDR case from pytest"
        }
    )
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    assert data["claim_id"] == claim_id
    assert data["idr_case_number"] == idr_case
    assert data["idr_status"] == "pending"
    
    print(f"✓ IDR tracking updated: Case {idr_case}")


# ── Payment List Tests ──

def test_list_payments():
    """GET /api/payments - list payments with filters"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/payments?limit=10", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    assert isinstance(data, list)
    
    if data:
        payment = data[0]
        assert "id" in payment
        assert "claim_id" in payment
        assert "amount" in payment
        assert "payment_method" in payment
        assert "status" in payment
    
    print(f"✓ Payments list: {len(data)} payments returned")


def test_list_batches():
    """GET /api/payments/batches - list payment batches"""
    headers = get_auth()
    response = requests.get(f"{BASE_URL}/api/payments/batches", headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    assert isinstance(data, list)
    
    if data:
        batch = data[0]
        assert "id" in batch
        assert "payment_count" in batch
        assert "total_amount" in batch
        assert "status" in batch
    
    print(f"✓ Batches list: {len(data)} batches returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
