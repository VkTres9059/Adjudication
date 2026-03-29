# FletchFlow Claims Adjudication System - PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system supporting multiple lines of coverage. Start with Medical coverage, use Microsoft MFA for authentication, accept EDI 834/837 input with 835 output. Provide reporting for claims/eligibility. Implement strict duplicate claim prevention, built-in Medicare fee schedules, multi-line coverage, a comprehensive Preventive Coverage module, and Group Management.

## Architecture (v2.0 - Modular)
```
/app/backend/
├── server.py              # Slim entry (~63 lines): FastAPI app, CORS, router includes
├── core/
│   ├── config.py          # JWT, logging config
│   ├── database.py        # MongoDB connection
│   └── auth.py            # Auth helpers (hash, verify, token, RBAC)
├── models/
│   ├── enums.py           # UserRole, ClaimStatus, ClaimType, etc.
│   └── schemas.py         # All Pydantic models
├── services/
│   ├── adjudication.py    # Claims adjudication engine
│   ├── claims.py          # Shared claim creation logic
│   ├── duplicates.py      # Duplicate detection
│   ├── examiner.py        # Auto-assignment engine
│   └── edi_parser.py      # X12 834/837 parsing
├── routers/ (16 routers)
│   ├── auth.py, plans.py, members.py, groups.py
│   ├── claims.py, examiner.py, duplicates.py
│   ├── dashboard.py, reports.py, edi.py
│   ├── codes.py, network.py, prior_auth.py
│   ├── preventive.py, settings.py, audit.py
├── cpt_codes.py, dental_codes.py, vision_codes.py
├── hearing_codes.py, preventive_services.py
```

Frontend: React + Tailwind CSS + Shadcn UI
Pages: Dashboard, Claims, ClaimDetail, Plans, Members, Groups, Reports, Settings, ExaminerQueue, Prior Auth, Preventive, Network, Code Database, Fee Schedule, Duplicates

## What's Been Implemented
### Phase 1: Core Claims Engine
- Multi-line coverage (Medical, Dental, Vision, Hearing)
- Medicare fee schedule with GPCI localities
- Duplicate claim detection (exact, near, line-level)
- EDI 834/837 intake, 835 output
- JWT authentication with RBAC

### Phase 2: MEC 1 Auto-Adjudication
- MEC 1 plan template from SOB
- ACA-compliant preventive-only adjudication
- Auto-deny non-preventive on MEC plans

### Phase 3: Global Adjudication Gateway
- Tiered Authorization Matrix (Tier 1/2/3)
- Auto-Pilot, Audit Hold, Hard Hold
- Configurable thresholds

### Phase 4: Examiner Workspace
- Multi-Plan Examiner Workspace
- Managerial Hold (place/release)
- Force Preventive, Adjust Deductible, Carrier Notification
- Examiner Queue Dashboard + Auto-Assignment Engine
- Performance Metrics

### Phase 5: Advanced Eligibility
- Reconciliation Dashboard (Census vs TPA 834)
- Retroactive Termination + Clawback Ledger
- 72-Hour Pending Eligibility Queue
- Age-Out Rules (26th birthday alerts)
- Member Audit Trail

### Phase 6: Modular Refactor (March 2026)
- Refactored ~3850-line monolithic server.py into modular architecture
- 16 routers, 5 services, 2 model files, 3 core files
- 100% regression test pass rate (iteration 10)
- Zero frontend changes required

### Phase 7: Navigation Consolidation (March 2026)
- Collapsible Categorized Sidebar with 4 groups:
  - Operations (Dashboard, Examiner Queue, Reports)
  - Plan Management (Plans, Preventive, Code Database)
  - Claims Center (Claims, Prior Auth, Duplicates, Fee Schedule)
  - Network & Groups (Groups, Members, Network)
- Settings as standalone admin footer item
- Chevron icons with rotation animation for expand/collapse
- Auto-expand active category based on current route
- Sub-menu indentation with left border for visual hierarchy
- Constant 256px sidebar width (zero-jitter)
- 100% test pass rate (iteration 11)

## Backlog
- P1: Carrier Bordereaux Reporting Module
- P1: Real X12 EDI parser for 834/837/835
- P1: Azure AD credentials for MSAL (currently JWT fallback)
- P2: Network repricing vs contracted rates
- P2: External billing system API integration
- P3: Member self-service portal

## DB Collections
users, plans, claims, members, groups, audit_logs, duplicate_alerts, accumulators, settings, network_contracts, prior_authorizations, clawback_ledger, member_audit_trail, tpa_834_feed, preventive_utilization, gateway_config, hour_bank, hour_bank_entries

## Test Reports
- iteration_6.json through iteration_10.json (all 100% pass)
