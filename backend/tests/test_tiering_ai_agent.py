"""
Test suite for Data Tiering Engine, Report Packages (Broker Deck, Carrier Bordereaux, Utilization Review),
and AI Provider Call Center Agent features.

Iteration 19 - Focus on new features added in this session.
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
    """Get authentication token for API calls."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TIERING ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTieringSummary:
    """Tests for GET /api/tiering/summary endpoint."""
    
    def test_tiering_summary_returns_200(self, api_client):
        """Verify tiering summary endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/tiering/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/tiering/summary returns 200")
    
    def test_tiering_summary_structure(self, api_client):
        """Verify tiering summary has correct structure with tier_1, tier_2, tier_3."""
        response = api_client.get(f"{BASE_URL}/api/tiering/summary")
        data = response.json()
        
        # Check required fields
        assert "tier_1" in data, "Missing tier_1 in response"
        assert "tier_2" in data, "Missing tier_2 in response"
        assert "tier_3" in data, "Missing tier_3 in response"
        assert "total_claims" in data, "Missing total_claims in response"
        
        # Check tier structure
        for tier_key in ["tier_1", "tier_2", "tier_3"]:
            tier = data[tier_key]
            assert "count" in tier, f"Missing count in {tier_key}"
            assert "total_paid" in tier, f"Missing total_paid in {tier_key}"
            assert "total_billed" in tier, f"Missing total_billed in {tier_key}"
            assert "label" in tier, f"Missing label in {tier_key}"
            assert "description" in tier, f"Missing description in {tier_key}"
        
        print(f"✅ Tiering summary structure valid: Tier 1={data['tier_1']['count']}, Tier 2={data['tier_2']['count']}, Tier 3={data['tier_3']['count']}, Total={data['total_claims']}")


class TestRiskDial:
    """Tests for GET /api/tiering/risk-dial endpoint."""
    
    def test_risk_dial_returns_200(self, api_client):
        """Verify risk dial endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/tiering/risk-dial")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/tiering/risk-dial returns 200")
    
    def test_risk_dial_structure(self, api_client):
        """Verify risk dial has groups array and summary."""
        response = api_client.get(f"{BASE_URL}/api/tiering/risk-dial")
        data = response.json()
        
        assert "groups" in data, "Missing groups in response"
        assert "summary" in data, "Missing summary in response"
        assert isinstance(data["groups"], list), "groups should be a list"
        
        # Check summary structure
        summary = data["summary"]
        assert "total_monitored" in summary, "Missing total_monitored in summary"
        assert "critical" in summary, "Missing critical in summary"
        assert "warning" in summary, "Missing warning in summary"
        assert "normal" in summary, "Missing normal in summary"
        
        print(f"✅ Risk dial structure valid: {summary['total_monitored']} monitored, {summary['critical']} critical, {summary['warning']} warning")
        
        # If there are groups, check their structure
        if data["groups"]:
            group = data["groups"][0]
            required_fields = ["group_id", "group_name", "specific_attachment_point", 
                             "aggregate_attachment_point", "specific_utilization_pct", 
                             "aggregate_utilization_pct", "alert_level"]
            for field in required_fields:
                assert field in group, f"Missing {field} in risk group"
            print(f"✅ Risk group structure valid: {group['group_name']} - {group['alert_level']}")


