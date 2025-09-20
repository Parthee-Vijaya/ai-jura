import React from 'react';
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
  FaGavel,
  FaChevronLeft,
  FaChevronRight,
  FaExternalLinkAlt,
  FaInfoCircle,
  FaCog
} from 'react-icons/fa';

const SidebarContainer = styled.aside`
  width: ${props => props.collapsed ? '80px' : '250px'};
  background: rgba(23, 25, 35, 0.95);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  color: ${props => props.theme.colors.white};
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

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(180deg, rgba(26, 54, 93, 0.1) 0%, rgba(45, 55, 72, 0.05) 100%);
    pointer-events: none;
  }

  @media (max-width: 768px) {
    transform: translateX(${props => props.collapsed ? '-100%' : '0'});
    width: 250px;
  }
`;

const SidebarHeader = styled.div`
  padding: 0 1.5rem 2rem;
  border-bottom: 1px solid ${props => props.theme.colors.gray[700]};
  margin-bottom: 2rem;

  .logo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 1.25rem;
    font-weight: 700;
    color: ${props => props.theme.colors.white};
  }

  .subtitle {
    font-size: 0.75rem;
    color: ${props => props.theme.colors.gray[400]};
    margin-top: 0.25rem;
  }
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
  color: ${props => props.theme.colors.gray[300]};
  text-decoration: none;
  transition: ${props => props.theme.animations.transition};
  border-left: 3px solid transparent;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(255, 255, 255, 0.05);
    transform: translateX(-100%);
    transition: ${props => props.theme.animations.transition};
  }

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: ${props => props.theme.colors.white};
    transform: translateX(4px);

    &::before {
      transform: translateX(0);
    }

    .icon {
      transform: scale(1.1);
      color: ${props => props.theme.colors.juridical.lightGold};
    }
  }

  &.active {
    background: ${props => props.theme.colors.gradients.primary};
    color: ${props => props.theme.colors.white};
    border-left-color: ${props => props.theme.colors.juridical.lightGold};
    box-shadow: ${props => props.theme.shadows.md};

    .icon {
      color: ${props => props.theme.colors.juridical.lightGold};
    }
  }

  .icon {
    width: 18px;
    height: 18px;
    transition: ${props => props.theme.animations.spring};
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
  color: ${props => props.theme.colors.gray[500]};
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 1rem 1.5rem 0.5rem;
  margin: 2rem 0 0.5rem;
  border-top: 1px solid ${props => props.theme.colors.gray[700]};

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
  color: ${props => props.theme.colors.gray[400]};
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
    background: ${props => props.theme.colors.gray[700]};
    color: ${props => props.theme.colors.gray[200]};
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
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: auto;
  background: rgba(26, 32, 44, 0.8);
  backdrop-filter: blur(10px);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: ${props => props.theme.colors.gradients.glass};
    opacity: 0.3;
  }

  > * {
    position: relative;
    z-index: 1;
  }

  .version-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;

    .version {
      color: ${props => props.theme.colors.juridical.lightGold};
      font-weight: 700;
      font-size: 0.875rem;
      text-shadow: 0 0 10px rgba(212, 175, 55, 0.5);
    }
  }

  .date {
    color: ${props => props.theme.colors.gray[300]};
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .organization {
    color: ${props => props.theme.colors.gray[300]};
    font-style: italic;
    font-size: 0.7rem;
    line-height: 1.2;
    opacity: 0.9;
  }
`;

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();

  const menuItems = [
    {
      section: 'Hovedfunktioner',
      items: [
        { path: '/', icon: FaHome, text: 'Forside' },
        { path: '/hurtig-tjek', icon: FaSearch, text: 'Hurtig Tjek' },
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
        <div className="logo">
          <FaGavel size={20} />
          {!collapsed && 'Project Judge Dredd'}
        </div>
        {!collapsed && <div className="subtitle">Compliance Control Platform</div>}
      </SidebarHeader>

      <NavContent>
        <nav>
          {menuItems.map((section, sectionIndex) => (
            <div key={sectionIndex}>
              {!collapsed && <SectionTitle>{section.section}</SectionTitle>}
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
            <span className="version">v0.7.9</span>
          </div>
          <div className="date">Sidst ændret: Oktober 2025</div>
          <div className="organization">Kun til internt brug Digitalisering og IT Kalundborg</div>
        </SidebarFooter>
      )}
    </SidebarContainer>
  );
};

export default Sidebar;