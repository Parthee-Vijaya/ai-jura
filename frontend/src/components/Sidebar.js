import React, { useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { useQuery } from 'react-query';
import {
  FaHome,
  FaSearch,
  FaClipboardList,
  FaChartBar,
  FaHistory,
  FaBook,
  FaGlobeEurope,
  FaBalanceScale,
  FaChevronLeft,
  FaChevronRight,
  FaChevronDown,
  FaChevronUp,
  FaExternalLinkAlt,
  FaInfoCircle,
  FaCog
} from 'react-icons/fa';

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

const fetchVersionInfo = async () => {
  const response = await fetch(buildApiUrl('/api/version'), {
    cache: 'no-store',
    headers: {
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache',
    },
  });
  if (!response.ok) {
    throw new Error('Kunne ikke hente versionsdata');
  }
  return response.json();
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

const SidebarContainer = styled.aside`
  width: ${props => props.collapsed ? '80px' : '250px'};
  background: ${props => props.theme.layout.sidebar.background};
  color: ${props => props.theme.layout.sidebar.text};
  border-right: 1px solid ${props => props.theme.layout.sidebar.border};
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  padding: 2rem 0 0;
  overflow-y: auto;
  transition: ${props => props.theme.animations.transition};
  z-index: 1000;
  display: flex;
  flex-direction: column;
  box-shadow: ${props => props.theme.shadows.glass};

  @media (max-width: 768px) {
    transform: translateX(${props => props.collapsed ? '-100%' : '0'});
    width: 250px;
  }
`;

const SidebarHeader = styled.div`
  position: relative;
  padding: 0 1.5rem 2rem;
  border-bottom: 1px solid ${props => props.theme.layout.sidebar.border};
  margin-bottom: 2rem;
`;

const BrandContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: ${props => props.$collapsed ? 'center' : 'flex-start'};
  text-align: ${props => props.$collapsed ? 'center' : 'left'};
  gap: ${props => props.$collapsed ? '0.35rem' : '0.25rem'};
  padding: ${props => props.$collapsed ? '0.5rem 0' : '0'};
`;

const BrandPrimary = styled.span`
  font-size: ${props => props.$collapsed ? '1rem' : '1.1rem'};
  font-weight: 700;
  letter-spacing: ${props => props.$collapsed ? '0.18em' : '0.04em'};
  text-transform: ${props => props.$collapsed ? 'uppercase' : 'none'};
  color: ${props => props.theme.layout.sidebar.text};
`;

const BrandSecondary = styled.span`
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: ${props => props.theme.layout.sidebar.muted};
  font-weight: 600;
`;

const NavList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const NavItem = styled.li`
  margin-bottom: 0.25rem;
`;

const NavLink = styled(Link)`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.5rem;
  color: ${props => props.theme.layout.sidebar.muted};
  text-decoration: none;
  transition: ${props => props.theme.animations.transition};
  border-left: 3px solid transparent;
  position: relative;
  overflow: hidden;

  &:hover {
    background: ${props => props.theme.layout.sidebar.hoverBackground};
    color: ${props => props.theme.layout.sidebar.hoverText};
    transform: translateX(4px);

    .icon {
      transform: scale(1.1);
      color: ${props => props.theme.colors.accent};
    }
  }

  &.active {
    background: ${props => props.theme.layout.sidebar.activeBackground};
    color: ${props => props.theme.layout.sidebar.activeText};
    border-left-color: ${props => props.theme.layout.sidebar.activeBorder};
    box-shadow: ${props => props.theme.shadows.md};

    .icon {
      color: ${props => props.theme.colors.accent};
    }
  }

  .icon {
    width: 18px;
    height: 18px;
    transition: ${props => props.theme.animations.spring};
    color: inherit;
  }

  .text {
    font-size: 0.875rem;
    font-weight: 500;
    position: relative;
    z-index: 1;
  }
`;

const SectionTitle = styled.h3`
  font-size: 0.75rem;
  font-weight: 600;
  color: ${props => props.theme.layout.sidebar.muted};
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 1rem 1.5rem 0.5rem;
  margin: 2rem 0 0.5rem;
  border-top: 1px solid ${props => props.theme.layout.sidebar.border};

  &:first-child {
    margin-top: 0;
    border-top: none;
  }
`;

const ToggleButton = styled.button`
  position: absolute;
  top: 1rem;
  right: 0.75rem;
  background: transparent;
  color: ${props => props.theme.layout.sidebar.muted};
  border: none;
  border-radius: 4px;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.75rem;
  transition: all 0.2s ease;
  z-index: 1001;
  opacity: 0.6;

  &:hover {
    background: ${props => props.theme.layout.sidebar.hoverBackground};
    color: ${props => props.theme.layout.sidebar.hoverText};
    opacity: 1;
    transform: translateX(-2px);
  }

  @media (max-width: 768px) {
    top: 1rem;
    right: 1rem;
    opacity: 0.8;
  }
`;

const NavContent = styled.div`
  flex: 1;
  overflow-y: auto;
`;

const SidebarFooter = styled.div`
  padding: 1.25rem 1.5rem 1.5rem;
  border-top: 1px solid ${props => props.theme.layout.sidebar.border};
  margin-top: auto;
  background: ${props => props.theme.mode === 'dark'
    ? 'linear-gradient(180deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.85) 100%)'
    : 'linear-gradient(180deg, rgba(241,245,249,0.8) 0%, rgba(226,232,240,0.8) 100%)'};
  position: relative;

  .organization {
    color: ${props => props.theme.layout.sidebar.muted};
    font-style: italic;
    font-size: 0.7rem;
    line-height: 1.2;
    opacity: 0.9;
    margin-top: 1rem;
  }
`;

const VersionPanel = styled.div`
  background: ${props => props.theme.mode === 'dark'
    ? 'linear-gradient(150deg, rgba(17, 24, 39, 0.95), rgba(30, 41, 59, 0.85))'
    : 'linear-gradient(150deg, rgba(255, 255, 255, 0.95), rgba(244, 247, 252, 0.9))'};
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.25)'
    : 'rgba(148, 163, 184, 0.4)'};
  border-radius: ${props => props.theme.borderRadiusLarge};
  box-shadow: ${props => props.theme.shadows.glass};
  padding: 1.1rem 1.15rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  position: relative;
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: ${props => props.theme.mode === 'dark'
      ? 'radial-gradient(circle at top right, rgba(59,130,246,0.18), transparent 55%)'
      : 'radial-gradient(circle at top right, rgba(59,130,246,0.18), transparent 45%)'};
    pointer-events: none;
  }

  > * {
    position: relative;
    z-index: 1;
  }
