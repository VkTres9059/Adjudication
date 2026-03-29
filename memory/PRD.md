# FletchFlow Claims Adjudication System - PRD

## Product Overview
FletchFlow is a scalable, API-first claims adjudication system named after Chevy Chase. It supports multiple lines of coverage (Medical, Dental, Vision, Hearing) with built-in CPT/CDT codes, Medicare fee schedule with GPCI locality adjustments, ACA-compliant preventive care, real X12 EDI parsing, network repricing, prior authorization, and duplicate claim prevention.

## Core Requirements (from User)
1. Microsoft MFA for authentication (MSAL scaffolded, JWT mock fallback)
2. Start with Medical coverage, expand to Dental, Vision, Hearing
3. Accept EDI 834 (eligibility) and 837 (claims) input, generate 835 output
4. Network APIs for provider contract management and repricing
5. Basic reporting for claims and eligibility
6. Built-in medical claims CPT codes and Medicare fee schedule with GPCI locality adjustments
7. Strict duplicate claim prevention and plan build functionality
8. New age creative design with good UI
9. External billing system will be plugged in later (not built)
10. ACA-compliant preventive coverage with $0 member cost share

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + MSAL
- **Backend**: FastAPI + MongoDB + JWT Auth
- **Database**: MongoDB (users, plans, claims, members, duplicates, prior_authorizations, network_contracts, accumulators, audit_logs, preventive_utilization)

## What's Been Implemented

### Phase 1 - Core (Complete)
- [x] FastAPI backend with MongoDB
- [x] JWT authentication with RBAC (admin, adjudicator, reviewer, auditor)
- [x] MSAL scaffolding for Microsoft MFA
- [x] Dashboard with real-time metrics and charts
- [x] Claims management (CRUD, adjudication, status tracking)
- [x] Plan builder with benefit configuration
- [x] Member management with eligibility tracking
- [x] Duplicate claim detection (exact, near, line-level)
- [x] Reports with claims and eligibility analytics
- [x] Settings with audit log, system info, role permissions
- [x] FletchFlow branding (named after Chevy Chase)

### Phase 2 - Multi-Line Coverage (Complete - March 2026)
- [x] Medical CPT codes: 189 codes across 7 categories
- [x] Medicare fee schedule with 87 GPCI localities
- [x] Dental CDT codes: 79 codes
- [x] Vision codes: 44 codes
- [x] Hearing codes: 65 codes
- [x] Unified Code Database page with tabbed search
- [x] Multi-line adjudication engine

### Phase 3 - Advanced Features (Complete - March 2026)
- [x] Real X12 EDI 834/837/835 parsing and generation
- [x] Network management with provider contracts
- [x] Network repricing (Medicare vs contracted rates)
- [x] Prior authorization workflow
- [x] Batch claim processing
- [x] Coordination of Benefits (COB)

### Phase 4 - Preventive Coverage (Complete - March 2026)
- [x] 63 ACA-compliant preventive service codes across 7 categories:
  - Wellness Visits (14): 99381-99387, 99391-99397
  - Immunizations (15): 90460-90474, CDC vaccine schedule
  - Cancer Screenings (11): Mammogram, Colonoscopy, Pap Smear, PSA
  - Preventive Screenings (5): Cholesterol, Diabetes, Hepatitis C, HIV
  - Women's Preventive (8): Maternity, Contraception, Breastfeeding, Gestational DM
  - Pediatric Preventive (4): Developmental, Autism, Vision, Hearing screening
  - Behavioral Counseling (6): Obesity, Tobacco, Alcohol, Depression
- [x] $0 member cost share when billed as preventive (Z-code + CPT match)
- [x] Modifier 33 support for preventive designation
- [x] Split claim logic (preventive + diagnostic secondary dx)
- [x] Frequency limits engine (annual, 3-year, 10-year, lifetime, per-pregnancy)
- [x] Age and gender eligibility checks
- [x] Preventive sits outside deductible (doesn't count toward plan accumulator)
- [x] Preventive utilization tracking per member
- [x] Abuse detection (duplicate visits, excess frequency)
- [x] Plan design: ACA Strict vs Enhanced Preventive in Plan Builder
- [x] EOB shows "Preventive Service - $0 Member Responsibility"
- [x] Preventive analytics (PMPM, compliance rate, category breakdown)
- [x] Frontend: Preventive Services page with Catalog, Analytics, Abuse Detection tabs

## Key Stats
- **Total Procedure Codes**: 440 (189 Medical + 79 Dental + 44 Vision + 65 Hearing + 63 Preventive)
- **GPCI Localities**: 87
- **Coverage Lines**: 4 (Medical, Dental, Vision, Hearing)

## Remaining / Future Work
- P1: Configure real Azure AD credentials for MSAL (needs user's Tenant/Client IDs)
- P2: Refactor server.py into modular routers
- P2: External billing system API integration
- P3: Advanced reporting/analytics with export capabilities
- P3: Member portal for self-service eligibility checks
