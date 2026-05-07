# Hjemmel — kommunal AI-compliance platform

**Kalundborg Kommunes officielle AI-compliance-platform** der hjemler hver vurdering i en konkret lovartikel — ordret citat, verificeret mod kilden, deterministisk regelmotor.

> Tidligere "Project Judge Dredd" / "Judge Jarvis". Branded "Hjemmel" fra v3.

## 🚀 Features (v3 / alpha.13)

### Kernefunktionalitet
- **Vurdering** (`/vurdering`) — Beskriv et AI-system i fri tekst eller upload PDF/DOCX. LLM ekstraherer signaler + predikater; deterministisk regelmotor evaluerer 15 regler og returnerer GO / BETINGET-GO / NO-GO med inline lov-citater.
- **Sager** (`/sager`) — Kanban-workflow med 6 statuses (kladde → vurderet → remediation → godkendt → idriftsat → arkiveret). Drag-drop mellem kolonner med audit-trail.
- **Historik** (`/historik`) — Append-only audit-log over alle vurderinger; filterbar per status; klik for fuld reproduktion.
- **Lov-overvågning** (`/lov-overvaagning`) — Daglig job verificerer at hver regels lov-citat stadig findes ordret i kilden (EUR-Lex, Retsinformation). Flagger til juridisk review hvis ikke.
- **Sammenlign** (`/sammenlign`) — Side-om-side diff mellem legacy ComplianceController og v3 rule_engine; bruges til at validere Kategori A-sletning.

### Aktive lovregler (15)
- **EU AI-forordningen 2024/1689**: art. 5 (forbudte praksisser), art. 6 (højrisiko-klassifikation), art. 13 (transparens), art. 14 (menneskelig overvågning), art. 50
- **GDPR / Databeskyttelsesforordningen 2016/679**: art. 5 (principper), art. 6 (retsgrundlag), art. 22 (automatiserede afgørelser), art. 32 (sikkerhed), art. 35 (DPIA)
- **Forvaltningsloven**: §§ 3, 19, 22, 24
- **Offentlighedsloven**: § 13
- **Sektorlove**: 6 templates klar til jurist-interview (servicelov §§ 11, 50, 102; beskæftigelseslov §§ 11, 27; sundhedslov § 23)

### Viden & Research
- **Videnbase** - Dynamisk knowledge base med automatisk opdatering
  - Auto-generering af nye termer fra research queries
  - LLM-baseret definition generering
  - Daglig scheduled opdatering kl. 03:00
  - Web search integration (EUR-Lex, Datatilsynet, EDPB, Retsinformation)
- **Juridisk Research** - Real-time legal research med AI-powered søgning
  - Multi-query web search
  - Source citations og authority scoring
  - LLM-based summaries
- **Relevante Links** - Kurateret samling af compliance ressourcer

### Tekniske Kapabiliteter
- **Multi-agent arkitektur** - LangGraph-baserede agenter for intelligent analyse
- **Automatisk dokumentation** - Generering af compliance rapporter
- **DPIA & FRIA Integration** - Automatisk vurdering af impact assessments
- **Risk assessment** - Unacceptable, High, Limited, Minimal risk levels
- **Automated decision-making analysis** - GDPR Artikel 22 compliance
- **Sector-specific compliance** - Branchespecifikke krav og regler
- **Real-time legal research** - Live web search og præcedens analyse
- **Gap analysis** - Identificering af compliance gaps og mitigation strategies
- **Knowledge Base Auto-updater** - Intelligent term extraction og definition generation

## 📋 Installation

### Forudsætninger
- Python 3.11+
- Node.js 18+ og npm 9+
- OpenAI API nøgle eller Anthropic API nøgle
- Docker og Docker Compose (valgfrit)

### Lokal Installation

1. **Klon repository:**
```bash
git clone https://github.com/Parthee-Vijaya/Judge_dredd.git
cd Judge_dredd
```

2. **Backend Setup:**
```bash
# Opret virtual environment
python -m venv venv
source venv/bin/activate  # På Windows: venv\Scripts\activate

# Installer dependencies
pip install -r requirements.txt

# Konfigurer environment
cp .env.example .env
# Rediger .env filen med dine API nøgler
```

3. **Frontend Setup:**
```bash
# Installer NPM workspace dependencies
npm install

# Start frontend development server
cd frontend && BROWSER=none npm start
```

4. **SMTP Configuration:**

Den indbyggede AI-sagsformular sender mails via SMTP. Udfyld følgende variabler i `.env`:

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS` – SMTP-server detaljer
- `SMTP_FROM` og evt. `SMTP_REPLY_TO` – afsenderadresse
- `AI_CASES_RECIPIENT` – hovedmodtager (standard: ServicePortalen@kalundborg.dk)
- `AI_CASES_CC` – ekstra modtagere (standard inkluderer pavi@kalundborg.dk)

5. **Start Services:**
```bash
# Backend (port 8000)
python main.py

