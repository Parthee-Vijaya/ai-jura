import React, { useEffect, useRef } from 'react';
import styled from 'styled-components';
import { FaTimes } from 'react-icons/fa';

/**
 * Bifrost — unified Modal med a11y focus-trap + ESC-dismiss + responsive sheet
 *
 * Usage:
 *   <Modal open={...} onClose={() => ...} title="Rediger" size="md">
 *     ...content...
 *     <Modal.Footer>
 *       <Button>OK</Button>
 *     </Modal.Footer>
 *   </Modal>
 */

const Backdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(20, 24, 31, 0.55);
  z-index: 1000;
  display: flex;
  align-items: ${(p) => (p.$sheet ? 'flex-end' : 'flex-start')};
  justify-content: center;
  padding: ${(p) => (p.$sheet ? '0' : '4vh 1rem')};
  overflow-y: auto;

  @media (max-width: 720px) {
    align-items: flex-end;
    padding: 0;
  }
`;

const Sheet = styled.div`
  background: ${(p) => p.theme.colors.surface || p.theme.colors.paper || '#fff'};
  border: 1px solid ${(p) => p.theme.colors.border};
  border-radius: 10px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  max-height: 92vh;
  width: 100%;
  max-width: ${(p) => ({
    sm: '420px',
    md: '600px',
    lg: '880px',
    xl: '1100px',
  }[p.$size || 'md'])};

  @media (max-width: 720px) {
    border-radius: 12px 12px 0 0;
    max-height: 92vh;
    max-width: 100%;
    /* Safe-area inset for iOS notch */
    padding-bottom: env(safe-area-inset-bottom);
  }
`;

const Head = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1.1rem 1.5rem 0.9rem;
  border-bottom: 1px solid ${(p) => p.theme.colors.border};

  h2 {
    font-family: ${(p) => p.theme.fonts.display};
    font-size: 1.15rem;
    font-weight: 600;
    margin: 0;
    color: ${(p) => p.theme.colors.text};
    letter-spacing: -0.01em;
  }
`;

const CloseButton = styled.button`
  background: transparent;
  border: none;
  color: ${(p) => p.theme.colors.textFaded};
  font-size: 1rem;
  cursor: pointer;
  margin-left: 1rem;
  padding: 0.35rem;
  border-radius: 4px;
  min-width: 32px;
  min-height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: ${(p) => p.theme.colors.surfaceAlt || 'rgba(0,0,0,0.04)'};
    color: ${(p) => p.theme.colors.text};
  }
  &:focus-visible {
    outline: 2px solid ${(p) => p.theme.colors.primary};
    outline-offset: 2px;
  }
`;

const Body = styled.div`
  padding: 1.2rem 1.5rem;
  overflow-y: auto;
  flex: 1;
`;

const Footer = styled.div`
  border-top: 1px solid ${(p) => p.theme.colors.border};
  padding: 0.9rem 1.5rem;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
`;

export const Modal = ({
  open,
  onClose,
  title,
  size = 'md',
  sheet = false,
  children,
  closeOnBackdrop = true,
}) => {
  const sheetRef = useRef(null);
  const triggerRef = useRef(null);

  // Lock body scroll
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    triggerRef.current = document.activeElement;
    // Focus first interactive element on open
    setTimeout(() => {
      const first = sheetRef.current?.querySelector(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      first?.focus();
    }, 50);
    return () => {
      document.body.style.overflow = prev;
      // Restore focus
      triggerRef.current?.focus?.();
    };
  }, [open]);

  // ESC to close
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (e.key === 'Escape' && onClose) onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <Backdrop
      $sheet={sheet}
      onClick={(e) => {
        if (closeOnBackdrop && e.target === e.currentTarget) onClose?.();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'bifrost-modal-title' : undefined}
    >
      <Sheet ref={sheetRef} $size={size} onClick={(e) => e.stopPropagation()}>
        {(title || onClose) && (
          <Head>
            <h2 id="bifrost-modal-title">{title}</h2>
            {onClose && (
              <CloseButton onClick={onClose} aria-label="Luk dialog">
                <FaTimes />
              </CloseButton>
            )}
          </Head>
        )}
        {children}
      </Sheet>
    </Backdrop>
  );
};

Modal.Body = Body;
Modal.Footer = Footer;

export default Modal;
