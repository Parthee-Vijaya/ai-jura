import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { useQuery } from 'react-query';
import axios from 'axios';
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
  FaMoon,
  FaSun,
  FaInfoCircle,
  FaChevronDown,
  FaChevronUp,
  FaServer,
  FaDatabase,
  FaSearch,
  FaRobot,
  FaSpinner
} from 'react-icons/fa';
import NewsSection from '../components/NewsSection';
import LiveNewsCard from '../components/LiveNewsCard';
import ComplianceTips from '../components/ComplianceTips';
import { FeatureCardSkeletonLoader } from '../components/SkeletonLoader';
import aiActDidYouKnowFacts from '../data/aiActDidYouKnow';
import { useUserPreferences } from '../contexts/UserPreferencesContext';

const HomeContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const DarkModeToggle = styled.button`
  position: absolute;
  top: 2rem;
  right: 2rem;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(255,255,255,0.1)'
    : 'rgba(0,0,0,0.05)'};
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(255,255,255,0.2)'
    : 'rgba(0,0,0,0.1)'};
  color: ${props => props.theme.mode === 'dark' ? props.theme.colors.white : props.theme.colors.text};
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 10;

  &:hover {
    transform: scale(1.1);
    background: ${props => props.theme.mode === 'dark'
      ? 'rgba(255,255,255,0.15)'
      : 'rgba(0,0,0,0.08)'};
  }
`;

const HeroSection = styled.section`
  background: ${props => props.theme.mode === 'dark'
    ? 'linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.92) 100%)'
    : 'linear-gradient(135deg, rgba(241,245,249,0.98) 0%, rgba(226,232,240,0.95) 100%)'};
  padding: 2.5rem;
  border-radius: ${props => props.theme.borderRadiusLarge};
  margin-bottom: 2rem;
  position: relative;
  overflow: hidden;
  box-shadow: ${props => props.theme.shadows.xl};

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 60%);
    pointer-events: none;
  }

  @media (max-width: 1024px) {
    padding: 2rem;
  }

  @media (max-width: 768px) {
    padding: 1.5rem;
  }
`;

const HeroLayout = styled.div`
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2rem;
  align-items: start;
  z-index: 1;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
`;

const HeroContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
  color: ${props => props.theme.mode === 'dark' ? props.theme.colors.white : props.theme.colors.text};
`;

const HeroSidebar = styled.div`
  width: 380px;

  @media (max-width: 1024px) {
    width: 100%;
  }
`;

const HeroLogo = styled.img`
  max-width: 180px;
  height: auto;

  @media (max-width: 768px) {
    max-width: 140px;
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
  font-size: clamp(2rem, 4vw, 2.8rem);
  font-weight: 700;
  line-height: 1.1;
  margin: 0;
`;

const HeroSubtitle = styled.p`
  font-size: 0.95rem;
  line-height: 1.5;
  max-width: 600px;
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

const VersionSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.75rem 0.9rem;
  border-radius: ${props => props.theme.borderRadius};
  background: ${props => props.theme.mode === 'dark'
    ? 'linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.88))'
    : 'linear-gradient(145deg, rgba(255, 255, 255, 0.96), rgba(241, 245, 249, 0.92))'};
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.2)'
    : 'rgba(148, 163, 184, 0.32)'};
  box-shadow: ${props => props.theme.shadows.md};
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(226, 232, 240, 0.92)'
    : props.theme.layout.sidebar.text};
`;

const VersionHeading = styled.div`
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(203, 213, 225, 0.85)'
    : 'rgba(71, 85, 105, 0.85)'};
`;

const VersionValue = styled.div`
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: ${props => props.theme.mode === 'dark'
    ? props.theme.colors.white
    : props.theme.colors.primary};
`;

const ChangeTypeBadge = styled.span`
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 0.25rem 0.55rem;
  border-radius: 999px;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(59, 130, 246, 0.18)'
    : 'rgba(29, 78, 216, 0.12)'};
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(191, 219, 254, 0.95)'
    : 'rgba(29, 78, 216, 0.85)'};
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(96, 165, 250, 0.35)'
    : 'rgba(29, 78, 216, 0.2)'};