class TestClaimTierAnalysis:
    """Tests for GET /api/tiering/analyze/{claim_id} endpoint."""
    
    def test_analyze_nonexistent_claim_returns_404(self, api_client):
        """Verify analyzing non-existent claim returns 404."""
        response = api_client.get(f"{BASE_URL}/api/tiering/analyze/nonexistent-claim-id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ GET /api/tiering/analyze/nonexistent returns 404")
    
    def test_analyze_existing_claim(self, api_client):
        """Verify analyzing an existing claim returns tier classification."""
        # First get a claim ID
        claims_response = api_client.get(f"{BASE_URL}/api/claims", params={"limit": 1})
        if claims_response.status_code != 200 or not claims_response.json():
            pytest.skip("No claims available for testing")
        
        claim_id = claims_response.json()[0]["id"]
        response = api_client.get(f"{BASE_URL}/api/tiering/analyze/{claim_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "tier" in data, "Missing tier in response"
        assert "tier_label" in data, "Missing tier_label in response"
        assert "tier_reason" in data, "Missing tier_reason in response"
        assert "claim_id" in data, "Missing claim_id in response"
        assert data["tier"] in [1, 2, 3], f"Invalid tier value: {data['tier']}"
        
        print(f"✅ Claim {claim_id} classified as Tier {data['tier']} ({data['tier_label']})")


class TestBatchClassify:
    """Tests for POST /api/tiering/batch-classify endpoint."""
    
    def test_batch_classify_returns_200(self, api_client):
        """Verify batch classify endpoint returns 200."""
        response = api_client.post(f"{BASE_URL}/api/tiering/batch-classify", params={"limit": 10})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ POST /api/tiering/batch-classify returns 200")
    
    def test_batch_classify_structure(self, api_client):
        """Verify batch classify returns tier counts."""
        response = api_client.post(f"{BASE_URL}/api/tiering/batch-classify", params={"limit": 10})
        data = response.json()
        
        assert "tier_1" in data, "Missing tier_1 count"
        assert "tier_2" in data, "Missing tier_2 count"
        assert "tier_3" in data, "Missing tier_3 count"
        assert "processed" in data, "Missing processed count"
        
        print(f"✅ Batch classify: processed={data['processed']}, T1={data['tier_1']}, T2={data['tier_2']}, T3={data['tier_3']}")


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT PACKAGES TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokerDeck:
    """Tests for GET /api/reports/broker-deck endpoint."""
    
    def test_broker_deck_returns_200(self, api_client):
        """Verify broker deck endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/reports/broker-deck")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/reports/broker-deck returns 200")
    
    def test_broker_deck_structure(self, api_client):
        """Verify broker deck has groups array and totals."""
        response = api_client.get(f"{BASE_URL}/api/reports/broker-deck")
        data = response.json()
        
        assert "groups" in data, "Missing groups in response"
        assert "totals" in data, "Missing totals in response"
        assert isinstance(data["groups"], list), "groups should be a list"
        
        # Check totals structure
        totals = data["totals"]
        required_totals = ["total_premium", "total_claims_paid", "total_surplus", "overall_loss_ratio", "group_count"]
        for field in required_totals:
            assert field in totals, f"Missing {field} in totals"
        
        print(f"✅ Broker deck: {totals['group_count']} groups, Premium=${totals['total_premium']:,.2f}, Paid=${totals['total_claims_paid']:,.2f}, Surplus=${totals['total_surplus']:,.2f}, LR={totals['overall_loss_ratio']}%")
        
        # Check group structure if groups exist
        if data["groups"]:
            group = data["groups"][0]
            required_fields = ["group_id", "group_name", "total_premium", "claims_paid", "surplus", "loss_ratio", "pepm"]
            for field in required_fields:
                assert field in group, f"Missing {field} in broker deck group"
            print(f"✅ Broker deck group structure valid: {group['group_name']}")


class TestCarrierBordereaux:
    """Tests for GET /api/reports/carrier-bordereaux endpoint."""
    
    def test_carrier_bordereaux_returns_200(self, api_client):
        """Verify carrier bordereaux endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/reports/carrier-bordereaux")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/reports/carrier-bordereaux returns 200")
    
    def test_carrier_bordereaux_structure(self, api_client):
        """Verify carrier bordereaux has groups with member details."""
        response = api_client.get(f"{BASE_URL}/api/reports/carrier-bordereaux")
        data = response.json()
        
        assert "groups" in data, "Missing groups in response"
        assert "total_groups" in data, "Missing total_groups in response"
        
        print(f"✅ Carrier bordereaux: {data['total_groups']} groups")
        
        # Check group structure if groups exist
        if data["groups"]:
            group = data["groups"][0]
            required_fields = ["group_id", "group_name", "total_members", "active_members", 
                             "termed_members", "expected_premium", "actual_premium", "member_details"]
            for field in required_fields:
                assert field in group, f"Missing {field} in bordereaux group"
            
            # Check member_details is a list
            assert isinstance(group["member_details"], list), "member_details should be a list"
            print(f"✅ Bordereaux group structure valid: {group['group_name']} - {group['active_members']} active, {group['termed_members']} termed")


