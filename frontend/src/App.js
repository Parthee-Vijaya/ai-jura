import React, { useState, Suspense, useMemo, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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

// Command palette
import CommandPalette, { useCommandPaletteShortcut } from './components/command-palette/CommandPalette';

// Lazy loaded pages - Optimized code splitting
const HomePage = React.lazy(() => import('./pages/HomePage'));
const KnowledgeBasePage = React.lazy(() => import('./pages/KnowledgeBasePage'));
const ResearchPage = React.lazy(() => import('./pages/ResearchPage'));
const LawAssistantPage = React.lazy(() => import('./pages/LawAssistantPage'));
const ResourcesPage = React.lazy(() => import('./pages/ResourcesPage'));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage'));
const AICasesPage = React.lazy(() => import('./pages/AICasesPage'));
const AIProjectsPage = React.lazy(() => import('./pages/AIProjectsPage'));
const VurderingPage = React.lazy(() => import('./pages/V3VurderingPage'));
const VurderingHistorikPage = React.lazy(() => import('./pages/VurderingHistorikPage'));

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
    --kalundborg-primary: #c94416;
    --kalundborg-primary-dark: #a03612;
    --kalundborg-primary-light: #e85a28;
    --kalundborg-primary-rgb: 201, 68, 22;

    /* Design C — paper & ink */
    --paper: #faf8f5;
    --paper-soft: #f3efe8;
    --ink: #1a1614;
    --ink-soft: #6b5e4f;
    --ink-faded: #9a8d7d;
    --line: #e8e2d6;
    --line-soft: #f0ebe1;

    /* Typography stack */
    --font-body: Lora, Georgia, "Times New Roman", serif;
    --font-display: "Source Serif Pro", Lora, Georgia, serif;
    --font-sans: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: "JetBrains Mono", "SF Mono", Consolas, monospace;
  }

  html {
    scroll-behavior: smooth;
  }

  body {
    margin: 0;
    font-family: ${props => props.theme.fonts.body};
    background-color: ${props => props.theme.colors.background};
    color: ${props => props.theme.colors.text};
    font-size: 17px;
    line-height: 1.7;
    font-feature-settings: "ss01", "kern";
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    transition: background-color 0.3s ease, color 0.3s ease;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  /* Display headings use Source Serif Pro for gravitas */
  h1, h2, h3, h4, h5, h6 {
    font-family: ${props => props.theme.fonts.display};
    letter-spacing: -0.012em;
    line-height: 1.25;
    color: ${props => props.theme.colors.ink};
  }

  a {
    text-decoration: none;
    color: ${props => props.theme.colors.primary};
    transition: color ${props => props.theme.animations.transitionFast};

    &:hover {
      color: ${props => props.theme.colors.primaryDark};
    }

    &:focus-visible {
      outline: 2px solid ${props => props.theme.colors.primary};
      outline-offset: 2px;
      border-radius: 2px;
    }
  }

  button {
    cursor: pointer;
    border: none;
    outline: none;
    font-family: ${props => props.theme.fonts.sans};
    background: none;

    &:focus-visible {
      outline: 2px solid ${props => props.theme.colors.primary};
      outline-offset: 2px;
      box-shadow: 0 0 0 3px rgba(201, 68, 22, 0.18);
    }
  }

  input, textarea, select {
    font-family: ${props => props.theme.fonts.sans};
    outline: none;
    transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
    background-color: ${props => props.theme.colors.inputBackground};
    color: ${props => props.theme.colors.text};
    border: 1px solid ${props => props.theme.colors.border};

    &:focus {
      border-color: ${props => props.theme.colors.primary};
      box-shadow: 0 0 0 3px rgba(201, 68, 22, 0.15);
    }
  }

  /* Body paragraphs in articles read as Lora */
  article p, .doc p, .lora {
    font-family: ${props => props.theme.fonts.body};
  }

  ::selection {
    background: ${props => props.theme.colors.primary};
    color: white;
  }

  ::-moz-selection {
    background: ${props => props.theme.colors.primary};
    color: white;
  }

  ::-webkit-scrollbar {
    width: 10px;
  }

  ::-webkit-scrollbar-thumb {
    background-color: ${props => props.theme.colors.gray[300]};
    border-radius: 999px;

    &:hover {
      background-color: ${props => props.theme.colors.primary};
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
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', themeMode.mode);
  }, [themeMode.mode]);

  useCommandPaletteShortcut(() => setPaletteOpen(true));

  const toggleSidebar = () => setSidebarCollapsed(prev => !prev);

  return (
    <ThemeProvider theme={themeMode}>
      <GlobalStyle />
      <Router>
        <CommandPalette isOpen={paletteOpen} onClose={() => setPaletteOpen(false)} />
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
            <PageErrorBoundary title="Side indlæsningsfejl" message="Der opstod en fejl ved indlæsning af siden.">
              <Suspense fallback={<SectionLoader text="Indlæser side..." />}>
                <Routes>
                  <Route path="/" element={<HomePage />} />

                  {/* Primary assessment page (replaces Hurtig Tjek + Compliance Control) */}
                  <Route path="/vurdering" element={<VurderingPage />} />

                  {/* Vurderingshistorik (audit log over /api/v3/audit) */}
                  <Route path="/historik" element={<VurderingHistorikPage />} />
                  <Route path="/historik/:id" element={<VurderingHistorikPage />} />

                  {/* Back-compat redirects from removed pages */}
                  <Route path="/hurtig-tjek" element={<Navigate to="/vurdering" replace />} />
                  <Route path="/fuld-vurdering" element={<Navigate to="/vurdering" replace />} />
                  <Route path="/v3-vurdering" element={<Navigate to="/vurdering" replace />} />
                  <Route path="/dashboard" element={<Navigate to="/" replace />} />

                  <Route path="/ai-sager" element={<AICasesPage />} />
                  <Route path="/videnbase" element={<KnowledgeBasePage />} />
                  <Route path="/ai-losninger" element={<AIProjectsPage />} />
                  <Route path="/research" element={<ResearchPage />} />
                  <Route path="/lov-assistent" element={<LawAssistantPage />} />
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
