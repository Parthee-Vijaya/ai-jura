import React, { useState, Suspense, useMemo, useEffect } from 'react';
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
import AICasesPage from './pages/AICasesPage';

// Contexts
import { UserPreferencesProvider, useUserPreferences } from './contexts/UserPreferencesContext';
import { LoadingProvider } from './contexts/LoadingContext';

// Lazy loaded pages
const HomePage = React.lazy(() => import('./pages/HomePage'));
const QuickCheckPage = React.lazy(() => import('./pages/QuickCheckPage'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

const commonThemeTokens = {
  fonts: {
    main: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
  },
  borderRadius: '12px',
  borderRadiusLarge: '16px',
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 10px 10px -5px rgb(0 0 0 / 0.04)',
    glass: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
    glow: '0 0 24px rgba(201, 68, 22, 0.35)',
    focus: '0 0 0 3px rgba(201, 68, 22, 0.18)',
  },
  animations: {
    transition: '0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    transitionFast: '0.15s cubic-bezier(0.4, 0, 0.2, 1)',
    transitionSlow: '0.5s cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  },
};

const lightTheme = {
  ...commonThemeTokens,
  mode: 'light',
  colors: {
    primary: '#A03612',
    primaryDark: '#7d2b0e',
    primaryLight: '#C94416',
    secondary: '#2d3748',
    accent: '#b8860b',
    success: '#2f855a',
    warning: '#d69e2e',
    danger: '#c53030',
    dark: '#1a202c',
    light: '#f7fafc',
    white: '#ffffff',
    background: '#f4f7fb',
    surface: '#ffffff',
    surfaceAlt: '#f1f5f9',
    text: '#1a202c',
    textMuted: '#64748b',
    border: '#e2e8f0',
    inputBackground: '#ffffff',
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
      900: '#171923',
    },
    juridical: {
      navy: '#1a365d',
      gold: '#b8860b',
      darkGold: '#9a7209',
      charcoal: '#2d3748',
      lightNavy: '#2c5282',
      deepNavy: '#0f2238',
      midNavy: '#1a4480',
      lightGold: '#d4af37',
      bronze: '#cd7f32',
      platinum: '#e5e4e2',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #7d2b0e 0%, #A03612 50%, #C94416 100%)',
      gold: 'linear-gradient(135deg, #b8860b 0%, #d4af37 50%, #f6e05e 100%)',
      hero: 'linear-gradient(135deg, #7d2b0e 0%, #A03612 25%, #C94416 75%, #E85A28 100%)',
      card: 'linear-gradient(145deg, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.08) 100%)',
      glass: 'linear-gradient(145deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%)',
      danger: 'linear-gradient(135deg, #c53030 0%, #e53e3e 50%, #f56565 100%)',
    },
  },
  glass: {
    background: 'rgba(255, 255, 255, 0.65)',
    border: '1px solid rgba(255, 255, 255, 0.35)',
    backdropFilter: 'blur(20px)',
    borderRadius: '16px',
  },
  layout: {
    nav: {
      background: 'rgba(255, 255, 255, 0.92)',
      border: '#e2e8f0',
      text: '#1f2937',
      badgeBackground: 'rgba(26, 54, 93, 0.08)',
    },
    sidebar: {
      background: 'linear-gradient(180deg, rgba(160,54,18,0.95) 0%, rgba(125,43,14,0.92) 100%)',
      border: 'rgba(160, 54, 18, 0.15)',
      text: '#f8fafc',
      muted: '#fed7aa',
      hoverBackground: 'rgba(160, 54, 18, 0.15)',
      hoverText: '#ffffff',
      activeBackground: 'linear-gradient(135deg, rgba(160,54,18,0.28) 0%, rgba(125,43,14,0.38) 100%)',
      activeBorder: '#A03612',
      activeText: '#ffffff',
      badgeBackground: 'rgba(255,255,255,0.12)',
    },
    card: {
      background: '#ffffff',
      border: '#e2e8f0',
    },
    ticker: {
      background: '#ffffff',
      text: '#252525',
      badgeBackground: 'rgba(201, 68, 22, 0.12)',
      badgeText: '#C94416',
    },
  },
};

const darkTheme = {
  ...commonThemeTokens,
  mode: 'dark',
  colors: {
    primary: '#A03612',
    primaryDark: '#7d2b0e',
    primaryLight: '#C94416',
    secondary: '#334155',
    accent: '#fbbf24',
    success: '#22c55e',
    warning: '#fbbf24',
    danger: '#f87171',
    dark: '#0f172a',
    light: '#1e293b',
    white: '#f8fafc',
    background: '#0b1220',
    surface: '#111827',
    surfaceAlt: '#1e293b',
    text: '#e2e8f0',
    textMuted: '#94a3b8',
    border: '#1f2937',
    inputBackground: '#1e293b',
    gray: {
      50: '#0b1220',
      100: '#111827',
      200: '#1e293b',
      300: '#27364a',
      400: '#334155',
      500: '#475569',
      600: '#64748b',
      700: '#94a3b8',
      800: '#cbd5f5',
      900: '#e2e8ff',
    },
    juridical: {
      navy: '#7aa2ff',
      gold: '#fbbf24',
      darkGold: '#f59e0b',
      charcoal: '#1f2937',
      lightNavy: '#60a5fa',
      deepNavy: '#172554',
      midNavy: '#1d4ed8',
      lightGold: '#facc15',
      bronze: '#f97316',
      platinum: '#faf5ff',
    },
    gradients: {
      primary: 'linear-gradient(135deg, #7d2b0e 0%, #A03612 50%, #C94416 100%)',
      gold: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 50%, #facc15 100%)',
      hero: 'linear-gradient(135deg, #0b1220 0%, #1e293b 40%, #A03612 100%)',
      card: 'linear-gradient(145deg, rgba(255,255,255,0.08) 0%, rgba(148, 163, 209, 0.05) 100%)',
      glass: 'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%)',
      danger: 'linear-gradient(135deg, #ef4444 0%, #f97316 50%, #facc15 100%)',
    },
  },
  glass: {
    background: 'rgba(17, 24, 39, 0.65)',
    border: '1px solid rgba(148, 163, 184, 0.15)',
    backdropFilter: 'blur(20px)',
    borderRadius: '16px',
  },
  layout: {
    nav: {
      background: 'rgba(17, 24, 39, 0.92)',
      border: '#1f2937',
      text: '#f8fafc',
      badgeBackground: 'rgba(124, 189, 255, 0.15)',
    },
    sidebar: {
      background: 'linear-gradient(180deg, rgba(160,54,18,0.85) 0%, rgba(125,43,14,0.88) 100%)',
      border: 'rgba(160, 54, 18, 0.25)',
      text: '#f8fafc',
      muted: '#fed7aa',
      hoverBackground: 'rgba(160, 54, 18, 0.20)',
      hoverText: '#ffffff',
      activeBackground: 'linear-gradient(135deg, rgba(160,54,18,0.35) 0%, rgba(125,43,14,0.45) 100%)',
      activeBorder: '#A03612',
      activeText: '#ffffff',
      badgeBackground: 'rgba(255, 255, 255, 0.12)',
    },
    card: {
      background: '#111827',
      border: '#1f2937',
    },
    ticker: {
      background: '#ffffff',
      text: '#252525',
      badgeBackground: 'rgba(201, 68, 22, 0.12)',
      badgeText: '#C94416',
    },
  },
};

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
