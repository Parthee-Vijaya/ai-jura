import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import {
  FaShieldAlt,
  FaGlobeEurope,
  FaArrowRight,
  FaCheckCircle,
  FaExclamationTriangle,
  FaTimesCircle,
  FaHistory,
  FaClock,
  FaUsers,
  FaFileAlt,
  FaCalendarAlt,
  FaBalanceScale,
  FaLightbulb,
  FaExternalLinkAlt,
  FaCode
} from 'react-icons/fa';
import NewsSection from '../components/NewsSection';
import NewsTicker from '../components/NewsTicker';
import { FeatureCardSkeletonLoader } from '../components/SkeletonLoader';
import aiActDidYouKnowFacts from '../data/aiActDidYouKnow';
import packageJson from '../../package.json';

const HomeContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const HeroSection = styled.section`
  background: ${props => props.theme.mode === 'dark'
    ? 'linear-gradient(135deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95))'
    : 'linear-gradient(135deg, rgba(241,245,249,1), rgba(226,232,240,0.85))'};
  padding: 3.5rem;
  border-radius: ${props => props.theme.borderRadiusLarge};
  margin-bottom: 3rem;
  position: relative;
  overflow: hidden;
  box-shadow: ${props => props.theme.shadows.xl};

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at top right, rgba(255,255,255,0.35), transparent 55%);
    opacity: ${props => props.theme.mode === 'dark' ? 0.1 : 0.4};
    pointer-events: none;
  }

  &::after {
    content: '';
    position: absolute;
    bottom: -30%;
    right: -20%;
    width: 60%;
    height: 60%;
    background: radial-gradient(circle, rgba(56, 189, 248, 0.25), transparent 70%);
    pointer-events: none;
  }

  @media (max-width: 1024px) {
    padding: 2.5rem;
  }

  @media (max-width: 768px) {
    padding: 2rem;
  }
`;

const HeroLayout = styled.div`
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 3rem;
  align-items: center;
  z-index: 1;
`;

const HeroContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  color: ${props => props.theme.mode === 'dark' ? props.theme.colors.white : props.theme.colors.text};
`;

const HeroLogo = styled.img`
  max-width: 200px;
  height: auto;
  margin-bottom: 0.5rem;

  @media (max-width: 768px) {
    max-width: 160px;
  }
`;

const HeroBadge = styled.span`
  align-self: flex-start;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: rgba(255,255,255,0.16);
  color: ${props => props.theme.mode === 'dark' ? props.theme.colors.white : props.theme.colors.primary};
  border: 1px solid rgba(255,255,255,0.3);
`;

const HeroTitle = styled.h1`
  font-size: clamp(2.2rem, 4vw, 3.2rem);
  font-weight: 700;
  line-height: 1.1;
  margin: 0;
`;

const HeroSubtitle = styled.p`
  font-size: 1.05rem;
  line-height: 1.6;
  max-width: 520px;
  margin: 0;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(226, 232, 240, 0.8)'
    : 'rgba(51, 65, 85, 0.85)'};
`;

const HeroActions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
`;

const CTAButton = styled(Link)`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  border-radius: 999px;
  padding: 0.85rem 1.8rem;
  font-weight: 600;
  background: ${props => props.theme.colors.gradients.primary};
  color: ${props => props.theme.colors.white};
  box-shadow: ${props => props.theme.shadows.glow};
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    transform: translateY(-2px);
    box-shadow: ${props => props.theme.shadows.xl};
  }
`;

const SecondaryCTA = styled(Link)`
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.85rem 1.4rem;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 600;
  color: ${props => props.theme.mode === 'dark' ? props.theme.colors.white : props.theme.colors.primary};
  background: rgba(255,255,255,0.18);
  border: 1px solid rgba(255,255,255,0.35);
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    transform: translateY(-2px);
    backdrop-filter: blur(6px);
  }
`;

const HeroInsights = styled.div`
  display: grid;
  gap: 1rem;
  position: relative;
`;