class TestUtilizationReview:
    """Tests for GET /api/reports/utilization-review endpoint."""
    
    def test_utilization_review_returns_200(self, api_client):
        """Verify utilization review endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/reports/utilization-review")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/reports/utilization-review returns 200")
    
    def test_utilization_review_structure(self, api_client):
        """Verify utilization review has top providers, CPTs, and network leakage."""
        response = api_client.get(f"{BASE_URL}/api/reports/utilization-review")
        data = response.json()
        
        assert "top_providers" in data, "Missing top_providers in response"
        assert "top_cpt_codes" in data, "Missing top_cpt_codes in response"
        assert "network_leakage" in data, "Missing network_leakage in response"
        assert "claims_by_type" in data, "Missing claims_by_type in response"
        
        # Check network leakage structure
        leakage = data["network_leakage"]
        required_leakage = ["total_claims", "oon_claims", "oon_percentage", "oon_paid", "total_paid", "oon_cost_percentage"]
        for field in required_leakage:
            assert field in leakage, f"Missing {field} in network_leakage"
        
        print(f"✅ Utilization review: {len(data['top_providers'])} top providers, {len(data['top_cpt_codes'])} top CPTs")
        print(f"   Network leakage: {leakage['oon_claims']}/{leakage['total_claims']} OON claims ({leakage['oon_percentage']}%)")
        
        # Check provider structure if providers exist
        if data["top_providers"]:
            provider = data["top_providers"][0]
            required_fields = ["provider_npi", "provider_name", "total_paid", "claim_count"]
            for field in required_fields:
                assert field in provider, f"Missing {field} in top provider"
            print(f"✅ Top provider structure valid: {provider['provider_name']}")


# ═══════════════════════════════════════════════════════════════════════════════
# AI PROVIDER CALL CENTER AGENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAIAgentChat:
    """Tests for POST /api/ai-agent/chat endpoint."""
    
    def test_chat_returns_200(self, api_client):
        """Verify chat endpoint returns 200 with valid message."""
        response = api_client.post(f"{BASE_URL}/api/ai-agent/chat", json={
            "message": "Hello, I need to check eligibility",
            "provider_tax_id": "12-3456789"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ POST /api/ai-agent/chat returns 200")
    
    def test_chat_response_structure(self, api_client):
        """Verify chat response has required fields."""
        response = api_client.post(f"{BASE_URL}/api/ai-agent/chat", json={
            "message": "What is the status of claim #12345?",
            "provider_tax_id": "12-3456789"
        })
        data = response.json()
        
        assert "response" in data, "Missing response in chat response"
        assert "session_id" in data, "Missing session_id in chat response"
        assert isinstance(data["response"], str), "response should be a string"
        assert len(data["response"]) > 0, "response should not be empty"
        
        print(f"✅ Chat response structure valid, session_id={data['session_id'][:8]}...")
        print(f"   AI Response (truncated): {data['response'][:100]}...")


class TestAIAgentSessions:
    """Tests for GET /api/ai-agent/sessions endpoint."""
    
    def test_sessions_returns_200(self, api_client):
        """Verify sessions endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/ai-agent/sessions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/ai-agent/sessions returns 200")
    
    def test_sessions_is_list(self, api_client):
        """Verify sessions returns a list."""
        response = api_client.get(f"{BASE_URL}/api/ai-agent/sessions")
        data = response.json()
        
        assert isinstance(data, list), "sessions should return a list"
        print(f"✅ Sessions list: {len(data)} sessions found")
        
        # Check session structure if sessions exist
        if data:
            session = data[0]
            required_fields = ["session_id", "last_message", "last_timestamp", "message_count"]
            for field in required_fields:
                assert field in session, f"Missing {field} in session"
            print(f"✅ Session structure valid: {session['message_count']} messages")


class TestAIAgentSessionMessages:
    """Tests for GET /api/ai-agent/sessions/{session_id}/messages endpoint."""
    
    def test_session_messages_returns_200(self, api_client):
        """Verify session messages endpoint returns 200 for existing session."""
        # First create a session by sending a message
        chat_response = api_client.post(f"{BASE_URL}/api/ai-agent/chat", json={
            "message": "Test message for session",
            "provider_tax_id": "99-9999999"
        })
        session_id = chat_response.json().get("session_id")
        
        response = api_client.get(f"{BASE_URL}/api/ai-agent/sessions/{session_id}/messages")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "messages should return a list"
        assert len(data) >= 2, "Should have at least user message and assistant response"
        
        print(f"✅ GET /api/ai-agent/sessions/{session_id[:8]}.../messages returns {len(data)} messages")


