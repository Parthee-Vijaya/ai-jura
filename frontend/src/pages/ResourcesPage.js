import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaExternalLinkAlt,
  FaUniversity,
  FaGavel,
  FaEuroSign,
  FaSearch,
  FaFilter,
  FaShieldAlt,
  FaBalanceScale,
  FaDatabase,
  FaGlobeEurope,
  FaFileAlt,
  FaInfoCircle,
  FaPlus,
  FaTimes,
  FaSave
} from 'react-icons/fa';

const ResourcesContainer = styled.div`
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

const ResourceGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
`;

const ResourceCard = styled(motion.div)`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: ${props => props.theme.shadows.glass};
  border-left: 4px solid ${props => {
    switch(props.category) {
      case 'eu': return props.theme.colors.juridical.gold;
      case 'danish': return props.theme.colors.juridical.navy;
      case 'legal': return props.theme.colors.success;
      case 'international': return props.theme.colors.warning;
      default: return props.theme.colors.gray[300];
    }
  }};
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: ${props => props.theme.shadows.xl};
  }
`;

const ResourceHeader = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;

  .icon {
    background: ${props => {
      switch(props.category) {
        case 'eu': return props.theme.colors.juridical.gold;
        case 'danish': return props.theme.colors.juridical.navy;
        case 'legal': return props.theme.colors.success;
        case 'international': return props.theme.colors.warning;
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

const ResourceDescription = styled.div`
  color: ${props => props.theme.colors.gray[700]};
  line-height: 1.6;
  margin-bottom: 1rem;
  font-size: 0.9rem;
`;

const ResourceLinks = styled.div`
  margin-bottom: 1rem;
`;

const ResourceLink = styled.a`
  display: block;
  color: ${props => props.theme.colors.primary};
  text-decoration: none;
  font-size: 0.875rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid ${props => props.theme.colors.gray[100]};
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;

  &:hover {
    color: ${props => props.theme.colors.juridical.lightNavy};
    background: ${props => props.theme.colors.gray[50]};
    padding-left: 0.5rem;
    border-radius: 4px;
  }

  &:last-child {
    border-bottom: none;
  }

  .external-icon {
    font-size: 0.75rem;
    opacity: 0.7;
  }
`;

const ResourceFooter = styled.div`
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

  .info {
    color: ${props => props.theme.colors.gray[500]};
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.2rem;
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

const LinksSection = styled.div`
  border: 1px solid ${props => props.theme.colors.gray[200]};
  border-radius: ${props => props.theme.borderRadius};
  padding: 1rem;
  margin-bottom: 1rem;

  .links-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;

    h4 {
      margin: 0;
      color: ${props => props.theme.colors.gray[700]};
    }
  }

  .link-item {
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

const AddLinkButton = styled.button`
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

const initialResources = [
    {
      id: 1,
      title: 'EU Databeskyttelse og AI Regulering',
      category: 'eu',
      icon: FaEuroSign,
      description: 'Omfattende samling af EU lovgivning vedrørende databeskyttelse, kunstig intelligens og digitale tjenester. Inkluderer GDPR, AI Act og Digital Services Act.',
      tags: ['GDPR', 'AI Act', 'Digital Services Act', 'Databeskyttelse'],
      links: [
        { title: 'GDPR - Databeskyttelsesforordningen', url: 'https://gdpr.eu/' },
        { title: 'AI Act - Kunstig Intelligens Forordningen', url: 'https://artificialintelligenceact.eu/' },
        { title: 'Digital Services Act', url: 'https://digital-strategy.ec.europa.eu/en/policies/digital-services-act-package' },
        { title: 'Digital Markets Act', url: 'https://digital-strategy.ec.europa.eu/en/policies/digital-markets-act' }
      ],
      lastUpdated: '2025-01-15'
    },
    {
      id: 2,
      title: 'Danske Tilsynsmyndigheder',
      category: 'danish',
      icon: FaUniversity,
      description: 'Officielle danske myndigheder og tilsynsorganer der regulerer digitalisering, databeskyttelse og compliance i den offentlige sektor.',
      tags: ['Datatilsynet', 'Digst', 'Offentlig sektor', 'Tilsyn'],
      links: [
        { title: 'Datatilsynet', url: 'https://www.datatilsynet.dk/' },
        { title: 'Digitaliseringsstyrelsen', url: 'https://digst.dk/' },
        { title: 'Erhvervsstyrelsen', url: 'https://erhvervsstyrelsen.dk/' },
        { title: 'Ankestyrelsen', url: 'https://www.ast.dk/' }
      ],
      lastUpdated: '2025-01-10'
    },
    {
      id: 3,
      title: 'Juridiske Database og Forskning',
      category: 'legal',
      icon: FaGavel,
      description: 'Professionelle juridiske databaser og forskningsressourcer til compliance analyse og juridisk rådgivning inden for teknologi og AI.',
      tags: ['Retsinformation', 'Karnov', 'Juridisk research', 'Lovgivning'],
      links: [
        { title: 'Retsinformation.dk', url: 'https://www.retsinformation.dk/' },
        { title: 'Karnov Group', url: 'https://www.karnovgroup.dk/' },
        { title: 'Advokatsamfundet', url: 'https://www.advokatsamfundet.dk/' },
        { title: 'Domstolsstyrelsen', url: 'https://www.domstol.dk/' }
      ],
      lastUpdated: '2025-01-08'
    },
    {
      id: 4,
      title: 'Internationale Standarder og Certificering',
      category: 'international',
      icon: FaBalanceScale,
      description: 'Internationale standarder og certificeringsorganer for informationssikkerhed, kvalitetsstyring og compliance indenfor AI og teknologi.',
      tags: ['ISO 27001', 'IEEE', 'Certificering', 'Standarder'],
      links: [
        { title: 'ISO - International Organization for Standardization', url: 'https://www.iso.org/' },
        { title: 'IEEE Standards Association', url: 'https://standards.ieee.org/' },
        { title: 'NIST AI Risk Management Framework', url: 'https://www.nist.gov/itl/ai-risk-management-framework' },
        { title: 'Partnership on AI', url: 'https://www.partnershiponai.org/' }
      ],
      lastUpdated: '2025-01-12'
    }
  ];

const ResourcesPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [resources, setResources] = useState(initialResources);

  const categories = [
    { id: 'all', name: 'Alle', icon: FaGlobeEurope },
    { id: 'eu', name: 'EU Regulering', icon: FaEuroSign },
    { id: 'danish', name: 'Danske Myndigheder', icon: FaUniversity },
    { id: 'legal', name: 'Juridiske Ressourcer', icon: FaGavel },
    { id: 'international', name: 'Internationale', icon: FaBalanceScale }
  ];

  const handleAddResource = (newResource) => {
    const newId = Math.max(...resources.map(resource => resource.id)) + 1;
    const resourceWithId = {
      ...newResource,
      id: newId,
      links: newResource.links.filter(link => link.title && link.url),
      lastUpdated: new Date().toISOString().split('T')[0]
    };
    setResources([...resources, resourceWithId]);
    setShowAddModal(false);
  };

  const filteredResources = useMemo(() => {
    return resources.filter(resource => {
      const matchesCategory = activeCategory === 'all' || resource.category === activeCategory;
      const matchesSearch = searchTerm === '' ||
        resource.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        resource.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        resource.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));

      return matchesCategory && matchesSearch;
    });
  }, [searchTerm, activeCategory]);

  const totalResources = resources.length;
  const totalLinks = resources.reduce((sum, resource) => sum + resource.links.length, 0);

  return (
    <ResourcesContainer>
      <PageHeader>
        <h1>
          <FaExternalLinkAlt />
          Relevante Links
        </h1>
        <p>Omfattende samling af juridiske og compliance ressourcer til AI-governance</p>
      </PageHeader>

      <StatsBar>
        <div className="stat">
          <div className="number">{totalResources}</div>
          <div className="label">Ressource kategorier</div>
        </div>
        <div className="stat">
          <div className="number">{totalLinks}</div>
          <div className="label">Eksterne links</div>
        </div>
        <div className="stat">
          <div className="number">{filteredResources.length}</div>
          <div className="label">Viste ressourcer</div>
        </div>
      </StatsBar>

      <SearchAndFilter>
        <SearchBox>
          <input
            type="text"
            placeholder="Søg i ressourcer, beskrivelser og tags..."
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
              {category.name}
            </CategoryButton>
          ))}
        </CategoryFilters>

        <AddButton onClick={() => setShowAddModal(true)}>
          <FaPlus />
          Tilføj ny ressource
        </AddButton>
      </SearchAndFilter>

      <ResourceGrid>
        {filteredResources.map((resource) => (
          <ResourceCard
            key={resource.id}
            category={resource.category}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <ResourceHeader category={resource.category}>
              <resource.icon className="icon" />
              <div className="content">
                <h3>{resource.title}</h3>
                <div className="meta">
                  <FaInfoCircle />
                  {resource.links.length} eksterne links
                </div>
              </div>
            </ResourceHeader>

            <ResourceDescription>
              {resource.description}
            </ResourceDescription>

            <ResourceLinks>
              {resource.links.map((link, index) => (
                <ResourceLink
                  key={index}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {link.title}
                  <FaExternalLinkAlt className="external-icon" />
                </ResourceLink>
              ))}
            </ResourceLinks>

            <ResourceFooter>
              <div className="tags">
                {resource.tags.map((tag, index) => (
                  <span key={index} className="tag">{tag}</span>
                ))}
              </div>
              <div className="info">
                <FaInfoCircle />
                Opdateret {resource.lastUpdated}
              </div>
            </ResourceFooter>
          </ResourceCard>
        ))}
      </ResourceGrid>

      <AnimatePresence>
        {showAddModal && (
          <AddResourceModal
            onClose={() => setShowAddModal(false)}
            onSave={handleAddResource}
            categories={categories}
          />
        )}
      </AnimatePresence>
    </ResourcesContainer>
  );
};

const AddResourceModal = ({ onClose, onSave, categories }) => {
  const [formData, setFormData] = useState({
    title: '',
    category: 'eu',
    description: '',
    tags: '',
    links: [{ title: '', url: '' }]
  });

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleLinkChange = (index, field, value) => {
    const newLinks = [...formData.links];
    newLinks[index][field] = value;
    setFormData(prev => ({ ...prev, links: newLinks }));
  };

  const addLink = () => {
    setFormData(prev => ({
      ...prev,
      links: [...prev.links, { title: '', url: '' }]
    }));
  };

  const removeLink = (index) => {
    if (formData.links.length > 1) {
      const newLinks = formData.links.filter((_, i) => i !== index);
      setFormData(prev => ({ ...prev, links: newLinks }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.title && formData.description) {
      const categoryIcon = categories.find(cat => cat.id === formData.category)?.icon || FaGlobeEurope;
      const newResource = {
        ...formData,
        icon: categoryIcon,
        tags: formData.tags.split(',').map(tag => tag.trim()).filter(tag => tag)
      };
      onSave(newResource);
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
            Tilføj ny ressource
          </h2>
          <CloseButton onClick={onClose}>
            <FaTimes />
          </CloseButton>
        </ModalHeader>

        <form onSubmit={handleSubmit}>
          <FormGroup>
            <label>Titel *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => handleInputChange('title', e.target.value)}
              placeholder="Fx: EU Databeskyttelse og AI Regulering"
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
                  {category.name}
                </option>
              ))}
            </select>
          </FormGroup>

          <FormGroup>
            <label>Beskrivelse *</label>
            <textarea
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Beskriv ressourcen og hvad den indeholder..."
              required
            />
          </FormGroup>

          <FormGroup>
            <label>Tags (komma-separeret)</label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => handleInputChange('tags', e.target.value)}
              placeholder="GDPR, AI Act, Databeskyttelse"
            />
          </FormGroup>

          <LinksSection>
            <div className="links-header">
              <h4>Links</h4>
            </div>
            {formData.links.map((link, index) => (
              <div key={index} className="link-item">
                <input
                  type="text"
                  placeholder="Link titel"
                  value={link.title}
                  onChange={(e) => handleLinkChange(index, 'title', e.target.value)}
                />
                <input
                  type="url"
                  placeholder="URL"
                  value={link.url}
                  onChange={(e) => handleLinkChange(index, 'url', e.target.value)}
                />
                {formData.links.length > 1 && (
                  <button type="button" onClick={() => removeLink(index)}>
                    <FaTimes />
                  </button>
                )}
              </div>
            ))}
            <AddLinkButton type="button" onClick={addLink}>
              <FaPlus />
              Tilføj link
            </AddLinkButton>
          </LinksSection>

          <ModalActions>
            <button type="button" className="cancel" onClick={onClose}>
              <FaTimes />
              Annuller
            </button>
            <button type="submit" className="save">
              <FaSave />
              Gem ressource
            </button>
          </ModalActions>
        </form>
      </ModalContent>
    </ModalOverlay>
  );
};

export default ResourcesPage;