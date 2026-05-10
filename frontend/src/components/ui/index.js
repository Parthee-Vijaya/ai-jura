/**
 * Bifrost UI library — barrel export.
 *
 * Centralt design-system. Importér ALDRIG styled-components for primitiver
 * direkte i pages — brug disse atomer i stedet:
 *
 *   import { Button, Pill, Banner, EmptyState, Modal, Tabs, Breadcrumb,
 *            useToast } from '../components/ui';
 *
 * Eksisterende PageChrome.js (PageHeader, PageShell, PrimaryButton osv.)
 * re-eksporteres her så pages kan migrate gradvist.
 */

// New atoms (May 2026)
export { default as Button } from './Button';
export { default as Pill } from './Pill';
export { default as Banner } from './Banner';
export { default as EmptyState } from './EmptyState';
export { default as LoadingState, SkeletonLine } from './LoadingState';
export { default as ErrorState } from './ErrorState';
export { default as Card } from './Card';
export { default as Modal } from './Modal';
export { default as Tabs } from './Tabs';
export { default as Breadcrumb } from './Breadcrumb';
export { ToastProvider, useToast } from './Toast';

// Re-export from existing PageChrome.js so consumers can use a single import path
export {
  PageShell,
  PageHeader,
  PageHeaderWrap,
  Eyebrow,
  PageTitle,
  Lede,
  SectionTitle,
  SectionSubtitle,
  OutlinePill,
  EditorialCard,
  PrimaryButton,  // legacy — prefer <Button variant="primary">
  GhostButton,    // legacy — prefer <Button variant="ghost">
  SearchField,
} from '../page-chrome/PageChrome';
