import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaBook,
  FaSearch,
  FaFilter,
  FaGavel,
  FaRobot,
  FaGraduationCap,
  FaBuilding,
  FaExternalLinkAlt,
  FaChevronRight,
  FaInfoCircle,
  FaTags,
  FaLanguage,
  FaBalanceScale,
  FaShieldAlt,
  FaCogs,
  FaDatabase,
  FaBrain,
  FaEye,
  FaLock,
  FaPlus,
  FaTimes,
  FaSave
} from 'react-icons/fa';

const initialKnowledgeItems = [
  // Juridiske Termer
  {
    id: 1,
    term: 'Risikoklassificering',
    category: 'legal',
    icon: FaGavel,
    definition: 'Systematisk proces til at kategorisere AI-systemer baseret på deres potentielle risiko for grundlæggende rettigheder, sikkerhed og samfund.',
    context: 'Under EU AI Act klassificeres AI-systemer i fire risikokategorier: Uacceptabel risiko (forbudt), Høj risiko (strenge krav), Begrænset risiko (gennemsigtighedskrav), og Minimal/ingen risiko (ingen specifikke regler).',
    tags: ['AI Act', 'EU Lov', 'Risikovurdering'],
    references: [
      { text: 'AI Act Art. 6-7', url: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj' }
    ]
  },
  {
    id: 2,
    term: 'Konformitetsvurdering',
    category: 'compliance',
    icon: FaShieldAlt,
    definition: 'Formel proces hvor organisationer dokumenterer og beviser, at deres AI-systemer overholder gældende lovkrav og standarder.',
    context: 'For høj-risiko AI-systemer kræver AI Act en omfattende konformitetsvurdering inklusive CE-mærkning før markedsføring. Processen omfatter risikovurdering, kvalitetsledelse, dokumentation og overvågning.',
    tags: ['CE-mærkning', 'Dokumentation', 'Kvalitetsledelse'],
    references: [
      { text: 'AI Act Art. 43', url: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj' }
    ]
  },
  {
    id: 3,
    term: 'Markedsovervågning',
    category: 'legal',
    icon: FaEye,
    definition: 'Myndighedernes kontrol og overvågning af AI-systemer på markedet for at sikre overholdelse af lovkrav efter markedsføring.',
    context: 'Danske myndigheder har pligt til at overvåge AI-systemer og kan kræve dokumentation, forbyde produkter eller pålægge bøder ved manglende compliance. Inkluderer både reactive og proaktive kontroltiltag.',
    tags: ['Myndigheder', 'Kontrol', 'Sanktioner'],
    references: [
      { text: 'AI Act Art. 74-77', url: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj' }
    ]
  },
  {
    id: 4,
    term: 'Databeskyttelse ved Design',
    category: 'legal',
    icon: FaLock,
    definition: 'Princip hvor databeskyttelse integreres direkte i AI-systemets design og arkitektur fra begyndelsen, ikke som et efterfølgende tilføjelse.',
    context: 'GDPR artikel 25 kræver "privacy by design" for alle systemer der behandler personoplysninger. For AI-systemer betyder det algoritmegennemsigtighed, dataministimering og indbyggede sikkerhedsforanstaltninger.',
    tags: ['GDPR', 'Privacy', 'Design'],
    references: [
      { text: 'GDPR Art. 25', url: 'https://eur-lex.europa.eu/eli/reg/2016/679/oj' }
    ]
  },
  {
    id: 5,
    term: 'Behandlingsgrundlag',
    category: 'legal',
    icon: FaBalanceScale,
    definition: 'Juridisk hjemmel der giver tilladelse til at behandle personoplysninger i AI-systemer under GDPR.',
    context: 'AI-systemer skal have lovligt grundlag for databehandling: samtykke, kontrakt, legal forpligtelse, vitale interesser, offentlig opgave eller legitime interesser. Behandlingsgrundlaget skal være fastlagt før dataindsamling.',
    tags: ['GDPR', 'Personoplysninger', 'Juridisk grundlag'],
    references: [
      { text: 'GDPR Art. 6', url: 'https://eur-lex.europa.eu/eli/reg/2016/679/oj' }
    ]
  },

  // AI Teknologi Termer
  {
    id: 6,
    term: 'MCP (Model Context Protocol)',
    category: 'ai',
    icon: FaRobot,
    definition: 'Standardprotokol for hvordan AI-agenter kommunikerer og deler kontekst med hinanden og eksterne systemer.',
    context: 'MCP muliggør interoperabilitet mellem forskellige AI-systemer og værktøjer. Protokollen definerer hvordan agenter kan tilgå data, udføre handlinger og dele information på en sikker og struktureret måde.',
    tags: ['Agent-kommunikation', 'Interoperabilitet', 'Protokol'],
    references: [
      { text: 'Anthropic MCP', url: 'https://www.anthropic.com/news/model-context-protocol' }
    ]
  },
  {
    id: 7,
    term: 'RAG (Retrieval Augmented Generation)',
    category: 'ai',
    icon: FaDatabase,
    definition: 'AI-teknik der kombinerer informationssøgning med tekstgenerering for at skabe mere præcise og faktuelle svar.',
    context: 'RAG-systemer søger først relevant information fra en vidensbase og bruger derefter denne information til at generere kontekstuelle svar. Teknikken reducerer hallucination og gør AI-systemer mere pålidelige til faktuelle opgaver.',
    tags: ['Informationssøgning', 'Tekstgenerering', 'Vidensbase'],
    references: [
      { text: 'RAG Research', url: 'https://arxiv.org/abs/2005.11401' }
    ]
  },
  {
    id: 8,
    term: 'LLM (Large Language Model)',
    category: 'ai',
    icon: FaBrain,
    definition: 'Store sprogmodeller trænet på omfattende tekstdata for at forstå og generere naturligt sprog.',
    context: 'LLM\'er som GPT, Claude og Llama er fundamentet for mange AI-applikationer. Under AI Act klassificeres foundation models med høj computational power som GPAI-modeller med særlige forpligtelser.',
    tags: ['Foundation Models', 'Sprogforståelse', 'GPAI'],
    references: [
      { text: 'AI Act Art. 51', url: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj' }
    ]
  },
  {
    id: 9,
    term: 'Indexering og Vektorer',
    category: 'technical',
    icon: FaCogs,
    definition: 'Proces hvor tekstuelle data konverteres til numeriske repræsentationer (vektorer) som kan søges og analyseres effektivt af AI-systemer.',
    context: 'Vektorindexering muliggør semantisk søgning hvor AI kan finde konceptuelt relateret information selv uden eksakte ordmatch. Teknologien er central for RAG-systemer og intelligent dokumentsøgning.',
    tags: ['Semantisk søgning', 'Embeddings', 'Datastruktur'],
    references: [
      { text: 'Vector DB Guide', url: 'https://www.pinecone.io/learn/vector-database/' }
    ]
  },
  {
    id: 10,
    term: 'Fine-tuning',
    category: 'technical',
    icon: FaGraduationCap,
    definition: 'Proces hvor en eksisterende AI-model tilpasses til specifikke opgaver eller domæner gennem yderligere træning på målrettede data.',
    context: 'Fine-tuning gør det muligt at specialisere generelle AI-modeller til specifikke use cases som juridisk analyse eller medicinsk diagnostik. Metoden reducerer træningsomkostninger og forbedrer performance på målrettede opgaver.',
    tags: ['Model-træning', 'Specialisering', 'Transfer Learning'],
    references: [
      { text: 'Fine-tuning Guide', url: 'https://huggingface.co/docs/transformers/training' }
    ]
  },
  {
    id: 11,
    term: 'Embeddings',
    category: 'technical',
    icon: FaDatabase,
    definition: 'Numeriske repræsentationer af ord, sætninger eller dokumenter der bevarer semantisk betydning i et højdimensionalt vektorrum.',
    context: 'Embeddings er fundamentale for moderne AI-systemer og muliggør semantisk analyse og sammenligning. De bruges til alt fra søgning og anbefaling til tekstklassificering og oversættelse.',
    tags: ['Semantisk analyse', 'Vektorrepræsentation', 'NLP'],
    references: [
      { text: 'Word2Vec Paper', url: 'https://arxiv.org/abs/1301.3781' }
    ]
  },
  {
    id: 12,
    term: 'Transformers',
    category: 'technical',
    icon: FaBrain,
    definition: 'Neural netværksarkitektur baseret på attention-mekanismer der revolutionerede sprogmodeller og AI-performance.',
    context: 'Transformer-arkitekturen er grundlaget for alle moderne LLM\'er. Teknologien muliggør parallel træning og kan håndtere lange sekvenser effektivt, hvilket har gjort store sprogmodeller mulige.',
    tags: ['Neural Networks', 'Attention', 'Arkitektur'],
    references: [
      { text: 'Attention Paper', url: 'https://arxiv.org/abs/1706.03762' }
    ]
  },

  // Compliance Termer
  {
    id: 13,
    term: 'GPAI (General Purpose AI)',
    category: 'compliance',
    icon: FaRobot,
    definition: 'AI-modeller designet til at udføre en bred vifte af opgaver på tværs af forskellige domæner og anvendelser.',
    context: 'Under AI Act har GPAI-modeller særlige forpligtelser inklusive risikovurdering, dokumentation og samarbejde med myndighederne. Modeller med systemisk risiko har yderligere krav.',
    tags: ['Foundation Models', 'Systemisk risiko', 'AI Act'],
    references: [
      { text: 'AI Act Art. 51-56', url: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj' }
    ]
  },
  {
    id: 14,
    term: 'Algoritmisk Gennemsigtighed',
    category: 'compliance',
    icon: FaEye,
    definition: 'Krav om at AI-systemer skal være forståelige og kunne forklare deres beslutningsprocesser for brugere og myndigheder.',
    context: 'AI Act og GDPR kræver gennemsigtighed i automatiserede beslutninger. Dette inkluderer ret til forklaring, dokumentation af algorithmic logic og mulighed for menneskelig intervention.',
    tags: ['Transparens', 'Forklarbarhed', 'Brugerrettigheder'],
    references: [
      { text: 'GDPR Art. 22', url: 'https://eur-lex.europa.eu/eli/reg/2016/679/oj' },
      { text: 'AI Act Art. 13', url: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj' }
    ]
  },
  {
    id: 15,
    term: 'Systemic Risk Models',
    category: 'compliance',
    icon: FaShieldAlt,
    definition: 'GPAI-modeller med så høj computational power at de kan påvirke EU\'s indre marked eller udgøre systemiske risici.',
    context: 'Modeller trænet med compute over 10^25 FLOPs anses som systemiske risiko-modeller med skærpede krav til evaluation, red teaming, cybersecurity og rapportering til AI Office.',
    tags: ['Systemisk risiko', 'Computational power', 'Red teaming'],
    references: [
      { text: 'AI Act Art. 55', url: 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj' }
    ]
  }
];

const KnowledgeContainer = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
`;

const PageHeader = styled.div`
  margin-bottom: 2rem;

  h1 {
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  p {
    color: ${props => props.theme.colors.gray[600]};
    font-size: 1.1rem;
  }
`;

const SearchAndFilter = styled.div`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: ${props => props.theme.shadows.glass};
  margin-bottom: 2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
`;

const SearchBox = styled.div`
  position: relative;
  flex: 1;
  min-width: 300px;

  input {
    width: 100%;
    padding: 0.75rem 2.5rem 0.75rem 1rem;
    border: 2px solid ${props => props.theme.colors.gray[300]};
    border-radius: ${props => props.theme.borderRadius};
    font-size: 0.875rem;
    background: white;

    &:focus {
      border-color: ${props => props.theme.colors.primary};
      outline: none;
    }
  }

  .search-icon {
    position: absolute;
    right: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: ${props => props.theme.colors.gray[400]};
  }
`;

const CategoryFilters = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
`;

const CategoryButton = styled.button`
  padding: 0.5rem 1rem;
  background: ${props => props.active ? props.theme.colors.primary : props.theme.colors.gray[100]};
  color: ${props => props.active ? 'white' : props.theme.colors.gray[700]};
  border: none;
  border-radius: 20px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.25rem;

  &:hover {
    background: ${props => props.active ? props.theme.colors.primary : props.theme.colors.gray[200]};
  }
`;

const KnowledgeGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
`;

const TermCard = styled(motion.div)`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: ${props => props.theme.shadows.glass};
  border-left: 4px solid ${props => {
    switch(props.category) {
      case 'legal': return props.theme.colors.juridical.navy;
      case 'ai': return props.theme.colors.juridical.gold;
      case 'technical': return props.theme.colors.success;
      case 'compliance': return props.theme.colors.warning;
      default: return props.theme.colors.gray[300];
    }
  }};
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: ${props => props.theme.shadows.xl};
  }
`;

const TermHeader = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;

  .icon {
    background: ${props => {
      switch(props.category) {
        case 'legal': return props.theme.colors.juridical.navy;
        case 'ai': return props.theme.colors.juridical.gold;
        case 'technical': return props.theme.colors.success;
        case 'compliance': return props.theme.colors.warning;
        default: return props.theme.colors.gray[400];
      }
    }};
    color: white;
    width: 40px;
    height: 40px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    flex-shrink: 0;
  }

  .content {
    flex: 1;

    h3 {
      color: ${props => props.theme.colors.gray[800]};
      margin-bottom: 0.25rem;
      font-size: 1.1rem;
      line-height: 1.3;
    }

    .meta {
      color: ${props => props.theme.colors.gray[500]};
      font-size: 0.875rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
  }
`;

const TermDefinition = styled.div`
  color: ${props => props.theme.colors.gray[700]};
  line-height: 1.6;
  margin-bottom: 1rem;
  font-size: 0.9rem;
`;

const TermContext = styled.div`
  background: ${props => props.theme.colors.gray[50]};
  border-radius: ${props => props.theme.borderRadius};
  padding: 0.75rem;
  margin-bottom: 1rem;
  border-left: 3px solid ${props => props.theme.colors.juridical.lightGold};

  .label {
    font-weight: 600;
    color: ${props => props.theme.colors.gray[700]};
    font-size: 0.8rem;
    margin-bottom: 0.25rem;
  }

  .content {
    color: ${props => props.theme.colors.gray[600]};
    font-size: 0.85rem;
    line-height: 1.5;
  }
`;

const TermFooter = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;

  .tags {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
  }

  .tag {
    padding: 0.2rem 0.5rem;
    background: ${props => props.theme.colors.gray[100]};
    color: ${props => props.theme.colors.gray[600]};
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 500;
  }

  .references {
    display: flex;
    gap: 0.5rem;
  }

  .reference-link {
    color: ${props => props.theme.colors.primary};
    text-decoration: none;
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.2rem;

    &:hover {
      color: ${props => props.theme.colors.juridical.lightNavy};
    }
  }
`;

const StatsBar = styled.div`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 1rem 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: ${props => props.theme.shadows.glass};
  margin-bottom: 2rem;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;

  .stat {
    text-align: center;

    .number {
      font-size: 1.5rem;
      font-weight: 700;
      color: ${props => props.theme.colors.primary};
    }

    .label {
      font-size: 0.8rem;
      color: ${props => props.theme.colors.gray[600]};
      margin-top: 0.2rem;
    }
  }
`;

const AddButton = styled.button`
  background: ${props => props.theme.colors.juridical.gold};
  color: white;
  border: none;
  border-radius: 20px;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 600;

  &:hover {
    background: ${props => props.theme.colors.juridical.lightGold};
    transform: translateY(-1px);
  }
`;

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const ModalContent = styled(motion.div)`
  background: white;
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 2rem;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: ${props => props.theme.shadows.xl};
`;

const ModalHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;

  h2 {
    color: ${props => props.theme.colors.gray[800]};
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  color: ${props => props.theme.colors.gray[500]};
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 50%;
  transition: all 0.2s ease;

  &:hover {
    background: ${props => props.theme.colors.gray[100]};
    color: ${props => props.theme.colors.gray[700]};
  }
`;

const FormGroup = styled.div`
  margin-bottom: 1.5rem;

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: ${props => props.theme.colors.gray[700]};
  }

  input, textarea, select {
    width: 100%;
    padding: 0.75rem;
    border: 2px solid ${props => props.theme.colors.gray[300]};
    border-radius: ${props => props.theme.borderRadius};
    font-size: 0.875rem;
    background: white;

    &:focus {
      border-color: ${props => props.theme.colors.primary};
      outline: none;
    }
  }

  textarea {
    resize: vertical;
    min-height: 100px;
  }
`;

const ReferenceSection = styled.div`
  border: 1px solid ${props => props.theme.colors.gray[200]};
  border-radius: ${props => props.theme.borderRadius};
  padding: 1rem;
  margin-bottom: 1rem;

  .reference-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;

    h4 {
      margin: 0;
      color: ${props => props.theme.colors.gray[700]};
    }
  }

  .reference-item {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;

    input {
      flex: 1;
    }

    button {
      background: ${props => props.theme.colors.danger};
      color: white;
      border: none;
      border-radius: 4px;
      padding: 0.75rem;
      cursor: pointer;
      transition: all 0.2s ease;

      &:hover {
        background: ${props => props.theme.colors.dangerDark || '#c53030'};
      }
    }
  }
`;

const AddReferenceButton = styled.button`
  background: ${props => props.theme.colors.gray[100]};
  color: ${props => props.theme.colors.gray[700]};
  border: 1px dashed ${props => props.theme.colors.gray[300]};
  border-radius: ${props => props.theme.borderRadius};
  padding: 0.75rem;
  width: 100%;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;

  &:hover {
    background: ${props => props.theme.colors.gray[200]};
    border-color: ${props => props.theme.colors.gray[400]};
  }
`;

const ModalActions = styled.div`
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;

  button {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: ${props => props.theme.borderRadius};
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 0.5rem;

    &.cancel {
      background: ${props => props.theme.colors.gray[100]};
      color: ${props => props.theme.colors.gray[700]};

      &:hover {
        background: ${props => props.theme.colors.gray[200]};
      }
    }

    &.save {
      background: ${props => props.theme.colors.primary};
      color: white;

      &:hover {
        background: ${props => props.theme.colors.primaryDark || '#1a365d'};
      }
    }
  }
`;

const KnowledgeBasePage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [knowledgeItems, setKnowledgeItems] = useState(initialKnowledgeItems);

  const categories = [
    { id: 'all', label: 'Alle', icon: FaBook },
    { id: 'legal', label: 'Juridiske Termer', icon: FaGavel },
    { id: 'ai', label: 'AI Teknologi', icon: FaRobot },
    { id: 'technical', label: 'Tekniske Begreber', icon: FaCogs },
    { id: 'compliance', label: 'Compliance', icon: FaBalanceScale }
  ];


  const handleAddTerm = (newTerm) => {
    const newId = Math.max(...knowledgeItems.map(item => item.id)) + 1;
    const termWithId = {
      ...newTerm,
      id: newId,
      references: newTerm.references.filter(ref => ref.text && ref.url)
    };
    setKnowledgeItems([...knowledgeItems, termWithId]);
    setShowAddModal(false);
  };

  const filteredItems = useMemo(() => {
    return knowledgeItems.filter(item => {
      const matchesSearch = item.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           item.definition.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           item.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchesCategory = activeCategory === 'all' || item.category === activeCategory;

      return matchesSearch && matchesCategory;
    });
  }, [searchTerm, activeCategory]);

  const stats = useMemo(() => {
    const total = knowledgeItems.length;
    const legal = knowledgeItems.filter(item => item.category === 'legal').length;
    const ai = knowledgeItems.filter(item => item.category === 'ai').length;
    const technical = knowledgeItems.filter(item => item.category === 'technical').length;
    const compliance = knowledgeItems.filter(item => item.category === 'compliance').length;

    return { total, legal, ai, technical, compliance };
  }, []);

  const getCategoryIcon = (categoryId) => {
    const category = categories.find(cat => cat.id === categoryId);
    return category ? category.icon : FaBook;
  };

  return (
    <KnowledgeContainer>
      <PageHeader>
        <h1><FaBook /> Videnbase</h1>
        <p>Omfattende guide til juridiske termer, AI teknologi og compliance begreber</p>
      </PageHeader>

      <StatsBar>
        <div className="stat">
          <div className="number">{stats.total}</div>
          <div className="label">Samlede Termer</div>
        </div>
        <div className="stat">
          <div className="number">{stats.legal}</div>
          <div className="label">Juridiske Termer</div>
        </div>
        <div className="stat">
          <div className="number">{stats.ai}</div>
          <div className="label">AI Teknologi</div>
        </div>
        <div className="stat">
          <div className="number">{stats.technical}</div>
          <div className="label">Tekniske Begreber</div>
        </div>
        <div className="stat">
          <div className="number">{stats.compliance}</div>
          <div className="label">Compliance</div>
        </div>
      </StatsBar>

      <SearchAndFilter>
        <SearchBox>
          <input
            type="text"
            placeholder="Søg efter termer, definitioner eller tags..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <FaSearch className="search-icon" />
        </SearchBox>

        <CategoryFilters>
          {categories.map(category => (
            <CategoryButton
              key={category.id}
              active={activeCategory === category.id}
              onClick={() => setActiveCategory(category.id)}
            >
              <category.icon />
              {category.label}
            </CategoryButton>
          ))}
        </CategoryFilters>

        <AddButton onClick={() => setShowAddModal(true)}>
          <FaPlus />
          Tilføj nyt term
        </AddButton>
      </SearchAndFilter>

      <KnowledgeGrid>
        {filteredItems.map((item) => {
          const IconComponent = item.icon;
          return (
            <TermCard
              key={item.id}
              category={item.category}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <TermHeader category={item.category}>
                <div className="icon">
                  <IconComponent />
                </div>
                <div className="content">
                  <h3>{item.term}</h3>
                  <div className="meta">
                    <FaTags />
                    <span>{categories.find(cat => cat.id === item.category)?.label}</span>
                  </div>
                </div>
              </TermHeader>

              <TermDefinition>
                {item.definition}
              </TermDefinition>

              <TermContext>
                <div className="label">Kontekst og anvendelse</div>
                <div className="content">{item.context}</div>
              </TermContext>

              <TermFooter>
                <div className="tags">
                  {item.tags.map((tag, index) => (
                    <span key={index} className="tag">{tag}</span>
                  ))}
                </div>
                <div className="references">
                  {item.references.map((ref, index) => (
                    <a
                      key={index}
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="reference-link"
                    >
                      {ref.text}
                      <FaExternalLinkAlt />
                    </a>
                  ))}
                </div>
              </TermFooter>
            </TermCard>
          );
        })}
      </KnowledgeGrid>

      {filteredItems.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          background: 'rgba(255, 255, 255, 0.95)',
          borderRadius: '16px',
          boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)'
        }}>
          <FaSearch style={{ fontSize: '3rem', color: '#a0aec0', marginBottom: '1rem' }} />
          <h3 style={{ color: '#4a5568', marginBottom: '0.5rem' }}>Ingen termer fundet</h3>
          <p style={{ color: '#718096' }}>Prøv at justere dine søgekriterier eller vælg en anden kategori.</p>
        </div>
      )}

      <AnimatePresence>
        {showAddModal && (
          <AddTermModal
            onClose={() => setShowAddModal(false)}
            onSave={handleAddTerm}
            categories={categories}
          />
        )}
      </AnimatePresence>
    </KnowledgeContainer>
  );
};

const AddTermModal = ({ onClose, onSave, categories }) => {
  const [formData, setFormData] = useState({
    term: '',
    category: 'legal',
    definition: '',
    context: '',
    tags: '',
    references: [{ text: '', url: '' }]
  });

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleReferenceChange = (index, field, value) => {
    const newReferences = [...formData.references];
    newReferences[index][field] = value;
    setFormData(prev => ({ ...prev, references: newReferences }));
  };

  const addReference = () => {
    setFormData(prev => ({
      ...prev,
      references: [...prev.references, { text: '', url: '' }]
    }));
  };

  const removeReference = (index) => {
    if (formData.references.length > 1) {
      const newReferences = formData.references.filter((_, i) => i !== index);
      setFormData(prev => ({ ...prev, references: newReferences }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.term && formData.definition) {
      const categoryIcon = categories.find(cat => cat.id === formData.category)?.icon || FaBook;
      const newTerm = {
        ...formData,
        icon: categoryIcon,
        tags: formData.tags.split(',').map(tag => tag.trim()).filter(tag => tag)
      };
      onSave(newTerm);
    }
  };

  return (
    <ModalOverlay onClick={onClose}>
      <ModalContent
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2 }}
      >
        <ModalHeader>
          <h2>
            <FaPlus />
            Tilføj nyt term
          </h2>
          <CloseButton onClick={onClose}>
            <FaTimes />
          </CloseButton>
        </ModalHeader>

        <form onSubmit={handleSubmit}>
          <FormGroup>
            <label>Term *</label>
            <input
              type="text"
              value={formData.term}
              onChange={(e) => handleInputChange('term', e.target.value)}
              placeholder="Fx: Risikoklassificering"
              required
            />
          </FormGroup>

          <FormGroup>
            <label>Kategori *</label>
            <select
              value={formData.category}
              onChange={(e) => handleInputChange('category', e.target.value)}
              required
            >
              {categories.filter(cat => cat.id !== 'all').map(category => (
                <option key={category.id} value={category.id}>
                  {category.label}
                </option>
              ))}
            </select>
          </FormGroup>

          <FormGroup>
            <label>Definition *</label>
            <textarea
              value={formData.definition}
              onChange={(e) => handleInputChange('definition', e.target.value)}
              placeholder="Kort og præcis definition af termen..."
              required
            />
          </FormGroup>

          <FormGroup>
            <label>Kontekst og anvendelse</label>
            <textarea
              value={formData.context}
              onChange={(e) => handleInputChange('context', e.target.value)}
              placeholder="Hvor og hvordan bruges dette term i praksis..."
            />
          </FormGroup>

          <FormGroup>
            <label>Tags (komma-separeret)</label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => handleInputChange('tags', e.target.value)}
              placeholder="AI Act, EU Lov, Risikovurdering"
            />
          </FormGroup>

          <ReferenceSection>
            <div className="reference-header">
              <h4>Referencer</h4>
            </div>
            {formData.references.map((ref, index) => (
              <div key={index} className="reference-item">
                <input
                  type="text"
                  placeholder="Reference tekst"
                  value={ref.text}
                  onChange={(e) => handleReferenceChange(index, 'text', e.target.value)}
                />
                <input
                  type="url"
                  placeholder="URL"
                  value={ref.url}
                  onChange={(e) => handleReferenceChange(index, 'url', e.target.value)}
                />
                {formData.references.length > 1 && (
                  <button type="button" onClick={() => removeReference(index)}>
                    <FaTimes />
                  </button>
                )}
              </div>
            ))}
            <AddReferenceButton type="button" onClick={addReference}>
              <FaPlus />
              Tilføj reference
            </AddReferenceButton>
          </ReferenceSection>

          <ModalActions>
            <button type="button" className="cancel" onClick={onClose}>
              <FaTimes />
              Annuller
            </button>
            <button type="submit" className="save">
              <FaSave />
              Gem term
            </button>
          </ModalActions>
        </form>
      </ModalContent>
    </ModalOverlay>
  );
};

export default KnowledgeBasePage;