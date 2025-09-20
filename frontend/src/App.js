import React, { useState, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import styled, { ThemeProvider, createGlobalStyle } from 'styled-components';

// Components
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import PageErrorBoundary from './components/PageErrorBoundary';
import { SectionLoader } from './components/LoadingSpinner';

// Pages
import FullAssessmentPage from './pages/FullAssessmentPage';
import DashboardPage from './pages/DashboardPage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import ResearchPage from './pages/ResearchPage';
import HistoryPage from './pages/HistoryPage';
import ResourcesPage from './pages/ResourcesPage';
import SettingsPage from './pages/SettingsPage';

// Contexts
import { UserPreferencesProvider } from './contexts/UserPreferencesContext';
import { LoadingProvider } from './contexts/LoadingContext';

// Lazy loaded pages for better performance and code splitting
const HomePage = React.lazy(() => import('./pages/HomePage'));
const QuickCheckPage = React.lazy(() => import('./pages/QuickCheckPage'));

// Theme - Enhanced Juridical Styling v0.8.0
const theme = {
  colors: {
    primary: '#1a365d',
    secondary: '#2d3748',
    accent: '#b8860b',
    success: '#2f855a',
    warning: '#d69e2e',
    danger: '#c53030',
    dark: '#1a202c',
    light: '#f7fafc',
    white: '#ffffff',
    gray: {
      50: '#f7fafc',
      100: '#edf2f7',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#a0aec0',
      500: '#718096',
      600: '#4a5568',
      700: '#2d3748',
      800: '#1a202c',
      900: '#171923'
    },
    juridical: {
      navy: '#1a365d',
      gold: '#b8860b',
      darkGold: '#9a7209',
      charcoal: '#2d3748',
      lightNavy: '#2c5282',
      // New v0.8.0 colors
      deepNavy: '#0f2238',
      midNavy: '#1a4480',
      lightGold: '#d4af37',
      bronze: '#cd7f32',
      platinum: '#e5e4e2'
    },
    gradients: {
      primary: 'linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #3182ce 100%)',
      gold: 'linear-gradient(135deg, #b8860b 0%, #d4af37 50%, #f6e05e 100%)',
      hero: 'linear-gradient(135deg, #0f2238 0%, #1a365d 25%, #2c5282 75%, #3182ce 100%)',
      card: 'linear-gradient(145deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)',
      glass: 'linear-gradient(145deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%)',
      danger: 'linear-gradient(135deg, #c53030 0%, #e53e3e 50%, #f56565 100%)'
    }
  },
  fonts: {
    main: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
  },
  borderRadius: '12px',
  borderRadiusLarge: '16px',
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 10px 10px -5px rgb(0 0 0 / 0.04)',
    glass: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
    glow: '0 0 20px rgba(26, 54, 93, 0.5)',
    focus: '0 0 0 3px rgba(26, 54, 93, 0.1)'
  },
  glass: {
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    backdropFilter: 'blur(20px)',
    borderRadius: '16px'
  },
  animations: {
    transition: '0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    transitionFast: '0.15s cubic-bezier(0.4, 0, 0.2, 1)',
    transitionSlow: '0.5s cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)'
  }
};

const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: ${props => props.theme.fonts.main};
    background-color: ${props => props.theme.colors.gray[50]};
    color: ${props => props.theme.colors.gray[900]};
    line-height: 1.6;
  }

  a {
    text-decoration: none;
    color: inherit;
  }

  button {
    cursor: pointer;
    border: none;
    outline: none;
    font-family: inherit;
  }

  input, textarea, select {
    font-family: inherit;
    outline: none;
  }
`;

const AppContainer = styled.div`
  display: flex;
  min-height: 100vh;
`;

const MainContent = styled.main`
  flex: 1;
  margin-left: ${props => props.sidebarCollapsed ? '80px' : '250px'};
  padding: 20px;
  transition: margin-left 0.3s ease;

  @media (max-width: 768px) {
    margin-left: 0;
    padding: 10px;
  }
`;

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <UserPreferencesProvider>
          <LoadingProvider>
            <ThemeProvider theme={theme}>
            <GlobalStyle />
            <Router>
              <AppContainer>
                <PageErrorBoundary title="Navigation fejl" message="Der opstod en fejl i sidebar. Siden kan stadig fungere.">
                  <Sidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
                </PageErrorBoundary>
                <MainContent sidebarCollapsed={sidebarCollapsed}>
                  <PageErrorBoundary title="Navbar fejl" message="Der opstod en fejl i navigation. Siden kan stadig fungere.">
                    <Navbar />
                  </PageErrorBoundary>
                  <PageErrorBoundary title="Side indlæsningsfejl" message="Der opstod en fejl ved indlæsning af siden.">
                    <Suspense fallback={<SectionLoader text="Indlæser side..." />}>
                      <Routes>
                      <Route path="/" element={<HomePage />} />
                      <Route path="/hurtig-tjek" element={<QuickCheckPage />} />
                      <Route path="/fuld-vurdering" element={<FullAssessmentPage />} />
                      <Route path="/dashboard" element={<DashboardPage />} />
                      <Route path="/historik" element={<HistoryPage />} />
                      <Route path="/videnbase" element={<KnowledgeBasePage />} />
                      <Route path="/research" element={<ResearchPage />} />
                      <Route path="/ressourcer" element={<ResourcesPage />} />
                      <Route path="/indstillinger" element={<SettingsPage />} />
                      </Routes>
                    </Suspense>
                  </PageErrorBoundary>
                </MainContent>
              </AppContainer>
              <Toaster
                position="top-right"
                toastOptions={{
                  duration: 4000,
                  style: {
                    background: '#363636',
                    color: '#fff',
                  },
                }}
              />
            </Router>
            </ThemeProvider>
          </LoadingProvider>
        </UserPreferencesProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;