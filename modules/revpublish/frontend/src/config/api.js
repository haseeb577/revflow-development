// RevPublish API Configuration
// Updated: 2026-01-29

// API Base URL - Frontend makes requests to /api/
// Nginx proxies /api/ to http://localhost:3000/api/revpublish/
export const API_BASE_URL = '/api';

// API Endpoints
export const ENDPOINTS = {
  // Dashboard
  DASHBOARD_STATS: `${API_BASE_URL}/dashboard-stats`,
  
  // Sites Management
  SITES: `${API_BASE_URL}/sites`,
  SITE_DETAIL: (id) => `${API_BASE_URL}/sites/${id}`,
  
  // Content Queue
  QUEUE: `${API_BASE_URL}/queue`,
  
  // Deployments
  DEPLOYMENTS: `${API_BASE_URL}/deployments`,
  DEPLOYMENT_DETAIL: (id) => `${API_BASE_URL}/deployments/${id}`,
  
  // Legacy deploy endpoints (if needed)
  DEPLOY: `${API_BASE_URL}/deploy`,
};

// API Helper Functions
export async function fetchAPI(endpoint, options = {}) {
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export default {
  API_BASE_URL,
  ENDPOINTS,
  fetchAPI,
};
