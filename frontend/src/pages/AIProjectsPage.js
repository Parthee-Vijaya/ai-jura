import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaSearch,
  FaExternalLinkAlt,
  FaRobot,
  FaCheckCircle,
  FaClock,
  FaMapMarkerAlt,
  FaTimes
} from 'react-icons/fa';

import projectsData from '../data/aiProjectsFallback.json';
import {
  PageShell,
  PageHeader,
  OutlinePill,
  SearchField,
} from '../components/page-chrome/PageChrome';

const Toolbar = styled.div`
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 1.25rem;
`;

const FilterChips = styled.div`
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
`;

const ResultsCount = styled.div`
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.82rem;
  letter-spacing: 0.02em;
  color: ${(p) => p.theme.colors.textMuted};
  margin-bottom: 1.5rem;
`;

const ProjectsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const ProjectCard = styled(motion.div)`
  background: ${(p) => p.theme.colors.surface};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: ${(p) => p.theme.borderRadius};
  overflow: hidden;
  transition: ${(p) => p.theme.animations.transition};
  cursor: pointer;

  &:hover {
    transform: translateY(-2px);
    box-shadow: ${(p) => p.theme.shadows.md};
    border-color: ${(p) => p.theme.colors.primary};
  }
`;

const ProjectImage = styled.div`
  width: 100%;
  height: 180px;
  background: ${props => props.$imageUrl
    ? `url(${props.$imageUrl})`
    : props.theme.colors.gradients.primary};
  background-size: cover;
  background-position: center;
  position: relative;

  ${props => props.$isSignature && `
    &::after {
      content: 'Signaturprojekt';
      position: absolute;
      top: 0.75rem;
      right: 0.75rem;
      padding: 0.35rem 0.75rem;
      background: rgba(16, 185, 129, 0.95);
      color: white;
      font-size: 0.7rem;
      font-weight: 600;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  `}
`;

const ProjectContent = styled.div`
  padding: 1.25rem;
`;

const ProjectTitle = styled.h3`
  font-family: ${(p) => p.theme.fonts.display};
  font-size: 1.18rem;
  font-weight: 600;
  letter-spacing: -0.005em;
  color: ${(p) => p.theme.colors.text};
  margin: 0 0 0.6rem 0;
  line-height: 1.3;
`;

const ProjectDescription = styled.p`
  font-family: ${(p) => p.theme.fonts.body};
  font-size: 0.95rem;
  color: ${(p) => p.theme.colors.text};
  line-height: 1.55;
  margin: 0 0 1rem 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
`;

const ProjectMeta = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
`;

const MetaBadge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 3px 10px;
  background: transparent;
  border: 1px solid ${(p) => p.theme.colors.border};
  color: ${(p) => p.theme.colors.textMuted};
  border-radius: 999px;
  font-family: ${(p) => p.theme.fonts.sans};
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.04em;

  svg {
    font-size: 0.7rem;
  }
`;

const StatusBadge = styled(MetaBadge)`
  ${({ $status, theme }) => {
    if ($status === 'I brug') {
      return `border-color: ${theme.colors.success}; color: ${theme.colors.success};`;
    }
    if ($status === 'Planlægges taget i brug') {
      return `border-color: ${theme.colors.warning}; color: ${theme.colors.warning};`;
    }
    return '';
  }}
`;

const Modal = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 2rem;
  overflow-y: auto;
`;

const ModalContent = styled(motion.div)`
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(15, 23, 42, 0.98)'
    : props.theme.colors.white};
  border-radius: ${props => props.theme.borderRadiusLarge};
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
`;

const ModalHeader = styled.div`
  position: sticky;
  top: 0;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(15, 23, 42, 0.98)'
    : props.theme.colors.white};
  padding: 1.5rem;
  border-bottom: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.2)'
    : props.theme.colors.gray[200]};
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  z-index: 10;
`;

const CloseButton = styled.button`
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.1)'
    : props.theme.colors.gray[100]};
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: ${props => props.theme.mode === 'dark'
    ? props.theme.colors.white
    : props.theme.colors.gray[600]};
  transition: all 0.2s ease;

  &:hover {
    background: ${props => props.theme.mode === 'dark'
      ? 'rgba(148, 163, 184, 0.2)'
      : props.theme.colors.gray[200]};
  }
`;

const ModalBody = styled.div`
  padding: 1.5rem;
`;

const ModalImage = styled.div`
  width: 100%;
  height: 300px;
  background: ${props => props.$imageUrl
    ? `url(${props.$imageUrl})`
    : props.theme.colors.gradients.primary};
  background-size: cover;
  background-position: center;
  border-radius: ${props => props.theme.borderRadius};
  margin-bottom: 1.5rem;
`;

const ModalTitle = styled.h2`
  font-size: 2rem;
  font-weight: 700;
  color: ${props => props.theme.mode === 'dark'
    ? props.theme.colors.white
    : props.theme.colors.gray[900]};
  margin: 0 0 1rem 0;
`;

const ModalDescription = styled.div`
  font-size: 1rem;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(226, 232, 240, 0.9)'
    : props.theme.colors.gray[700]};
  line-height: 1.7;
  margin-bottom: 1.5rem;

  p {
    margin-bottom: 1rem;
  }
