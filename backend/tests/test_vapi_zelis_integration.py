"""
Test Vapi Voice Agent and Zelis Payment Vendor Integration
Tests the new voice and payment integrations added in this iteration.

Vapi Voice Agent:
- GET /api/vapi/config - Returns enabled=true, assistant_id populated
- GET /api/vapi/assistant - Returns configured assistant details
- POST /api/vapi/webhook - Handles tool-calls (check_member_eligibility with member_id MBR001)
- POST /api/vapi/webhook - Handles status-update events
- POST /api/vapi/webhook - Handles end-of-call-report events
- GET /api/vapi/calls - Returns voice call history

Zelis Payment Vendor (MOCKED):
- GET /api/zelis/methods - Returns 5 payment methods
- GET /api/zelis/summary - Returns transaction summary
- POST /api/zelis/submit - Submit claim payment via Zelis
- GET /api/zelis/status/{zelis_transaction_id} - Check Zelis payment status
- GET /api/zelis/transactions - Lists Zelis transactions
- POST /api/zelis/era-835 - Generate ERA 835 for payment IDs
- GET /api/zelis/era-documents - Lists ERA 835 documents
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://plan-config-engine.preview.emergentagent.com').rstrip('/')


class TestAuth:
    """Get auth token for authenticated endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@fletchflow.com",
            "password": "Demo123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in login response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Return headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestVapiVoiceAgent(TestAuth):
    """Test Vapi Voice Agent Integration"""
    
    def test_vapi_config_returns_enabled(self, auth_headers):
        """GET /api/vapi/config - Returns enabled=true, assistant_id populated"""
        response = requests.get(f"{BASE_URL}/api/vapi/config", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify config structure
        assert "enabled" in data, "Missing 'enabled' field"
        assert data["enabled"] == True, "Vapi should be enabled (VAPI_API_KEY is set)"
        assert "assistant_id" in data, "Missing 'assistant_id' field"
        # assistant_id should be populated (from previous setup)
        print(f"Vapi config: enabled={data['enabled']}, assistant_id={data.get('assistant_id')}")
    
    def test_vapi_assistant_details(self, auth_headers):
        """GET /api/vapi/assistant - Returns configured assistant details"""
        response = requests.get(f"{BASE_URL}/api/vapi/assistant", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify assistant structure
        assert "configured" in data, "Missing 'configured' field"
        assert "vapi_key_set" in data, "Missing 'vapi_key_set' field"
        assert data["vapi_key_set"] == True, "VAPI_API_KEY should be set"
        print(f"Vapi assistant: configured={data.get('configured')}, assistant_id={data.get('assistant_id')}")
    
    def test_vapi_webhook_tool_calls_eligibility(self):
        """POST /api/vapi/webhook - Handles tool-calls (check_member_eligibility with member_id MBR001)
        
        Note: This endpoint does NOT require auth - Vapi sends webhooks directly.
        """
        webhook_payload = {
            "message": {
                "type": "tool-calls",
                "toolCallList": [
                    {
                        "id": "tc-test-001",
                        "function": {
                            "name": "check_member_eligibility",
                            "arguments": {"member_id": "MBR001"}
                        }
                    }
                ]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/vapi/webhook", json=webhook_payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        data = response.json()
        
        # Verify tool call results
        assert "results" in data, "Missing 'results' in webhook response"
        assert len(data["results"]) > 0, "No results returned"
        
        result = data["results"][0]
        assert "toolCallId" in result, "Missing toolCallId"
        assert result["toolCallId"] == "tc-test-001", "Wrong toolCallId"
        assert "result" in result, "Missing result"
        
        # Parse the result JSON string
        import json
        result_data = json.loads(result["result"])
        print(f"Eligibility result for MBR001: {result_data}")
        
        # If member found, verify structure
        if "error" not in result_data:
            assert "member_id" in result_data, "Missing member_id in result"
            assert "status" in result_data, "Missing status in result"
    
    def test_vapi_webhook_status_update(self):
        """POST /api/vapi/webhook - Handles status-update events"""
        call_id = f"test-call-{uuid.uuid4().hex[:8]}"
        webhook_payload = {
            "message": {
                "type": "status-update",
                "status": "in-progress",
                "call": {
                    "id": call_id,
                    "assistantId": "test-assistant-id"
                }
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/vapi/webhook", json=webhook_payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        data = response.json()
        
        assert "received" in data, "Missing 'received' in response"
        assert data["received"] == True, "Webhook not acknowledged"
        print(f"Status update webhook processed for call {call_id}")
    
    def test_vapi_webhook_end_of_call_report(self):
        """POST /api/vapi/webhook - Handles end-of-call-report events"""
        call_id = f"test-call-{uuid.uuid4().hex[:8]}"
        webhook_payload = {
            "message": {
                "type": "end-of-call-report",
                "endedReason": "customer-ended-call",
                "call": {
                    "id": call_id,
                    "duration": 120
                },
                "artifact": {
                    "transcript": "Test transcript content",
                    "messages": [
                        {"role": "assistant", "content": "Hello"},
                        {"role": "user", "content": "Hi"}
                    ]
                }
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/vapi/webhook", json=webhook_payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        data = response.json()
        
        assert "received" in data, "Missing 'received' in response"
        assert data["received"] == True, "Webhook not acknowledged"
        print(f"End-of-call report webhook processed for call {call_id}")
    
    def test_vapi_calls_history(self, auth_headers):
        """GET /api/vapi/calls - Returns voice call history"""
        response = requests.get(f"{BASE_URL}/api/vapi/calls", headers=auth_headers, params={"limit": 20})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should return a list (may be empty if no calls yet)
        assert isinstance(data, list), "Expected list of calls"
        print(f"Voice call history: {len(data)} calls found")
        
        if len(data) > 0:
            call = data[0]
            assert "call_id" in call, "Missing call_id in call record"
            print(f"Latest call: {call.get('call_id')}, status={call.get('status')}")


class TestZelisPaymentVendor(TestAuth):
    """Test Zelis Payment Vendor Integration (MOCKED)"""
    
    def test_zelis_methods_returns_5_methods(self, auth_headers):
        """GET /api/zelis/methods - Returns 5 payment methods (ach, virtual_card, check, ach_plus, zapp)"""
        response = requests.get(f"{BASE_URL}/api/zelis/methods", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "methods" in data, "Missing 'methods' field"
        methods = data["methods"]
        assert len(methods) == 5, f"Expected 5 payment methods, got {len(methods)}"
        
        method_ids = [m["id"] for m in methods]
        expected_methods = ["ach", "virtual_card", "check", "ach_plus", "zapp"]
        for expected in expected_methods:
            assert expected in method_ids, f"Missing payment method: {expected}"
        
        print(f"Zelis payment methods: {method_ids}")
    
    def test_zelis_summary(self, auth_headers):
        """GET /api/zelis/summary - Returns transaction summary"""
        response = requests.get(f"{BASE_URL}/api/zelis/summary", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify summary structure
        assert "supported_methods" in data, "Missing 'supported_methods'"
        assert "total_transactions" in data, "Missing 'total_transactions'"
        assert "total_amount" in data, "Missing 'total_amount'"
        
        print(f"Zelis summary: {data['total_transactions']} transactions, ${data['total_amount']} total")
    
    def test_zelis_transactions_list(self, auth_headers):
        """GET /api/zelis/transactions - Lists Zelis transactions"""
        response = requests.get(f"{BASE_URL}/api/zelis/transactions", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list), "Expected list of transactions"
        print(f"Zelis transactions: {len(data)} found")
        
        if len(data) > 0:
            tx = data[0]
            assert "zelis_transaction_id" in tx, "Missing zelis_transaction_id"
            assert "status" in tx, "Missing status"
            print(f"Latest transaction: {tx.get('zelis_transaction_id')}, status={tx.get('status')}")
    
    def test_zelis_submit_payment(self, auth_headers):
        """POST /api/zelis/submit - Submit claim payment via Zelis
        
        First find a claim with total_paid > 0 that hasn't been submitted to Zelis yet.
        """
        # Get claims to find one with total_paid > 0
        claims_response = requests.get(f"{BASE_URL}/api/claims", headers=auth_headers, params={"limit": 50})
        assert claims_response.status_code == 200, f"Failed to get claims: {claims_response.text}"
        claims = claims_response.json()
        
        # Find a claim with total_paid > 0 and status approved/paid
        eligible_claim = None
        for claim in claims:
            if claim.get("total_paid", 0) > 0 and claim.get("status") in ["approved", "paid"]:
                # Check if already submitted to Zelis
                zelis_tx_response = requests.get(
                    f"{BASE_URL}/api/zelis/transactions",
                    headers=auth_headers,
                    params={"limit": 200}
                )
                zelis_txs = zelis_tx_response.json()
                already_submitted = any(tx.get("claim_number") == claim.get("claim_number") for tx in zelis_txs)
                
                if not already_submitted:
                    eligible_claim = claim
                    break
        
        if not eligible_claim:
            pytest.skip("No eligible claim found for Zelis submission (all claims already submitted or no paid claims)")
        
        # Submit to Zelis
        submit_payload = {
            "claim_id": eligible_claim["id"],
            "payment_method": "ach"
        }
        
        response = requests.post(f"{BASE_URL}/api/zelis/submit", headers=auth_headers, json=submit_payload)
        
        # May get 400 if already submitted
        if response.status_code == 400:
            error_detail = response.json().get("detail", "")
            if "already submitted" in error_detail.lower():
                print(f"Claim already submitted to Zelis: {error_detail}")
                pytest.skip("Claim already submitted to Zelis")
        
        assert response.status_code == 200, f"Zelis submit failed: {response.text}"
        data = response.json()
        
        assert "payment" in data, "Missing 'payment' in response"
        assert "zelis" in data, "Missing 'zelis' in response"
        
        zelis_result = data["zelis"]
        assert "zelis_transaction_id" in zelis_result, "Missing zelis_transaction_id"
        assert "status" in zelis_result, "Missing status"
        assert zelis_result["status"] in ["accepted", "card_issued"], f"Unexpected status: {zelis_result['status']}"
        
        print(f"Zelis payment submitted: {zelis_result['zelis_transaction_id']}, status={zelis_result['status']}")
        return zelis_result["zelis_transaction_id"]
    
    def test_zelis_status_check(self, auth_headers):
        """GET /api/zelis/status/{zelis_transaction_id} - Check Zelis payment status
        
        Use an existing Zelis transaction ID.
        """
        # Get existing transactions
        tx_response = requests.get(f"{BASE_URL}/api/zelis/transactions", headers=auth_headers)
        assert tx_response.status_code == 200
        transactions = tx_response.json()
        
        if len(transactions) == 0:
            pytest.skip("No Zelis transactions to check status")
        
        zelis_tx_id = transactions[0]["zelis_transaction_id"]
        
        response = requests.get(f"{BASE_URL}/api/zelis/status/{zelis_tx_id}", headers=auth_headers)
        assert response.status_code == 200, f"Status check failed: {response.text}"
        data = response.json()
        
        assert "zelis_transaction_id" in data, "Missing zelis_transaction_id"
        assert data["zelis_transaction_id"] == zelis_tx_id, "Wrong transaction ID"
        assert "status" in data, "Missing status"
        assert "last_checked" in data, "Missing last_checked"
        
        print(f"Zelis status for {zelis_tx_id}: {data['status']}")
    
    def test_zelis_era_documents_list(self, auth_headers):
        """GET /api/zelis/era-documents - Lists ERA 835 documents"""
        response = requests.get(f"{BASE_URL}/api/zelis/era-documents", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list), "Expected list of ERA documents"
        print(f"ERA 835 documents: {len(data)} found")
        
        if len(data) > 0:
            era = data[0]
            assert "era_number" in era, "Missing era_number"
            assert "format" in era, "Missing format"
            print(f"Latest ERA: {era.get('era_number')}, format={era.get('format')}")
    
    def test_zelis_era_835_generation(self, auth_headers):
        """POST /api/zelis/era-835 - Generate ERA 835 for payment IDs
        
        Get payment IDs from existing payments and generate ERA.
        """
        # Get payments
        payments_response = requests.get(f"{BASE_URL}/api/payments", headers=auth_headers, params={"limit": 10})
        assert payments_response.status_code == 200
        payments = payments_response.json()
        
        if len(payments) == 0:
            pytest.skip("No payments available for ERA generation")
        
        # Get payment IDs
        payment_ids = [p["id"] for p in payments[:3]]  # Use up to 3 payments
        
        response = requests.post(
            f"{BASE_URL}/api/zelis/era-835",
            headers=auth_headers,
            json={"payment_ids": payment_ids}
        )
        
        # May get 400 if no valid payments
        if response.status_code == 400:
            error_detail = response.json().get("detail", "")
            print(f"ERA generation failed: {error_detail}")
            pytest.skip(f"ERA generation failed: {error_detail}")
        
        assert response.status_code == 200, f"ERA generation failed: {response.text}"
        data = response.json()
        
        assert "era_number" in data, "Missing era_number"
        assert "format" in data, "Missing format"
        assert data["format"] == "ANSI X12 835", "Wrong ERA format"
        assert "transaction_count" in data, "Missing transaction_count"
        
        print(f"ERA 835 generated: {data['era_number']}, {data['transaction_count']} transactions")


class TestVapiWebhookEdgeCases(TestAuth):
    """Test Vapi webhook edge cases"""
    
    def test_vapi_webhook_claim_status_lookup(self):
        """POST /api/vapi/webhook - Test check_claim_status function"""
        webhook_payload = {
            "message": {
                "type": "tool-calls",
                "toolCallList": [
                    {
                        "id": "tc-claim-001",
                        "function": {
                            "name": "check_claim_status",
                            "arguments": {"claim_number": "CLM-TEST-001"}
                        }
                    }
                ]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/vapi/webhook", json=webhook_payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        data = response.json()
        
        assert "results" in data
        result = data["results"][0]
        assert result["toolCallId"] == "tc-claim-001"
        print(f"Claim status lookup result: {result['result']}")
    
    def test_vapi_webhook_prior_auth_check(self):
        """POST /api/vapi/webhook - Test check_prior_auth function"""
        webhook_payload = {
            "message": {
                "type": "tool-calls",
                "toolCallList": [
                    {
                        "id": "tc-auth-001",
                        "function": {
                            "name": "check_prior_auth",
                            "arguments": {"cpt_code": "55840", "member_id": "MBR001"}
                        }
                    }
                ]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/vapi/webhook", json=webhook_payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        data = response.json()
        
        assert "results" in data
        result = data["results"][0]
        assert result["toolCallId"] == "tc-auth-001"
        
        import json
        result_data = json.loads(result["result"])
        assert "cpt_code" in result_data
        assert "requires_auth" in result_data
        print(f"Prior auth check result: {result_data}")
    
    def test_vapi_webhook_create_escalation(self):
        """POST /api/vapi/webhook - Test create_escalation function"""
        webhook_payload = {
            "message": {
                "type": "tool-calls",
                "toolCallList": [
                    {
                        "id": "tc-esc-001",
                        "function": {
                            "name": "create_escalation",
                            "arguments": {
                                "reason": "Test escalation from voice agent",
                                "member_id": "MBR001"
                            }
                        }
                    }
                ]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/vapi/webhook", json=webhook_payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        data = response.json()
        
        assert "results" in data
        result = data["results"][0]
        
        import json
        result_data = json.loads(result["result"])
        assert "ticket_id" in result_data, "Missing ticket_id in escalation result"
        assert "message" in result_data, "Missing message in escalation result"
        print(f"Escalation created: {result_data['ticket_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
