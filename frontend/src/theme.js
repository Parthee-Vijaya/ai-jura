/**
 * Bifrost — Northern Modern theme (Design system v2)
 *
 * Skandinavisk civic-tech sobriety. Off-white papir, kongelig blå primær,
 * bronze rune-accent. IBM Plex Sans + Mono + Serif italic.
 *
 * Reference: DESIGN.md (canonical source).
 *
 * Forløb: Project Judge Dredd → Hjemmel → Bifrost → Bifrost (alpha.18+).
 */

const commonThemeTokens = {
  fonts: {
    main: '"IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif',
    body: '"IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif',
    display: '"IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif',
    sans: '"IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif',
    serif: '"IBM Plex Serif", Georgia, "Times New Roman", serif',
    mono: '"IBM Plex Mono", "SF Mono", Consolas, monospace',
  },
  borderRadius: '4px',
  borderRadiusLarge: '6px',
  shadows: {
    sm: '0 1px 2px 0 rgba(20, 24, 31, 0.04)',
    md: '0 4px 8px -2px rgba(20, 24, 31, 0.06)',
    lg: '0 24px 48px -12px rgba(20, 24, 31, 0.16)',
    xl: '0 32px 64px -16px rgba(20, 24, 31, 0.20)',
    glass: '0 4px 16px 0 rgba(20, 24, 31, 0.08)',
    glow: '0 0 0 3px rgba(13, 46, 84, 0.12)',
    focus: '0 0 0 3px rgba(13, 46, 84, 0.18)',
  },
  animations: {
    transition: '0.18s ease-out',
    transitionFast: '0.1s ease-out',
    transitionSlow: '0.28s ease-out',
    bounce: 'cubic-bezier(0.4, 0, 0.2, 1)',
    spring: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
};

export const lightTheme = {
  ...commonThemeTokens,
  mode: 'light',
  colors: {
    // Primary — Kongelig blå (autoritet)
    primary: '#0d2e54',
    primaryDark: '#082040',
    primaryLight: '#1c4a7d',
    primarySoft: '#e2eaf3',
    primaryBg: '#eef3f8',
    secondary: '#0d2e54',

    // Bronze — runen, sekundær accent
    bronze: '#b08a4a',
    bronzeDark: '#8e6e35',
    bronzeLight: '#c9a360',
    bronzeSoft: '#f3ead6',

    // Semantic
    accent: '#b08a4a',
    success: '#2f6b2f',
    successSoft: '#e3eedc',
    warning: '#b08a4a',
    warningSoft: '#f3ead6',
    danger: '#a52822',
    dangerSoft: '#f4dfdc',

    // Legacy alias (Kalundborg teglrød kun til ekstrem-CTA / NO-GO)
    teglrod: '#c94416',

    dark: '#14181f',
    light: '#f5f4ef',
    white: '#ffffff',

    // Surface — Northern Modern off-white
    background: '#f5f4ef',
    surface: '#ffffff',
    surfaceAlt: '#ebe9e2',
    paper: '#f5f4ef',
    paperSoft: '#ebe9e2',
    card: '#ffffff',

    // Text
    text: '#14181f',
    textMuted: '#555a64',
    textFaded: '#8a8f96',
    ink: '#14181f',
    inkSoft: '#555a64',
    inkFaded: '#8a8f96',

    // Lines
    border: '#d8d3c5',
    borderSoft: '#ebe7da',
    line: '#d8d3c5',
    lineSoft: '#ebe7da',
    inputBackground: '#ffffff',

    // Gray (preserved for legacy components)
    gray: {
      50: '#f5f4ef',
      100: '#ebe9e2',
      200: '#d8d3c5',
      300: '#bbb6a8',
      400: '#8a8f96',
      500: '#555a64',
      600: '#3d4148',
      700: '#262930',
      800: '#14181f',
      900: '#0a0c10',
    },

    // Kalundborg-spec (legacy alias — bevares til NO-GO + Kalundborg-logo)
    kalundborg: {
      teglrod: '#c94416',
      teglrodDark: '#a03612',
      teglrodLight: '#e85a28',
      buttonSecondary: '#0d2e54',
      textDark: '#14181f',
      bronze: '#b08a4a',
      platinum: '#e5e4e2',
    },

    // Gradients (sjælden brug — Northern Modern er low-gradient)
    gradients: {
      primary: 'linear-gradient(135deg, #0d2e54 0%, #1c4a7d 100%)',
      secondary: 'linear-gradient(135deg, #b08a4a 0%, #c9a360 100%)',
      hero: 'linear-gradient(135deg, #f5f4ef 0%, #ebe9e2 100%)',
      card: 'linear-gradient(145deg, #ffffff 0%, #f5f4ef 100%)',
      glass: 'linear-gradient(145deg, rgba(255,255,255,0.92) 0%, rgba(245,244,239,0.85) 100%)',
      danger: 'linear-gradient(135deg, #a52822 0%, #c53030 100%)',
      gold: 'linear-gradient(135deg, #b08a4a 0%, #c9a360 100%)',
    },
  },

  glass: {
    background: 'rgba(245, 244, 239, 0.92)',
    border: '1px solid #d8d3c5',
    backdropFilter: 'blur(8px)',
    borderRadius: '6px',
  },

  layout: {
    nav: {
      background: 'rgba(255, 255, 255, 0.92)',
      border: '#d8d3c5',
      text: '#14181f',
      badgeBackground: '#e2eaf3',
    },
    sidebar: {
      background: '#ffffff',
      backgroundSolid: '#ffffff',
      border: '#d8d3c5',
      text: '#14181f',
      muted: '#8a8f96',
      hoverBackground: '#ebe9e2',
      hoverText: '#14181f',
      activeBackground: '#e2eaf3',
      activeBorder: '#0d2e54',
      activeText: '#0d2e54',
      badgeBackground: '#ebe9e2',
    },
    card: {
      background: '#ffffff',
      border: '#d8d3c5',
    },
    ticker: {
      background: '#e2eaf3',
      text: '#0d2e54',
      badgeBackground: '#f3ead6',
      badgeText: '#8e6e35',
    },
  },
};

export const darkTheme = {
  ...commonThemeTokens,
  mode: 'dark',
  colors: {
    // Primary — lighter blue for dark mode
    primary: '#5a8ec4',
    primaryDark: '#3d6da3',
    primaryLight: '#7ca7d6',
    primarySoft: 'rgba(90, 142, 196, 0.16)',
    primaryBg: 'rgba(90, 142, 196, 0.10)',
    secondary: '#5a8ec4',

    // Bronze (lighter)
    bronze: '#d4a866',
    bronzeDark: '#b08a4a',
    bronzeLight: '#e0bc7c',
    bronzeSoft: 'rgba(212, 168, 102, 0.16)',

    // Semantic
    accent: '#d4a866',
    success: '#7eaf78',
    successSoft: 'rgba(126, 175, 120, 0.14)',
    warning: '#d4a866',
    warningSoft: 'rgba(212, 168, 102, 0.16)',
    danger: '#d65c4d',
    dangerSoft: 'rgba(214, 92, 77, 0.14)',

    teglrod: '#e85a28',

    dark: '#0a0c10',
    light: '#14181f',
    white: '#f0eee9',

    // Surface — dark cool warm
    background: '#14181f',
    surface: '#1c2129',
    surfaceAlt: '#252a32',
    paper: '#14181f',
    paperSoft: '#1c2129',
    card: '#1c2129',

    // Text
    text: '#f0eee9',
    textMuted: '#a8aaae',
    textFaded: '#6a6d72',
    ink: '#f0eee9',
    inkSoft: '#a8aaae',
    inkFaded: '#6a6d72',

    // Lines
    border: '#2e333c',
    borderSoft: '#252a32',
    line: '#2e333c',
    lineSoft: '#252a32',
    inputBackground: '#1c2129',

    gray: {
      50: '#14181f',
      100: '#1c2129',
      200: '#252a32',
      300: '#2e333c',
      400: '#6a6d72',
      500: '#a8aaae',
      600: '#c8cacd',
      700: '#e0e0e0',
      800: '#f0eee9',
      900: '#ffffff',
    },

    kalundborg: {
      teglrod: '#e85a28',
      teglrodDark: '#c94416',
      teglrodLight: '#f07040',
      buttonSecondary: '#5a8ec4',
      textDark: '#f0eee9',
      bronze: '#d4a866',
      platinum: '#faf5ff',
    },

    gradients: {
      primary: 'linear-gradient(135deg, #0d2e54 0%, #5a8ec4 100%)',
      secondary: 'linear-gradient(135deg, #b08a4a 0%, #d4a866 100%)',
      hero: 'linear-gradient(135deg, #14181f 0%, #1c2129 100%)',
      card: 'linear-gradient(145deg, #1c2129 0%, #14181f 100%)',
      glass: 'linear-gradient(145deg, rgba(28,33,41,0.85) 0%, rgba(20,24,31,0.75) 100%)',
      danger: 'linear-gradient(135deg, #a52822 0%, #d65c4d 100%)',
      gold: 'linear-gradient(135deg, #b08a4a 0%, #d4a866 100%)',
    },
  },

  glass: {
    background: 'rgba(20, 24, 31, 0.92)',
    border: '1px solid #2e333c',
    backdropFilter: 'blur(8px)',
    borderRadius: '6px',
  },

  layout: {
    nav: {
      background: 'rgba(20, 24, 31, 0.92)',
      border: '#2e333c',
      text: '#f0eee9',
      badgeBackground: 'rgba(90, 142, 196, 0.16)',
    },
    sidebar: {
      background: '#14181f',
      backgroundSolid: '#14181f',
      border: '#2e333c',
      text: '#f0eee9',
      muted: '#6a6d72',
      hoverBackground: '#1c2129',
      hoverText: '#ffffff',
      activeBackground: 'rgba(90, 142, 196, 0.14)',
      activeBorder: '#5a8ec4',
      activeText: '#7ca7d6',
      badgeBackground: 'rgba(255, 255, 255, 0.06)',
    },
    card: {
      background: '#1c2129',
      border: '#2e333c',
    },
    ticker: {
      background: 'rgba(90, 142, 196, 0.14)',
      text: '#7ca7d6',
      badgeBackground: 'rgba(212, 168, 102, 0.20)',
      badgeText: '#d4a866',
    },
  },
};

// Legacy juridical color aliases (preserved for components that still reference)
lightTheme.colors.juridical = {
  navy: '#0d2e54',
  gold: '#b08a4a',
  darkGold: '#8e6e35',
  charcoal: '#14181f',
  lightNavy: '#1c4a7d',
  deepNavy: '#082040',
  midNavy: '#15396a',
  lightGold: '#c9a360',
  bronze: '#b08a4a',
  platinum: '#e5e4e2',
};

darkTheme.colors.juridical = {
  navy: '#5a8ec4',
  gold: '#d4a866',
  darkGold: '#b08a4a',
  charcoal: '#1c2129',
  lightNavy: '#7ca7d6',
  deepNavy: '#0d2e54',
  midNavy: '#3d6da3',
  lightGold: '#e0bc7c',
  bronze: '#d4a866',
  platinum: '#faf5ff',
};

const themes = { lightTheme, darkTheme };
export default themes;
