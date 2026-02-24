import React, { useState, useEffect } from 'react'
import JSONRender from './components/JSONRender'
import './App.css'

export default function App() {
  // Map tabs to schema files
  const schemaMap = {
    dashboard: 'revscore-iq-dashboard',
    'new-assessment': 'revscore-iq-new-assessment',
    competitors: 'revscore-iq-competitors',
    configuration: 'revscore-iq-configuration',
    review: 'revscore-iq-review',
    progress: 'revscore-iq-progress',
    complete: 'revscore-iq-complete',
    'module-detail': 'revscore-iq-module-detail',
    competitive: 'revscore-iq-competitive',
    reports: 'revscore-iq-reports',
    'report-viewer': 'revscore-iq-report-viewer',
    appendices: 'revscore-iq-appendices',
    'appendix-viewer': 'revscore-iq-appendix-viewer',
    settings: 'revscore-iq-settings'
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
    document.title = 'RevScore IQ™ - Assessment Platform'
    loadSchema(activeTab)
  }, [activeTab])

  async function loadSchema(tab) {
    console.log('Loading schema for tab:', tab)
    
    try {
      setLoading(true)
      setError(null)
      
      const schemaName = schemaMap[tab]
      if (!schemaName) {
        throw new Error(`No schema mapping found for tab: ${tab}`)
      }
      
      // Vite serves public folder files from root
      // Try multiple paths to handle different environments
      const basePath = import.meta.env.BASE_URL || '/'
      const cleanBasePath = basePath === '/' ? '' : basePath.replace(/\/$/, '')
      
      // Try primary path first
      let schemaUrl = `${cleanBasePath}/schemas/${schemaName}.json`
      
      console.log('🔍 Loading schema:', schemaName)
      console.log('📥 Attempting path:', schemaUrl)
      console.log('📦 BASE_URL:', basePath, '| MODE:', import.meta.env.MODE)
      
      let response = await fetch(schemaUrl)
      
      // If 404, try alternative paths
      if (!response.ok && response.status === 404) {
        console.log('⚠️ Primary path failed, trying alternatives...')
        const alternatives = [
          `/schemas/${schemaName}.json`,
          `./schemas/${schemaName}.json`,
          `${window.location.origin}/schemas/${schemaName}.json`
        ]
        
        for (const altPath of alternatives) {
          console.log('🔄 Trying:', altPath)
          try {
            response = await fetch(altPath)
            if (response.ok) {
              schemaUrl = altPath
              console.log('✅ Found at:', altPath)
              break
            }
          } catch (e) {
            console.log('❌ Failed:', altPath)
          }
        }
      }
      
      if (!response.ok) {
        throw new Error(`Failed to load schema: ${response.status} ${response.statusText}. Tried: ${schemaUrl}`)
      }
      
      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text()
        console.error('Expected JSON but got:', text.substring(0, 200))
        throw new Error(`Invalid response: expected JSON but got ${contentType}`)
      }
      
      const schemaData = await response.json()
      console.log('✅ Schema loaded:', schemaData.name)
      
      setSchema(schemaData)
      setLoading(false)
    } catch (err) {
      console.error('❌ Schema load error:', err)
      setError(err.message)
      setLoading(false)
    }
  }

  const dashboardUrl = import.meta.env.VITE_DASHBOARD_URL || (typeof window !== 'undefined' ? window.location.origin + '/' : '/')

  return (
    <div className="revscore-iq-app">
      <div className="app-header">
        <div className="header-left">
          <a href={dashboardUrl} className="back-to-dashboard">
            <span className="back-icon">←</span>
            <span className="back-text">RevFlow OS</span>
          </a>
          <div className="header-title">
            <h1>RevScore IQ™</h1>
            <p>Professional Website Assessment Platform</p>
          </div>
        </div>
        <div className="header-badge">Module 2</div>
      </div>
      
      <div className="app-nav">
        {Object.keys(schemaMap).map(tab => (
          <button
            key={tab}
            className={`nav-btn ${activeTab === tab ? 'active' : ''}`}
            onClick={() => handleTabChange(tab)}
          >
            {tab.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
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