`;

const VersionMeta = styled.div`
  font-size: 0.68rem;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(203, 213, 225, 0.82)'
    : 'rgba(71, 85, 105, 0.85)'};
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;

  .relative {
    opacity: 0.75;
    font-size: 0.66rem;
  }

  .author {
    font-weight: 600;
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(191, 219, 254, 0.9)'
      : 'rgba(30, 64, 175, 0.9)'};
  }
`;

const VersionDetailsButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: transparent;
  border: none;
  padding: 0.4rem 0;
  margin-top: 0.2rem;
  font-size: 0.65rem;
  font-weight: 600;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.85)'
    : 'rgba(100, 116, 139, 0.85)'};
  cursor: pointer;
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(191, 219, 254, 0.95)'
      : 'rgba(30, 64, 175, 0.95)'};
  }

  .chevron {
    font-size: 0.6rem;
    transition: ${props => props.theme.animations.transitionFast};
  }
`;

const VersionDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: ${props => props.$isOpen ? '500px' : '0'};
  overflow: hidden;
  opacity: ${props => props.$isOpen ? '1' : '0'};
  transition: all 0.3s ease-in-out;
  margin-top: ${props => props.$isOpen ? '0.4rem' : '0'};
  padding-top: ${props => props.$isOpen ? '0.4rem' : '0'};
  border-top: ${props => props.$isOpen
    ? `1px solid ${props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.2)' : 'rgba(148, 163, 184, 0.25)'}`
    : 'none'};
`;

const SystemStatusSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-top: 0.6rem;
  padding-top: 0.6rem;
  border-top: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.2)'
    : 'rgba(148, 163, 184, 0.25)'};
`;

const SystemStatusGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.4rem;
`;

const ServiceStatus = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.5rem;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(15, 23, 42, 0.4)'
    : 'rgba(255, 255, 255, 0.5)'};
  border-radius: 4px;
  border: 1px solid ${props => {
    if (props.$status === 'healthy') return props.theme.mode === 'dark' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(34, 197, 94, 0.25)';
    if (props.$status === 'degraded') return props.theme.mode === 'dark' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(245, 158, 11, 0.25)';
    if (props.$status === 'down') return props.theme.mode === 'dark' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(239, 68, 68, 0.25)';
    return props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.2)' : 'rgba(148, 163, 184, 0.15)';
  }};

  .service-label {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.7rem;
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(226, 232, 240, 0.85)'
      : 'rgba(71, 85, 105, 0.85)'};

    svg {
      font-size: 0.85rem;
      color: ${props => props.theme.mode === 'dark'
        ? 'rgba(148, 163, 184, 0.7)'
        : 'rgba(100, 116, 139, 0.7)'};
    }
  }

  .service-indicator {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.65rem;
    font-weight: 600;
    color: ${props => {
      if (props.$status === 'healthy') return props.theme.mode === 'dark' ? 'rgba(134, 239, 172, 0.95)' : 'rgba(22, 163, 74, 0.95)';
      if (props.$status === 'degraded') return props.theme.mode === 'dark' ? 'rgba(253, 224, 71, 0.95)' : 'rgba(202, 138, 4, 0.95)';
      if (props.$status === 'down') return props.theme.mode === 'dark' ? 'rgba(252, 165, 165, 0.95)' : 'rgba(220, 38, 38, 0.95)';
      return props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.8)' : 'rgba(100, 116, 139, 0.8)';
    }};

    svg {
      font-size: 0.7rem;
      ${props => props.$status === 'checking' && `
        animation: spin 1s linear infinite;
      `}
    }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const SystemStatusDetailsButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: transparent;
  border: none;
  padding: 0.4rem 0;
  margin-top: 0.4rem;
  font-size: 0.65rem;
  font-weight: 600;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.85)'
    : 'rgba(100, 116, 139, 0.85)'};
  cursor: pointer;
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(191, 219, 254, 0.95)'
      : 'rgba(30, 64, 175, 0.95)'};
  }

  .chevron {
    font-size: 0.6rem;
    transition: ${props => props.theme.animations.transitionFast};
  }
`;

const SystemStatusDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: ${props => props.$isOpen ? '800px' : '0'};
  overflow: hidden;
  opacity: ${props => props.$isOpen ? '1' : '0'};
  transition: all 0.3s ease-in-out;
  margin-top: ${props => props.$isOpen ? '0.5rem' : '0'};
