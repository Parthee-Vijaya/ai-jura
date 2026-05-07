/**
 * Judge Dredd / Forseti — Design C ("Editorial workspace") theme
 *
 * Visuel kanon: cream-paper baggrund, Lora body + Source Serif Pro display,
 * Inter chrome (nav/UI), JetBrains Mono til audit/case-id.
 *
 * Primary brand: Kalundborg teglrød — bevares som accent, men er ikke længere
 * hovedbaggrund. C er en "rolig juridisk læsebog", ikke en alarm-rød panel.
 */

const commonThemeTokens = {
  fonts: {
    main: 'Lora, Georgia, "Times New Roman", serif',
    body: 'Lora, Georgia, "Times New Roman", serif',
    display: '"Source Serif Pro", Lora, Georgia, serif',
    sans: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
    mono: '"JetBrains Mono", "SF Mono", Consolas, monospace',
  },
  borderRadius: '8px',
  borderRadiusLarge: '10px',
  shadows: {
    sm: '0 1px 2px 0 rgb(20 17 13 / 0.04)',
    md: '0 4px 8px -2px rgb(20 17 13 / 0.06)',
    lg: '0 10px 20px -4px rgb(20 17 13 / 0.08)',
    xl: '0 20px 30px -8px rgb(20 17 13 / 0.10)',
    glass: '0 4px 16px 0 rgba(20, 17, 13, 0.06)',
    glow: '0 0 16px rgba(201, 68, 22, 0.18)',
    focus: '0 0 0 3px rgba(201, 68, 22, 0.15)',
  },
  animations: {
    transition: '0.25s cubic-bezier(0.4, 0, 0.2, 1)',
    transitionFast: '0.15s cubic-bezier(0.4, 0, 0.2, 1)',
    transitionSlow: '0.4s cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  },
};

export const lightTheme = {
  ...commonThemeTokens,
  mode: 'light',
  colors: {
    // Brand (Kalundborg teglrød) — accent, ikke baggrund
    primary: '#c94416',
    primaryDark: '#a03612',
    primaryLight: '#e85a28',
    primarySoft: '#fbe9dd',
    primaryBg: '#fdf2eb',
    secondary: '#bc4d30',

    // Semantic
    accent: '#b8860b',
    success: '#2d6a31',
    successSoft: '#ecf5ec',
    warning: '#b8860b',
    danger: '#a02020',
    dangerSoft: '#fae6e6',
    dark: '#14110d',
    light: '#fbfaf6',
    white: '#ffffff',

    // Surface — Design C cream-paper
    background: '#faf8f5',          // paper
    surface: '#ffffff',             // card
    surfaceAlt: '#f3efe8',          // paper-soft
    paper: '#faf8f5',
    paperSoft: '#f3efe8',
    card: '#ffffff',

    // Text
    text: '#1a1614',                // ink
    textMuted: '#6b5e4f',           // ink-soft
    textFaded: '#9a8d7d',           // ink-faded
    ink: '#1a1614',
    inkSoft: '#6b5e4f',
    inkFaded: '#9a8d7d',

    // Lines
    border: '#e8e2d6',              // line
    borderSoft: '#f0ebe1',          // line-soft
    line: '#e8e2d6',
    lineSoft: '#f0ebe1',
    inputBackground: '#ffffff',

    // Gray (preserved for legacy components — but warm-toned)
    gray: {
      50: '#faf8f5',
      100: '#f3efe8',
      200: '#e8e2d6',
      300: '#d4ccba',
      400: '#9a8d7d',
      500: '#6b5e4f',
      600: '#4a4035',
      700: '#2f2823',
      800: '#1a1614',
      900: '#0d0a08',
    },

    // Kalundborg-spec (legacy alias)
    kalundborg: {
      teglrod: '#c94416',
      teglrodDark: '#a03612',
      teglrodLight: '#e85a28',
      buttonSecondary: '#bc4d30',
      textDark: '#1a1614',
      bronze: '#b8860b',
      platinum: '#e5e4e2',
    },

    // Gradients (kun i specielle steder; C er low-gradient)
    gradients: {
      primary: 'linear-gradient(135deg, #c94416 0%, #e85a28 100%)',
      secondary: 'linear-gradient(135deg, #bc4d30 0%, #c94416 100%)',
      hero: 'linear-gradient(135deg, #faf8f5 0%, #f3efe8 100%)',
      card: 'linear-gradient(145deg, #ffffff 0%, #faf8f5 100%)',
      glass: 'linear-gradient(145deg, rgba(255,255,255,0.85) 0%, rgba(250,248,245,0.75) 100%)',
      danger: 'linear-gradient(135deg, #a02020 0%, #c53030 100%)',
      gold: 'linear-gradient(135deg, #b8860b 0%, #d4af37 100%)',
    },
  },

  glass: {
    background: 'rgba(251, 250, 246, 0.88)',
    border: '1px solid #e8e2d6',
    backdropFilter: 'blur(10px)',
    borderRadius: '10px',
  },

  layout: {
    nav: {
      background: 'rgba(251, 250, 246, 0.88)',
      border: '#e8e2d6',
      text: '#1a1614',
      badgeBackground: '#fdf2eb',
    },
    sidebar: {
      // Design C: cream-paper, dark ink (ikke længere rød gradient)
      background: '#fbfaf6',
      backgroundSolid: '#fbfaf6',
      border: '#e8e2d6',
      text: '#1a1614',
      muted: '#9a8d7d',
      hoverBackground: '#f3efe8',
      hoverText: '#1a1614',
      activeBackground: '#fdf2eb',
      activeBorder: '#c94416',
      activeText: '#c94416',
      badgeBackground: '#f3efe8',
    },
    card: {
      background: '#ffffff',
      border: '#e8e2d6',
    },
    ticker: {
      background: '#fdf2eb',
      text: '#a03612',
      badgeBackground: '#fbe9dd',
      badgeText: '#a03612',
    },
  },
};

export const darkTheme = {
  ...commonThemeTokens,
  mode: 'dark',
  colors: {
    // Brand (lighter shade for dark mode)
    primary: '#e85a28',
    primaryDark: '#c94416',
    primaryLight: '#f07040',
    primarySoft: 'rgba(232, 90, 40, 0.18)',
    primaryBg: 'rgba(232, 90, 40, 0.10)',
    secondary: '#bc4d30',

    // Semantic
    accent: '#fbbf24',
    success: '#4ade80',
    successSoft: 'rgba(74, 222, 128, 0.10)',
    warning: '#fbbf24',
    danger: '#f87171',
    dangerSoft: 'rgba(248, 113, 113, 0.10)',
    dark: '#0a0907',
    light: '#1a1614',
    white: '#f5f3ee',

    // Surface — dark warm
    background: '#1a1614',
    surface: '#231d18',
    surfaceAlt: '#2a231d',
    paper: '#1a1614',
    paperSoft: '#231d18',
    card: '#231d18',

    // Text
    text: '#f0ebe1',
    textMuted: '#b3a799',
    textFaded: '#7a6e60',
    ink: '#f0ebe1',
    inkSoft: '#b3a799',
    inkFaded: '#7a6e60',

    // Lines
    border: '#3a322a',
    borderSoft: '#2a231d',
    line: '#3a322a',
    lineSoft: '#2a231d',
    inputBackground: '#231d18',

    gray: {
      50: '#1a1614',
      100: '#231d18',
      200: '#2a231d',
      300: '#3a322a',
      400: '#7a6e60',
      500: '#b3a799',
      600: '#d4c8b8',
      700: '#e8e0d2',
      800: '#f0ebe1',
      900: '#faf8f5',
    },

    kalundborg: {
      teglrod: '#e85a28',
      teglrodDark: '#c94416',
      teglrodLight: '#f07040',
      buttonSecondary: '#bc4d30',
      textDark: '#f0ebe1',
      bronze: '#f97316',
      platinum: '#faf5ff',
    },

    gradients: {
      primary: 'linear-gradient(135deg, #c94416 0%, #e85a28 100%)',
      secondary: 'linear-gradient(135deg, #bc4d30 0%, #c94416 100%)',
      hero: 'linear-gradient(135deg, #1a1614 0%, #231d18 100%)',
      card: 'linear-gradient(145deg, #231d18 0%, #1a1614 100%)',
      glass: 'linear-gradient(145deg, rgba(35,29,24,0.85) 0%, rgba(26,22,20,0.75) 100%)',
      danger: 'linear-gradient(135deg, #a02020 0%, #ef4444 100%)',
      gold: 'linear-gradient(135deg, #b8860b 0%, #fbbf24 100%)',
    },
  },

  glass: {
    background: 'rgba(26, 22, 20, 0.88)',
    border: '1px solid #3a322a',
    backdropFilter: 'blur(10px)',
    borderRadius: '10px',
  },

  layout: {
    nav: {
      background: 'rgba(26, 22, 20, 0.92)',
      border: '#3a322a',
      text: '#f0ebe1',
      badgeBackground: 'rgba(232, 90, 40, 0.18)',
    },
    sidebar: {
      background: '#1a1614',
      backgroundSolid: '#1a1614',
      border: '#3a322a',
      text: '#f0ebe1',
      muted: '#7a6e60',
      hoverBackground: '#231d18',
      hoverText: '#ffffff',
      activeBackground: 'rgba(232, 90, 40, 0.14)',
      activeBorder: '#e85a28',
      activeText: '#f07040',
      badgeBackground: 'rgba(255, 255, 255, 0.06)',
    },
    card: {
      background: '#231d18',
      border: '#3a322a',
    },
    ticker: {
      background: 'rgba(232, 90, 40, 0.14)',
      text: '#f07040',
      badgeBackground: 'rgba(232, 90, 40, 0.20)',
      badgeText: '#f07040',
    },
  },
};

// Legacy juridical color aliases (preserved for components that still reference)
lightTheme.colors.juridical = {
  navy: '#c94416',
  gold: '#b8860b',
  darkGold: '#9a7209',
  charcoal: '#1a1614',
  lightNavy: '#e85a28',
  deepNavy: '#a03612',
  midNavy: '#bc4d30',
  lightGold: '#d4af37',
  bronze: '#cd7f32',
  platinum: '#e5e4e2',
};

darkTheme.colors.juridical = {
  navy: '#e85a28',
  gold: '#fbbf24',
  darkGold: '#f59e0b',
  charcoal: '#231d18',
  lightNavy: '#f07040',
  deepNavy: '#a03612',
  midNavy: '#c94416',
  lightGold: '#facc15',
  bronze: '#f97316',
  platinum: '#faf5ff',
};

const themes = { lightTheme, darkTheme };
export default themes;
