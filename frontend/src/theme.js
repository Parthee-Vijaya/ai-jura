/**
 * Judge Dredd - Kalundborg Kommune Theme Configuration
 *
 * Primary branding colors based on Kalundborg Kommune's official design:
 * - Teglrød (Brick Red): #C94416
 * - Dark variant: #A03612
 * - Light variant: #E85A28
 * - Secondary button: #BC4D30
 */

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
    glass: '0 8px 32px 0 rgba(201, 68, 22, 0.37)',
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

export const lightTheme = {
  ...commonThemeTokens,
  mode: 'light',
  colors: {
    // Kalundborg Kommune primary colors
    primary: '#C94416',           // Teglrød (Brick Red)
    primaryDark: '#A03612',       // Dark brick red
    primaryLight: '#E85A28',      // Light brick red
    secondary: '#BC4D30',         // Secondary button color

    // Semantic colors
    accent: '#b8860b',
    success: '#2f855a',
    warning: '#d69e2e',
    danger: '#c53030',
    dark: '#252525',              // Kalundborg text dark
    light: '#f7fafc',
    white: '#ffffff',

    // Surface colors
    background: '#f4f7fb',
    surface: '#ffffff',
    surfaceAlt: '#f1f5f9',

    // Text colors
    text: '#252525',              // Kalundborg text dark
    textMuted: '#64748b',

    // UI elements
    border: '#e2e8f0',
    inputBackground: '#ffffff',

    // Gray scale (preserved for compatibility)
    gray: {
      50: '#f7fafc',
      100: '#edf2f7',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#a0aec0',
      500: '#718096',
      600: '#4a5568',
      700: '#2d3748',
      800: '#252525',             // Aligned with Kalundborg dark
      900: '#171923',
    },

    // Kalundborg specific colors
    kalundborg: {
      teglrod: '#C94416',         // Primary brick red
      teglrodDark: '#A03612',     // Dark brick red
      teglrodLight: '#E85A28',    // Light brick red
      buttonSecondary: '#BC4D30', // Secondary button
      textDark: '#252525',        // Text dark
      bronze: '#cd7f32',
      platinum: '#e5e4e2',
    },

    // Gradients with Kalundborg colors
    gradients: {
      primary: 'linear-gradient(135deg, #C94416 0%, #E85A28 50%, #F07040 100%)',
      secondary: 'linear-gradient(135deg, #BC4D30 0%, #C94416 50%, #E85A28 100%)',
      hero: 'linear-gradient(135deg, #A03612 0%, #C94416 25%, #E85A28 75%, #F07040 100%)',
      card: 'linear-gradient(145deg, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.08) 100%)',
      glass: 'linear-gradient(145deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%)',
      danger: 'linear-gradient(135deg, #c53030 0%, #e53e3e 50%, #f56565 100%)',
      gold: 'linear-gradient(135deg, #b8860b 0%, #d4af37 50%, #f6e05e 100%)',
    },
  },

  // Glassmorphism effects
  glass: {
    background: 'rgba(255, 255, 255, 0.65)',
    border: '1px solid rgba(255, 255, 255, 0.35)',
    backdropFilter: 'blur(20px)',
    borderRadius: '16px',
  },

  // Layout specific colors
  layout: {
    nav: {
      background: 'rgba(255, 255, 255, 0.92)',
      border: '#e2e8f0',
      text: '#252525',
      badgeBackground: 'rgba(201, 68, 22, 0.08)',
    },
    sidebar: {
      background: 'linear-gradient(180deg, rgba(201,68,22,0.95) 0%, rgba(160,54,18,0.92) 100%)',
      border: 'rgba(148, 163, 184, 0.15)',
      text: '#f8fafc',
      muted: '#fbd5c5',
      hoverBackground: 'rgba(255,255,255,0.08)',
      hoverText: '#ffffff',
      activeBackground: 'linear-gradient(135deg, rgba(232,90,40,0.28) 0%, rgba(201,68,22,0.38) 100%)',
      activeBorder: '#d4af37',
      activeText: '#ffffff',
      badgeBackground: 'rgba(255,255,255,0.12)',
    },
    card: {
      background: '#ffffff',
      border: '#e2e8f0',
    },
    ticker: {
      background: 'linear-gradient(135deg, #C94416 0%, #E85A28 100%)',
      text: '#ffffff',
      badgeBackground: 'rgba(255, 255, 255, 0.15)',
      badgeText: '#ffffff',
    },
  },
};

