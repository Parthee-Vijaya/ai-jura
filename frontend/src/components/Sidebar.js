import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import {
  FaHome,
  FaClipboardList,
  FaBook,
  FaGlobeEurope,
  FaBalanceScale,
  FaChevronLeft,
  FaChevronRight,
  FaExternalLinkAlt,
  FaCog,
  FaChevronDown,
  FaChevronUp,
  FaRobot,
  FaGavel
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
  padding: 1.75rem 0 0;
  overflow-y: auto;
  transition: ${props => props.theme.animations.transition};
  z-index: 1000;
  display: flex;
  flex-direction: column;
  font-family: ${props => props.theme.fonts.sans};

  @media (max-width: 768px) {
    transform: translateX(${props => props.collapsed ? '-100%' : '0'});
    width: 250px;
  }
`;

const SidebarHeader = styled.div`
  position: relative;
  padding: 0 1.25rem 1.5rem;
  border-bottom: 1px solid ${props => props.theme.layout.sidebar.border};
  margin-bottom: 1.25rem;
`;

const BrandContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: ${props => props.$collapsed ? 'center' : 'flex-start'};
  text-align: ${props => props.$collapsed ? 'center' : 'left'};
  gap: ${props => props.$collapsed ? '0.35rem' : '0.2rem'};
  padding: ${props => props.$collapsed ? '0.5rem 0' : '0'};
`;

const BrandPrimary = styled.span`
  font-family: ${props => props.theme.fonts.display};
  font-size: ${props => props.$collapsed ? '1.1rem' : '1.4rem'};
  font-weight: 700;
  letter-spacing: -0.02em;
  color: ${props => props.theme.layout.sidebar.text};
  display: inline-flex;
  align-items: baseline;
  gap: 4px;

  .brand-dot {
    color: ${props => props.theme.colors.primary};
    font-weight: 800;
  }

  .brand-version {
    font-family: ${props => props.theme.fonts.sans};
    font-size: 0.6rem;
    font-weight: 600;
    color: ${props => props.theme.layout.sidebar.muted};
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-left: 4px;
  }
`;

const BrandSecondary = styled.span`
  font-family: ${props => props.theme.fonts.sans};
  font-size: 0.65rem;
  letter-spacing: 0.14em;
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
  gap: 0.7rem;
  padding: 0.5rem 1.25rem;
  margin: 0 0.5rem;
  border-radius: 5px;
  color: ${props => props.theme.layout.sidebar.muted};
  text-decoration: none;
  transition: background-color ${props => props.theme.animations.transitionFast},
              color ${props => props.theme.animations.transitionFast};
  border-left: 2px solid transparent;
  position: relative;

  &:hover {
    background: ${props => props.theme.layout.sidebar.hoverBackground};
    color: ${props => props.theme.layout.sidebar.hoverText};
  }

  &.active {
    background: ${props => props.theme.layout.sidebar.activeBackground};
    color: ${props => props.theme.layout.sidebar.activeText};
    font-weight: 500;

    .icon {
      color: ${props => props.theme.layout.sidebar.activeText};
    }
  }

  .icon {
    width: 14px;
    height: 14px;
    color: inherit;
    flex-shrink: 0;
  }

  .text {
    font-family: ${props => props.theme.fonts.sans};
    font-size: 0.85rem;
    font-weight: 500;
    line-height: 1.4;
  }
`;

const SectionTitle = styled.button`
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: ${props => props.theme.fonts.sans};
  font-size: 0.66rem;
  font-weight: 600;
  color: ${props => props.theme.layout.sidebar.muted};
  text-transform: uppercase;
  letter-spacing: 0.12em;
  padding: 0.5rem 1.25rem 0.35rem;
  margin: 1.25rem 0 0.25rem;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    color: ${props => props.theme.colors.ink};
  }

  &:first-child {
    margin-top: 0.25rem;
  }

  .chevron {
    font-size: 0.58rem;
    transition: ${props => props.theme.animations.transitionFast};
    opacity: 0.6;
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
  padding: 1.1rem 1.25rem 1.1rem;
  border-top: 1px solid ${props => props.theme.layout.sidebar.border};
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
`;

const FooterNote = styled.div`
  font-family: ${props => props.theme.fonts.sans};
  font-size: 0.7rem;
  line-height: 1.45;
  color: ${props => props.theme.colors.inkFaded};
  font-style: italic;
  letter-spacing: 0.02em;
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
        { path: '/vurdering', icon: FaClipboardList, text: 'Vurdering' },
        { path: '/ai-sager', icon: FaBalanceScale, text: 'AI Sager' }
      ]
    },
    {
      section: 'Viden & Research',
      sectionKey: 'viden',
      items: [
        { path: '/videnbase', icon: FaBook, text: 'Videnbase' },
        { path: '/ai-losninger', icon: FaRobot, text: 'AI Løsninger' },
        { path: '/research', icon: FaGlobeEurope, text: 'Juridisk Research' },
        { path: '/lov-assistent', icon: FaGavel, text: 'Lov Assistent' },
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
            {collapsed ? (
              <>H<span className="brand-dot">.</span></>
            ) : (
              <>Hjemmel<span className="brand-dot">.</span><span className="brand-version">v3</span></>
            )}
          </BrandPrimary>
          {!collapsed && <BrandSecondary>AI-kompliance · Kalundborg</BrandSecondary>}
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
