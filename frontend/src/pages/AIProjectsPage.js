import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaSearch,
  FaFilter,
  FaExternalLinkAlt,
  FaRobot,
  FaCheckCircle,
  FaClock,
  FaMapMarkerAlt,
  FaTimes
} from 'react-icons/fa';

import projectsData from '../data/aiProjectsFallback.json';

const PageContainer = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem 1rem;
`;

const PageHeader = styled.div`
  margin-bottom: 3rem;
`;

const PageTitle = styled.h1`
  font-size: 2.5rem;
  font-weight: 700;
  color: ${props => props.theme.mode === 'dark'
    ? props.theme.colors.white
    : props.theme.colors.gray[900]};
  margin-bottom: 0.5rem;
`;

const PageDescription = styled.p`
  font-size: 1.1rem;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(226, 232, 240, 0.8)'
    : props.theme.colors.gray[600]};
  max-width: 800px;
`;

const SearchAndFilterBar = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
`;

const SearchBox = styled.div`
  flex: 1;
  min-width: 300px;
  position: relative;

  svg {
    position: absolute;
    left: 1rem;
    top: 50%;
    transform: translateY(-50%);
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(148, 163, 184, 0.7)'
      : props.theme.colors.gray[400]};
  }

  input {
    width: 100%;
    padding: 0.75rem 1rem 0.75rem 2.75rem;
    border-radius: ${props => props.theme.borderRadius};
    border: 1px solid ${props => props.theme.mode === 'dark'
      ? 'rgba(148, 163, 184, 0.2)'
      : props.theme.colors.gray[300]};
    background: ${props => props.theme.mode === 'dark'
      ? 'rgba(15, 23, 42, 0.6)'
      : props.theme.colors.white};
    color: ${props => props.theme.mode === 'dark'
      ? props.theme.colors.white
      : props.theme.colors.gray[900]};
    font-size: 1rem;

    &:focus {
      outline: none;
      border-color: ${props => props.theme.colors.primary};
    }

    &::placeholder {
      color: ${props => props.theme.mode === 'dark'
        ? 'rgba(148, 163, 184, 0.5)'
        : props.theme.colors.gray[400]};
    }
  }
`;

const FilterButton = styled.button`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: ${props => props.theme.borderRadius};
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.2)'
    : props.theme.colors.gray[300]};
  background: ${props => props.$active
    ? props.theme.colors.primary
    : props.theme.mode === 'dark'
      ? 'rgba(15, 23, 42, 0.6)'
      : props.theme.colors.white};
  color: ${props => props.$active
    ? props.theme.colors.white
    : props.theme.mode === 'dark'
      ? props.theme.colors.white
      : props.theme.colors.gray[700]};
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: ${props => props.theme.colors.primary};
    background: ${props => props.$active
      ? props.theme.colors.primaryDark
      : props.theme.mode === 'dark'
        ? 'rgba(15, 23, 42, 0.8)'
        : props.theme.colors.gray[50]};
  }
`;

const ResultsCount = styled.div`
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(226, 232, 240, 0.7)'
    : props.theme.colors.gray[600]};
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
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(15, 23, 42, 0.8)'
    : props.theme.colors.white};
  border-radius: ${props => props.theme.borderRadiusLarge};
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.2)'
    : props.theme.colors.gray[200]};
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;

  &:hover {
    transform: translateY(-4px);
    box-shadow: ${props => props.theme.shadows.xl};
    border-color: ${props => props.theme.colors.primary};
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
  font-size: 1.15rem;
  font-weight: 700;
  color: ${props => props.theme.mode === 'dark'
    ? props.theme.colors.white
    : props.theme.colors.gray[900]};
  margin: 0 0 0.75rem 0;
  line-height: 1.3;
`;

const ProjectDescription = styled.p`
  font-size: 0.9rem;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(226, 232, 240, 0.8)'
    : props.theme.colors.gray[600]};
  line-height: 1.6;
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
  gap: 0.35rem;
  padding: 0.3rem 0.65rem;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(59, 130, 246, 0.15)'
    : 'rgba(59, 130, 246, 0.1)'};
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(147, 197, 253, 0.95)'
    : props.theme.colors.primary};
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;

  svg {
    font-size: 0.7rem;
  }
`;

const StatusBadge = styled(MetaBadge)`
  background: ${props => {
    if (props.$status === 'I brug') return props.theme.mode === 'dark' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)';
    if (props.$status === 'Planlægges taget i brug') return props.theme.mode === 'dark' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.1)';
    return props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.15)' : 'rgba(148, 163, 184, 0.1)';
  }};
  color: ${props => {
    if (props.$status === 'I brug') return props.theme.mode === 'dark' ? 'rgba(167, 243, 208, 0.95)' : '#059669';
    if (props.$status === 'Planlægges taget i brug') return props.theme.mode === 'dark' ? 'rgba(253, 230, 138, 0.95)' : '#d97706';
    return props.theme.mode === 'dark' ? 'rgba(203, 213, 225, 0.95)' : props.theme.colors.gray[600];
  }};
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
    <PageContainer>
      <PageHeader>
        <PageTitle>AI Løsninger i Det Offentlige</PageTitle>
        <PageDescription>
          Udforsk danske offentlige AI-projekter og løsninger. Find inspiration til din egen organisation
          og lær af andres erfaringer med kunstig intelligens i den offentlige sektor.
        </PageDescription>
      </PageHeader>

      <SearchAndFilterBar>
        <SearchBox>
          <FaSearch />
          <input
            type="text"
            placeholder="Søg efter projekter..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </SearchBox>
        {categories.map(cat => (
          <FilterButton
            key={cat}
            $active={selectedCategory === cat}
            onClick={() => setSelectedCategory(cat)}
          >
            <FaFilter />
            {cat === 'all' ? 'Alle kategorier' : cat}
          </FilterButton>
        ))}
      </SearchAndFilterBar>

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
    </PageContainer>
  );
};

export default AIProjectsPage;