# Frontend (port 3000)
cd frontend && npm start
```

### NPM Workspace Setup

Projektet bruger NPM workspaces for optimal monorepo management:

```bash
# Root package.json indeholder workspace konfiguration
# Clean install ved konflikter:
npm run clean && npm install
```

### Docker Installation

1. **Byg og start med Docker Compose:**
```bash
docker-compose up --build
```

Dette starter:
- FastAPI backend på http://localhost:8000
- React frontend på http://localhost:3000
- PostgreSQL database
- Qdrant vector database

## 🎯 Anvendelse

### Quick Check
Hurtig compliance vurdering:

1. Åbn http://localhost:8501
2. Naviger til "Quick Check"
3. Beskriv dit AI system
4. Få øjeblikkelig feedback om risk level og compliance status

### Full Assessment
Omfattende analyse:

1. Gå til "Full Assessment"
2. Udfyld detaljeret information om dit projekt
3. Systemet analyserer:
   - AI Act compliance
   - GDPR requirements
   - Danske regler
   - Sektor-specifikke krav
4. Modtag komplet rapport med:
   - Risk assessment
   - Compliance gaps
   - Recommendations
   - Action items

### API Endpoints

**7-Punkts AI-Vurdering (NYT!):**
Komplet struktureret vurdering gennem 7 trin:
```bash
curl -X POST http://localhost:8000/api/compliance/7-punkts-vurdering \
  -H "Content-Type: application/json" \
  -d @example_7_step_request.json
```

**Vurderingsguide:**
```bash
curl -X GET http://localhost:8000/api/compliance/7-punkts-guide
```

**Quick Check:**
```bash
curl -X POST http://localhost:8000/api/compliance/hurtig-tjek \
  -H "Content-Type: application/json" \
  -d '{
    "description": "AI recruitment tool",
    "ai_type": "predictive_ai",
    "sector": "Employment",
    "uses_personal_data": true,
    "automated_decisions": true
  }'
```

**Full Assessment:**
```bash
curl -X POST http://localhost:8000/api/compliance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My AI Project",
    "description": "Detailed description...",
    "ai_type": "predictive_ai",
    "sector": "Healthcare",
    "personal_data": true,
    "automated_decision_making": false
  }'
```

## 🏗️ Arkitektur

### Komponenter

```
Judge_dredd/
├── frontend/               # React frontend application
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   │   ├── Sidebar.js          # Collapsible navigation
│   │   │   ├── NewsSection.js      # Kalundborg news integration
│   │   │   ├── NewsTicker.js       # Real-time news ticker
│   │   │   └── SkeletonLoader.js   # Loading states
│   │   ├── pages/         # Page components
│   │   │   ├── HomePage.js         # Landing page
│   │   │   ├── QuickCheckPage.js   # Quick compliance check
│   │   │   ├── AISagerPage.js      # AI cases management
│   │   │   ├── KnowledgeBasePage.js # Dynamic knowledge base
│   │   │   ├── ResearchPage.js     # Legal research tool
│   │   │   └── DashboardPage.js    # Analytics dashboard
│   │   ├── data/          # Static data and configurations
│   │   │   ├── statsData.js        # 100+ Kalundborg Kommune stats
│   │   │   └── aiActDidYouKnow.js  # Educational content
│   │   └── App.js         # Main app component
│   └── package.json       # Frontend dependencies
├── src/                   # Python backend
│   ├── core/              # Core models og utilities
│   │   └── models.py      # Pydantic data models
│   ├── compliance/        # Compliance checkers
│   │   ├── ai_act_checker.py
│   │   └── gdpr_checker.py
│   ├── agents/            # LangGraph agents
│   │   └── quick_check_agent.py
│   ├── research/          # Research tools
│   │   └── web_searcher.py         # Web search integration
│   └── services/          # Background services
│       └── knowledge_base_updater.py # Auto KB updates
├── data/                  # Data storage
│   ├── knowledge_base.json         # Dynamic knowledge base
│   └── news_fallback.json          # News cache
├── main.py                # FastAPI backend
├── requirements.txt       # Python dependencies
├── package.json           # NPM workspace configuration
├── docker-compose.yml     # Docker configuration
└── README.md
```

### Tech Stack
- **Backend:** FastAPI, LangGraph, LangChain, APScheduler
- **Frontend:** React 18, React Router, Styled Components, Framer Motion
- **AI/LLM:** OpenAI GPT-4, Anthropic Claude
- **Database:** JSON-based storage (PostgreSQL ready)
- **Web Search:** DuckDuckGo, authoritative legal sources
- **Deployment:** Docker, NPM workspaces, Kubernetes-ready
- **Scheduling:** APScheduler for automated tasks

## 📊 Compliance Frameworks

### EU AI Act (2024)
- Prohibited practices detection
- Risk level classification
- High-risk system requirements
- Transparency obligations

### GDPR
- Legal basis assessment
- Data subject rights
- Automated decision-making (Art. 22)
- DPIA requirements

### Danish Regulations
- Datatilsynet guidelines
- Sector-specific requirements
- National AI strategy alignment

## 🔧 Konfiguration

### Environment Variables

Opret `.env` fil med:

```env
# AI Models
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
DEFAULT_LLM_MODEL=gpt-4o-mini

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/compliance_db
QDRANT_URL=http://localhost:6333

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key

