# FletchFlow Claims Adjudication System - PRD

## Product Overview
FletchFlow is a scalable, API-first claims adjudication system named after Chevy Chase. Multi-line coverage (Medical, Dental, Vision, Hearing) with ACA-compliant preventive care, X12 EDI parsing, Group Management with stop-loss/SFTP, MEC 1 plan templates, tiered adjudication gateway, examiner workspace, advanced eligibility management, and duplicate claim prevention.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + MSAL
- **Backend**: FastAPI + MongoDB + JWT Auth
- **Database**: MongoDB (users, plans, claims, members, groups, duplicates, prior_authorizations, network_contracts, accumulators, audit_logs, preventive_utilization, settings, tpa_834_feed, clawback_ledger, member_audit_trail)

## What's Been Implemented

### Phase 1 - Core (Complete)
- [x] FastAPI backend with MongoDB, JWT auth with RBAC
- [x] Dashboard, Claims, Plans, Members, Duplicates, Reports, Settings
- [x] FletchFlow branding (named after Chevy Chase)

### Phase 2 - Multi-Line Coverage (Complete)
- [x] Medical: 189 CPT codes, 87 GPCI localities, Medicare fee schedule
- [x] Dental: 79 CDT codes, Vision: 44 codes, Hearing: 65 codes

### Phase 3 - Advanced Features (Complete)
- [x] Real X12 EDI 834/837/835 parsing and generation
- [x] Network management, Prior authorization, Batch processing, COB

### Phase 4 - Preventive Coverage (Complete)
- [x] 63 ACA-compliant preventive codes, $0 member cost share

### Phase 5 - Group Management & MEC 1 (Complete)
- [x] Group CRUD, Stop-Loss, SFTP, MEC 1 plan template, Pulse Analytics, Surplus

### Phase 6 - MEC 1 Auto-Adjudication & Financial Reporting (Complete)
- [x] MEC 1 100% auto-adjudication, Fixed Cost vs Claims Spend report

### Phase 7 - Global Adjudication Gateway & Examiner Workspace (Complete)
- [x] Tiered Authorization Matrix (Tier 1 Auto-Pilot, Tier 2 Audit Hold, Tier 3 Hard Hold)
- [x] Multi-Plan Examiner Workspace (MEC Preventive Validator, Deductible Tracker, Carrier Notification)
- [x] Managerial Hold with reason codes and Bordereaux exclusion
- [x] Users Management (GET/POST /api/users)

### Phase 8 - Advanced Eligibility & Member Lifecycle (Complete - March 2026)
- [x] **Member Reconciliation Dashboard**: Compare MGU Census vs TPA 834 Feed, flag Ghost Members (on census, missing from TPA) and Unmatched Members (on TPA, missing from census). Upload TPA feed via pipe-delimited file.
- [x] **Retroactive Termination & Clawback**: Retro-Term Monitor scans for members terminated in the past with approved claims after term date. "Request Provider Refund" button logs recovery amount to clawback_ledger.
- [x] **Pending Eligibility Queue**: Claims for members NOT in census → `pending_eligibility` status with 72-hour deadline. "Process Pending Eligibility" auto-releases if member found via 834, auto-denies if expired.
- [x] **Dependent Age-Out Rules**: Alerts for dependents (child/dependent) turning 26 within 30 days, sorted by urgency.
- [x] **Member Audit Trail**: Every eligibility change (Add/Term/Retro-Term/Change/Refund) logged to persistent `member_audit_trail` collection. Visible on member profile detail modal.
- [x] **834 Upload Integration**: `_save_834_member` now auto-populates `tpa_834_feed` for reconciliation and logs all changes to audit trail with action type detection (added/updated/terminated/retro-terminated).
- [x] **New API Endpoints**:
  - GET /api/members/eligibility/reconciliation
  - POST /api/members/eligibility/upload-tpa-feed
  - GET /api/members/eligibility/retro-terms
  - POST /api/members/{id}/request-refund
  - POST /api/claims/process-pending-eligibility
  - GET /api/members/eligibility/age-out-alerts
  - GET /api/members/{id}/audit-trail
- [x] **New ClaimStatus**: `pending_eligibility` with Claims filter support

## Key Stats
- **Total Procedure Codes**: 440
- **Coverage Lines**: 4 (Medical, Dental, Vision, Hearing)
- **GPCI Localities**: 87
- **Pages**: 14
- **Adjudication Tiers**: 3
- **Hold Reason Codes**: 5
- **Eligibility Features**: 5 (Reconciliation, Retro-Term, Pending Queue, Age-Out, Audit Trail)

## Remaining / Future Work
- P1: Configure real Azure AD credentials for MSAL
- P1: Real X12 EDI parser enhancements
- P2: Refactor server.py into modular routers (~3600+ lines)
- P2: External billing system API integration
- P2: Network repricing vs contracted rates
- P3: Carrier Bordereaux reporting module
- P3: Member self-service portal
- P3: Automated age-out termination (currently alert-only)
