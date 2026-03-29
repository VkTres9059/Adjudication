# FletchFlow Claims Adjudication System - PRD

## Product Overview
FletchFlow is a scalable, API-first claims adjudication system named after Chevy Chase. Multi-line coverage (Medical, Dental, Vision, Hearing) with ACA-compliant preventive care, real X12 EDI parsing, Group Management with stop-loss/SFTP, MEC 1 plan templates, network repricing, prior authorization, and duplicate claim prevention.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + MSAL
- **Backend**: FastAPI + MongoDB + JWT Auth
- **Database**: MongoDB (users, plans, claims, members, groups, duplicates, prior_authorizations, network_contracts, accumulators, audit_logs, preventive_utilization)

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
- [x] 63 ACA-compliant preventive codes (7 categories: Wellness, Immunizations, Cancer Screening, Preventive Screening, Women's, Pediatric, Behavioral)
- [x] $0 member cost share, modifier 33, split claim, frequency limits, age/gender eligibility
- [x] Preventive utilization tracking, abuse detection, analytics (PMPM, compliance)
- [x] Plan Builder: ACA Strict vs Enhanced Preventive design
- [x] EOB: "Preventive Service - $0 Member Responsibility"

### Phase 5 - Group Management & MEC 1 (Complete - March 2026)
- [x] Group Management module: create employer groups (name, Tax ID, contact, address, SIC code, employee count)
- [x] Stop-Loss configuration: specific deductible, aggregate attachment point, aggregate factor, contract period, laser deductibles
- [x] SFTP Scheduler: host, schedule (daily/weekly/monthly), file types (834/835), enable/disable
- [x] Plan attachment to groups: attach/detach plans from group profile
- [x] MEC 1 plan template per MEC Preventive SOB (Ver. 05232025): $0 deductible, $0 OOP, ACA Strict, 22 benefit categories (10 covered + 12 not-covered), 30 exclusions, reference-based pricing, 50% pre-auth penalty
- [x] Pulse Analytics per group: PMPM, claims, total paid, surplus bucket, YTD utilization bar
- [x] Frontend: Group Management page with create modal (tabs: Info/Stop-Loss/SFTP), detail modal with Pulse, Stop-Loss status, SFTP config, Plan Offerings

## Key Stats
- **Total Procedure Codes**: 440 (189 Medical + 79 Dental + 44 Vision + 65 Hearing + 63 Preventive)
- **Coverage Lines**: 4 (Medical, Dental, Vision, Hearing)
- **GPCI Localities**: 87
- **Pages**: 14 (Dashboard, Claims, ClaimDetail, Plans, PlanBuilder, Members, Groups, Prior Auth, Preventive, Network, Code Database, Fee Schedule, Duplicates, Reports)

## Remaining / Future Work
- P1: Configure real Azure AD credentials for MSAL
- P2: Refactor server.py into modular routers
- P2: External billing system API integration
- P3: Advanced reporting with CSV/PDF export
- P3: Carrier Reporting module
- P3: Member self-service portal
