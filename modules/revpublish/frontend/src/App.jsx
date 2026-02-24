import React, { useState, useEffect } from 'react'
import JSONRender from './components/JSONRender'
import './App.css'

export default function App() {
  // Map tabs to schema files
  const schemaMap = {
    dashboard: 'revpublish-dashboard',
    sites: 'revpublish-sites',
    animation: 'revpublish-animation',
    images: 'revpublish-images',
    queue: 'revpublish-queue',
    deploy: 'revpublish-deploy',
    import: 'revpublish-import',
    conflicts: 'revpublish-conflicts',
    history: 'revpublish-history'
  }

  // Get initial tab from URL hash or default to dashboard
  const getTabFromHash = () => {
    const hash = window.location.hash.replace('#', '')
    return schemaMap[hash] ? hash : 'dashboard'
  }

  const [activeTab, setActiveTab] = useState(getTabFromHash)
  const [schema, setSchema] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Handle tab change - update URL hash
  const handleTabChange = (tab) => {
    window.location.hash = tab
    setActiveTab(tab)
  }

  // Listen for hash changes (back/forward buttons)
  useEffect(() => {
    const handleHashChange = () => {
      setActiveTab(getTabFromHash())
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  useEffect(() => {
    document.title = 'RevPublish™ - WordPress Publishing Automation'
    loadSchema(activeTab)
  }, [activeTab])

  async function loadSchema(tab) {
    console.log('🔍 Loading schema for tab:', tab)
    
    try {
      setLoading(true)
      setError(null)
      
      const schemaName = schemaMap[tab]
      const basePath = import.meta.env.BASE_URL || '/'
      const schemaUrl = `${basePath}schemas/${schemaName}.json`
      
      console.log('📥 Fetching:', schemaUrl)
      const response = await fetch(schemaUrl)
      
      if (!response.ok) {
        throw new Error(`Failed to load schema: ${response.status}`)
      }
      
      const schemaData = await response.json()
      console.log('✅ Schema loaded:', schemaData.name)
      
      setSchema(schemaData)
      setLoading(false)
    } catch (err) {
      console.error('💥 Schema load error:', err)
      setError(err.message)
      setLoading(false)
    }
  }

  // const dashboardUrl = 'http://217.15.168.106:3000/'
  const dashboardUrl = import.meta.env.VITE_DASHBOARD_URL || (typeof window !== 'undefined' ? window.location.origin + '/' : '/')

  return (
    <div className="revpublish-app">
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
                cursor: 'pointer'
              }}
            >
              Retry
            </button>
          </div>
        )}
        
        {!loading && !error && schema && (
          <JSONRender config={schema} />
        )}
      </div>
    </div>
  )
}