`;

const ServiceDetailCard = styled.div`
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(15, 23, 42, 0.6)'
    : 'rgba(255, 255, 255, 0.7)'};
  border: 1px solid ${props => {
    if (props.$status === 'healthy') return props.theme.mode === 'dark' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(34, 197, 94, 0.25)';
    if (props.$status === 'degraded') return props.theme.mode === 'dark' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(245, 158, 11, 0.25)';
    if (props.$status === 'down') return props.theme.mode === 'dark' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(239, 68, 68, 0.25)';
    return props.theme.mode === 'dark' ? 'rgba(148, 163, 184, 0.2)' : 'rgba(148, 163, 184, 0.15)';
  }};
  border-radius: 6px;
  padding: 0.6rem;

  .service-detail-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;

    svg {
      font-size: 1rem;
      color: ${props => props.theme.mode === 'dark'
        ? 'rgba(148, 163, 184, 0.8)'
        : 'rgba(100, 116, 139, 0.8)'};
    }

    h5 {
      margin: 0;
      font-size: 0.75rem;
      font-weight: 600;
      color: ${props => props.theme.mode === 'dark'
        ? props.theme.colors.white
        : props.theme.colors.gray[800]};
    }
  }

  .service-detail-content {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.68rem;
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(226, 232, 240, 0.85)'
      : 'rgba(71, 85, 105, 0.85)'};

    .detail-row {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .label {
        font-weight: 500;
        opacity: 0.8;
      }

      .value {
        font-weight: 600;
        font-family: 'Courier New', monospace;
        color: ${props => props.theme.mode === 'dark'
          ? props.theme.colors.white
          : props.theme.colors.primary};
      }
    }

    .error-message {
      color: ${props => props.theme.mode === 'dark'
        ? 'rgba(252, 165, 165, 0.95)'
        : 'rgba(220, 38, 38, 0.95)'};
      font-size: 0.65rem;
      padding: 0.3rem;
      background: ${props => props.theme.mode === 'dark'
        ? 'rgba(239, 68, 68, 0.1)'
        : 'rgba(239, 68, 68, 0.05)'};
      border-radius: 4px;
      margin-top: 0.2rem;
    }
  }
