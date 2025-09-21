import React, { useMemo } from 'react';
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
    headers: {
      'Cache-Control': 'no-cache',
    },
    cache: 'no-store',
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
  padding: 1rem 1.5rem;
  border-top: 1px solid ${props => props.theme.layout.sidebar.border};
  margin-top: auto;
  background: ${props => props.theme.layout.sidebar.badgeBackground};
  position: relative;

  .version-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;

    svg {
      flex-shrink: 0;
      opacity: 0.9;
    }

    .meta {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }

    .version {
      color: ${props => props.theme.colors.accent};
      font-weight: 700;
      font-size: 0.9rem;
      text-shadow: 0 0 6px rgba(212, 175, 55, 0.35);
      letter-spacing: 0.01em;
    }

    .change-type {
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      border-radius: 999px;
      padding: 0.15rem 0.5rem;
      background: ${props => props.theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(26, 54, 93, 0.12)'};
      color: ${props => props.theme.mode === 'dark' ? props.theme.colors.white : props.theme.colors.primary};
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
    }
  }

  .date {
    color: ${props => props.theme.layout.sidebar.muted};
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;

    .relative {
      font-size: 0.7rem;
      opacity: 0.85;
    }
  }

  .commit {
    color: ${props => props.theme.layout.sidebar.muted};
    font-size: 0.72rem;
    letter-spacing: 0.02em;
    text-transform: none;
    margin-bottom: 0.5rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .organization {
    color: ${props => props.theme.layout.sidebar.muted};
    font-style: italic;
    font-size: 0.7rem;
    line-height: 1.2;
    opacity: 0.9;
  }
`;

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();
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
        { path: '/historik', icon: FaHistory, text: 'Assessment Historik' }
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
          <div className="version-info">
            <FaInfoCircle size={12} />
            <div className="meta">
              <span className="version">{versionLabel}</span>
              {changeTypeLabel && <span className="change-type">{changeTypeLabel}</span>}
            </div>
          </div>
          <div className="date">
            {lastUpdated ? (
              <>
                <span>Sidst ændret: {lastUpdated.formatted}</span>
                {lastUpdated.relative && <span className="relative">{lastUpdated.relative}</span>}
              </>
            ) : (
              <span>{versionError ? 'Sidst ændret: ukendt' : 'Opdaterer versionsinfo...'}</span>
            )}
          </div>
          {(lastUpdated?.shortHash || lastUpdated?.message) && (
            <div className="commit">
              {lastUpdated.shortHash && <span>Commit {lastUpdated.shortHash}</span>}
              {lastUpdated.message && <span> · {lastUpdated.message}</span>}
            </div>
          )}
          <div className="organization">Kun til internt brug – Digitalisering og IT</div>
        </SidebarFooter>
      )}
    </SidebarContainer>
  );
};

export default Sidebar;
