import React from 'react';
import ReactDOM from 'react-dom/client';
import axios from 'axios';
import App from './App';

// Default base URL for every axios call. When the app is served under a
// sub-path (e.g. /ai-jura/ behind a reverse proxy), set
// REACT_APP_API_BASE_URL at build time so bare `axios.get('/api/...')` calls
// resolve to `${baseURL}/api/...` instead of the site root. Leaving it unset
// keeps the existing behaviour (same-origin / CRA dev proxy).
axios.defaults.baseURL = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/$/, '');

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Register service worker for PWA functionality
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('SW registered: ', registration);
      })
      .catch((registrationError) => {
        console.log('SW registration failed: ', registrationError);
      });
  });
}