# FletchFlow — Claims Adjudication System PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system supporting multiple lines of coverage. Start with Medical coverage, use Microsoft MFA for authentication, accept EDI 834/837 input with 835 output. Provide reporting for claims/eligibility. Implement strict duplicate claim prevention, built-in Medicare fee schedules, multi-line coverage, a comprehensive Preventive Coverage module, and Group Management.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI, collapsible categorized sidebar
- **Backend**: FastAPI (modular routers), MongoDB, JWT Auth (MSAL fallback)
- **Structure**: `/app/backend/routers/`, `/app/backend/services/`, `/app/backend/models/`, `/app/backend/core/`

## Completed Features

### Phase 1-3: Core Engine + Gateway + Lifecycle
- Multi-line claims adjudication (Medical, Dental, Vision, Pharmacy)
- Medicare fee schedule pricing (377+ CPT codes, 87 GPCI localities)
- Real-time duplicate claim detection
- JWT auth with role-based access (Admin, Examiner, Viewer)
- Tiered Authorization Matrix, Examiner Queue with auto-assignment
- Group Management with stop-loss, Preventive Coverage module
- Member lifecycle: reconciliation, retro-term/clawback, age-out rules

### Phase 4-5: Backend Refactoring + Navigation
- Modular router architecture (16 routers)
- Collapsible categorized sidebar

### Phase 6: Variable Hour Bank Module — Mar 29 2026
- Multi-Tier Banking (Current + Reserve), Predictive Eligibility Alerts
- Automated Bridge Payments, Manual Hour Entry
- Claims Integration Gatekeeper with eligibility source tracking

### Phase 7: Member 360 View — Mar 30 2026
- Financial Accumulator Dashboard (Individual/Family Deductible, OOP Max progress bars)
- Claims History tab with one-click inline EOB
- Dependent & Household Management with cross-accumulation
- Hour Bank status in header, static UI layout

### Phase 8: Real X12 EDI Parser — Mar 30 2026
- **834 Parser**: Full X12 envelope parsing (ISA/GS/ST), INS maintenance type codes (addition/cancellation/reinstatement), NM1 member names, DMG demographics, N3/N4 address, DTP effective dates, HD coverage types (health/dental/vision), REF member/group IDs
- **837 Parser**: Hierarchical claim parsing, NM1*85 billing provider + NM1*IL subscriber, CLM total billed, HI diagnosis codes with ICD-10 decimal insertion, SV1/SV2 service lines with modifiers, REF*G1 prior auth, DTP service dates
- **835 Generator**: Compliant X12 output with ISA/GS/ST/BPR/TRN/DTM/N1/CLP/CAS/NM1/SVC/AMT/SE/GE/IEA segments, CO-45 contractual + PR-1 deductible adjustments, service-level CAS and AMT
- **Validate/Preview**: `/api/edi/validate-834` and `/api/edi/validate-837` — preview without committing
- **Transaction Log**: Every EDI file processed is logged with type, status, envelope, record count, errors
- **Pipe-delimited fallback**: Both 834 and 837 accept pipe-delimited format for testing
- **Dedicated EDI Management page** (`/edi`): Upload & Validate tab, Generate 835 tab, Transaction Log tab
- **Reports shortcut**: EDI Interchange link on Reports page

## Key API Endpoints
- EDI: `/validate-834`, `/upload-834`, `/validate-837`, `/upload-837`, `/generate-835`, `/transactions`
- Members: CRUD + `/accumulators`, `/claims-history`, `/dependents`, `/audit-trail`
- Hour Bank: `/upload-work-report`, `/{id}`, `/{id}/manual-entry`, `/{id}/bridge-payment`, `/run-monthly`
- Settings: `/adjudication-gateway`, `/bridge-payment`
- Reports: `/fixed-cost-vs-claims`, `/hour-bank-deficiency`, `/predictive-eligibility`

## Upcoming Tasks
- **P1**: Carrier Bordereaux Reporting Module
- **P1**: Azure AD MSAL real credentials
- **P2**: Network repricing vs contracted rates
- **P2**: External billing system API
- **P3**: Member self-service portal

## Mocked/Stubbed
- MSAL Azure AD (JWT fallback)

## Test Reports
- Iterations 1-12: Core features, refactoring, sidebar, base hour bank
- Iteration 13: Hour Bank Upgrade — 100% pass
- Iteration 14: Member 360 View — 100% pass (14/14 backend)
- Iteration 15: X12 EDI Parser — 100% pass (25/25 backend, all frontend)
