# FletchFlow — Claims Adjudication System PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system supporting multiple lines of coverage. Start with Medical coverage, use Microsoft MFA for authentication, accept EDI 834/837 input with 835 output. Provide reporting for claims/eligibility. Implement strict duplicate claim prevention, built-in Medicare fee schedules, multi-line coverage, a comprehensive Preventive Coverage module, and Group Management.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI, collapsible categorized sidebar
- **Backend**: FastAPI (20 routers), MongoDB, JWT Auth (MSAL fallback), APScheduler
- **Structure**: `/app/backend/routers/`, `/app/backend/services/`, `/app/backend/models/`, `/app/backend/core/`

## Completed Features

### Phase 1-3: Core Engine + Gateway + Lifecycle
- Multi-line claims adjudication (Medical, Dental, Vision, Pharmacy)
- Medicare fee schedule pricing (377+ CPT codes, 87 GPCI localities)
- Real-time duplicate claim detection, JWT auth, Tiered Authorization Matrix
- Group Management with stop-loss, Preventive Coverage module
- Member lifecycle: reconciliation, retro-term/clawback, age-out rules

### Phase 4-5: Backend Refactoring + Navigation
- Modular router architecture, Collapsible categorized sidebar

### Phase 6: Variable Hour Bank Module — Mar 29 2026
- Multi-Tier Banking, Predictive Eligibility, Bridge Payments

### Phase 7: Member 360 View — Mar 30 2026
- Financial Accumulators, Claims History, Dependent Management

### Phase 8: Real X12 EDI Parser — Mar 30 2026
- 834/837 Parser, 835 Generator, Transaction Log

### Phase 9: External Data Export Engine — Mar 30 2026
- Export 834/278 Feeds, Vendor Config, Transmission Log

### Phase 10: SFTP Scheduler Module — Mar 30 2026
- Connection Manager, Automated Intake Scheduling, Intelligent Routing

### Phase 11: ASO/Level Funded Funding Module — Mar 30 2026
- Toggleable Funding Types (ASO/Level Funded/Fully Insured) in Groups
- Level Funded Claims Reserve Fund with deficit detection
- Dashboard Funding Health Widget

### Phase 12: Finance & Disbursement Module — Mar 30 2026
- **ASO Check Run Manager** (`/check-runs`): Provider-level claim batching (consolidate by NPI), 3-tab interface (Pending Runs, Run History, Vendor Payables), 5 real-time metrics
- **Wells Fargo API Integration** (SIMULATED): Funding Pull (employer → trust), Disbursement Push (trust → providers), WF Transaction IDs recorded on claims, WF webhook handler for auto-confirmation, Transaction status tracking per check run
- **Vendor Fee Management**: Non-claim vendor fees (PBM Access, Telehealth PEPM, Network Access, Admin Fee) as line items in check runs, CRUD management in Vendor Payables tab
- **Funding Request PDF**: Downloadable PDF with financial summary, provider payment schedule, vendor fee line items, WF transaction references
- **Check Run Lifecycle**: Generate (WF pull) → Confirm Funding (webhook) → Execute (WF disburse + ACH batch) → Claims to Paid with wf_transaction_id

## Key API Endpoints
- Check Runs: `/groups`, `/pending`, `/generate-funding-request`, `/{id}/confirm-funding`, `/{id}/execute`, `/{id}/pdf`, `/wf-webhook`, `/wf-transactions/{id}`, `/vendor-payables`
- Groups: CRUD + `/reserve-fund`, `/reserve-deposit`, `/pulse`
- Dashboard: `/metrics`, `/claims-by-status`, `/funding-health`
- EDI: `/validate-834`, `/upload-834`, `/generate-835`, `/export-834`, `/export-auth-feed`
- SFTP: `/connections`, `/schedules`, `/intake-logs`
- Members, Hour Bank, Settings, Reports, etc.

## Upcoming Tasks
- **P1**: Carrier Bordereaux Reporting Module
- **P1**: Azure AD MSAL real credentials
- **P2**: Network repricing vs contracted rates
- **P2**: External billing system API
- **P2**: Connect real Wells Fargo credentials
- **P3**: Member self-service portal

## Mocked/Stubbed
- MSAL Azure AD (JWT fallback)
- Wells Fargo API (SIMULATED — auto-success)

## Test Reports
- Iteration 13: Hour Bank — 100%
- Iteration 14: Member 360 — 100%
- Iteration 15: X12 EDI Parser — 100%
- Iteration 16: SFTP Scheduler + Export — 100% (24/24)
- Iteration 17: ASO/Level Funded Funding — 100% (28/28)
- Iteration 18: Finance & Disbursement + WF — 100% (23/23 + all frontend)