`;

const FACTS_PER_VIEW = 3;
const FACT_ROTATION_INTERVAL_MS = 120000;

const VERSION_QUERY_KEY = 'platform-version-info';
const VERSION_REFRESH_INTERVAL = 60 * 1000;

const CHANGE_TYPE_LABELS = {
  major: 'Stor ændring',
  minor: 'Mellem ændring',
  patch: 'Mindre ændring'
};

const buildApiUrl = (path) => {
  const base = process.env.REACT_APP_API_BASE_URL || '';
  if (!base) {
    return path;
  }
  return `${base.replace(/\/$/, '')}${path}`;
};

const fetchJsonNoCache = async (url, { timeout = 4000 } = {}) => {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);
  let response;
  try {
    response = await fetch(url, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        Pragma: 'no-cache',
      },
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timer);
  }
  if (!response.ok) {
    throw new Error(`Kunne ikke hente data fra ${url}`);
  }
  return response.json();
};

const fetchVersionInfo = async () => {
  const fallback = await fetchJsonNoCache('/fallback/version.json', { timeout: 1500 }).catch(() => null);
  try {
    const live = await fetchJsonNoCache(buildApiUrl('/api/version'));
    return live;
  } catch (error) {
    console.warn('Version API utilgængelig – anvender fallback', error);
    if (fallback) {
      return fallback;
    }
    throw error;
  }
};

const formatRelativeTime = (date) => {
  const diffMs = date.getTime() - Date.now();
  const diffMinutes = Math.round(diffMs / 60000);

  if (Math.abs(diffMinutes) < 1) {
    return 'lige nu';
  }

  const formatter = new Intl.RelativeTimeFormat('da', { numeric: 'auto' });

  if (Math.abs(diffMinutes) < 60) {
    return formatter.format(diffMinutes, 'minute');
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) {
    return formatter.format(diffHours, 'hour');
  }

  const diffDays = Math.round(diffHours / 24);
  if (Math.abs(diffDays) < 7) {
    return formatter.format(diffDays, 'day');
  }

  const diffWeeks = Math.round(diffDays / 7);
  if (Math.abs(diffWeeks) < 5) {
    return formatter.format(diffWeeks, 'week');
  }

  const diffMonths = Math.round(diffDays / 30);
  if (Math.abs(diffMonths) < 12) {
    return formatter.format(diffMonths, 'month');
  }

  const diffYears = Math.round(diffDays / 365);
  return formatter.format(diffYears, 'year');
};

const HomePage = () => {
  const { preferences, updatePreferences } = useUserPreferences();
  const [loading, setLoading] = useState(true);
  const [currentFactIndex, setCurrentFactIndex] = useState(0);
  const [versionDetailsExpanded, setVersionDetailsExpanded] = useState(false);
  const [systemStatusExpanded, setSystemStatusExpanded] = useState(false);
  const [services, setServices] = useState({
    backend: { status: 'checking', responseTime: null, version: null },
    database: { status: 'checking', responseTime: null, records: null },
    websearch: { status: 'checking', responseTime: null, resultsFound: null },
    llm: { status: 'checking', responseTime: null, model: null }
  });

  const toggleDarkMode = () => {
    updatePreferences({ theme: preferences?.theme === 'dark' ? 'light' : 'dark' });
  };

  const checkHealth = useCallback(async () => {
    const results = {};

    // Check Backend
    try {
      const start = Date.now();
      const response = await axios.get('/api/version', { timeout: 5000 });
      const responseTime = Date.now() - start;
      results.backend = {
        status: response.status === 200 ? 'healthy' : 'degraded',
        responseTime,
        version: response.data.version,
        error: null
      };
    } catch (error) {
      results.backend = {
        status: 'down',
        responseTime: null,
        version: null,
        error: error.message
      };
    }

    // Check Database
    try {
      const start = Date.now();
      const response = await axios.get('/api/health/database', { timeout: 5000 });
      const responseTime = Date.now() - start;
      results.database = {
        status: response.data.healthy ? 'healthy' : 'degraded',
        responseTime,
        records: response.data.record_count,
        error: null
      };
    } catch (error) {
      results.database = {
        status: 'down',
        responseTime: null,
        records: null,
        error: error.message
      };
    }

    // Check Web Search
    try {
      const start = Date.now();
      const response = await axios.post('/api/compliance/test-search', {
        query: 'GDPR test'
      }, { timeout: 10000 });
      const responseTime = Date.now() - start;
      results.websearch = {
        status: response.data.success ? 'healthy' : 'degraded',
        responseTime,
        resultsFound: response.data.results_count,
        error: null
      };
    } catch (error) {
      results.websearch = {
        status: 'down',
        responseTime: null,
        resultsFound: null,
        error: error.message
      };
    }

    // Check LLM
    try {
      const start = Date.now();
      const response = await axios.post('/api/compliance/test-llm', {
        prompt: 'Test'
      }, { timeout: 15000 });
      const responseTime = Date.now() - start;
      results.llm = {
        status: response.data.success ? 'healthy' : 'degraded',
        responseTime,
        model: response.data.model,
        error: null
      };
    } catch (error) {
      results.llm = {
        status: 'down',
        responseTime: null,
        model: null,
        error: error.message
      };
    }

    setServices(results);
  }, []);

  useEffect(() => {
    // Simulate loading time
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 60000); // Check every minute
    return () => clearInterval(interval);
  }, [checkHealth]);

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

  const { data: versionData, isError: versionError } = useQuery(
    VERSION_QUERY_KEY,
    fetchVersionInfo,
    {
      refetchInterval: VERSION_REFRESH_INTERVAL,
      staleTime: VERSION_REFRESH_INTERVAL / 2,
      retry: 1,
    }
  );

  const versionLabel = useMemo(() => {
    if (versionData?.version) {
      const buildNum = versionData?.buildNumber ? ` build ${versionData.buildNumber}` : '';
      return `v${versionData.version}${buildNum}`;
    }
    if (versionError) {
      return 'v--';
    }
    return 'Henter...';
  }, [versionData, versionError]);

  const changeTypeLabel = useMemo(() => {
    if (!versionData?.lastChangeType) {
      return null;
    }
    return CHANGE_TYPE_LABELS[versionData.lastChangeType] || null;
  }, [versionData]);

  const lastCommitMeta = versionData?.lastCommit;

  const lastUpdated = useMemo(() => {
    if (!lastCommitMeta?.timestamp) {
      return null;
    }
    const commitDate = new Date(lastCommitMeta.timestamp);
    if (Number.isNaN(commitDate.getTime())) {
      return null;
    }

    return {
      formatted: new Intl.DateTimeFormat('da-DK', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(commitDate),
      relative: formatRelativeTime(commitDate),
      shortHash: lastCommitMeta?.shortHash || null,
      message: lastCommitMeta?.message || null,
      author: lastCommitMeta?.author || null,
    };
  }, [lastCommitMeta]);

  const quickStartSteps = [
    {
      title: 'Lav en vurdering',
      description: 'Beskriv AI-systemet i fri tekst og få en deterministisk regelmotor-vurdering med lov-citater i marginen',
      link: '/vurdering'
    },
    {
      title: 'Registrér AI-sag',
      description: 'Opret en formel sag i ServicePortalen med automatisk e-mail til Digitalisering og IT',
      link: '/ai-sager'
    },
    {
      title: 'Slå loven op',
      description: 'Find paragraf, præcedens og afgørelser via Juridisk Research og Lov-assistent',
      link: '/research'
    }
  ];


  const getStatusIcon = (status) => {
    if (status === 'healthy') return <FaCheckCircle />;
    if (status === 'degraded') return <FaExclamationTriangle />;
    if (status === 'down') return <FaTimesCircle />;
    return <FaSpinner />;
  };

  const getServiceIcon = (serviceName) => {
    if (serviceName === 'backend') return <FaServer />;
    if (serviceName === 'database') return <FaDatabase />;
    if (serviceName === 'websearch') return <FaSearch />;
    if (serviceName === 'llm') return <FaRobot />;
    return <FaServer />;
  };

  const getServiceLabel = (serviceName) => {
    if (serviceName === 'backend') return 'Backend';
    if (serviceName === 'database') return 'Database';
    if (serviceName === 'websearch') return 'Søgning';
    if (serviceName === 'llm') return 'LLM';
    return serviceName;
  };

  return (
    <HomeContainer>
      <HeroSection>
        <HeroLayout>
          <HeroContent>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <HeroBadge>Forseti · v3 — kommunal AI-compliance</HeroBadge>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.05 }}
            >
              <HeroTitle>Forseti</HeroTitle>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.12 }}
            >
              <HeroSubtitle>
                Hver kommunal AI-vurdering bliver hjemlet i en konkret lovartikel
                — ordret citat, verificeret mod kilden, deterministisk regelmotor.
                EU AI Act, GDPR, forvaltningslov og offentlighedslov er dækket på
                tværs; sektorlove kommer i takt med jurist-input.
              </HeroSubtitle>
            </motion.div>
            <HeroActions>
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.18 }}
              >
                <CTAButton to="/vurdering">
                  Start vurdering
                  <FaArrowRight />
                </CTAButton>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.24 }}
              >
                <SecondaryCTA to="/sager">
                  <FaBalanceScale size={16} />
                  Sag-overblik
                </SecondaryCTA>
              </motion.div>
            </HeroActions>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              style={{ marginTop: '2rem' }}
            >
              <HeroLogo src="/kalundborg-logo.svg" alt="Kalundborg Kommune" />
            </motion.div>
          </HeroContent>

          <HeroSidebar>
            <VersionSection>
              <VersionHeading>
                <FaInfoCircle size={10} />
                <span>Version</span>
              </VersionHeading>
              <VersionValue>
                {versionLabel}
                {changeTypeLabel && <ChangeTypeBadge>{changeTypeLabel}</ChangeTypeBadge>}
              </VersionValue>
              <VersionMeta>
                {lastUpdated ? (
                  <>
                    {lastUpdated.relative || lastUpdated.formatted}
                  </>
                ) : (
                  versionError ? 'Ukendt' : 'Henter...'
                )}
              </VersionMeta>

              {(lastUpdated || changeTypeLabel) && (
                <>
                  <VersionDetailsButton onClick={() => setVersionDetailsExpanded(!versionDetailsExpanded)}>
                    <span>Se detaljer</span>
                    {versionDetailsExpanded ? (
                      <FaChevronUp className="chevron" />
                    ) : (
                      <FaChevronDown className="chevron" />
                    )}
                  </VersionDetailsButton>

                  <VersionDetails $isOpen={versionDetailsExpanded}>
                    {lastUpdated && (
                      <>
                        {versionData?.branch && (
                          <VersionMeta>
                            <strong>Branch:</strong> <span>{versionData.branch === 'main' ? '🏠 main' : `🔧 ${versionData.branch}`}</span>
                          </VersionMeta>
                        )}

                        <VersionMeta>
                          <strong>Opdateret:</strong> {lastUpdated.formatted}
                        </VersionMeta>

                        {(lastUpdated.shortHash || lastUpdated.message) && (
                          <VersionMeta>
                            <strong>Commit:</strong>
                            {lastUpdated.shortHash && <span> #{lastUpdated.shortHash}</span>}
                            {lastUpdated.message && (
                              <span>{lastUpdated.shortHash ? ' – ' : ''}{lastUpdated.message}</span>
                            )}
                          </VersionMeta>
                        )}

                        {lastUpdated.author && (
                          <VersionMeta>
                            <strong>Ændret af:</strong> <span className="author">{lastUpdated.author}</span>
                          </VersionMeta>
                        )}
                      </>
                    )}
                  </VersionDetails>
                </>
              )}

              <SystemStatusSection>
                <VersionHeading>
                  <FaServer size={9} />
                  <span>System Status</span>
                </VersionHeading>
                <SystemStatusGrid>
                  {Object.entries(services).map(([name, service]) => (
                    <ServiceStatus key={name} $status={service.status}>
                      <div className="service-label">
                        {getServiceIcon(name)}
                        <span>{getServiceLabel(name)}</span>
                      </div>
                      <div className="service-indicator">
                        {getStatusIcon(service.status)}
                      </div>
                    </ServiceStatus>
                  ))}
                </SystemStatusGrid>

                <SystemStatusDetailsButton onClick={() => setSystemStatusExpanded(!systemStatusExpanded)}>
                  <span>Se detaljer</span>
                  {systemStatusExpanded ? (
                    <FaChevronUp className="chevron" />
                  ) : (
                    <FaChevronDown className="chevron" />
                  )}
                </SystemStatusDetailsButton>

                <SystemStatusDetails $isOpen={systemStatusExpanded}>
                  {Object.entries(services).map(([name, service]) => (
                    <ServiceDetailCard key={name} $status={service.status}>
                      <div className="service-detail-header">
                        {getServiceIcon(name)}
                        <h5>{getServiceLabel(name)}</h5>
                      </div>
                      <div className="service-detail-content">
                        {service.responseTime !== null && (
                          <div className="detail-row">
                            <span className="label">Responstid:</span>
                            <span className="value">{service.responseTime}ms</span>
                          </div>
                        )}
                        {service.version && (
                          <div className="detail-row">
                            <span className="label">Version:</span>
                            <span className="value">{service.version}</span>
                          </div>
                        )}
                        {service.model && (
                          <div className="detail-row">
                            <span className="label">Model:</span>
                            <span className="value">{service.model}</span>
                          </div>
                        )}
                        {service.records !== null && service.records !== undefined && (
                          <div className="detail-row">
                            <span className="label">Records:</span>
                            <span className="value">{service.records}</span>
                          </div>
                        )}
                        {service.resultsFound !== null && service.resultsFound !== undefined && (
                          <div className="detail-row">
                            <span className="label">Resultater fundet:</span>
                            <span className="value">{service.resultsFound}</span>
                          </div>
                        )}
                        {service.error && (
                          <div className="error-message">
                            <strong>Fejl:</strong> {service.error}
                          </div>
                        )}
                      </div>
                    </ServiceDetailCard>
                  ))}
                </SystemStatusDetails>
              </SystemStatusSection>
            </VersionSection>
          </HeroSidebar>
        </HeroLayout>
      </HeroSection>

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

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '3rem' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <LiveNewsCard />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <ComplianceTips />
        </motion.div>
      </div>

      <NewsSection />

      <QuickStartSection>
        <QuickStartTitle>Kom Godt i Gang</QuickStartTitle>
        <p style={{ color: '#64748b', marginBottom: '2rem' }}>
          Følg disse trin for at få maksimal værdi af Forseti
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
