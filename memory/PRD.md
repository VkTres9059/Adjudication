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
- Modular router architecture (17 routers)
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
- **834 Parser**: Full X12 envelope parsing, INS maintenance type codes, NM1 member names, DMG demographics, DTP dates, HD coverage types, REF IDs
- **837 Parser**: Hierarchical claim parsing, NM1*85 billing provider, CLM total billed, HI diagnosis codes with ICD-10, SV1/SV2 service lines, REF*G1 prior auth
- **835 Generator**: Compliant X12 output with ISA/GS/ST/BPR/TRN/DTM/N1/CLP/CAS/NM1/SVC/AMT/SE/GE/IEA segments
- **Validate/Preview**: `/api/edi/validate-834` and `/api/edi/validate-837`
- **Transaction Log**: EDI file processed log with type, status, envelope, record count, errors
- **Dedicated EDI Management page** (`/edi`): Upload & Validate, Generate 835, Transaction Log

### Phase 9: External Data Export Engine — Mar 30 2026
- **Export 834 Feed**: Active members = Add (021), below-threshold = Term (024), HIPAA 5010 X12 and CSV formats
- **Export Auth (278) Feed**: Authorization records from hold releases, X12 and CSV formats
- **Vendor Feed Configuration**: CRUD for feed vendors with type, feed types, format toggle (HIPAA 5010/CSV)
- **Transmission Log**: Outbound feed audit trail with date, filename, destination, status, record counts
- **EDI Management Tabs**: Export Feeds, Transmission Log, Inbound Log

### Phase 10: SFTP Scheduler Module — Mar 30 2026
- **SFTP Connection Manager**: Full CRUD for SFTP connections (Host, Port, Username, Password/SSH Key, Base Path) with password masking in API responses
- **Test Connection**: Validate credentials before saving (inline) or after saving (by ID), returns success/failure with message
- **Automated Intake Scheduling**: Frequency (Hourly/Daily at time/Weekly at day+time), File Name Pattern masking (e.g. `*834_Acme_*.dat`), Route Type mapping
- **Intelligent Routing Logic**: 834 files → Member Enrollment engine, 835/Claims files → Adjudication engine, Work Reports → Hour Bank module
- **APScheduler Integration**: Background cron-like scheduler with job rebuild on config change, manual trigger support
- **Intake Logs**: Full history table (Date, Schedule, Connection, Filename, Route, Records, Status, Error)
- **Error Handling**: Unknown members in work reports pushed to Duplicates & Errors queue
- **Settings Tab**: SFTP Scheduler tab with connection form, schedule form, and routing logic reference
- **EDI Management Tab**: SFTP Intake tab with intake history table

## Key API Endpoints
- EDI: `/validate-834`, `/upload-834`, `/validate-837`, `/upload-837`, `/generate-835`, `/transactions`, `/transmissions`, `/export-834`, `/export-auth-feed`
- SFTP: `/connections`, `/connections/{id}/test`, `/connections/test-inline`, `/schedules`, `/schedules/{id}/toggle`, `/schedules/{id}/run-now`, `/intake-logs`
- Members: CRUD + `/accumulators`, `/claims-history`, `/dependents`, `/audit-trail`
- Hour Bank: `/upload-work-report`, `/{id}`, `/{id}/manual-entry`, `/{id}/bridge-payment`, `/run-monthly`
- Settings: `/adjudication-gateway`, `/bridge-payment`, `/vendors`
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
- Iteration 16: SFTP Scheduler + Export Engine — 100% pass (24/24 backend, all frontend)
