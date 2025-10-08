import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { FaSearch, FaSun, FaMoon } from 'react-icons/fa';
import { useUserPreferences } from '../contexts/UserPreferencesContext';

const NavbarContainer = styled.nav`
  background: ${props => props.theme.layout.nav.background};
  padding: 1rem 2rem;
  border-bottom: 1px solid ${props => props.theme.layout.nav.border};
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  color: ${props => props.theme.layout.nav.text};
  transition: ${props => props.theme.animations.transition};
`;

const NavLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
`;

const NavBrand = styled(Link)`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
  color: ${props => props.theme.layout.nav.text};
`;

const Logo = styled.img`
  max-width: 150px;
  height: auto;
  transition: ${props => props.theme.animations.transition};

  @media (max-width: 768px) {
    max-width: 120px;
  }
`;

const BrandText = styled.div`
  display: flex;
  flex-direction: column;
  line-height: 1.1;

  span:first-child {
    font-size: 1.05rem;
    font-weight: 700;
    color: ${props => props.theme.layout.nav.text};
  }

  span:last-child {
    font-size: 0.75rem;
    font-weight: 500;
    color: ${props => props.theme.colors.textMuted};
    letter-spacing: 0.02em;
  }
`;

const NavCenter = styled.div`
  display: flex;
  align-items: center;
  flex: 1;
  justify-content: center;
  max-width: 420px;
  margin: 0 2rem;
`;

const SearchContainer = styled.div`
  position: relative;
  width: 100%;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 0.55rem 1rem 0.55rem 2.5rem;
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 10px;
  background: ${props => props.theme.colors.inputBackground};
  font-size: 0.9rem;
  color: ${props => props.theme.colors.text};
  transition: ${props => props.theme.animations.transitionFast};

  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.primary};
    box-shadow: ${props => props.theme.shadows.focus};
  }

  &::placeholder {
    color: ${props => props.theme.colors.textMuted};
  }
`;

const SearchIcon = styled.div`
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: ${props => props.theme.colors.textMuted};
  pointer-events: none;
`;

const NavActions = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  color: ${props => props.theme.colors.textMuted};
`;

const ThemeToggleButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: ${props => props.theme.colors.surfaceAlt};
  color: ${props => props.theme.colors.text};
  border: 1px solid ${props => props.theme.colors.border};
  transition: ${props => props.theme.animations.transitionFast};

  &:hover {
    transform: translateY(-1px);
    box-shadow: ${props => props.theme.shadows.sm};
  }
`;

const Navbar = () => {
  const [searchValue, setSearchValue] = useState('');
  const { preferences, updatePreference } = useUserPreferences();
  const isDark = preferences?.theme === 'dark';

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchValue.trim()) {
      console.log('Søger efter:', searchValue);
    }
  };

  const handleThemeToggle = () => {
    updatePreference('theme', isDark ? 'light' : 'dark');
  };

  return (
    <NavbarContainer>
      <NavLeft>
        <NavBrand to="/">
          <Logo
            src="/kalundborg-logo.svg"
            alt="Kalundborg Kommune"
          />
          <BrandText>
            <span>Project Judge Dredd</span>
            <span>AI-komplianceplatform</span>
          </BrandText>
        </NavBrand>
      </NavLeft>

      <NavCenter>
        <SearchContainer>
          <form onSubmit={handleSearchSubmit}>
            <SearchIcon>
              <FaSearch size={14} />
            </SearchIcon>
            <SearchInput
              type="text"
              placeholder="Søg i platformen..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
            />
          </form>
        </SearchContainer>
      </NavCenter>

      <NavActions>
        <ThemeToggleButton onClick={handleThemeToggle} aria-label="Skift tema">
          {isDark ? <FaSun size={16} /> : <FaMoon size={16} />}
        </ThemeToggleButton>
      </NavActions>
    </NavbarContainer>
  );
};

export default Navbar;
