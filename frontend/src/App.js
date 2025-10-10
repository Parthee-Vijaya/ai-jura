import React, { useState, Suspense, useMemo, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import styled, { ThemeProvider, createGlobalStyle } from 'styled-components';

// Theme
import { lightTheme, darkTheme } from './theme';

// Components
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import PageErrorBoundary from './components/PageErrorBoundary';
import { SectionLoader } from './components/LoadingSpinner';

// Contexts
import { UserPreferencesProvider, useUserPreferences } from './contexts/UserPreferencesContext';
import { LoadingProvider } from './contexts/LoadingContext';

// Lazy loaded pages - Optimized code splitting
const HomePage = React.lazy(() => import('./pages/HomePage'));
const QuickCheckPage = React.lazy(() => import('./pages/QuickCheckPage'));
const FullAssessmentPage = React.lazy(() => import('./pages/FullAssessmentPage'));
const DashboardPage = React.lazy(() => import('./pages/DashboardPage'));
const KnowledgeBasePage = React.lazy(() => import('./pages/KnowledgeBasePage'));
const ResearchPage = React.lazy(() => import('./pages/ResearchPage'));
const HistoryPage = React.lazy(() => import('./pages/HistoryPage'));
const ResourcesPage = React.lazy(() => import('./pages/ResourcesPage'));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage'));
const AICasesPage = React.lazy(() => import('./pages/AICasesPage'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

// Theme is now imported from './theme'

const GlobalStyle = createGlobalStyle`
  :root {
    --kalundborg-primary: #A03612;
    --kalundborg-primary-dark: #7d2b0e;
    --kalundborg-primary-light: #C94416;
    --kalundborg-primary-rgb: 160, 54, 18;
  }

  html {
    scroll-behavior: smooth;
  }

  body {
    margin: 0;
    font-family: ${props => props.theme.fonts.main};
    background-color: ${props => props.theme.colors.background};
    color: ${props => props.theme.colors.text};
    line-height: 1.6;
    transition: background-color 0.3s ease, color 0.3s ease;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  a {
    text-decoration: none;
    color: #A03612;
    transition: color ${props => props.theme.animations.transitionFast};

    &:hover {
      color: #7d2b0e;
    }

    &:focus-visible {
      outline: 2px solid #A03612;
      outline-offset: 2px;
      border-radius: 2px;
    }
  }

  button {
    cursor: pointer;
    border: none;
    outline: none;
    font-family: inherit;
    background: none;

    &:focus-visible {
      outline: 2px solid #A03612;
      outline-offset: 2px;
      box-shadow: 0 0 0 3px rgba(160, 54, 18, 0.18);
    }
  }

  input, textarea, select {
    font-family: inherit;
    outline: none;
    transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
    background-color: ${props => props.theme.colors.inputBackground};
    color: ${props => props.theme.colors.text};
    border: 1px solid ${props => props.theme.colors.border};

    &:focus {
      border-color: #A03612;
      box-shadow: 0 0 0 3px rgba(160, 54, 18, 0.12);
    }
  }

  ::selection {
    background: #A03612;
    color: white;
  }

  ::-moz-selection {
    background: #A03612;
    color: white;
  }

  ::-webkit-scrollbar {
    width: 10px;
  }

  ::-webkit-scrollbar-thumb {
    background-color: ${props => props.theme.colors.gray[400]};
    border-radius: 999px;

    &:hover {
      background-color: #A03612;
    }
  }

  ::-webkit-scrollbar-track {
    background-color: ${props => props.theme.colors.surfaceAlt};
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
`;

const AppContainer = styled.div`
  display: flex;
  min-height: 100vh;
  background-color: ${props => props.theme.colors.background};
`;

const MainContent = styled.main`
  flex: 1;
  margin-left: ${props => props.sidebarCollapsed ? '80px' : '250px'};
  padding: 20px;
  transition: margin-left 0.3s ease;
  background-color: ${props => props.theme.colors.background};
  color: ${props => props.theme.colors.text};

  @media (max-width: 768px) {
    margin-left: 0;
    padding: 10px;
  }
`;

const AppInner = () => {
  const { preferences } = useUserPreferences();
  const themeMode = useMemo(() => (preferences?.theme === 'dark' ? darkTheme : lightTheme), [preferences?.theme]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', themeMode.mode);
  }, [themeMode.mode]);

  const toggleSidebar = () => setSidebarCollapsed(prev => !prev);

  return (
    <ThemeProvider theme={themeMode}>
      <GlobalStyle />
      <Router>
        <AppContainer>
          <PageErrorBoundary title="Navigation fejl" message="Der opstod en fejl i sidebar. Siden kan stadig fungere.">
            <Sidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
          </PageErrorBoundary>
          <MainContent sidebarCollapsed={sidebarCollapsed}>
            <Toaster
              position="top-right"
              toastOptions={{
                style: {
                  background: themeMode.colors.surface,
                  color: themeMode.colors.text,
                  borderRadius: themeMode.borderRadius,
                  border: `1px solid ${themeMode.colors.border}`,
                },
              }}
            />
            <PageErrorBoundary title="Navbar fejl" message="Der opstod en fejl i navigation. Siden kan stadig fungere.">
              <Navbar />
            </PageErrorBoundary>
            <PageErrorBoundary title="Side indlæsningsfejl" message="Der opstod en fejl ved indlæsning af siden.">
              <Suspense fallback={<SectionLoader text="Indlæser side..." />}>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/hurtig-tjek" element={<QuickCheckPage />} />
                  <Route path="/ai-sager" element={<AICasesPage />} />
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
      </Router>
    </ThemeProvider>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <UserPreferencesProvider>
          <LoadingProvider>
            <AppInner />
          </LoadingProvider>
        </UserPreferencesProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
