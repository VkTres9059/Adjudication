# FletchFlow — Claims Adjudication System PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system supporting multiple lines of coverage. Start with Medical, use Microsoft MFA for authentication, accept EDI 834/837 input with 835 output. Reporting for claims/eligibility. Strict duplicate claim prevention, built-in Medicare fee schedules, multi-line coverage, Preventive Coverage module, and Group Management.

## Architecture
- **Frontend**: React 18, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, MongoDB, APScheduler, ReportLab
- **AI**: OpenAI GPT-5.2 via emergentintegrations (EMERGENT_LLM_KEY)

## Completed Features

### Core Engine (Phase 1)
- Medical claims adjudication with Medicare fee schedule pricing
- EDI 834/837 parser with 835 output generation
- Duplicate claim detection with fuzzy matching
- Member/Group/Plan CRUD with eligibility verification
- Examiner Queue with auto-assignment engine
- Prior Authorization workflows
- Preventive Coverage module with 440+ procedure codes
- Hour Bank system with reserve/bridge logic

### Financial & Disbursement (Phase 2)
- ASO Check Run Manager with provider batching
- Level Funded Claims Reserve Tracker
- Vendor Payables ledger
- Wells Fargo API integration (MOCKED) for funding pulls/disbursements
- PDF generation (funding requests, SBC documents)

### SFTP & EDI Automation (Phase 2)
- SFTP Connection Manager with encrypted credentials
- Automated intake scheduling (APScheduler)
- External Data Export Engine

### Plan Configuration (Phase 3)
- Multi-tier benefit design with modular benefit stacking
- Network tiers with Reference Based Pricing (RBP)
- Specific/Aggregate stop-loss tracking + auto-flag in adjudication
- SBC PDF generation endpoint
- 6-tab Plan Builder UI (General, Cost Sharing, Benefits, Network, Risk, Exclusions)

### Data Tiering & Reporting (Phase 4 — Current)
- **Tiering Engine**: Auto-categorizes claims into 3 tiers:
  - Tier 1 (Auto-Pilot): Claims < $2,500 passing all edits
  - Tier 2 (Clinical Review): Trigger CPT codes or Prior Auths
  - Tier 3 (Stop-Loss Trigger): >50% specific or 80% aggregate attachment
- **Broker Deck**: Surplus vs Paid with loss ratios, PEPM across all groups
- **Carrier Bordereaux**: Eligibility/premium reconciliation with member details
- **Utilization Review**: Top 10 providers, costliest CPT codes, network leakage %
- **Risk Dial**: Real-time Agg/Spec stop-loss utilization on Dashboard (auto-renders when groups have stop-loss configured)
- Batch claim classification with tier persistence

### AI Provider Call Center Agent (Phase 4 — Current)
- GPT-5.2 powered HIPAA-compliant AI assistant
- Eligibility verification via Member data + Hour Bank
- Claim status inquiry with adjudication notes
- Accumulator inquiry (deductible, OOP, annual max)
- Pre-certification check against plan rules
- Provider authentication via Tax ID + Member ID
- Multi-session support with conversation history
- Escalation to Examiner Queue with Call Log tickets
- Quick-prompt UI with suggested queries

## Testing History
- Iteration 16: SFTP Tests — 100% Pass
- Iteration 17: Funding Module Tests — 100% Pass
- Iteration 18: Finance & Disbursement — 100% Pass
- Iteration 19: Data Tiering, Reports, AI Agent, Plan Builder — 100% (29/29 backend, all frontend)

## Mocked Integrations
- **MSAL Azure AD**: JWT fallback for local dev
- **Wells Fargo API**: Simulated in services/wells_fargo.py
- **Email Alerts**: Risk trigger emails logged, not sent

## Upcoming Tasks (Backlog)
- P1: Azure AD real MSAL credentials configuration
- P2: Network repricing (Medicare vs contracted rates)
- P2: External billing system API integration
- P2: Real Wells Fargo credentials
- P3: Member self-service portal
- P3: Twilio/Vapi voice integration for AI Agent
