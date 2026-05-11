import React from 'react';

/**
 * BifrostLogo — Lady Justice-inspireret vægtskål-mærke.
 *
 * Erstatter tidligere Berkanan-rune (ᛒ) som lignede Bluetooth-logoet.
 * Symboliserer compliance + balance + lovens vægt — kerne-værdier i Bifrost.
 *
 * Designet til at virke i to størrelser:
 *   - Lille (16-24px) i nav/header — kun stregerne, ingen detaljer
 *   - Stor (48-128px) i hero — samme strege, opskaleret rent
 *
 * Stroke-baseret SVG der arver currentColor — så samme komponent virker
 * bronze i sidebar-header (Northern Modern theme) og navy i light-knapper.
 *
 * Props:
 *   size: number — pixel-størrelse (default 24)
 *   stroke: number — stregbredde (default 2, brug 1.5 for små størrelser)
 *   title: string — tilgængelighedstitel (default "Bifrost-logo")
 */
const BifrostLogo = ({
  size = 24,
  stroke = 2,
  title = 'Bifrost-logo',
  ...rest
}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={stroke}
    strokeLinecap="round"
    strokeLinejoin="round"
    role="img"
    aria-label={title}
    {...rest}
  >
    <title>{title}</title>
    {/* Central søjle - lovens akse */}
    <line x1="12" y1="3" x2="12" y2="20" />
    {/* Vandret bjælke der bærer vægtskålene */}
    <line x1="3" y1="7" x2="21" y2="7" />
    {/* Lille top-prik - balancepunktet */}
    <circle cx="12" cy="4.5" r="1.1" fill="currentColor" stroke="none" />
    {/* Venstre kæde + skål (halvcirkel) */}
    <line x1="6" y1="7" x2="6" y2="10" />
    <path d="M3 10 Q6 14 9 10" />
    {/* Højre kæde + skål */}
    <line x1="18" y1="7" x2="18" y2="10" />
    <path d="M15 10 Q18 14 21 10" />
    {/* Base / fod */}
    <line x1="8.5" y1="20" x2="15.5" y2="20" />
    <line x1="10" y1="20" x2="10" y2="18" />
    <line x1="14" y1="20" x2="14" y2="18" />
  </svg>
);

export default BifrostLogo;
