# FletchFlow — Claims Adjudication System PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system supporting multiple lines of coverage. Start with Medical coverage, use Microsoft MFA for authentication, accept EDI 834/837 input with 835 output. Provide reporting for claims/eligibility. Implement strict duplicate claim prevention, built-in Medicare fee schedules, multi-line coverage, a comprehensive Preventive Coverage module, and Group Management.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI, collapsible categorized sidebar
- **Backend**: FastAPI (modular routers), MongoDB, JWT Auth (MSAL fallback), APScheduler
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
- Modular router architecture (19 routers)
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
- 834/837 Parser with full X12 envelope validation
- 835 Generator with compliant ISA/GS/ST segments
- Validate/Preview endpoints, Transaction Log

### Phase 9: External Data Export Engine — Mar 30 2026
- Export 834 Enrollment Feed, Authorization 278 Feed
- Vendor Feed Configuration CRUD, Transmission Log
- HIPAA 5010 X12 and CSV format support

### Phase 10: SFTP Scheduler Module — Mar 30 2026
- SFTP Connection Manager with Test Connection button
- APScheduler-backed automated intake scheduling (Hourly/Daily/Weekly)
- Intelligent Routing: 834→Enrollment, 835→Adjudication, Work Reports→Hour Bank
- Intake Logs & Error Handling with Duplicates queue integration

### Phase 11: ASO/Level Funded Funding Module — Mar 30 2026
- **ASO Check Run Manager**: Weekly claim aggregation, Funding Request generation, Check Run execution with ACH batch generation. Full lifecycle: pending_funding → funded → executed (claims move to 'paid')
- **Level Funded Claims Reserve Fund**: Virtual claims bucket with monthly deposit tracking, auto-deduction as claims adjudicate, deficit detection, Aggregate Stop-Loss flagging, 6-month rolling breakdown
- **Toggleable Funding Types**: Mandatory `funding_type` dropdown (ASO/Level Funded/Fully Insured) in Create Group wizard. Dynamic UI shows Check Run or Reserve Tracker based on type
- **Dashboard Funding Health Widget**: Real-time ASO (Pending Funding vs Paid), Level Funded (Expected Fund vs Actual Claims vs Surplus), Fully Insured summary. Deficit groups highlighted
- **Static UI**: All financial ledgers, check run tables, and reserve trackers render without layout shift

## Key API Endpoints
- Check Runs: `/check-runs/groups`, `/check-runs/pending`, `/check-runs/generate-funding-request`, `/check-runs/{id}/confirm-funding`, `/check-runs/{id}/execute`, `/check-runs`
- Groups: CRUD + `/reserve-fund`, `/reserve-deposit`, `/pulse`, `/attach-plan`
- Dashboard: `/metrics`, `/claims-by-status`, `/claims-by-type`, `/recent-activity`, `/funding-health`
- EDI: `/validate-834`, `/upload-834`, `/validate-837`, `/upload-837`, `/generate-835`, `/export-834`, `/export-auth-feed`, `/transmissions`
- SFTP: `/connections`, `/connections/{id}/test`, `/schedules`, `/schedules/{id}/toggle`, `/intake-logs`
- Members: CRUD + `/accumulators`, `/claims-history`, `/dependents`
- Hour Bank: `/upload-work-report`, `/{id}/manual-entry`, `/{id}/bridge-payment`, `/run-monthly`
- Settings: `/adjudication-gateway`, `/bridge-payment`, `/vendors`

## Upcoming Tasks
- **P1**: Build Carrier Bordereaux Reporting Module
- **P1**: Configure real Azure AD credentials for MSAL
- **P2**: Network repricing vs contracted rates
- **P2**: External billing system API
- **P3**: Member self-service portal

## Mocked/Stubbed
- MSAL Azure AD (JWT fallback)

## Test Reports
- Iteration 13: Hour Bank Upgrade — 100% pass
- Iteration 14: Member 360 View — 100% pass
- Iteration 15: X12 EDI Parser — 100% pass
- Iteration 16: SFTP Scheduler + Export Engine — 100% pass (24/24)
- Iteration 17: ASO/Level Funded Funding Module — 100% pass (28/28 backend, all frontend)
