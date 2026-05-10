import { useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

/**
 * useNavigationTrail — tracker sidste 10 ruter i sessionStorage så vi kan
 * lave en pålidelig "← Tilbage"-knap der respekterer modal-åbninger og
 * cross-page-flows.
 *
 * `navigate(-1)` er upålidelig efter at modal har manipuleret history.
 * Vores trail giver os mulighed for at:
 *   - Skip over modal-åbninger (samme path tæller én gang)
 *   - Bevare URL-parameters (filter-state)
 *   - Vide hvor brugeren faktisk kom fra
 *
 * Usage:
 *   const { trail, goBack, addExplicit } = useNavigationTrail();
 *   <button onClick={goBack}>← Tilbage</button>
 *
 *   // Eller manuelt: <Link to={trail.previous?.path || '/sager'}>...
 */

const STORAGE_KEY = 'bifrostNavTrail';
const MAX_TRAIL = 10;

function loadTrail() {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveTrail(trail) {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(trail));
  } catch {
    // Quota or disabled storage — silently ignore
  }
}

export function useNavigationTrail() {
  const location = useLocation();
  const navigate = useNavigate();

  // Track route changes
  useEffect(() => {
    const fullPath = `${location.pathname}${location.search}${location.hash}`;
    const current = loadTrail();
    const last = current[current.length - 1];

    // Skip if same path (modal openings, query-only changes within same page)
    if (last?.path === fullPath) return;

    const next = [
      ...current,
      {
        path: fullPath,
        pathname: location.pathname,
        timestamp: Date.now(),
      },
    ].slice(-MAX_TRAIL);

    saveTrail(next);
  }, [location.pathname, location.search, location.hash]);

  const trail = loadTrail();
  const previous = trail.length >= 2 ? trail[trail.length - 2] : null;

  const goBack = useCallback((fallback = '/') => {
    const t = loadTrail();
    if (t.length >= 2) {
      const prev = t[t.length - 2];
      // Pop current entry so navigating back doesn't immediately re-track
      saveTrail(t.slice(0, -1));
      navigate(prev.path);
    } else {
      navigate(fallback);
    }
  }, [navigate]);

  const addExplicit = useCallback((path) => {
    const t = loadTrail();
    saveTrail([...t, { path, pathname: path.split('?')[0], timestamp: Date.now() }].slice(-MAX_TRAIL));
  }, []);

  const clear = useCallback(() => {
    saveTrail([]);
  }, []);

  return {
    trail,
    previous,
    goBack,
    addExplicit,
    clear,
  };
}

export default useNavigationTrail;