`;

const ModalMetaSection = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  padding: 1.5rem;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(30, 41, 59, 0.5)'
    : props.theme.colors.gray[50]};
  border-radius: ${props => props.theme.borderRadius};
  margin-bottom: 1.5rem;
`;

const MetaItem = styled.div`
  .label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(148, 163, 184, 0.8)'
      : props.theme.colors.gray[500]};
    margin-bottom: 0.25rem;
  }

  .value {
    font-size: 0.95rem;
    font-weight: 600;
    color: ${props => props.theme.mode === 'dark'
      ? props.theme.colors.white
      : props.theme.colors.gray[900]};
  }
`;

const ExternalLink = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: ${props => props.theme.colors.gradients.primary};
  color: white;
  text-decoration: none;
  border-radius: ${props => props.theme.borderRadius};
  font-weight: 600;
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: ${props => props.theme.shadows.lg};
  }
`;

const AIProjectsPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedProject, setSelectedProject] = useState(null);

  const categories = useMemo(() => {
    const cats = new Set(projectsData.map(p => p.category));
    return ['all', ...Array.from(cats)];
  }, []);

  const filteredProjects = useMemo(() => {
    return projectsData.filter(project => {
      const matchesSearch = project.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           project.description.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesCategory = selectedCategory === 'all' || project.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [searchTerm, selectedCategory]);

  return (
    <PageShell>
      <PageHeader
        eyebrow="Forseti · ai-løsninger"
        title="AI-løsninger i det offentlige"
        lede="Udforsk danske offentlige AI-projekter — find inspiration, lær af andres erfaringer, og se hvilke løsninger der allerede er i drift på tværs af kommuner og styrelser."
      />

      <Toolbar>
        <SearchField>
          <FaSearch />
          <input
            type="text"
            placeholder="Søg efter projekter…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </SearchField>
      </Toolbar>

      <FilterChips style={{ marginBottom: '1.25rem' }}>
        {categories.map(cat => (
          <OutlinePill
            key={cat}
            $active={selectedCategory === cat}
            onClick={() => setSelectedCategory(cat)}
          >
            {cat === 'all' ? 'Alle kategorier' : cat}
          </OutlinePill>
        ))}
      </FilterChips>

      <ResultsCount>
        Viser {filteredProjects.length} af {projectsData.length} projekter
      </ResultsCount>

      <ProjectsGrid>
        {filteredProjects.map(project => (
          <ProjectCard
            key={project.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            onClick={() => setSelectedProject(project)}
          >
            <ProjectImage
              $imageUrl={project.imageUrl}
              $isSignature={project.isSignature}
            />
            <ProjectContent>
              <ProjectTitle>{project.title}</ProjectTitle>
              <ProjectDescription>{project.description}</ProjectDescription>
              <ProjectMeta>
                <MetaBadge>
                  <FaRobot />
                  {project.category}
                </MetaBadge>
                <MetaBadge>
                  <FaMapMarkerAlt />
                  {project.scope}
                </MetaBadge>
                {project.status && (
                  <StatusBadge $status={project.status}>
                    {project.status === 'I brug' ? <FaCheckCircle /> : <FaClock />}
                    {project.status}
                  </StatusBadge>
                )}
              </ProjectMeta>
            </ProjectContent>
          </ProjectCard>
        ))}
      </ProjectsGrid>

      <AnimatePresence>
        {selectedProject && (
          <Modal
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedProject(null)}
          >
            <ModalContent
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              <ModalHeader>
                <div>
                  <ModalTitle>{selectedProject.title}</ModalTitle>
                  {selectedProject.isSignature && (
                    <MetaBadge style={{ marginBottom: '0.5rem' }}>
                      <FaCheckCircle />
                      Signaturprojekt
                    </MetaBadge>
                  )}
                </div>
                <CloseButton onClick={() => setSelectedProject(null)}>
                  <FaTimes />
                </CloseButton>
              </ModalHeader>
              <ModalBody>
                <ModalImage $imageUrl={selectedProject.imageUrl} />
                <ModalDescription>
                  <p>{selectedProject.description}</p>
                </ModalDescription>
                <ModalMetaSection>
                  <MetaItem>
                    <div className="label">Klassifikation</div>
                    <div className="value">{selectedProject.category}</div>
                  </MetaItem>
                  <MetaItem>
                    <div className="label">Udbredelse</div>
                    <div className="value">{selectedProject.scope}</div>
                  </MetaItem>
                  {selectedProject.status && (
                    <MetaItem>
                      <div className="label">Status</div>
                      <div className="value">{selectedProject.status}</div>
                    </MetaItem>
                  )}
                </ModalMetaSection>
                <ExternalLink
                  href={selectedProject.externalUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Læs mere på Offentlig AI
                  <FaExternalLinkAlt />
                </ExternalLink>
              </ModalBody>
            </ModalContent>
          </Modal>
        )}
      </AnimatePresence>
    </PageShell>
  );
};

export default AIProjectsPage;
