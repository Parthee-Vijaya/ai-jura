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
  FaExternalLinkAlt,
  FaInfoCircle,
  FaCog,
  FaChevronDown,
  FaChevronUp
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

const SectionTitle = styled.button`
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
  font-weight: 600;
  color: ${props => props.theme.layout.sidebar.muted};
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 1rem 1.5rem 0.5rem;
  margin: 2rem 0 0.5rem;
  border: none;
  border-top: 1px solid ${props => props.theme.layout.sidebar.border};
  background: transparent;
  cursor: pointer;
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    color: ${props => props.theme.layout.sidebar.hoverText};
  }

  &:first-child {
    margin-top: 0;
    border-top: none;
  }

  .chevron {
    font-size: 0.65rem;
    transition: ${props => props.theme.animations.transitionFast};
  }
`;

const CollapsibleSection = styled.div`
  max-height: ${props => props.$isOpen ? '1000px' : '0'};
  overflow: hidden;
  transition: max-height 0.3s ease-in-out;
  opacity: ${props => props.$isOpen ? '1' : '0'};
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
  padding: 1.4rem 1.5rem 1.3rem;
  border-top: 1px solid ${props => props.theme.layout.sidebar.border};
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
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

const FooterNote = styled.div`
  font-size: 0.68rem;
  line-height: 1.3;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(148, 163, 184, 0.78)'
    : 'rgba(100, 116, 139, 0.85)'};
  font-style: italic;
  letter-spacing: 0.03em;
`;

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();
  const [expandedSections, setExpandedSections] = useState({
    'viden': true,
    'indstillinger': false
  });
  const [versionDetailsExpanded, setVersionDetailsExpanded] = useState(false);

  const toggleSection = (sectionKey) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionKey]: !prev[sectionKey]
    }));
  };

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
      author: lastCommitMeta?.author || null,
    };
  }, [lastCommitMeta]);

  const menuItems = [
    {
      section: null,
      sectionKey: null,
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
      sectionKey: 'viden',
      items: [
        { path: '/videnbase', icon: FaBook, text: 'Videnbase' },
        { path: '/research', icon: FaGlobeEurope, text: 'Juridisk Research' },
        { path: '/ressourcer', icon: FaExternalLinkAlt, text: 'Relevante Links' }
      ]
    },
    {
      section: 'Indstillinger',
      sectionKey: 'indstillinger',
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
        {!collapsed && <BrandSecondary>AI-komplianceplatform</BrandSecondary>}
        </BrandContainer>
      </SidebarHeader>

      <NavContent>
        <nav>
          {menuItems.map((section, sectionIndex) => (
            <div key={sectionIndex}>
              {!collapsed && section.section && section.sectionKey ? (
                <>
                  <SectionTitle onClick={() => toggleSection(section.sectionKey)}>
                    <span>{section.section}</span>
                    {expandedSections[section.sectionKey] ? (
                      <FaChevronUp className="chevron" />
                    ) : (
                      <FaChevronDown className="chevron" />
                    )}
                  </SectionTitle>
                  <CollapsibleSection $isOpen={expandedSections[section.sectionKey]}>
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
                  </CollapsibleSection>
                </>
              ) : (
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
              )}
            </div>
          ))}
        </nav>
      </NavContent>

      {!collapsed && (
        <SidebarFooter>
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
          </VersionSection>

          <FooterNote>Kun til internt brug – Digitalisering og IT</FooterNote>
        </SidebarFooter>
      )}
    </SidebarContainer>
  );
};

export default Sidebar;