const HeroStatCard = styled(motion.div)`
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(15, 23, 42, 0.6)'
    : 'rgba(255, 255, 255, 0.9)'};
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 1.25rem 1.5rem;
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.25)'
    : 'rgba(148, 163, 184, 0.2)'};
  box-shadow: ${props => props.theme.shadows.lg};
  display: flex;
  flex-direction: column;
  gap: 0.45rem;

  .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: ${props => props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.8)' : props.theme.colors.gray[500]};
  }

  .value {
    font-size: 1.8rem;
    font-weight: 700;
    color: ${props => props.theme.mode === 'dark'
      ? props.theme.colors.white
      : props.theme.colors.primary};
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
  }

  .trend {
    font-size: 0.8rem;
    font-weight: 600;
  }

  .caption {
    font-size: 0.8rem;
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(226, 232, 240, 0.7)'
      : props.theme.colors.gray[500]};
  }
`;

const VersionCard = styled(motion.div)`
  background: linear-gradient(135deg, rgba(160, 54, 18, 0.1) 0%, rgba(125, 43, 14, 0.05) 100%);
  border-radius: ${props => props.theme.borderRadiusLarge};
  padding: 1rem 1.5rem;
  border: 2px solid rgba(160, 54, 18, 0.3);
  box-shadow: ${props => props.theme.shadows.md};
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;

  .version-icon {
    font-size: 1.8rem;
    color: #A03612;
  }

  .version-info {
    flex: 1;

    .version-label {
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: ${props => props.theme.colors.textMuted};
      margin-bottom: 0.2rem;
    }

    .version-number {
      font-size: 1.1rem;
      font-weight: 700;
      color: #A03612;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .version-date {
      font-size: 0.7rem;
      color: ${props => props.theme.colors.textMuted};
      margin-top: 0.2rem;
    }
  }

  .changelog-link {
    font-size: 0.75rem;
    color: #A03612;
    text-decoration: none;
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-weight: 600;
    transition: ${props => props.theme.animations.transitionFast};

    &:hover {
      color: #7d2b0e;
      transform: translateX(2px);
    }
  }
`;

const FeaturesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
`;

const FeatureCard = styled(motion.div)`
  background: ${props => props.theme.mode === 'dark' ? 'rgba(15, 23, 42, 0.85)' : 'rgba(255, 255, 255, 0.9)'};
  backdrop-filter: blur(20px);
  padding: 2rem;
  border-radius: ${props => props.theme.borderRadiusLarge};
  border: 1px solid ${props => props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.2)' : 'rgba(255, 255, 255, 0.2)'};
  box-shadow: ${props => props.theme.shadows.glass};
  text-align: center;
  transition: ${props => props.theme.animations.transition};
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: ${props => props.theme.colors.gradients.card};
    opacity: 0;
    transition: ${props => props.theme.animations.transition};
  }

  &:hover {
    transform: translateY(-8px);
    box-shadow: ${props => props.theme.shadows.xl};
    border-color: rgba(26, 54, 93, 0.3);

    &::before {
      opacity: 1;
    }

    .icon {
      transform: scale(1.1);
      box-shadow: ${props => props.theme.shadows.glow};
    }
  }

  > * {
    position: relative;
    z-index: 1;
  }

  .icon {
    background: ${props => props.theme.colors.gradients.primary};
    color: white;
    width: 70px;
    height: 70px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1.5rem;
    transition: ${props => props.theme.animations.spring};
    box-shadow: ${props => props.theme.shadows.md};
  }

  h3 {
    color: ${props => props.theme.mode === 'dark' ? props.theme.colors.gray[100] : props.theme.colors.gray[800]};
    margin-bottom: 1rem;
    font-weight: 700;
  }

  p {
    color: ${props => props.theme.mode === 'dark' ? 'rgba(226, 232, 240, 0.85)' : props.theme.colors.gray[600]};
    line-height: 1.6;
  }

  .fact-source {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin-top: 1.5rem;
    font-size: 0.85rem;
    font-weight: 600;
    color: ${props => props.theme.colors.primary};
    text-decoration: none;
    transition: ${props => props.theme.animations.transitionFast};

    svg {
      font-size: 0.75rem;
    }

    &:hover {
      text-decoration: underline;
    }
  }
