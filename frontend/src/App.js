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
import CommandPalette, { useCommandPaletteShortcut, useGotoShortcuts } from './components/command-palette/CommandPalette';
import { useNavigate } from 'react-router-dom';

// Lazy loaded pages - Optimized code splitting
const HomePage = React.lazy(() => import('./pages/HomePage'));
const KnowledgeBasePage = React.lazy(() => import('./pages/KnowledgeBasePage'));
const ResearchPage = React.lazy(() => import('./pages/ResearchPage'));
const LawAssistantPage = React.lazy(() => import('./pages/LawAssistantPage'));
const ResourcesPage = React.lazy(() => import('./pages/ResourcesPage'));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage'));
const AIProjectsPage = React.lazy(() => import('./pages/AIProjectsPage'));
const VurderingPage = React.lazy(() => import('./pages/V3VurderingPage'));
const VurderingHistorikPage = React.lazy(() => import('./pages/VurderingHistorikPage'));
const SammenlignPage = React.lazy(() => import('./pages/SammenlignPage'));
const SagerPage = React.lazy(() => import('./pages/SagerPage'));
const LovOvervaagningPage = React.lazy(() => import('./pages/LovOvervaagningPage'));

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
    /* Tyr — Northern Modern */
    --primary: #0d2e54;          /* kongelig blå */
    --primary-dark: #082040;
    --primary-light: #1c4a7d;
    --primary-rgb: 13, 46, 84;

    --bronze: #b08a4a;           /* rune-signatur */
    --bronze-soft: #f3ead6;

    --paper: #f5f4ef;            /* off-white papir */
    --paper-soft: #ebe9e2;
    --surface: #ffffff;
    --ink: #14181f;
    --ink-soft: #555a64;
    --ink-faded: #8a8f96;
    --line: #d8d3c5;
    --line-soft: #ebe7da;

    /* Typography stack — IBM Plex */
    --font-body: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif;
    --font-display: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif;
    --font-sans: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif;
    --font-serif: "IBM Plex Serif", Georgia, "Times New Roman", serif;
    --font-mono: "IBM Plex Mono", "SF Mono", Consolas, monospace;

    /* Legacy alias (kun til Kalundborg-logo + ekstrem-CTA) */
    --kalundborg-primary: #c94416;
    --kalundborg-primary-dark: #a03612;
    --kalundborg-primary-light: #e85a28;
    --kalundborg-primary-rgb: 201, 68, 22;
  }

  html {
    scroll-behavior: smooth;
  }

  body {
    margin: 0;
    font-family: ${props => props.theme.fonts.body};
    background-color: ${props => props.theme.colors.background};
    color: ${props => props.theme.colors.text};
    font-size: 16px;
    line-height: 1.6;
    font-feature-settings: "ss01", "kern";
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    transition: background-color 0.18s ease, color 0.18s ease;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  /* Display headings use IBM Plex Sans (geometric authority) */
  h1, h2, h3, h4, h5, h6 {
    font-family: ${props => props.theme.fonts.display};
    letter-spacing: -0.015em;
    line-height: 1.2;
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
      box-shadow: 0 0 0 3px rgba(13, 46, 84, 0.18);
    }
  }

  input, textarea, select {
    font-family: ${props => props.theme.fonts.sans};
    outline: none;
    transition: background-color 0.18s ease, color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    background-color: ${props => props.theme.colors.inputBackground};
    color: ${props => props.theme.colors.text};
    border: 1px solid ${props => props.theme.colors.border};

    &:focus {
      border-color: ${props => props.theme.colors.primary};
      box-shadow: 0 0 0 3px rgba(13, 46, 84, 0.15);
    }
  }

  /* Lov-citater renderes i Plex Serif italic for "ordret kilde"-signal */
  article p.citat, .doc p.citat, .citat {
    font-family: ${props => props.theme.fonts.serif};
    font-style: italic;
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

// Tiny in-Router wrapper that wires `g v`-style shortcuts (needs useNavigate
// which only works inside <Router>).
const RouterShortcuts = ({ paletteOpen }) => {
  const navigate = useNavigate();
  useGotoShortcuts(navigate, paletteOpen);
  return null;
};

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
        <RouterShortcuts paletteOpen={paletteOpen} />
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

                  {/* Sammenlign engines (v3 vs legacy) — Step 4 validation */}
                  <Route path="/sammenlign" element={<SammenlignPage />} />

                  {/* Sager — kanban over /api/v3/cases (Step 2 workflow) */}
                  <Route path="/sager" element={<SagerPage />} />

                  {/* Lov-overvågning — daglig citation-verifier (Step 3) */}
                  <Route path="/lov-overvaagning" element={<LovOvervaagningPage />} />

                  {/* Back-compat redirects from removed pages */}
                  <Route path="/hurtig-tjek" element={<Navigate to="/vurdering" replace />} />
                  <Route path="/fuld-vurdering" element={<Navigate to="/vurdering" replace />} />
                  <Route path="/v3-vurdering" element={<Navigate to="/vurdering" replace />} />
                  <Route path="/dashboard" element={<Navigate to="/" replace />} />
                  <Route path="/ai-sager" element={<Navigate to="/sager" replace />} />

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
