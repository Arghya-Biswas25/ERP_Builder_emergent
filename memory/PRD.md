# Zappizo - AI-Powered ERP Builder PRD

## Original Problem Statement
Build a production-ready AI-powered ERP Builder platform called Zappizo that converts natural language prompts into fully functional ERP system architectures with generated code.

## Architecture
- **Backend**: FastAPI + MongoDB + OpenRouter API (free tier, model: openrouter/free)
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **AI Agents**: 7 agents orchestrated by a central pipeline state machine

## User Personas
- Business owners/CTOs wanting to prototype ERP systems
- Developers looking for ERP architecture scaffolding
- Consultants designing ERP solutions for clients

## Core Requirements (Static)
1. Chat-based interface for entering business descriptions
2. AI-powered requirement analysis and gathering
3. ERP architecture generation (modules, schemas, APIs, workflows)
4. Code generation for frontend and backend
5. Code review with quality scoring
6. Live preview of all generated artifacts
7. Modification support via chat in completed projects

## What's Been Implemented (March 30, 2026)
- [x] Dashboard with project CRUD
- [x] Chat-based AI interaction with multi-step requirement gathering
- [x] 7 AI agents: Requirement Analyzer, Requirement Gatherer, ERP Architect, JSON Transformer, Frontend Generator, Backend Generator, Code Reviewer
- [x] Central orchestrator with pipeline state machine
- [x] Background task auto-pipeline after requirements gathering
- [x] Preview panel with 7 tabs: Overview, Modules, Database, API, Code, Review, JSON
- [x] Syntax-highlighted code viewer
- [x] Modification support in COMPLETE state
- [x] Pipeline progress indicator with animated stages
- [x] Lazy-loading of large pipeline outputs

## Prioritized Backlog
### P0 (Critical)
- [ ] Deployment pipeline agent
- [ ] Version history panel

### P1 (Important)
- [ ] Streaming responses (SSE) for real-time chat
- [ ] Database schema visualization (ER diagram)
- [ ] Export/download generated code as ZIP
- [ ] Selective module regeneration

### P2 (Nice to Have)
- [ ] Multi-tenant architecture
- [ ] Role-based access control
- [ ] Plugin system for custom modules
- [ ] AI automation features (auto-invoice, demand prediction)

## Next Tasks
1. Add version history panel with file snapshots
2. Implement streaming responses for better UX
3. Add code download/export feature
4. Build ER diagram visualization for database tab
5. Add deployment pipeline (Docker + CI/CD)
