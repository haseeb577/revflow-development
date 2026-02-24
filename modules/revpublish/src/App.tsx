import React, { useState, useEffect } from 'react';
// @ts-ignore - JSONRender is a JSX component
import JSONRender from '../frontend/src/components/JSONRender';
import '../frontend/src/App.css';

export default function RevpublishApp() {
  // Map tabs to schema files
  const schemaMap: { [key: string]: string } = {
    dashboard: 'revpublish-dashboard',
    sites: 'revpublish-sites',
    animation: 'revpublish-animation',
    images: 'revpublish-images',
    queue: 'revpublish-queue',
    deploy: 'revpublish-deploy',
    import: 'revpublish-import',
    conflicts: 'revpublish-conflicts',
    history: 'revpublish-history'
  };

  // Get initial tab from URL hash or default to dashboard
  const getTabFromHash = (): string => {
    if (typeof window === 'undefined') return 'dashboard';
    const hash = window.location.hash.replace('#', '');
    return schemaMap[hash] ? hash : 'dashboard';
  };

  const [activeTab, setActiveTab] = useState<string>(getTabFromHash);
  const [schema, setSchema] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Handle tab change - update URL hash
  const handleTabChange = (tab: string) => {
    if (typeof window !== 'undefined') {
      window.location.hash = tab;
    }
    setActiveTab(tab);
  };

  // Listen for hash changes (back/forward buttons)
  useEffect(() => {
    const handleHashChange = () => {
      setActiveTab(getTabFromHash());
    };
    if (typeof window !== 'undefined') {
      window.addEventListener('hashchange', handleHashChange);
      return () => window.removeEventListener('hashchange', handleHashChange);
    }
  }, []);

  useEffect(() => {
    // Set document title
    document.title = 'RevPublish™ - WordPress Publishing Automation';
    loadSchema(activeTab);
  }, [activeTab]);

  const loadSchema = async (tab: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const schemaName = schemaMap[tab];
      const basePath = '/revflow_os/revpublish/';
      
      // Try multiple paths to find the schema
      const schemaPaths = [
        `${basePath}schemas/${schemaName}.json`,  // With base path
        `/schemas/${schemaName}.json`,  // Without base path
        `${basePath}frontend/public/schemas/${schemaName}.json`,  // Full path
      ];
      
      let loaded = false;
      let lastError: Error | null = null;
      
      for (const schemaUrl of schemaPaths) {
        try {
          console.log('📥 Fetching schema from:', schemaUrl);
          const response = await fetch(schemaUrl);
          
          if (response.ok) {
            // Check if response is actually JSON (not HTML error page)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
              const data = await response.json();
              console.log('✅ Schema loaded:', data.name);
              setSchema(data);
              loaded = true;
              break;
            } else {
              console.warn('⚠️ Response is not JSON, trying next path...');
              continue;
            }
          }
        } catch (err) {
          lastError = err instanceof Error ? err : new Error(String(err));
          console.warn('⚠️ Failed to load from:', schemaUrl, err);
          continue;
        }
      }
      
      if (!loaded) {
        throw lastError || new Error(`Failed to load schema: ${schemaName}.json not found`);
      }
      setLoading(false);
    } catch (err) {
      console.error('Error loading schema:', err);
      setError(err instanceof Error ? err.message : 'Failed to load schema');
      setLoading(false);
    }
  };

  const dashboardUrl = typeof window !== 'undefined' ? window.location.origin + '/' : '/';

  return (
    <div className="revpublish-app">
      {/* Header Section */}
      <div className="app-header">
        <div className="header-left">
          <a href={dashboardUrl} className="back-to-dashboard">
            <span className="back-icon">←</span>
            <span className="back-text">RevFlow OS</span>
          </a>
          <div className="header-title">
            <h1>RevPublish™</h1>
            <p>WordPress Publishing Automation Platform</p>
          </div>
        </div>
        <div className="header-badge">Module 9</div>
      </div>

      {/* Navigation Tabs */}
      <div className="app-nav">
        {Object.keys(schemaMap).map(tab => (
          <button
            key={tab}
            className={`nav-btn ${activeTab === tab ? 'active' : ''}`}
            onClick={() => handleTabChange(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <div className="app-main">
        {loading && (
          <div style={{ 
            padding: '3rem', 
            textAlign: 'center', 
            color: '#94a3b8',
            fontSize: '1.2rem'
          }}>
            <div>Loading {activeTab}...</div>
          </div>
        )}
        
        {error && (
          <div style={{ 
            padding: '2rem',
            margin: '2rem',
            background: '#7f1d1d',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            color: '#fff'
          }}>
            <h3 style={{ marginTop: 0 }}>Error Loading {activeTab}</h3>
            <p>{error}</p>
            <button 
              onClick={() => loadSchema(activeTab)}
              style={{
                padding: '0.5rem 1rem',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                marginTop: '1rem'
              }}
            >
              Retry
            </button>
            <div style={{ marginTop: '1rem', fontSize: '0.875rem', opacity: 0.8 }}>
              <p>Note: If the backend is not running, some features may not work.</p>
              <p>API calls will fail, but the dashboard structure should still display.</p>
            </div>
          </div>
        )}
        
        {!loading && !error && schema && (
          <JSONRender config={schema} />
        )}
      </div>
    </div>
  );
}
