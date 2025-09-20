import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import {
  FaShieldAlt,
  FaGlobeEurope,
  FaChartLine,
  FaArrowRight,
  FaCheckCircle,
  FaExclamationTriangle,
  FaTimesCircle,
  FaHistory,
  FaClock,
  FaUsers,
  FaFileAlt,
  FaCalendarAlt
} from 'react-icons/fa';
import NewsSection from '../components/NewsSection';
import NewsTicker from '../components/NewsTicker';
import { FeatureCardSkeletonLoader, StatCardSkeletonLoader } from '../components/SkeletonLoader';

const HomeContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const HeroSection = styled.section`
  background: ${props => props.theme.colors.gradients.hero};
  color: white;
  padding: 4rem 2rem;
  border-radius: ${props => props.theme.borderRadiusLarge};
  margin-bottom: 3rem;
  text-align: center;
  position: relative;
  overflow: hidden;
  box-shadow: ${props => props.theme.shadows.xl};

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: ${props => props.theme.colors.gradients.glass};
    backdrop-filter: blur(1px);
    z-index: 1;
  }

  &::after {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    animation: heroGlow 8s ease-in-out infinite;
    z-index: 1;
  }

  @keyframes heroGlow {
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.3; }
    50% { transform: translate(-50%, -50%) scale(1.1); opacity: 0.5; }
  }

  > * {
    position: relative;
    z-index: 2;
  }
`;

const HeroTitle = styled.h1`
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: 1rem;

  @media (max-width: 768px) {
    font-size: 2rem;
  }
`;

const HeroSubtitle = styled.p`
  font-size: 1.25rem;
  margin-bottom: 2rem;
  opacity: 0.9;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
`;

const CTAButton = styled(Link)`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: white;
  color: ${props => props.theme.colors.primary};
  padding: 1rem 2rem;
  border-radius: ${props => props.theme.borderRadius};
  font-weight: 600;
  text-decoration: none;
  transition: ${props => props.theme.animations.transition};
  position: relative;
  overflow: hidden;
  border: 2px solid transparent;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: ${props => props.theme.colors.gradients.primary};
    opacity: 0;
    transition: ${props => props.theme.animations.transition};
    z-index: 1;
  }

  &:hover {
    transform: translateY(-3px);
    box-shadow: ${props => props.theme.shadows.xl};
    color: white;
    border-color: ${props => props.theme.colors.juridical.lightGold};

    &::before {
      opacity: 1;
    }

    > * {
      position: relative;
      z-index: 2;
    }
  }

  &:active {
    transform: translateY(-1px);
    transition: ${props => props.theme.animations.transitionFast};
  }
`;

const FeaturesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
`;

const FeatureCard = styled(motion.div)`
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  padding: 2rem;
  border-radius: ${props => props.theme.borderRadiusLarge};
  border: 1px solid rgba(255, 255, 255, 0.2);
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
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 1rem;
    font-weight: 700;
  }

  p {
    color: ${props => props.theme.colors.gray[600]};
    line-height: 1.6;
  }
`;


const QuickStartSection = styled.section`
  background: ${props => props.theme.colors.gray[50]};
  padding: 3rem 2rem;
  border-radius: ${props => props.theme.borderRadius};
  text-align: center;
`;

const QuickStartTitle = styled.h2`
  color: ${props => props.theme.colors.gray[800]};
  margin-bottom: 2rem;
`;

const QuickStartGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
`;

const QuickStartCard = styled(Link)`
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  padding: 1.5rem;
  border-radius: ${props => props.theme.borderRadius};
  text-decoration: none;
  color: inherit;
  transition: ${props => props.theme.animations.transition};
  border: 2px solid rgba(255, 255, 255, 0.3);
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
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.5rem;
    font-weight: 600;
  }

  p {
    color: ${props => props.theme.colors.gray[600]};
    font-size: 0.875rem;
    line-height: 1.5;
  }
`;

const StatusOverviewSection = styled.section`
  margin-bottom: 3rem;
`;

const StatusGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
`;

const StatusCard = styled(motion.div)`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  padding: 1.5rem;
  border-radius: ${props => props.theme.borderRadiusLarge};
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: ${props => props.theme.shadows.glass};
  position: relative;
  overflow: hidden;
  border-left: 4px solid ${props => {
    switch(props.type) {
      case 'success': return props.theme.colors.success;
      case 'warning': return props.theme.colors.warning;
      case 'danger': return props.theme.colors.danger;
      default: return props.theme.colors.primary;
    }
  }};

  &:hover {
    transform: translateY(-4px);
    box-shadow: ${props => props.theme.shadows.xl};
  }

  .icon {
    background: ${props => {
      switch(props.type) {
        case 'success': return props.theme.colors.success;
        case 'warning': return props.theme.colors.warning;
        case 'danger': return props.theme.colors.danger;
        default: return props.theme.colors.primary;
      }
    }};
    color: white;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1rem;
    transition: ${props => props.theme.animations.spring};
  }

  .value {
    font-size: 2rem;
    font-weight: 700;
    color: ${props => props.theme.colors.gray[800]};
    margin-bottom: 0.25rem;
  }

  .label {
    color: ${props => props.theme.colors.gray[600]};
    font-size: 0.875rem;
    font-weight: 500;
  }

  .trend {
    position: absolute;
    top: 1rem;
    right: 1rem;
    font-size: 0.75rem;
    color: ${props => props.theme.colors.success};
    font-weight: 600;
  }
