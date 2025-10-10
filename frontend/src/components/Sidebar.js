import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';
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
  FaCog,
  FaChevronDown,
  FaChevronUp
} from 'react-icons/fa';

const NAVIGATION_ID = 'sidebar-navigation';

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

const FooterNote = styled.div`
  font-size: 0.68rem;
  line-height: 1.3;
  color: ${props => props.theme.mode === 'dark'
    ? 'rgba(255, 255, 255, 0.9)'
    : 'rgba(255, 255, 255, 0.95)'};
  font-style: italic;
  letter-spacing: 0.03em;
`;

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();
  const [expandedSections, setExpandedSections] = useState({
    'viden': true,
    'indstillinger': false
  });
  const sidebarRef = useRef(null);
  const [isMobileView, setIsMobileView] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.matchMedia('(max-width: 768px)').matches;
  });

  const toggleSection = (sectionKey) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionKey]: !prev[sectionKey]
    }));
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    const mediaQuery = window.matchMedia('(max-width: 768px)');
    const handleChange = (event) => setIsMobileView(event.matches);

    setIsMobileView(mediaQuery.matches);
    mediaQuery.addEventListener('change', handleChange);

    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    const sidebarNode = sidebarRef.current;
    if (!sidebarNode) {
      return undefined;
    }

    const shouldTrapFocus = !collapsed && isMobileView;
    if (!shouldTrapFocus) {
      return undefined;
    }

    const focusableSelectors = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"]), input, select, textarea';
    const focusableElements = Array.from(sidebarNode.querySelectorAll(focusableSelectors))
      .filter((element) => !element.hasAttribute('aria-hidden') && element.offsetParent !== null);

    if (!focusableElements.length) {
      return undefined;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onToggle();
        return;
      }

      if (event.key !== 'Tab') {
        return;
      }

      if (event.shiftKey) {
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else if (document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    const handleFocusIn = (event) => {
      if (!sidebarNode.contains(event.target)) {
        firstElement.focus();
      }
    };

    firstElement.focus();

    sidebarNode.addEventListener('keydown', handleKeyDown);
    document.addEventListener('focusin', handleFocusIn);

    return () => {
      sidebarNode.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('focusin', handleFocusIn);
    };
  }, [collapsed, isMobileView, onToggle]);

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

  const toggleLabel = collapsed ? 'Åbn navigation' : 'Luk navigation';

  return (
    <SidebarContainer
      ref={sidebarRef}
      collapsed={collapsed}
      role="navigation"
      aria-label="Primær navigation"
      aria-hidden={collapsed && isMobileView ? 'true' : 'false'}
    >
      <SidebarHeader>
        <ToggleButton
          type="button"
          onClick={onToggle}
          aria-label={toggleLabel}
          aria-expanded={!collapsed}
          aria-controls={NAVIGATION_ID}
        >
          {collapsed ? <FaChevronRight /> : <FaChevronLeft />}
        </ToggleButton>
        <BrandContainer $collapsed={collapsed}>
          <BrandPrimary $collapsed={collapsed}>
            {collapsed ? 'JD' : 'Project Judge Dredd'}
          </BrandPrimary>
        {!collapsed && <BrandSecondary>AI-komplianceplatform</BrandSecondary>}
        </BrandContainer>
      </SidebarHeader>

      <NavContent id={NAVIGATION_ID}>
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
          <FooterNote>Kun til internt brug – Digitalisering og IT</FooterNote>
        </SidebarFooter>
      )}
    </SidebarContainer>
  );
};

export default Sidebar;