`;

const VersionSummary = styled.button`
  display: flex;
  align-items: center;
  width: 100%;
  gap: 0.9rem;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 0;
  text-align: left;
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    transform: translateY(-1px);
  }
`;

const SummaryIcon = styled.div`
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(59, 130, 246, 0.25)'
    : 'rgba(37, 99, 235, 0.12)'};
  color: ${props => props.theme.mode === 'dark'
    ? props.theme.colors.white
    : props.theme.colors.primary};
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
`;

const VersionText = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;

  .title {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-weight: 600;
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(226, 232, 240, 0.75)'
      : props.theme.layout.sidebar.muted};
  }

  .value {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1rem;
    font-weight: 700;
    color: ${props => props.theme.mode === 'dark'
      ? props.theme.colors.white
      : props.theme.colors.primary};
    letter-spacing: 0.02em;
  }
`;

const ChangeBadge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.24)'
    : 'rgba(37, 99, 235, 0.18)'};
  color: ${props => props.theme.mode === 'dark'
    ? props.theme.colors.white
    : props.theme.colors.primary};
`;

const SummaryChevron = styled.div`
  width: 26px;
  height: 26px;
  border-radius: 9px;
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.28)'
    : 'rgba(148, 163, 184, 0.35)'};
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(30, 41, 59, 0.7)'
    : 'rgba(255, 255, 255, 0.8)'};
  color: ${props => props.theme.mode === 'dark'
    ? props.theme.colors.white
    : props.theme.colors.primary};
`;

const VersionDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-top: 0.3rem;
  padding: 0.85rem 0.95rem;
  border-radius: ${props => props.theme.borderRadius};
  background: ${props => props.theme.mode === 'dark'
    ? 'rgba(15, 23, 42, 0.72)'
    : 'rgba(248, 250, 252, 0.92)'};
  border: 1px solid ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.2)'
    : 'rgba(148, 163, 184, 0.3)'};
  font-size: 0.75rem;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(226, 232, 240, 0.9)'
    : props.theme.layout.sidebar.muted};
`;

const MetaRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.2rem;

  .label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-weight: 600;
    color: ${props => props.theme.mode === 'dark'
      ? 'rgba(148, 163, 184, 0.65)'
      : 'rgba(100, 116, 139, 0.9)'};
  }

  .value {
    font-size: 0.75rem;
    line-height: 1.35;
    color: inherit;
  }

  .relative {
    font-size: 0.7rem;
    opacity: 0.8;
  }