# Features
ENABLE_CACHING=True
DEBUG_MODE=False
```

## 🧪 Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

## 📚 Eksempler

### Eksempel 1: Healthcare AI
```python
project = ProjectInput(
    name="Patient Diagnosis Assistant",
    description="AI system for preliminary diagnosis",
    ai_type="predictive_ai",
    sector="Healthcare",
    personal_data=True,
    data_types=["health", "biometric"],
    automated_decision_making=False
)
# Result: HIGH RISK - Requires full compliance
```

### Eksempel 2: Chatbot
```python
project = ProjectInput(
    name="Customer Service Bot",
    description="AI chatbot for customer support",
    ai_type="generative_ai",
    sector="Retail",
    personal_data=False,
    automated_decision_making=False
)
# Result: LIMITED RISK - Transparency requirements
```

## 🤝 Bidrag

Vi modtager gerne bidrag! Se CONTRIBUTING.md og AGENTS.md for guidelines.

## 📄 Licens

MIT License - se LICENSE fil for detaljer.

## 🆘 Support

- **Documentation:** http://localhost:8501 (Knowledge Base)
- **API Docs:** http://localhost:8000/docs
- **Issues:** GitHub Issues

## 🔄 Version Historik

### v0.8.0 - Kalundborg Branding & UI Improvements (8. Oktober 2025)
**UI/UX Forbedringer:**
- ✅ Kompakt sidebar med sammenklappelige sektioner
- ✅ Optimeret platform version kort med collapsible detaljer
- ✅ Fjernet platform version fra hero sektion
- ✅ Kalundborg red theme (#C94416) på tværs af komponenter
- ✅ Smooth animations og hover effects
- ✅ Responsive design forbedringer

**Knowledge Base:**
- ✅ Automatisk daglig opdatering kl. 03:00
- ✅ LLM-baseret term extraction fra research queries
- ✅ Auto-generering af definitioner med web search
- ✅ Integration med EUR-Lex, Datatilsynet, EDPB, Retsinformation

**Teknisk:**
- ✅ APScheduler integration for scheduled tasks
- ✅ WebSearcher async implementation
- ✅ Query tracking (sidste 100 research queries)
- ✅ Improved error handling

### v0.7.0 - Hero Stats & Dynamic Content (7. Oktober 2025)
**Features:**
- ✅ 100+ real stats fra Kalundborg Kommune
- ✅ Auto-rotation hvert minut (60s interval)
- ✅ 20+ kategorier (Budget, Klima, Borgere, Sundhed, etc.)
- ✅ FadeIn animations for smooth transitions
- ✅ Responsive grid layout

### v0.6.0 - Quick Check Web Research (6. Oktober 2025)
**Features:**
- ✅ Web search integration i quick check
- ✅ Præcedens og afgørelser søgning
- ✅ LLM-generated summaries med citations
- ✅ Authority scoring for sources

### v0.5.0 - Initial React Frontend (5. Oktober 2025)
**Features:**
- ✅ React + Vite frontend setup
- ✅ NPM workspace monorepo struktur
- ✅ React Router navigation
- ✅ Styled Components design system
- ✅ Core pages (Home, Quick Check, Dashboard, Knowledge Base)

### v0.4.0 - Backend API Foundation (4. Oktober 2025)
**Features:**
- ✅ FastAPI backend struktur
- ✅ Quick check endpoint
- ✅ Full assessment endpoint
- ✅ AI cases management med SMTP
- ✅ Knowledge base API

### v0.3.0 - Compliance Logic (3. Oktober 2025)
**Features:**
- ✅ AI Act risk assessment
- ✅ GDPR compliance checker
- ✅ DPIA requirements detection
- ✅ Sector-specific rules

### v0.2.0 - LangGraph Agents (2. Oktober 2025)
**Features:**
- ✅ Quick check agent implementation
- ✅ Multi-agent architecture
- ✅ LLM integration (OpenAI + Anthropic)

### v0.1.0 - Project Kickoff (1. Oktober 2025)
**Features:**
- ✅ Initial project structure
- ✅ Core models og data schemas
- ✅ Basic compliance framework

## 🔮 Roadmap

**Q4 2025:**
- 🔄 PostgreSQL database integration
- 🔄 Qdrant vector database for semantic search
- 🔄 Advanced dashboard analytics
- 🔄 PDF export af compliance rapporter
- 🔄 Multi-language support (DA, EN)

**Q1 2026:**
- 🔄 AI case workflow automation
- 🔄 Integration med Kalundborg Kommune systemer
- 🔄 Advanced compliance monitoring
- 🔄 Automated alert system

## ⚠️ Disclaimer

Dette værktøj er designet som hjælp til compliance vurdering, men erstatter ikke juridisk rådgivning. Konsulter altid juridiske eksperter for kritiske beslutninger.

---

**Current Version:** v0.8.0 - Kalundborg Branding
**Sidst opdateret:** 8. Oktober 2025
**Udviklet af:** Kalundborg Kommune - Digitalisering og IT
