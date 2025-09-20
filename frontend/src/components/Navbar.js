import React, { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import styled from 'styled-components';
import { FaGavel, FaSearch } from 'react-icons/fa';

const NavbarContainer = styled.nav`
  background: white;
  padding: 1rem 2rem;
  border-bottom: 1px solid ${props => props.theme.colors.gray[200]};
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
`;

const NavLeft = styled.div`
  display: flex;
  align-items: center;
`;

const NavBrand = styled(Link)`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;

  h1 {
    color: ${props => props.theme.colors.primary};
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
  }

  .brand-icon {
    color: ${props => props.theme.colors.juridical.gold};
  }
`;

const NavCenter = styled.div`
  display: flex;
  align-items: center;
  flex: 1;
  justify-content: center;
  max-width: 400px;
  margin: 0 2rem;
`;

const SearchContainer = styled.div`
  position: relative;
  width: 100%;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 0.5rem 1rem 0.5rem 2.5rem;
  border: 1px solid ${props => props.theme.colors.gray[300]};
  border-radius: 6px;
  background: white;
  font-size: 0.875rem;

  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.primary};
  }

  &::placeholder {
    color: ${props => props.theme.colors.gray[500]};
  }
`;

const SearchIcon = styled.div`
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: ${props => props.theme.colors.gray[400]};
  pointer-events: none;
`;


const NavActions = styled.div`
  display: flex;
  align-items: center;
  color: ${props => props.theme.colors.gray[600]};
  font-size: 0.875rem;
`;

const Navbar = () => {
  const [searchValue, setSearchValue] = useState('');



  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchValue.trim()) {
      console.log('Søger efter:', searchValue);
    }
  };


  return (
    <NavbarContainer>
      <NavLeft>
        <NavBrand to="/">
          <FaGavel size={20} className="brand-icon" />
          <h1>Judge Dredd</h1>
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
              placeholder="Søg..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
            />
          </form>
        </SearchContainer>
      </NavCenter>

      <NavActions>
        Kalundborg Kommune
      </NavActions>
    </NavbarContainer>
  );
};

export default Navbar;