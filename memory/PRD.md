# FletchFlow Claims Adjudication System - PRD

## Product Overview
FletchFlow is a scalable, API-first claims adjudication system named after Chevy Chase. Multi-line coverage (Medical, Dental, Vision, Hearing) with ACA-compliant preventive care, X12 EDI parsing, Group Management, MEC 1 plan templates, tiered adjudication gateway, examiner workspace & queue, advanced eligibility management, and duplicate claim prevention.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + MSAL
- **Backend**: FastAPI + MongoDB + JWT Auth
- **Database**: MongoDB (users, plans, claims, members, groups, duplicates, prior_authorizations, network_contracts, accumulators, audit_logs, preventive_utilization, settings, tpa_834_feed, clawback_ledger, member_audit_trail)

## What's Been Implemented

### Phase 1-4 — Core, Multi-Line Coverage, Advanced Features, Preventive (Complete)
- [x] Full claims engine with 440 procedure codes across 4 coverage lines
- [x] ACA-compliant preventive services, EDI 834/837/835, Prior Auth, Batch, COB

### Phase 5-6 — Group Management, MEC 1, Financial Reporting (Complete)
- [x] Group CRUD with Stop-Loss, SFTP, MEC 1 plans, Surplus Bucket
- [x] Fixed Cost vs Claims Spend report

### Phase 7 — Adjudication Gateway & Examiner Workspace (Complete)
- [x] Tiered Authorization Matrix (Tier 1 Auto-Pilot, Tier 2 Audit Hold, Tier 3 Hard Hold)
- [x] Multi-Plan Examiner Workspace (MEC Validator, Deductible Tracker, Carrier Notification)
- [x] Managerial Hold with Bordereaux exclusion

### Phase 8 — Advanced Eligibility & Member Lifecycle (Complete)
- [x] Member Reconciliation Dashboard (Census vs TPA 834 Feed, Ghost/Unmatched flagging)
- [x] Retro-Term Monitor & Clawback with Provider Refund requests
- [x] Pending Eligibility Queue (72-hour hold for unknown members)
- [x] Dependent Age-Out Rules (26-year alert)
- [x] Member Audit Trail (all eligibility changes logged)

### Phase 9 — Examiner Queue & Auto-Assignment Engine (Complete - March 2026)
- [x] **Examiner Queue Dashboard** (`/examiner-queue`): New page showing `pending_review` and `managerial_hold` claims. Priority sorting by Days in Queue (oldest first) or Dollar Amount (highest risk first). Summary cards: Total, Pending Review, On Hold, Total Exposure.
- [x] **Auto-Assignment Logic**: Load balancing — Tier 3 claims auto-assigned to examiner with fewest open claims. Authority routing: <$5,000 → Junior Examiner (adjudicator role), ≥$5,000 → Senior Examiner (admin role).
- [x] **One-Click Adjudication Panel**: Approve, Deny, Request Info buttons per queue row. Deny and Request Info open notes modal. Claims removed from queue instantly (static, no animation).
- [x] **Admin Reassign**: Reassign button (UserCog icon) visible for admins. Modal shows all examiners with Senior/Junior labels.
- [x] **Examiner Performance Metrics**: Dashboard widget showing per-examiner: Open Claims, Closed Today, Average TAT (hours).
- [x] **New API Endpoints**:
  - GET /api/examiner/queue, /api/examiner/queue/all
  - POST /api/examiner/queue/{id}/quick-action?action=approve|deny|request_info
  - POST /api/claims/{id}/reassign?examiner_id={id}
  - GET /api/examiner/performance, /api/examiner/list
- [x] **New Fields**: assigned_to, assigned_to_name, assigned_at on claims

## Key Stats
- **Total Procedure Codes**: 440
- **Coverage Lines**: 4 (Medical, Dental, Vision, Hearing)
- **Pages**: 15 (Dashboard, Claims, ClaimDetail, Plans, PlanBuilder, Members, Groups, Prior Auth, Preventive, Network, Code Database, Fee Schedule, Duplicates, Examiner Queue, Reports)
- **Adjudication Tiers**: 3
- **Hold Reason Codes**: 5
- **Eligibility Features**: 5

## Remaining / Future Work
- P1: Configure real Azure AD credentials for MSAL
- P1: Real X12 EDI parser enhancements
- P2: Refactor server.py into modular routers (~3800+ lines)
- P2: External billing system API integration
- P2: Network repricing vs contracted rates
- P3: Carrier Bordereaux reporting module
- P3: Member self-service portal
- P3: Automated age-out termination