`;

const QuickStartSection = styled.section`
  background: ${props => props.theme.mode === 'dark' ? 'rgba(15, 23, 42, 0.85)' : props.theme.colors.gray[50]};
  padding: 3rem 2rem;
  border-radius: ${props => props.theme.borderRadius};
  text-align: center;
`;

const QuickStartTitle = styled.h2`
  color: ${props => props.theme.mode === 'dark' ? props.theme.colors.gray[100] : props.theme.colors.gray[800]};
  margin-bottom: 2rem;
`;

const QuickStartGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
`;

const QuickStartCard = styled(Link)`
  background: ${props => props.theme.mode === 'dark' ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.8)'};
  backdrop-filter: blur(10px);
  padding: 1.5rem;
  border-radius: ${props => props.theme.borderRadius};
  text-decoration: none;
  color: inherit;
  transition: ${props => props.theme.animations.transition};
  border: 2px solid ${props => props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.3)' : 'rgba(255, 255, 255, 0.3)'};
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: ${props => props.theme.colors.gradients.card};
    opacity: 0;
    transition: ${props => props.theme.animations.transition};
  }

  &:hover {
    border-color: ${props => props.theme.colors.juridical.lightGold};
    transform: translateY(-4px);
    box-shadow: ${props => props.theme.shadows.lg};

    &::before {
      opacity: 1;
    }

    .step-number {
      background: ${props => props.theme.colors.gradients.gold};
      transform: scale(1.1);
    }
  }

  > * {
    position: relative;
    z-index: 1;
  }

  .step-number {
    background: ${props => props.theme.colors.gradients.primary};
    color: white;
    width: 35px;
    height: 35px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.875rem;
    margin: 0 auto 1rem;
    transition: ${props => props.theme.animations.spring};
    box-shadow: ${props => props.theme.shadows.md};
  }

  h4 {
    color: ${props => props.theme.mode === 'dark' ? props.theme.colors.gray[100] : props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
    font-weight: 600;
  }

  p {
    color: ${props => props.theme.mode === 'dark' ? 'rgba(226, 232, 240, 0.85)' : props.theme.colors.gray[600]};
    font-size: 0.875rem;
    line-height: 1.5;
  }
`;

const RecentActivitySection = styled.section`
  background: ${props => props.theme.mode === 'dark' ? 'rgba(15, 23, 42, 0.75)' : 'rgba(255, 255, 255, 0.95)'};
  backdrop-filter: blur(20px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  border: 1px solid ${props => props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.2)' : 'rgba(255, 255, 255, 0.2)'};
  box-shadow: ${props => props.theme.shadows.glass};
  padding: 2rem;
  margin-bottom: 3rem;

  h3 {
    color: ${props => props.theme.mode === 'dark' ? props.theme.colors.gray[100] : props.theme.colors.gray[800]};
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
`;