class TestAIAgentEscalation:
    """Tests for POST /api/ai-agent/escalate endpoint."""
    
    def test_escalate_returns_200(self, api_client):
        """Verify escalation endpoint returns 200."""
        response = api_client.post(f"{BASE_URL}/api/ai-agent/escalate", json={
            "provider_tax_id": "12-3456789",
            "member_id": "TEST-MEMBER-001",
            "query_summary": "Test escalation for eligibility verification",
            "session_id": str(uuid.uuid4())
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ POST /api/ai-agent/escalate returns 200")
    
    def test_escalate_creates_ticket(self, api_client):
        """Verify escalation creates a call log ticket."""
        response = api_client.post(f"{BASE_URL}/api/ai-agent/escalate", json={
            "provider_tax_id": "TEST-TIN-123",
            "member_id": "TEST-MEMBER-002",
            "query_summary": "Test escalation ticket creation",
            "session_id": str(uuid.uuid4())
        })
        data = response.json()
        
        assert "id" in data, "Missing id in escalation response"
        assert "status" in data, "Missing status in escalation response"
        assert data["status"] == "open", f"Expected status 'open', got {data['status']}"
        
        print(f"✅ Escalation ticket created: {data['id'][:8]}...")


class TestAIAgentCallLogs:
    """Tests for GET /api/ai-agent/call-logs endpoint."""
    
    def test_call_logs_returns_200(self, api_client):
        """Verify call logs endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/ai-agent/call-logs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/ai-agent/call-logs returns 200")
    
    def test_call_logs_is_list(self, api_client):
        """Verify call logs returns a list."""
        response = api_client.get(f"{BASE_URL}/api/ai-agent/call-logs")
        data = response.json()
        
        assert isinstance(data, list), "call_logs should return a list"
        print(f"✅ Call logs: {len(data)} logs found")
        
        # Check log structure if logs exist
        if data:
            log = data[0]
            required_fields = ["id", "type", "status", "created_at"]
            for field in required_fields:
                assert field in log, f"Missing {field} in call log"
            print(f"✅ Call log structure valid: status={log['status']}")


class TestAIAgentResolveCallLog:
    """Tests for PUT /api/ai-agent/call-logs/{id}/resolve endpoint."""
    
    def test_resolve_nonexistent_returns_404(self, api_client):
        """Verify resolving non-existent call log returns 404."""
        response = api_client.put(f"{BASE_URL}/api/ai-agent/call-logs/nonexistent-id/resolve")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ PUT /api/ai-agent/call-logs/nonexistent/resolve returns 404")
    
    def test_resolve_existing_call_log(self, api_client):
        """Verify resolving an existing call log works."""
        # First create an escalation
        escalate_response = api_client.post(f"{BASE_URL}/api/ai-agent/escalate", json={
            "provider_tax_id": "RESOLVE-TEST-TIN",
            "member_id": "RESOLVE-TEST-MEMBER",
            "query_summary": "Test escalation for resolution test",
            "session_id": str(uuid.uuid4())
        })
        log_id = escalate_response.json().get("id")
        
        # Now resolve it
        response = api_client.put(f"{BASE_URL}/api/ai-agent/call-logs/{log_id}/resolve", params={"notes": "Resolved via test"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "resolved", f"Expected status 'resolved', got {data['status']}"
        
        print(f"✅ Call log {log_id[:8]}... resolved successfully")


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN BUILDER TESTS (Regression for all tabs)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlanBuilder:
    """Tests for Plan Builder endpoints."""
    
    def test_list_plans_returns_200(self, api_client):
        """Verify list plans endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✅ GET /api/plans returns 200 ({len(response.json())} plans)")
    
    def test_get_plan_with_all_fields(self, api_client):
        """Verify plan has all new fields (benefit_modules, network_tiers, risk_management)."""
        # Get first plan
        plans_response = api_client.get(f"{BASE_URL}/api/plans")
        if not plans_response.json():
            pytest.skip("No plans available for testing")
        
        plan_id = plans_response.json()[0]["id"]
        response = api_client.get(f"{BASE_URL}/api/plans/{plan_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check basic fields
        basic_fields = ["id", "name", "plan_type", "deductible_individual", "deductible_family", 
                       "oop_max_individual", "oop_max_family", "network_type"]
        for field in basic_fields:
            assert field in data, f"Missing {field} in plan"
        
        print(f"✅ Plan {data['name']} has all basic fields")
        
        # Check for new fields (may not exist in older plans)
        if "benefit_modules" in data and data["benefit_modules"]:
            print(f"   benefit_modules: {len(data['benefit_modules'])} modules")
        if "network_tiers" in data and data["network_tiers"]:
            print(f"   network_tiers: {len(data['network_tiers'])} tiers")
        if "risk_management" in data and data["risk_management"]:
            print(f"   risk_management: specific={data['risk_management'].get('specific_attachment_point', 0)}, aggregate={data['risk_management'].get('aggregate_attachment_point', 0)}")


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD RISK DIAL INTEGRATION TEST
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardIntegration:
    """Tests for Dashboard with Risk Dial widget."""
    
    def test_dashboard_metrics_returns_200(self, api_client):
        """Verify dashboard metrics endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/metrics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/dashboard/metrics returns 200")
    
    def test_funding_health_returns_200(self, api_client):
        """Verify funding health endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/funding-health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ GET /api/dashboard/funding-health returns 200")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
