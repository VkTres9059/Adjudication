# Javelina Claims Adjudication System - PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system on top of Javelina that supports multiple lines of coverage including medical, dental, vision, and hearing. The system must be modular, configurable by product and plan, and capable of high-volume automated adjudication with minimal manual intervention. The system must also include robust plan build functionality and strict duplicate claim prevention.

## User Personas
- **Admin**: Full system access - plan configuration, user management, settings, audit logs
- **Adjudicator**: Claims processing - create/adjudicate claims, add members, resolve duplicates
- **Reviewer**: Read-only review access - view claims, members, plans, resolve duplicates
- **Auditor**: Compliance access - view claims, audit logs, reports, export data

## Core Requirements (Static)
1. Plan Build and Benefit Configuration Layer
2. Intake Layer (EDI 834/837, API)
3. Adjudication Engine (Medical first, then Dental/Vision/Hearing)
4. Duplicate Claim Prevention (Exact + Near duplicate detection)
5. Payment Output Layer (835 generation)
6. Analytics and Monitoring Dashboard
7. Role-based Access Control

## User Choices & Decisions
- **Authentication**: JWT-based auth (Microsoft MFA mocked for demo)
- **Phase 1 Coverage**: Medical only
- **EDI Support**: 834 enrollment, 837 claims input, 835 payment output
- **Reporting**: Basic claims and eligibility reports
- **Design**: New-age creative UI with organic & earthy theme

## What's Been Implemented (March 2026)

### Backend (FastAPI + MongoDB)
- [x] JWT Authentication with role-based access control (Admin, Adjudicator, Reviewer, Auditor)
- [x] Plan Build API - CRUD for benefit plans with deductibles, copays, coinsurance, OOP max
- [x] Member Management API - eligibility, enrollment
- [x] Claims Processing API - create, adjudicate, approve/deny/pend
- [x] Duplicate Detection Engine - exact and near-duplicate matching
- [x] EDI 834 upload (enrollment)
- [x] EDI 837 upload (claims)
- [x] EDI 835 generation (payment output)
- [x] Dashboard Metrics API
- [x] Audit Logging
- [x] **CPT Code Database** - 189 codes across 7 categories (E/M, Surgery, Radiology, Pathology/Lab, Medicine, Anesthesia, HCPCS)
- [x] **Medicare Fee Schedule** - Work RVU, PE RVU, MP RVU with 2024 Conversion Factor ($33.2875)
- [x] **GPCI Localities** - 87 localities with geographic cost index adjustments
- [x] **Medicare Rate Calculator** - Formula: [(Work RVU × Work GPCI) + (PE RVU × PE GPCI) + (MP RVU × MP GPCI)] × CF

### Frontend (React + Tailwind + Shadcn UI)
- [x] Login/Register with role selection
- [x] Dashboard with metrics, duplicate alerts, charts
- [x] Claims List with filters, search, status badges
- [x] Claim Detail with adjudication actions
- [x] Plan Builder with tabs for General, Cost Sharing, Benefits, Exclusions
- [x] Plans List with status and type filters
- [x] Members List with search and 834 upload
- [x] **Fee Schedule Page** - CPT code search, GPCI locality selector, rate calculator
- [x] Duplicates Review page with resolution workflow
- [x] Reports page with charts and 835 export
- [x] Settings page with audit log viewer
- [x] Responsive sidebar navigation with user profile

### Adjudication Features
- [x] **Medicare-based pricing** - Uses CPT code RVUs with GPCI adjustments
- [x] Plan reimbursement methods: fee_schedule (100%), percent_medicare (120%), percent_billed (80%), rbp (140%), contracted (100%)
- [x] Accumulator tracking (deductible, OOP)
- [x] Service line level processing with CPT descriptions
- [x] Automatic duplicate denial for 95%+ matches
- [x] Pend for review on 50-95% matches
- [x] Override duplicate capability for authorized users

## Prioritized Backlog

### P0 - Critical (Next Sprint)
- [ ] Dental line of coverage
- [ ] Vision line of coverage
- [ ] Hearing line of coverage
- [ ] Real EDI X12 parser (currently simplified format)

### P1 - High Priority
- [ ] Microsoft Entra ID (Azure AD) SSO integration
- [ ] Network repricing integration
- [ ] Prior authorization workflow
- [ ] Fee schedule management
- [ ] Batch claim processing

### P2 - Medium Priority
- [ ] Coordination of Benefits (COB)
- [ ] Stop-loss tracking
- [ ] Member portal
- [ ] Provider portal
- [ ] EOB/EOP document generation

### P3 - Future
- [ ] Real-time eligibility verification API
- [ ] Payment vendor integrations (ACH, virtual card)
- [ ] Advanced analytics and MLR reporting
- [ ] AI-powered claim review assistance

## Next Action Items
1. Add dental coverage support with CDT codes, class-based benefits, annual max
2. Implement vision coverage with exam/materials logic
3. Integrate proper X12 EDI parser library
4. Add Microsoft Entra ID authentication
5. Build network repricing workflow

## Technical Notes
- Backend runs on port 8001 (FastAPI)
- Frontend runs on port 3000 (React)
- MongoDB for data persistence
- JWT tokens expire in 60 minutes
- All routes prefixed with /api
