# The Judge - AI Compliance Platform

En omfattende løsning til AI compliance checking baseret på EU AI Act, GDPR og dansk lovgivning.

## 🚀 Features

### Kernefunktionalitet
- **7-Punkts AI-Vurdering** - Struktureret, trinvis compliance vurdering (NYT!)
- **AI Act Compliance Checker** - Automatisk risikovurdering og kravidentifikation
- **GDPR Analysis** - Specialiseret GDPR analyse for AI systemer
- **Dansk lovgivning** - Integration med danske regler og Datatilsynets vejledninger
- **Multi-agent arkitektur** - LangGraph-baserede agenter for intelligent analyse
- **Automatisk dokumentation** - Generering af compliance rapporter
- **DPIA & FRIA Integration** - Automatisk vurdering af impact assessments

### Tekniske Kapabiliteter
- Risk assessment (Unacceptable, High, Limited, Minimal)
- Automated decision-making analysis
- Data Protection Impact Assessment (DPIA) vurdering
- Sector-specific compliance checking
- Real-time legal research
- Gap analysis og mitigation strategies

## 📋 Installation

### Forudsætninger
- Python 3.11+
- Docker og Docker Compose (valgfrit)
- OpenAI API nøgle eller Anthropic API nøgle

### Lokal Installation

1. **Klon repository:**
```bash
cd ai-compliance-platform
```

2. **Opret virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # På Windows: venv\Scripts\activate
```

3. **Installer dependencies:**
```bash
pip install -r requirements.txt
```

4. **Konfigurer environment:**
```bash
cp .env.example .env
# Rediger .env filen med dine API nøgler
```

5. **Start backend:**
```bash
python main.py
```

6. **Start frontend (i ny terminal):**
```bash
streamlit run streamlit_app.py
```

### Docker Installation

1. **Byg og start med Docker Compose:**
```bash
docker-compose up --build
```

Dette starter:
- FastAPI backend på http://localhost:8000
- Streamlit frontend på http://localhost:8501
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
ai-compliance-platform/
├── src/
│   ├── core/              # Core models og utilities
│   │   └── models.py       # Pydantic data models
│   ├── compliance/         # Compliance checkers
│   │   ├── ai_act_checker.py
│   │   └── gdpr_checker.py
│   └── agents/            # LangGraph agents
│       └── compliance_orchestrator.py
├── main.py                # FastAPI backend
├── streamlit_app.py       # Streamlit frontend
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker configuration
└── README.md
```

### Tech Stack
- **Backend:** FastAPI, LangGraph, LangChain
- **Frontend:** Streamlit
- **AI/LLM:** OpenAI GPT-4, Anthropic Claude
- **Database:** PostgreSQL, Qdrant (vector DB)
- **Deployment:** Docker, Kubernetes-ready

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

Vi modtager gerne bidrag! Se CONTRIBUTING.md for guidelines.

## 📄 Licens

MIT License - se LICENSE fil for detaljer.

## 🆘 Support

- **Documentation:** http://localhost:8501 (Knowledge Base)
- **API Docs:** http://localhost:8000/docs
- **Issues:** GitHub Issues

## 🔄 Opdateringer

Systemet opdateres løbende med:
- Nye lovgivningsmæssige ændringer
- Opdaterede compliance guidelines
- Forbedrede AI modeller
- Udvidede sektor-specifikke regler

## ⚠️ Disclaimer

Dette værktøj er designet som hjælp til compliance vurdering, men erstatter ikke juridisk rådgivning. Konsulter altid juridiske eksperter for kritiske beslutninger.

---

**Version:** 0.1.0
**Sidst opdateret:** September 2025
**Udviklet af:** AI Compliance Team