export const darkTheme = {
  ...commonThemeTokens,
  mode: 'dark',
  colors: {
    // Kalundborg Kommune primary colors (adjusted for dark mode)
    primary: '#E85A28',           // Light brick red for dark mode
    primaryDark: '#C94416',       // Original brick red
    primaryLight: '#F07040',      // Even lighter for highlights
    secondary: '#BC4D30',         // Secondary button color

    // Semantic colors
    accent: '#fbbf24',
    success: '#22c55e',
    warning: '#fbbf24',
    danger: '#f87171',
    dark: '#0f172a',
    light: '#1e293b',
    white: '#f8fafc',

    // Surface colors
    background: '#0b1220',
    surface: '#111827',
    surfaceAlt: '#1e293b',

    // Text colors
    text: '#e2e8f0',
    textMuted: '#94a3b8',

    // UI elements
    border: '#1f2937',
    inputBackground: '#1e293b',

    // Gray scale
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

    // Kalundborg specific colors (dark mode adjusted)
    kalundborg: {
      teglrod: '#E85A28',         // Lighter for dark mode
      teglrodDark: '#C94416',     // Original
      teglrodLight: '#F07040',    // Even lighter
      buttonSecondary: '#BC4D30', // Secondary button
      textDark: '#e2e8f0',        // Light text for dark mode
      bronze: '#f97316',
      platinum: '#faf5ff',
    },

    // Gradients with Kalundborg colors (dark mode)
    gradients: {
      primary: 'linear-gradient(135deg, #C94416 0%, #E85A28 50%, #F07040 100%)',
      secondary: 'linear-gradient(135deg, #BC4D30 0%, #C94416 50%, #E85A28 100%)',
      hero: 'linear-gradient(135deg, #0b1220 0%, #1e293b 40%, #C94416 100%)',
      card: 'linear-gradient(145deg, rgba(255,255,255,0.08) 0%, rgba(201, 68, 22, 0.05) 100%)',
      glass: 'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%)',
      danger: 'linear-gradient(135deg, #ef4444 0%, #f97316 50%, #facc15 100%)',
      gold: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 50%, #facc15 100%)',
    },
  },

  // Glassmorphism effects (dark mode)
  glass: {
    background: 'rgba(17, 24, 39, 0.65)',
    border: '1px solid rgba(148, 163, 184, 0.15)',
    backdropFilter: 'blur(20px)',
    borderRadius: '16px',
  },

  // Layout specific colors (dark mode)
  layout: {
    nav: {
      background: 'rgba(17, 24, 39, 0.92)',
      border: '#1f2937',
      text: '#f8fafc',
      badgeBackground: 'rgba(232, 90, 40, 0.15)',
    },
    sidebar: {
      background: 'linear-gradient(180deg, rgba(17,24,39,0.94) 0%, rgba(11,18,32,0.95) 100%)',
      border: 'rgba(15, 23, 42, 0.6)',
      text: '#f8fafc',
      muted: '#94a3b8',
      hoverBackground: 'rgba(232, 90, 40, 0.15)',
      hoverText: '#ffffff',
      activeBackground: 'linear-gradient(135deg, rgba(232,90,40,0.28) 0%, rgba(201,68,22,0.38) 100%)',
      activeBorder: '#fbbf24',
      activeText: '#f8fafc',
      badgeBackground: 'rgba(15, 23, 42, 0.4)',
    },
    card: {
      background: '#111827',
      border: '#1f2937',
    },
    ticker: {
      background: 'linear-gradient(135deg, #C94416 0%, #A03612 100%)',
      text: '#f8fafc',
      badgeBackground: 'rgba(255, 255, 255, 0.12)',
      badgeText: '#f8fafc',
    },
  },
};

// Legacy support - keeping juridical colors for backward compatibility
lightTheme.colors.juridical = {
  navy: '#C94416',              // Replaced with Kalundborg teglrød
  gold: '#b8860b',
  darkGold: '#9a7209',
  charcoal: '#2d3748',
  lightNavy: '#E85A28',         // Replaced with light teglrød
  deepNavy: '#A03612',          // Replaced with dark teglrød
  midNavy: '#BC4D30',           // Replaced with secondary
  lightGold: '#d4af37',
  bronze: '#cd7f32',
  platinum: '#e5e4e2',
};

darkTheme.colors.juridical = {
  navy: '#E85A28',              // Replaced with Kalundborg light teglrød
  gold: '#fbbf24',
  darkGold: '#f59e0b',
  charcoal: '#1f2937',
  lightNavy: '#F07040',         // Replaced with even lighter teglrød
  deepNavy: '#A03612',          // Replaced with dark teglrød
  midNavy: '#C94416',           // Replaced with primary teglrød
  lightGold: '#facc15',
  bronze: '#f97316',
  platinum: '#faf5ff',
};

export default { lightTheme, darkTheme };