`;

const RecentActivitySection = styled.section`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: ${props => props.theme.borderRadiusLarge};
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: ${props => props.theme.shadows.glass};
  padding: 2rem;
  margin-bottom: 3rem;

  h3 {
    color: ${props => props.theme.colors.gray[800]};
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
  background: ${props => props.theme.colors.gray[50]};
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
      color: ${props => props.theme.colors.gray[800]};
      margin-bottom: 0.25rem;
    }

    .activity-description {
      color: ${props => props.theme.colors.gray[600]};
      font-size: 0.875rem;
    }
  }

  .activity-time {
    color: ${props => props.theme.colors.gray[500]};
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }
`;

const HomePage = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading time
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  const features = [
    {
      icon: FaShieldAlt,
      title: 'EU AI Act Compliance',
      description: 'Omfattende tjek af AI-systemer mod EU AI Act krav med automatisk risikoanalyse og implementeringsguide.'
    },
    {
      icon: FaGlobeEurope,
      title: 'GDPR & Dansk Lovgivning',
      description: 'Specialiseret analyse af GDPR compliance for AI med fokus på danske implementeringsregler og Datatilsynets vejledninger.'
    },
    {
      icon: FaChartLine,
      title: 'Juridisk Research',
      description: 'Dyb research i relevante love og forordninger med præcise kildehenvisninger og opdaterede guidelines.'
    }
  ];

  const quickStartSteps = [
    {
      title: 'Hurtig Tjek',
      description: 'Få øjeblikkelig feedback på dit AI-systems compliance status',
      link: '/hurtig-tjek'
    },
    {
      title: 'Compliance Control',
      description: 'Omfattende analyse med detaljeret rapport og handlingsplan',
      link: '/fuld-vurdering'
    },
    {
      title: 'Se Resultater',
      description: 'Analyser trends og følg compliance progress i dashboard',
      link: '/dashboard'
    }
  ];

  const statusData = [
    {
      icon: FaCheckCircle,
      value: '32',
      label: 'Approved Assessments',
      type: 'success',
      trend: '+8%'
    },
    {
      icon: FaExclamationTriangle,
      value: '12',
      label: 'Pending Reviews',
      type: 'warning',
      trend: '+3'
    },
    {
      icon: FaTimesCircle,
      value: '3',
      label: 'Rejected Systems',
      type: 'danger',
      trend: '-1'
    },
    {
      icon: FaHistory,
      value: '47',
      label: 'Total Assessments',
      type: 'primary',
      trend: '+12%'
    }
  ];

  const recentActivities = [
    {
      type: 'assessment',
      icon: FaFileAlt,
      title: 'AI Chatbot Assessment Complete',
      description: 'Customer service chatbot received conditional approval',
      time: '2 timer siden'
    },
    {
      type: 'research',
      icon: FaGlobeEurope,
      title: 'Research: GDPR Article 22 Analysis',
      description: 'Completed automated decision-making compliance research',
      time: '5 timer siden'
    },
    {
      type: 'compliance',
      icon: FaShieldAlt,
      title: 'Compliance Report Generated',
      description: 'Document classification system approved for production',
      time: '1 dag siden'
    },
    {
      type: 'assessment',
      icon: FaUsers,
      title: 'Team Assessment Review',
      description: 'HR automation system flagged for manual review',
      time: '2 dage siden'
    }
  ];

  return (
    <HomeContainer>
      <HeroSection>
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <HeroTitle>Project Judge Dredd</HeroTitle>
          <HeroSubtitle>
            AI Compliance Control Platform. Omfattende juridisk compliance analyse for AI-systemer efter EU AI Act, GDPR og dansk lovgivning.
          </HeroSubtitle>
          <CTAButton to="/hurtig-tjek">
            Start Compliance Tjek <FaArrowRight />
          </CTAButton>
        </motion.div>
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
          features.map((feature, index) => (
            <FeatureCard
              key={index}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.2 }}
            >
              <div className="icon">
                <feature.icon size={24} />
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
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