`;

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();
  const [showVersionDetails, setShowVersionDetails] = useState(false);
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
      return `v${versionData.version}`;
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
    };
  }, [lastCommitMeta]);

  const menuItems = [
    {
      section: null,
      items: [
        { path: '/', icon: FaHome, text: 'Forside' },
        { path: '/hurtig-tjek', icon: FaSearch, text: 'Hurtig Tjek' },
        { path: '/ai-sager', icon: FaBalanceScale, text: 'AI Sager' },
        { path: '/fuld-vurdering', icon: FaClipboardList, text: 'Compliance Control' },
        { path: '/dashboard', icon: FaChartBar, text: 'Dashboard' },
        { path: '/historik', icon: FaHistory, text: 'Vurderingshistorik' }
      ]
    },
    {
      section: 'Viden & Research',
      items: [
        { path: '/videnbase', icon: FaBook, text: 'Videnbase' },
        { path: '/research', icon: FaGlobeEurope, text: 'Juridisk Research' },
        { path: '/ressourcer', icon: FaExternalLinkAlt, text: 'Relevante Links' }
      ]
    },
    {
      section: 'Indstillinger',
      items: [
        { path: '/indstillinger', icon: FaCog, text: 'Indstillinger' }
      ]
    }
  ];

  return (
    <SidebarContainer collapsed={collapsed}>
      <SidebarHeader>
        <ToggleButton onClick={onToggle}>
          {collapsed ? <FaChevronRight /> : <FaChevronLeft />}
        </ToggleButton>
        <BrandContainer $collapsed={collapsed}>
          <BrandPrimary $collapsed={collapsed}>
            {collapsed ? 'JD' : 'Project Judge Dredd'}
          </BrandPrimary>
          {!collapsed && <BrandSecondary>AI Compliance Platform</BrandSecondary>}
        </BrandContainer>
      </SidebarHeader>

      <NavContent>
        <nav>
          {menuItems.map((section, sectionIndex) => (
            <div key={sectionIndex}>
              {!collapsed && section.section && <SectionTitle>{section.section}</SectionTitle>}
              <NavList>
                {section.items.map((item, itemIndex) => (
                  <NavItem key={itemIndex}>
                    <NavLink
                      to={item.path}
                      className={location.pathname === item.path ? 'active' : ''}
                      title={collapsed ? item.text : ''}
                    >
                      <item.icon className="icon" />
                      {!collapsed && <span className="text">{item.text}</span>}
                    </NavLink>
                  </NavItem>
                ))}
              </NavList>
            </div>
          ))}
        </nav>
      </NavContent>

      {!collapsed && (
        <SidebarFooter>
          <VersionPanel>
            <VersionSummary
              onClick={() => setShowVersionDetails(prev => !prev)}
              aria-label={showVersionDetails ? 'Skjul versionsdetaljer' : 'Vis versionsdetaljer'}
              aria-expanded={showVersionDetails}
            >
              <SummaryIcon>
                <FaInfoCircle size={14} />
              </SummaryIcon>
              <VersionText>
                <span className="title">Platformsversion</span>
                <span className="value">
                  {versionLabel}
                  {changeTypeLabel && <ChangeBadge>{changeTypeLabel}</ChangeBadge>}
                </span>
              </VersionText>
              <SummaryChevron>
                {showVersionDetails ? <FaChevronUp size={12} /> : <FaChevronDown size={12} />}
              </SummaryChevron>
            </VersionSummary>

            {showVersionDetails && (
              <VersionDetails>
                <MetaRow>
                  <span className="label">Sidst opdateret</span>
                  {lastUpdated ? (
                    <span className="value">
                      {lastUpdated.formatted}
                      {lastUpdated.relative && (
                        <span className="relative">{lastUpdated.relative}</span>
                      )}
                    </span>
                  ) : (
                    <span className="value">
                      {versionError ? 'Ukendt' : 'Opdaterer versionsinfo...'}
                    </span>
                  )}
                </MetaRow>

                {(lastUpdated?.shortHash || lastUpdated?.message) && (
                  <MetaRow>
                    <span className="label">Seneste commit</span>
                    <span className="value">
                      {lastUpdated.shortHash && <span>#{lastUpdated.shortHash}</span>}
                      {lastUpdated.message && <span> – {lastUpdated.message}</span>}
                    </span>
                  </MetaRow>
                )}
              </VersionDetails>
            )}
          </VersionPanel>

          <div className="organization">Kun til internt brug – Digitalisering og IT</div>
        </SidebarFooter>
      )}
    </SidebarContainer>
  );
};

export default Sidebar;
