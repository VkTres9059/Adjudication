# FletchFlow — Claims Adjudication System PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system supporting multiple lines of coverage. Start with Medical coverage, use Microsoft MFA for authentication, accept EDI 834/837 input with 835 output. Provide reporting for claims/eligibility. Implement strict duplicate claim prevention, built-in Medicare fee schedules, multi-line coverage, a comprehensive Preventive Coverage module, and Group Management.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI, collapsible categorized sidebar
- **Backend**: FastAPI (modular routers), MongoDB, JWT Auth (MSAL fallback)
- **Structure**: `/app/backend/routers/`, `/app/backend/services/`, `/app/backend/models/`, `/app/backend/core/`

## Completed Features

### Phase 1 — Core Claims Engine
- Multi-line claims adjudication (Medical, Dental, Vision, Pharmacy)
- Medicare fee schedule pricing (377+ CPT codes, 87 GPCI localities)
- Real-time duplicate claim detection
- EDI 834/837 intake, 835 output (mocked parser)
- JWT authentication with role-based access (Admin, Examiner, Viewer)
- Group Management with stop-loss analytics
- Preventive Coverage module
- Dashboard with metrics, claims-by-status, claims-by-type charts

### Phase 2 — Adjudication Gateway & Examiner Workspace
- Tiered Authorization Matrix (auto-approve, examiner review, manager approval)
- Global Adjudication Gateway settings
- Examiner Queue Dashboard with auto-assignment engine
- Hard Hold / Soft Hold claim states
- Prior Authorization tracking, COB processing

### Phase 3 — Eligibility & Member Lifecycle
- Reconciliation Dashboard, Retroactive Termination / Clawback
- Pending Eligibility Queue, Age-Out Rules

### Phase 4 — Backend Refactoring
- Migrated ~3,850 line server.py monolith to modular router architecture (16 routers)

### Phase 5 — Navigation & UX
- Collapsible categorized sidebar (Operations, Plan Management, Claims Center, Network & Groups)

### Phase 6 — Variable Hour Bank Module (Base + Upgrade) — Mar 29 2026
- Multi-Tier Banking: Current Month + Reserve Bank (capped at 500 hrs)
- Predictive Eligibility Alerts: Burn rate, months remaining, at-risk flags
- Automated Bridge Payment Logic: Cash-to-hours, instant activation
- Manual Hour Entry, Claims Integration Gatekeeper
- Eligibility Source Tracking badges on claims
- Bridge Payment Settings, Predictive Eligibility Dashboard
- Enhanced Hour Bank Deficiency Report with multi-tier columns

### Phase 7 — Member 360 View — Mar 30 2026
- **Financial Accumulator Dashboard**: Live progress bars for Individual Deductible, Family Deductible, OOP Max — update on paid claims
- **Member Claims History**: Full claims table within member profile with one-click inline EOB
- **Dependent & Household Management**: Subscriber hierarchy, dependents list, family deductible cross-accumulation
- **Integrated Hour Bank Status**: Balance chip in member header showing hold status
- **Static UI**: Header + accumulators remain stationary while tabs switch (zero layout jitter)
- New endpoints: `/api/members/{id}/accumulators`, `/api/members/{id}/claims-history`, `/api/members/{id}/dependents`

## Key API Endpoints
- Members: CRUD + `/accumulators` + `/claims-history` + `/dependents` + `/audit-trail`
- Hour Bank: `/upload-work-report` + `/{id}` + `/{id}/manual-entry` + `/{id}/bridge-payment` + `/run-monthly` + `/notifications/list`
- Settings: `/adjudication-gateway` + `/bridge-payment`
- Reports: `/fixed-cost-vs-claims` + `/hour-bank-deficiency` + `/predictive-eligibility`
- Claims: CRUD + `/adjudicate` + `/batch` + `/cob` + `/hold` + `/release-hold`

## Upcoming Tasks (Prioritized Backlog)
- **P1**: Carrier Bordereaux Reporting Module (link hour bank draws to premium push)
- **P1**: Real X12 EDI parser (834/837/835)
- **P1**: Azure AD MSAL real credentials
- **P2**: Network repricing vs contracted rates
- **P2**: External billing system API integration
- **P3**: Member self-service portal

## Mocked/Stubbed
- Real X12 EDI parsing (mocked)
- MSAL Azure AD (JWT fallback)

## Test Reports
- Iterations 1-12: Core features, refactoring, sidebar, base hour bank
- Iteration 13: Hour Bank Module Upgrade — 100% pass
- Iteration 14: Member 360 View — 100% pass (14/14 backend, all frontend)
