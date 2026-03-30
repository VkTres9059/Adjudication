"""
EDI Parser Tests - X12 834, 837, 835 endpoints
Tests real X12 parsing, validation, upload, and 835 generation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Sample X12 834 content
SAMPLE_834_X12 = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *260330*1200*^*00501*000000001*0*P*:~
GS*BE*SENDER*RECEIVER*20260330*1200*1*X*005010X220A1~
ST*834*0001~
BGN*00*12345*20260330~
INS*Y*18*021*20*A****EMP~
REF*0F*TESTMBR01~
REF*1L*GRP001~
NM1*IL*1*TESTLAST*TESTFIRST****MI*TESTMBR01~
DMG*D8*19900101*F~
DTP*348*D8*20260101~
HD*021**HLT**EMP~
SE*11*0001~
GE*1*1~
IEA*1*000000001~"""

# Sample X12 837 content
SAMPLE_837_X12 = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *260330*1200*^*00501*000000002*0*P*:~
GS*HC*SENDER*RECEIVER*20260330*1200*2*X*005010X222A1~
ST*837*0001~
BHT*0019*00*12345*20260330*1200*CH~
HL*1**20*1~
NM1*85*2*TEST CLINIC*****XX*9876543210~
HL*2*1*22*1~
SBR*P*18*******MC~
NM1*IL*1*DOE*JOHN****MI*MBR001~
CLM*CTRL001*250.00***11:B:1~
DTP*472*D8*20260320~
HI*ABK:J069*ABF:R059~
SV1*HC:99213*250.00*UN*1***1~
SE*13*0001~
GE*1*2~
IEA*1*000000002~"""

# Sample pipe-delimited 834
SAMPLE_834_PIPE = """PIPEMBR01|John|Pipe|1985-05-15|M|GRP002|PLAN001|2026-01-01
PIPEMBR02|Jane|Pipe|1988-08-20|F|GRP002|PLAN001|2026-01-01"""

# Sample pipe-delimited 837
SAMPLE_837_PIPE = """MBR001|1234567890|Test Provider|medical|2026-03-20|2026-03-20|150.00|J069,R059|99213:1:150.00"""


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "demo@fletchflow.com",
        "password": "Demo123!"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
    }


class TestEDI834Validate:
    """Tests for POST /api/edi/validate-834 - X12 834 parsing/preview"""

    def test_validate_834_x12_parses_envelope(self, auth_headers):
        """834 validation returns envelope info (sender, receiver, control number)"""
        files = {"file": ("test.edi", SAMPLE_834_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("is_x12") is True, "Should detect X12 format"
        assert data.get("format") == "x12_834"
        
        envelope = data.get("envelope", {})
        assert envelope.get("sender_id") == "SENDER", f"Expected SENDER, got {envelope.get('sender_id')}"
        assert envelope.get("receiver_id") == "RECEIVER", f"Expected RECEIVER, got {envelope.get('receiver_id')}"
        assert envelope.get("control_number") == "000000001"

    def test_validate_834_x12_parses_members(self, auth_headers):
        """834 validation returns member list with maintenance types"""
        files = {"file": ("test.edi", SAMPLE_834_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("member_count") >= 1, "Should have at least 1 member"
        members = data.get("members", [])
        assert len(members) >= 1
        
        member = members[0]
        assert member.get("member_id") == "TESTMBR01"
        assert member.get("first_name") == "TESTFIRST"
        assert member.get("last_name") == "TESTLAST"
        assert member.get("maintenance_type") == "addition"  # 021 = addition
        assert member.get("relationship") == "subscriber"  # Y = subscriber

    def test_validate_834_x12_parses_dmg_gender_dob(self, auth_headers):
        """834 parser extracts DMG segment (gender, DOB)"""
        files = {"file": ("test.edi", SAMPLE_834_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        members = data.get("members", [])
        
        member = members[0]
        assert member.get("gender") == "F", f"Expected F, got {member.get('gender')}"
        assert member.get("dob") == "1990-01-01", f"Expected 1990-01-01, got {member.get('dob')}"

    def test_validate_834_x12_parses_dtp_effective_date(self, auth_headers):
        """834 parser extracts DTP*348 effective date"""
        files = {"file": ("test.edi", SAMPLE_834_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        members = data.get("members", [])
        
        member = members[0]
        assert member.get("effective_date") == "2026-01-01"

    def test_validate_834_x12_parses_hd_coverage_type(self, auth_headers):
        """834 parser extracts HD segment coverage type"""
        files = {"file": ("test.edi", SAMPLE_834_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        members = data.get("members", [])
        
        member = members[0]
        assert member.get("coverage_type") == "health", f"Expected health, got {member.get('coverage_type')}"

    def test_validate_834_pipe_fallback(self, auth_headers):
        """834 validation handles pipe-delimited format"""
        files = {"file": ("test.txt", SAMPLE_834_PIPE, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("is_x12") is False
        assert data.get("format") == "pipe_delimited"
        preview = data.get("preview", {})
        assert preview.get("member_count") == 2


class TestEDI834Upload:
    """Tests for POST /api/edi/upload-834 - X12 834 processing"""

    def test_upload_834_x12_creates_members(self, auth_headers):
        """834 upload processes X12 and creates/updates members"""
        files = {"file": ("test.edi", SAMPLE_834_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/upload-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("format") == "x12"
        # Should have created or updated at least 1 member
        total = data.get("members_created", 0) + data.get("members_updated", 0)
        assert total >= 1, f"Expected at least 1 member processed, got {total}"

    def test_upload_834_returns_counts(self, auth_headers):
        """834 upload returns created/updated/terminated counts"""
        files = {"file": ("test.edi", SAMPLE_834_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/upload-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "members_created" in data
        assert "members_updated" in data
        assert "members_terminated" in data

    def test_upload_834_pipe_fallback(self, auth_headers):
        """834 upload handles pipe-delimited format"""
        files = {"file": ("test.txt", SAMPLE_834_PIPE, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/upload-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("format") == "pipe"


class TestEDI837Validate:
    """Tests for POST /api/edi/validate-837 - X12 837 parsing/preview"""

    def test_validate_837_x12_parses_envelope(self, auth_headers):
        """837 validation returns envelope info"""
        files = {"file": ("test.edi", SAMPLE_837_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-837", files=files, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("is_x12") is True
        assert data.get("format") == "x12_837"
        
        envelope = data.get("envelope", {})
        assert envelope.get("sender_id") == "SENDER"
        assert envelope.get("control_number") == "000000002"

    def test_validate_837_x12_parses_claims(self, auth_headers):
        """837 validation returns claims with diagnosis codes and provider info"""
        files = {"file": ("test.edi", SAMPLE_837_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-837", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("claim_count") >= 1
        claims = data.get("claims", [])
        assert len(claims) >= 1
        
        claim = claims[0]
        assert claim.get("member_id") == "MBR001"
        assert claim.get("total_billed") == 250.00
        assert claim.get("provider_name") == "TEST CLINIC"
        assert claim.get("provider_npi") == "9876543210"

    def test_validate_837_x12_parses_diagnosis_codes(self, auth_headers):
        """837 parser extracts HI diagnosis codes with ICD-10 decimal insertion"""
        files = {"file": ("test.edi", SAMPLE_837_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-837", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        claims = data.get("claims", [])
        
        claim = claims[0]
        diag_codes = claim.get("diagnosis_codes", [])
        # Should have J06.9 and R05.9 (with decimal inserted)
        assert len(diag_codes) >= 2, f"Expected at least 2 diagnosis codes, got {diag_codes}"
        # Check decimal insertion for codes > 3 chars
        assert any("." in code for code in diag_codes), f"Expected decimal in ICD-10 codes: {diag_codes}"

    def test_validate_837_x12_parses_service_lines(self, auth_headers):
        """837 parser extracts SV1 service lines with modifiers"""
        files = {"file": ("test.edi", SAMPLE_837_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-837", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        claims = data.get("claims", [])
        
        claim = claims[0]
        assert claim.get("service_line_count") >= 1

    def test_validate_837_pipe_fallback(self, auth_headers):
        """837 validation handles pipe-delimited format"""
        files = {"file": ("test.txt", SAMPLE_837_PIPE, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-837", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("is_x12") is False
        assert data.get("format") == "pipe_delimited"


class TestEDI837Upload:
    """Tests for POST /api/edi/upload-837 - X12 837 processing"""

    def test_upload_837_x12_creates_claims(self, auth_headers):
        """837 upload processes X12 and creates claims"""
        files = {"file": ("test.edi", SAMPLE_837_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/upload-837", files=files, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("format") == "x12"
        assert data.get("claims_created") >= 1, f"Expected at least 1 claim created"

    def test_upload_837_returns_envelope(self, auth_headers):
        """837 upload returns envelope info"""
        files = {"file": ("test.edi", SAMPLE_837_X12, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/upload-837", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        envelope = data.get("envelope", {})
        assert envelope.get("control_number") == "000000002"


class TestEDI835Generate:
    """Tests for GET /api/edi/generate-835 - X12 835 remittance generation"""

    def test_generate_835_x12_format(self, auth_headers):
        """835 generation returns X12 format with proper segments"""
        params = {"date_from": "2025-01-01", "date_to": "2026-12-31", "format": "x12"}
        response = requests.get(f"{BASE_URL}/api/edi/generate-835", params=params, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("format") == "x12"
        content = data.get("content", "")
        
        # Check for required X12 835 segments
        assert "ISA*" in content, "Missing ISA segment"
        assert "GS*HP*" in content, "Missing GS segment (HP = 835)"
        assert "ST*835*" in content, "Missing ST segment"
        assert "BPR*" in content, "Missing BPR (financial info) segment"

    def test_generate_835_pipe_format(self, auth_headers):
        """835 generation returns pipe-delimited format"""
        params = {"date_from": "2025-01-01", "date_to": "2026-12-31", "format": "pipe"}
        response = requests.get(f"{BASE_URL}/api/edi/generate-835", params=params, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("format") == "pipe"
        content = data.get("content", "")
        assert "# EDI 835 Payment File" in content

    def test_generate_835_returns_claim_count(self, auth_headers):
        """835 generation returns claim count"""
        params = {"date_from": "2025-01-01", "date_to": "2026-12-31", "format": "x12"}
        response = requests.get(f"{BASE_URL}/api/edi/generate-835", params=params, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "claim_count" in data
        assert isinstance(data["claim_count"], int)

    def test_generate_835_x12_has_clp_svc_segments(self, auth_headers):
        """835 X12 format includes CLP (claim payment) and SVC (service) segments for claims"""
        params = {"date_from": "2025-01-01", "date_to": "2026-12-31", "format": "x12"}
        response = requests.get(f"{BASE_URL}/api/edi/generate-835", params=params, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        content = data.get("content", "")
        claim_count = data.get("claim_count", 0)
        
        # If there are claims, should have CLP segments
        if claim_count > 0:
            assert "CLP*" in content, "Missing CLP (claim payment) segment"


class TestEDITransactions:
    """Tests for GET /api/edi/transactions - Transaction history log"""

    def test_transactions_returns_list(self, auth_headers):
        """Transactions endpoint returns list of EDI transactions"""
        response = requests.get(f"{BASE_URL}/api/edi/transactions", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)

    def test_transactions_have_required_fields(self, auth_headers):
        """Transaction records have type, status, record_count, errors"""
        response = requests.get(f"{BASE_URL}/api/edi/transactions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            tx = data[0]
            assert "type" in tx, "Missing type field"
            assert "status" in tx, "Missing status field"
            assert "record_count" in tx, "Missing record_count field"
            assert "filename" in tx, "Missing filename field"

    def test_transactions_filter_by_type(self, auth_headers):
        """Transactions can be filtered by type"""
        response = requests.get(f"{BASE_URL}/api/edi/transactions", params={"tx_type": "834"}, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned transactions should be type 834
        for tx in data:
            assert tx.get("type") == "834", f"Expected type 834, got {tx.get('type')}"


class TestEDI834MaintenanceCodes:
    """Tests for 834 maintenance type code handling"""

    def test_834_cancellation_maintenance_type(self, auth_headers):
        """834 parser handles INS maintenance type 024 (cancellation)"""
        # Create 834 with cancellation maintenance type
        cancellation_834 = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *260330*1200*^*00501*000000003*0*P*:~
GS*BE*SENDER*RECEIVER*20260330*1200*1*X*005010X220A1~
ST*834*0001~
BGN*00*12345*20260330~
INS*Y*18*024*20*A****EMP~
REF*0F*CANCELMBR~
NM1*IL*1*CANCELLED*MEMBER****MI*CANCELMBR~
DMG*D8*19850101*M~
DTP*348*D8*20260101~
DTP*349*D8*20260331~
SE*9*0001~
GE*1*1~
IEA*1*000000003~"""
        
        files = {"file": ("test.edi", cancellation_834, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        members = data.get("members", [])
        
        if len(members) > 0:
            member = members[0]
            assert member.get("maintenance_type") == "cancellation"

    def test_834_reinstatement_maintenance_type(self, auth_headers):
        """834 parser handles INS maintenance type 025 (reinstatement)"""
        reinstatement_834 = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *260330*1200*^*00501*000000004*0*P*:~
GS*BE*SENDER*RECEIVER*20260330*1200*1*X*005010X220A1~
ST*834*0001~
BGN*00*12345*20260330~
INS*Y*18*025*20*A****EMP~
REF*0F*REINSTMBR~
NM1*IL*1*REINSTATED*MEMBER****MI*REINSTMBR~
DMG*D8*19850101*M~
DTP*348*D8*20260101~
SE*8*0001~
GE*1*1~
IEA*1*000000004~"""
        
        files = {"file": ("test.edi", reinstatement_834, "text/plain")}
        response = requests.post(f"{BASE_URL}/api/edi/validate-834", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        members = data.get("members", [])
        
        if len(members) > 0:
            member = members[0]
            assert member.get("maintenance_type") == "reinstatement"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
