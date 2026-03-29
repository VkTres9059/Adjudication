# FletchFlow Claims Adjudication System - PRD

## Product Overview
FletchFlow is a scalable, API-first claims adjudication system named after Chevy Chase. Multi-line coverage (Medical, Dental, Vision, Hearing) with ACA-compliant preventive care, real X12 EDI parsing, Group Management with stop-loss/SFTP, MEC 1 plan templates, network repricing, prior authorization, and duplicate claim prevention.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + MSAL
- **Backend**: FastAPI + MongoDB + JWT Auth
- **Database**: MongoDB (users, plans, claims, members, groups, duplicates, prior_authorizations, network_contracts, accumulators, audit_logs, preventive_utilization, settings)

## What's Been Implemented

### Phase 1 - Core (Complete)
- [x] FastAPI backend with MongoDB, JWT auth with RBAC
- [x] Dashboard, Claims, Plans, Members, Duplicates, Reports, Settings
- [x] FletchFlow branding (named after Chevy Chase)

### Phase 2 - Multi-Line Coverage (Complete)
- [x] Medical: 189 CPT codes, 87 GPCI localities, Medicare fee schedule
- [x] Dental: 79 CDT codes, Vision: 44 codes, Hearing: 65 codes
- [x] Unified Code Database with tabbed search

### Phase 3 - Advanced Features (Complete)
- [x] Real X12 EDI 834/837/835 parsing and generation
- [x] Network management with provider contracts + repricing
- [x] Prior authorization workflow, Batch processing, COB

### Phase 4 - Preventive Coverage (Complete)
- [x] 63 ACA-compliant preventive codes (7 categories)
- [x] $0 member cost share, modifier 33, split claim, frequency limits, age/gender eligibility
- [x] Preventive utilization tracking, abuse detection, analytics

### Phase 5 - Group Management & MEC 1 (Complete)
- [x] Group Management module: CRUD, Stop-Loss configs, SFTP scheduler
- [x] MEC 1 plan template, Pulse Analytics per group, Surplus Bucket
- [x] MEC 1 100% auto-adjudication, MEC-specific financial reporting

### Phase 6 - MEC 1 Auto-Adjudication & Financial Reporting (Complete - March 2026)
- [x] MEC 1 100% Auto-Adjudication: Preventive auto-approved $0, non-preventive auto-denied
- [x] MEC Surplus: Total Premium - (MGU Fees + Claims Paid)
- [x] Group Financials: Total Premium & MGU Fees fields
- [x] Fixed Cost vs. Claims Spend report with per-group chart + table

### Phase 7 - Global Adjudication Gateway & Examiner Workspace (Complete - March 2026)
- [x] **Tiered Authorization Matrix** in Settings:
  - Tier 1 (Auto-Pilot): Claims ≤ $X auto-paid (default $500)
  - Tier 2 (Audit Hold): Claims $X-$Y paid + flagged for Post-Payment Audit (default $2,500)
  - Tier 3 (Hard Hold): Claims > $Y → Pending Review requiring examiner digital signature
- [x] **Multi-Plan Examiner Workspace** in Claim Detail:
  - MEC 1: ACA Preventive Validator — toggle preventive flag to force $0 member cost
  - Standard: Deductible/OOP Tracker — manually adjust Applied to Deductible
  - Stop-Loss: Specific Attachment Point — flag claim for Carrier Notification
- [x] **Managerial Hold** feature:
  - Hold/Release toggle with 5 reason codes (Medical Necessity, COB, Subrogation, Fraud, Stop-Loss)
  - Bordereaux Exclusion: held claims excluded from all financial reports
  - Admin-only release with audit trail
- [x] **Dashboard Integration**:
  - Held claims banner, pending_review status tracking
  - Auto-adjudication rate updates in real-time
- [x] **Users Management**: Admin-only user list and creation endpoint (GET/POST /api/users)
- [x] **New ClaimStatus values**: managerial_hold, pending_review
- [x] **New API Endpoints**: 
  - GET/PUT /api/settings/adjudication-gateway
  - PUT /api/claims/{id}/hold, PUT /api/claims/{id}/release-hold
  - POST /api/claims/{id}/force-preventive, /adjust-deductible, /carrier-notification

## Key Stats
- **Total Procedure Codes**: 440 (189 Medical + 79 Dental + 44 Vision + 65 Hearing + 63 Preventive)
- **Coverage Lines**: 4 (Medical, Dental, Vision, Hearing)
- **GPCI Localities**: 87
- **Pages**: 14
- **Adjudication Tiers**: 3 (Auto-Pilot, Audit Hold, Hard Hold)
- **Hold Reason Codes**: 5

## Remaining / Future Work
- P1: Configure real Azure AD credentials for MSAL
- P1: Real X12 EDI parser enhancements
- P2: Refactor server.py into modular routers (~3200+ lines)
- P2: External billing system API integration
- P2: Network repricing vs contracted rates
- P3: Advanced reporting with CSV/PDF export
- P3: Carrier Bordereaux reporting module
- P3: Member self-service portal
