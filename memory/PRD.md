# FletchFlow Claims Adjudication System - PRD

## Product Overview
FletchFlow is a scalable, API-first claims adjudication system named after Chevy Chase. It supports multiple lines of coverage (Medical, Dental, Vision, Hearing) with built-in CPT/CDT codes, Medicare fee schedule with GPCI locality adjustments, real X12 EDI parsing, network repricing, prior authorization, and duplicate claim prevention.

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

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + MSAL
- **Backend**: FastAPI + MongoDB + JWT Auth
- **Database**: MongoDB (users, plans, claims, members, duplicates, prior_authorizations, network_contracts, accumulators, audit_logs)

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
- [x] FletchFlow branding (renamed from Javelina)

### Phase 2 - Multi-Line Coverage (Complete - March 2026)
- [x] Medical CPT codes: 189 codes across 7 categories
- [x] Medicare fee schedule with 87 GPCI localities
- [x] Dental CDT codes: 79 codes (Diagnostic, Preventive, Restorative, Crown, Endodontics, Periodontics, Prosthodontics, Oral Surgery, Orthodontics)
- [x] Vision codes: 44 codes (Eye Exam, Refraction, Contact Lens, Lenses, Frames, Special Procedures)
- [x] Hearing codes: 65 codes (Audiometric Testing, Hearing Aid Services/Devices, Cochlear Implant, Vestibular)
- [x] Unified Code Database page with tabbed search across all coverage lines
- [x] Multi-line adjudication engine supporting dental benefit classes, vision allowances, hearing device allowances

### Phase 3 - Advanced Features (Complete - March 2026)
- [x] Real X12 EDI 834 parser (enrollment) - supports both X12 and pipe-delimited
- [x] Real X12 EDI 837 parser (claims) - supports both X12 and pipe-delimited
- [x] X12 EDI 835 generator (payment/remittance) - real X12 format output
- [x] Network management with provider contracts
- [x] Network repricing (Medicare vs contracted rates comparison)
- [x] Prior authorization workflow (create, review, approve/deny/pend)
- [x] Batch claim processing
- [x] Coordination of Benefits (COB) - secondary payer calculation
- [x] Member accumulators (deductible, OOP, annual max tracking per coverage type)

## Key API Endpoints
- `POST /api/auth/login` - JWT authentication
- `POST /api/auth/register` - User registration
- `GET/POST /api/claims` - Claims CRUD
- `POST /api/claims/batch` - Batch claim processing
- `POST /api/claims/{id}/cob` - Coordination of Benefits
- `GET/POST /api/plans` - Plan management
- `GET/POST /api/members` - Member management
- `GET /api/duplicates` - Duplicate detection
- `GET /api/dental-codes/search` - Dental CDT code search
- `GET /api/vision-codes/search` - Vision code search
- `GET /api/hearing-codes/search` - Hearing code search
- `GET /api/code-database/stats` - All code database stats
- `GET /api/cpt-codes/search` - Medical CPT code search
- `GET /api/fee-schedule/stats` - Fee schedule statistics
- `POST /api/edi/upload-834` - EDI 834 enrollment file upload (X12 + pipe)
- `POST /api/edi/upload-837` - EDI 837 claims file upload (X12 + pipe)
- `GET /api/edi/generate-835` - EDI 835 payment file generation (X12 + pipe)
- `GET/POST /api/network/contracts` - Network contract management
- `GET /api/network/reprice/{claim_id}` - Network repricing
- `GET /api/network/summary` - Network savings summary
- `GET/POST /api/prior-auth` - Prior authorization workflow
- `POST /api/prior-auth/{id}/decide` - Prior auth decision
- `GET /api/dashboard/metrics` - Dashboard analytics

## Remaining / Future Work
- P1: Configure real Azure AD credentials for MSAL (needs user's Tenant/Client IDs)
- P2: Refactor server.py into modular routers
- P2: External billing system API integration
- P3: Advanced reporting/analytics with export capabilities
- P3: Member portal for self-service eligibility checks
