# FletchFlow — Claims Adjudication System PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system supporting multiple lines of coverage. Fully automated, tightly coupled system where Plan Design → Drives → Group Setup → Drives → Claims Adjudication → Drives → Payment Execution with zero fragmentation, zero duplication of logic, and full transparency.

## Architecture
- **Frontend**: React 18, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, MongoDB, APScheduler, ReportLab
- **AI**: OpenAI GPT-5.2 via emergentintegrations (EMERGENT_LLM_KEY)

---

## Completed Features

### Phase 1 — Core Engine
- Medical claims adjudication with Medicare fee schedule pricing
- EDI 834/837 parser with 835 output generation
- Duplicate claim detection with fuzzy matching
- Member/Group/Plan CRUD with eligibility verification
- Examiner Queue with auto-assignment engine
- Prior Authorization workflows
- Preventive Coverage module (440+ procedure codes)
- Hour Bank system with reserve/bridge logic

### Phase 2 — Financial & Automation
- ASO Check Run Manager with provider batching
- Level Funded Claims Reserve Tracker
- Vendor Payables ledger
- Wells Fargo API integration (MOCKED)
- SFTP Connection Manager & Automated Intake Scheduling
- External Data Export Engine
- PDF generation (ReportLab) for funding requests, SBC documents

### Phase 3 — Plan Configuration
- Multi-tier benefit design with modular benefit stacking
- Network tiers with Reference Based Pricing (RBP)
- Specific/Aggregate stop-loss tracking + auto-flag in adjudication
- SBC PDF generation endpoint
- 6-tab Plan Builder UI (General, Cost Sharing, Benefits, Network, Risk, Exclusions)

### Phase 4 — Data Tiering & AI
- Tiering Engine: Tier 1 (Auto-Pilot <$2,500), Tier 2 (Clinical Review), Tier 3 (Stop-Loss Trigger)
- Broker Deck, Carrier Bordereaux, Utilization Review reports
- Risk Dial: Real-time Agg/Spec stop-loss on Dashboard
- AI Provider Call Center Agent (GPT-5.2, HIPAA-compliant, with escalation)

### Phase 5 — Core Architecture Completion (Current)
**Plan Design Engine:**
- Plan version control (snapshot before every update, diff between versions)
- Rx Rules Engine (5 formulary tiers, GLP-1 handling, mandatory generic substitution)
- Visit-based service limits (per-plan configurable)
- Network naming (Cigna OAP, Anthem BlueCard, etc.)

**Group & Eligibility:**
- Enrollment tier logic (EE, ES, EC, Family with auto-adjust >2 dependents)
- Block of Business tracking at group level
- Carrier + MGU relationship management with contract IDs
- Premium per member tracking

**Claims Adjudication:**
- Coordination of Benefits (COB) engine with birthday rule, active employee priority
- EOB PDF generation (member-facing) with service line details
- EOP PDF generation (provider-facing) with payment details
- IDR tracking fields (case number, status, audit)

**Payment & Check Run System:**
- Payment types: ACH, Virtual Card, Check
- Duplicate payment prevention
- Payment batch processing (grouped by funding source)
- Payment reversals with claim status revert
- Payment adjustments (increase, decrease, void)
- Full reconciliation (claims paid vs payments disbursed vs stop-loss)

**Admin Portal:**
- 5 portal roles: Admin, TPA Admin, MGU Admin, Carrier Viewer, Analytics Viewer
- User creation with portal role assignment and group-level access
- TPA onboarding with data feed configuration (EDI/API/SFTP)
- System-wide overview dashboard
- Full audit log system with filters (entity, action, user, date range)
- Cross-system traceability: Plan → Group → Eligibility → Claim → Payment chain

---

**Adjudication Enhancement (Phase 5 Final):**
- Fixed P0 bug: ClaimResponse Pydantic model now returns all adjudication fields (data_tier, tier_label, plan_version, cob_applied, stop_loss_flag, precert_penalty_applied, payment_ready, network_status, idr_case_number, idr_status)
- Claims UI: Tier column (T1/T2/T3 badges), Flags column (COB/IDR/SL/PC), Docs column (EOB/EOP PDF links)
- Claims Lifecycle Funnel on Dashboard
- Auto data-tier classification in adjudication engine
- Auto payment queueing for Tier 1 claims

## Testing History
- Iterations 16-18: SFTP, Funding, Check Runs, Wells Fargo — 100% Pass
- Iteration 19: Data Tiering, Reports, AI Agent, Plan Builder — 100% (29/29 backend)
- Iteration 20: Payments, Admin Portal, Audit, Rx Rules, EOB/EOP, IDR — 100% (18/18 backend, all frontend)
- Iteration 21: P0 ClaimResponse adjudication fields fix — 100% (10/10 backend, all frontend)

## Mocked Integrations
- **MSAL Azure AD**: JWT fallback for local dev
- **Wells Fargo API**: Simulated in services/wells_fargo.py
- **Email Alerts**: Risk trigger emails logged, not sent

## Upcoming Tasks (Backlog)
- P1: Azure AD real MSAL credentials configuration
- P2: Network repricing (Medicare vs contracted rates)
- P2: External billing system API integration
- P2: Real Wells Fargo credentials
- P2: Zelis payment vendor integration
- P3: Member self-service portal
- P3: Twilio/Vapi voice integration for AI Agent