const ActivityList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const ActivityItem = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: ${props => props.theme.mode === 'dark' ? 'rgba(15, 23, 42, 0.85)' : props.theme.colors.gray[50]};
  border-radius: ${props => props.theme.borderRadius};
  border-left: 3px solid ${props => {
    switch(props.type) {
      case 'assessment': return props.theme.colors.primary;
      case 'research': return props.theme.colors.warning;
      case 'compliance': return props.theme.colors.success;
      default: return props.theme.colors.gray[400];
    }
  }};

  .activity-icon {
    background: ${props => {
      switch(props.type) {
        case 'assessment': return props.theme.colors.primary;
        case 'research': return props.theme.colors.warning;
        case 'compliance': return props.theme.colors.success;
        default: return props.theme.colors.gray[400];
      }
    }};
    color: white;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.875rem;
  }

  .activity-content {
    flex: 1;

    .activity-title {
      font-weight: 600;
      color: ${props => props.theme.mode === 'dark' ? props.theme.colors.gray[100] : props.theme.colors.gray[800]};
      margin-bottom: 0.25rem;
    }

    .activity-description {
      color: ${props => props.theme.mode === 'dark' ? 'rgba(226, 232, 240, 0.85)' : props.theme.colors.gray[600]};
      font-size: 0.875rem;
    }
  }

  .activity-time {
    color: ${props => props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.8)' : props.theme.colors.gray[500]};
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }
`;

const FACTS_PER_VIEW = 3;
const FACT_ROTATION_INTERVAL_MS = 120000;

const HomePage = () => {
  const [loading, setLoading] = useState(true);
  const [currentFactIndex, setCurrentFactIndex] = useState(0);

  useEffect(() => {
    // Simulate loading time
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const total = aiActDidYouKnowFacts.length;
    if (!total) {
      return;
    }

    const randomStart = Math.floor(Math.random() * total);
    const normalised = randomStart - (randomStart % FACTS_PER_VIEW);
    setCurrentFactIndex(normalised);
  }, []);

  useEffect(() => {
    const total = aiActDidYouKnowFacts.length;
    if (total <= FACTS_PER_VIEW) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setCurrentFactIndex((prev) => (prev + FACTS_PER_VIEW) % total);
    }, FACT_ROTATION_INTERVAL_MS);

    return () => window.clearInterval(interval);
  }, []);

  const displayedFacts = useMemo(() => {
    if (!aiActDidYouKnowFacts.length) {
      return [];
    }

    const total = aiActDidYouKnowFacts.length;
    return Array.from({ length: FACTS_PER_VIEW }, (_, offset) => {
      const index = (currentFactIndex + offset) % total;
      return aiActDidYouKnowFacts[index];
    });
  }, [currentFactIndex]);

  const quickStartSteps = [
    {
      title: 'Hurtig Tjek',
      description: 'Få øjeblikkelig feedback på om dit AI-system lever op til kravene',
      link: '/hurtig-tjek'
    },
    {
      title: 'Compliance Control',
      description: 'Gennemfør en fuld analyse med detaljeret rapport og handlingsplan',
      link: '/fuld-vurdering'
    },
    {
      title: 'Se Resultater',
      description: 'Følg udviklingen og compliance-status i dashboardet',
      link: '/dashboard'
    }
  ];

  const statusData = [
    {
      icon: FaCheckCircle,
      value: '32',
      label: 'Godkendte vurderinger',
      type: 'success',
      trend: '+8%'
    },
    {
      icon: FaExclamationTriangle,
      value: '12',
      label: 'Under behandling',
      type: 'warning',
      trend: '+3'
    },
    {
      icon: FaTimesCircle,
      value: '3',
      label: 'Afviste systemer',
      type: 'danger',
      trend: '-1'
    },
    {
      icon: FaHistory,
      value: '47',
      label: 'Samlede vurderinger',
      type: 'primary',
      trend: '+12%'
    }
  ];

  const recentActivities = [
    {
      type: 'assessment',
      icon: FaFileAlt,
      title: 'AI-chatbot vurdering fuldført',
      description: 'Chatbot til borgerservice fik en betinget godkendelse',
      time: '2 timer siden'
    },
    {
      type: 'research',
      icon: FaGlobeEurope,
      title: 'Research: Analyse af GDPR artikel 22',
      description: 'Research om automatiske afgørelser er gennemført og dokumenteret',
      time: '5 timer siden'
    },
    {
      type: 'compliance',
      icon: FaShieldAlt,
      title: 'Compliance-rapport genereret',
      description: 'Dokumentklassificeringssystem godkendt til drift',
      time: '1 dag siden'
    },
    {
      type: 'assessment',
      icon: FaUsers,
      title: 'Teamvurdering igangsat',
      description: 'HR-automationssystem markeret til manuel gennemgang',
      time: '2 dage siden'
    }
  ];

  const heroHighlights = statusData.slice(0, 3);
  const trendColors = {
    success: '#16a34a',
    warning: '#f59e0b',
    danger: '#ef4444',
    primary: '#2563eb'
  };

  return (
    <HomeContainer>
      <HeroSection>
        <HeroLayout>
          <HeroContent>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <HeroLogo src="/kalundborg-logo.svg" alt="Kalundborg Kommune" />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <HeroBadge>AI Compliance & Risikostyring</HeroBadge>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.05 }}
            >
              <HeroTitle>Project Judge Dredd</HeroTitle>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.12 }}
            >
              <HeroSubtitle>
                Få et samlet overblik over AI-kompliance på tværs af EU AI Act, GDPR og danske standarder. Automatisér risikovurderinger, dokumentation og juridisk research fra ét sted.
              </HeroSubtitle>
            </motion.div>
            <HeroActions>
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.18 }}
              >
                <CTAButton to="/hurtig-tjek">
                  Start compliance tjek
                  <FaArrowRight />
                </CTAButton>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.24 }}
              >
                <SecondaryCTA to="/ai-sager">
                  <FaBalanceScale size={16} />
                  Registrér AI sag
                </SecondaryCTA>
              </motion.div>
            </HeroActions>
          </HeroContent>

          <HeroInsights>
            {heroHighlights.map((item, index) => (
              <HeroStatCard
                key={item.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 + index * 0.1 }}
              >
                <span className="label">{item.label}</span>
                <span className="value">
                  {item.value}
                  {item.trend && (
                    <span className="trend" style={{ color: trendColors[item.type] || trendColors.primary }}>
                      {item.trend}
                    </span>
                  )}
                </span>
                <span className="caption">Seneste status opdateret</span>
              </HeroStatCard>
            ))}

            <VersionCard
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            >
              <div className="version-icon">
                <FaCode />
              </div>
              <div className="version-info">
                <div className="version-label">Platform Version</div>
                <div className="version-number">
                  v0.8.0
                  <span style={{ fontSize: '0.7rem', fontWeight: 500, color: '#059669' }}>
                    • Kalundborg Branding
                  </span>
                </div>
                <div className="version-date">Opdateret: 8. Okt 2025</div>
              </div>
              <a href="https://github.com/Parthee-Vijaya/Judge_dredd" target="_blank" rel="noopener noreferrer" className="changelog-link">
                Changelog <FaExternalLinkAlt size={10} />
              </a>
            </VersionCard>
          </HeroInsights>
        </HeroLayout>
      </HeroSection>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        <NewsTicker />
      </motion.div>

      <FeaturesGrid>
        {loading ? (
          // Show skeleton loaders while loading
          [...Array(3)].map((_, index) => (
            <FeatureCardSkeletonLoader key={index} />
          ))
        ) : (
          // Show actual feature cards
          displayedFacts.map((fact, index) => (
            <FeatureCard
              key={fact.id}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.2 }}
            >
              <div className="icon">
                <FaLightbulb size={24} />
              </div>
              <h3>{fact.title}</h3>
              <p>{fact.text}</p>
              <a
                className="fact-source"
                href={fact.source}
                target="_blank"
                rel="noopener noreferrer"
              >
                Se kilde
                <FaExternalLinkAlt />
              </a>
            </FeatureCard>
          ))
        )}
      </FeaturesGrid>
 
      <RecentActivitySection>
        <h3>
          <FaClock />
          Seneste Aktivitet
        </h3>
        <ActivityList>
          {recentActivities.map((activity, index) => (
            <ActivityItem key={index} type={activity.type}>
              <div className="activity-icon">
                <activity.icon />
              </div>
              <div className="activity-content">
                <div className="activity-title">{activity.title}</div>
                <div className="activity-description">{activity.description}</div>
              </div>
              <div className="activity-time">
                <FaCalendarAlt />
                {activity.time}
              </div>
            </ActivityItem>
          ))}
        </ActivityList>
      </RecentActivitySection>

      <NewsSection />

      <QuickStartSection>
        <QuickStartTitle>Kom Godt i Gang</QuickStartTitle>
        <p style={{ color: '#64748b', marginBottom: '2rem' }}>
          Følg disse trin for at få maksimal værdi af Project Judge Dredd platform
        </p>

        <QuickStartGrid>
          {quickStartSteps.map((step, index) => (
            <QuickStartCard key={index} to={step.link}>
              <div className="step-number">{index + 1}</div>
              <h4>{step.title}</h4>
              <p>{step.description}</p>
            </QuickStartCard>
          ))}
        </QuickStartGrid>
      </QuickStartSection>
    </HomeContainer>
  );
};

export default HomePage;
