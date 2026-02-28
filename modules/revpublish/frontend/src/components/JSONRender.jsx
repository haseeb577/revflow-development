import React, { useState, useEffect } from 'react'
import ImageUploadBrowser from './ImageUploadBrowser'

function normalizeApiUrl(url, basePath = '/') {
  const raw = String(url || '').trim()
  const bp = basePath || '/'
  if (!raw || raw === '/' || raw === bp) return null
  if (raw.startsWith('/api/')) return raw
  if (raw.startsWith('/')) return `${bp}${raw.slice(1)}`
  return `${bp}${raw}`
}

/**
 * Dynamic Select Component - Fetches options from API
 */
function DynamicSelect({ field, basePath }) {
  const [options, setOptions] = useState(field.options || [])
  const [loading, setLoading] = useState(false)
  const [dependencyValue, setDependencyValue] = useState('')
  
  // Get last selected site from localStorage if this is a site selector
  const getInitialValue = () => {
    if (field.name === 'target_site' || field.name === 'site_id') {
      try {
        const lastSite = localStorage.getItem('revpublish_last_selected_site')
        if (lastSite) {
          const siteInfo = JSON.parse(lastSite)
          // Return site_url for target_site, or id for site_id
          if (field.name === 'target_site') {
            return siteInfo.site_url || ''
          } else if (field.name === 'site_id') {
            return siteInfo.id || siteInfo.site_id || ''
          }
        }
      } catch (e) {
        console.warn('⚠️ Could not parse last selected site:', e)
      }
    }
    return field.default || ''
  }
  
  const [selectedValue, setSelectedValue] = useState(getInitialValue())

  useEffect(() => {
    if (!field.dependsOn) return undefined

    const readDependencyValue = () => {
      const dependencyEl = document.querySelector(`[name="${field.dependsOn}"]`)
      const nextValue = dependencyEl ? String(dependencyEl.value || '').trim() : ''
      setDependencyValue(prev => (prev === nextValue ? prev : nextValue))
    }

    readDependencyValue()
    const intervalId = window.setInterval(readDependencyValue, 400)
    return () => window.clearInterval(intervalId)
  }, [field.dependsOn])

  useEffect(() => {
    if (field.dataSource) {
      setLoading(true)

      // Handle dataSource as string URL or object with url property
      const url = typeof field.dataSource === 'string'
        ? field.dataSource
        : (field.dataSource.url || field.dataSource)

      // Build the full API URL
      // For /api/* endpoints, use directly (Vite proxy handles it)
      // For other paths, prepend basePath
      let apiUrl = url
      const basePathValue = import.meta.env.BASE_URL || '/'

      // Support dynamic URLs like /api/site-pages?site_url={target_site}
      // so one select can depend on another field value.
      apiUrl = String(apiUrl).replace(/\{([^}]+)\}/g, (_, key) => {
        const sourceEl = document.querySelector(`[name="${key}"]`)
        return sourceEl ? encodeURIComponent(String(sourceEl.value || '').trim()) : ''
      })
      
      // Strip any existing basePath if url already has it
      if (url.startsWith(basePathValue) && url.includes('/api/')) {
        // Remove basePath prefix if it exists
        apiUrl = url.replace(basePathValue, '/')
      }
      
      // If it's an API endpoint, use it directly (proxy will handle it)
      // Don't prepend basePath for /api/ endpoints
      if (!apiUrl.startsWith('/api/')) {
        // Only prepend basePath for non-API endpoints
        if (url.startsWith('/')) {
          // Other absolute path - prepend basePath
          apiUrl = `${basePathValue}${url.slice(1)}`
        } else {
          // Relative path
          apiUrl = `${basePathValue}${url}`
        }
      }
      // If apiUrl starts with /api/, use it as-is (Vite proxy handles it)
      apiUrl = normalizeApiUrl(apiUrl, basePathValue)
      if (!apiUrl) {
        console.warn('⚠️ DynamicSelect skipped invalid URL:', url)
        setOptions([{ label: 'Invalid data source URL', value: '' }])
        setLoading(false)
        return
      }

      console.log('📥 DynamicSelect fetching from:', apiUrl, '(url was:', url, ')')

      // If dependency is required and still not selected, keep select empty.
      if (field.dependsOn && !dependencyValue) {
        setOptions([{
          label: field.dependsOnPlaceholder || 'Select site first',
          value: ''
        }])
        setLoading(false)
        return
      }

      fetch(apiUrl)
        .then(res => {
          // Check content type first
          const contentType = res.headers.get('content-type') || ''
          if (!contentType.includes('application/json')) {
            return res.text().then(text => {
              console.error('❌ DynamicSelect got non-JSON response:', text.substring(0, 200))
              throw new Error(`Expected JSON but got ${contentType}. Response: ${text.substring(0, 100)}`)
            })
          }
          if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
          return res.json()
        })
        .then(data => {
          console.log('📦 DynamicSelect received data:', data)

          // Get dataPath from field.dataPath or field.dataSource.dataPath
          const dataPath = field.dataPath ||
            (typeof field.dataSource === 'object' ? field.dataSource.dataPath : null)

          console.log(`📋 DynamicSelect dataPath: ${dataPath}, field.dataPath: ${field.dataPath}`)

          // Extract items array from response
          let items = []
          if (dataPath && data[dataPath]) {
            items = data[dataPath]
            console.log(`✅ Found items in dataPath "${dataPath}": ${items.length} items`)
          } else if (Array.isArray(data)) {
            items = data
            console.log(`✅ Data is array: ${items.length} items`)
          } else if (data.sites) {
            items = data.sites
            console.log(`✅ Found items in data.sites: ${items.length} items`)
          } else if (data.data) {
            items = data.data
            console.log(`✅ Found items in data.data: ${items.length} items`)
          } else {
            console.warn('⚠️ No items found in response. Data keys:', Object.keys(data))
          }

          // Get label and value field names
          const labelKey = field.labelField ||
            (typeof field.dataSource === 'object' ? field.dataSource.labelKey : null) ||
            'site_name'
          const valueKey = field.valueField ||
            (typeof field.dataSource === 'object' ? field.dataSource.valueKey : null) ||
            'id'

          console.log(`📋 Using labelKey=${labelKey}, valueKey=${valueKey}, items count=${items.length}`)

          if (items.length === 0) {
            console.warn('⚠️ No items to display in select. Setting empty options.')
            console.warn('   Full response data:', data)
            setOptions([{
              label: 'No sites available - Discover sites first',
              value: ''
            }])
          } else {
            const dynamicOptions = items.map(item => ({
              label: item[labelKey] || item.name || item.label || 'Unknown',
              value: item[valueKey] || item.id || item.value
            }))

            console.log(`✅ DynamicSelect loaded ${dynamicOptions.length} options:`, dynamicOptions.slice(0, 3))
            setOptions(dynamicOptions)
            
            // Auto-select last saved site if available and not already selected
            if ((field.name === 'target_site' || field.name === 'site_id') && !selectedValue) {
              try {
                const lastSite = localStorage.getItem('revpublish_last_selected_site')
                if (lastSite) {
                  const siteInfo = JSON.parse(lastSite)
                  let valueToSelect = ''
                  
                  if (field.name === 'target_site') {
                    valueToSelect = siteInfo.site_url || ''
                  } else if (field.name === 'site_id') {
                    valueToSelect = siteInfo.id || siteInfo.site_id || ''
                  }
                  
                  // Check if the value exists in options
                  if (valueToSelect && dynamicOptions.some(opt => opt.value === valueToSelect || opt.value === String(valueToSelect))) {
                    setSelectedValue(valueToSelect)
                    console.log(`✅ Auto-selected last saved site: ${valueToSelect}`)
                  }
                }
              } catch (e) {
                console.warn('⚠️ Could not auto-select last site:', e)
              }
            }
          }
          setLoading(false)
        })
        .catch(err => {
          console.error('❌ DynamicSelect error:', err)
          console.error('   URL attempted:', apiUrl)
          console.error('   Original URL:', url)
          console.error('   Error details:', err.message)
          
          // Show error in UI if no fallback options
          if (!field.options || field.options.length === 0) {
            setOptions([{
              label: `Error loading sites: ${err.message.substring(0, 50)}`,
              value: '',
              disabled: true
            }])
          } else {
            // Fall back to static options if available
            console.log('📋 Falling back to static options')
            setOptions(field.options)
          }
          setLoading(false)
        })
    }
  }, [field.dataSource, basePath, field.dataPath, field.labelField, field.valueField, field.dependsOn, dependencyValue])

  const handleChange = (e) => {
    setSelectedValue(e.target.value)
    if (field.name === 'target_site') {
      try {
        const selectedOption = e.target.options[e.target.selectedIndex]
        localStorage.setItem('revpublish_last_selected_site', JSON.stringify({
          site_url: e.target.value,
          site_name: selectedOption?.text || ''
        }))
      } catch (_) {}
      window.dispatchEvent(new Event('revpublish_target_site_changed'))
    }
    if (field.name === 'existing_page_id' || field.name === 'target_page_id') {
      window.dispatchEvent(new Event('revpublish_existing_page_changed'))
    }
  }

  return (
    <select
      name={field.name}
      value={selectedValue}
      onChange={handleChange}
      required={field.required}
      disabled={loading}
      style={{
        padding: '0.75rem',
        borderRadius: '6px',
        border: '1px solid #334155',
        background: '#1e293b',
        color: '#fff',
        width: '100%',
        fontSize: '1rem',
        cursor: loading ? 'wait' : 'pointer'
      }}
    >
      <option value="">{loading ? '⏳ Loading sites...' : (field.placeholder || 'Select...')}</option>
      {options.map((opt, j) => (
        <option key={j} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  )
}

/**
 * JSON Viewer element for selected page Elementor data
 */
function JsonViewerElement({ element }) {
  const [jsonText, setJsonText] = useState('Select a site and page to view Elementor JSON.')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    const onChanged = () => setRefresh(v => v + 1)
    window.addEventListener('revpublish_target_site_changed', onChanged)
    window.addEventListener('revpublish_existing_page_changed', onChanged)
    return () => {
      window.removeEventListener('revpublish_target_site_changed', onChanged)
      window.removeEventListener('revpublish_existing_page_changed', onChanged)
    }
  }, [])

  useEffect(() => {
    const endpoint = element?.dataSource?.endpoint
    if (!endpoint) return

    let apiUrl = String(endpoint).replace(/\{([^}]+)\}/g, (_, key) => {
      const sourceEl = document.querySelector(`[name="${key}"]`)
      return sourceEl ? encodeURIComponent(String(sourceEl.value || '').trim()) : ''
    })
    apiUrl = normalizeApiUrl(apiUrl, import.meta.env.BASE_URL || '/')
    if (!apiUrl) {
      setJsonText('Select a site and page to view Elementor JSON.')
      setError(null)
      return
    }

    if (apiUrl.includes('site_url=&') || apiUrl.endsWith('site_url=') || apiUrl.includes('page_id=&') || apiUrl.endsWith('page_id=')) {
      setJsonText('Select a site and page to view Elementor JSON.')
      setError(null)
      return
    }

    setLoading(true)
    setError(null)
    fetch(apiUrl, { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        const txt = await res.text()
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${txt.substring(0, 180)}`)
        }
        try {
          return JSON.parse(txt)
        } catch (_) {
          throw new Error(`Invalid JSON response: ${txt.substring(0, 180)}`)
        }
      })
      .then((payload) => {
        const display = payload?.elementor_data ?? payload
        setJsonText(JSON.stringify(display, null, 2))
      })
      .catch((err) => {
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [element?.dataSource?.endpoint, refresh])

  return (
    <div style={{
      marginTop: '1rem',
      padding: '1rem',
      borderRadius: '8px',
      border: '1px solid rgba(99, 102, 241, 0.25)',
      background: 'rgba(15, 23, 42, 0.5)',
      ...element.style
    }}>
      {element.title && <h4 style={{ margin: '0 0 0.75rem 0', color: '#fff' }}>{element.title}</h4>}
      {loading && <div style={{ color: '#94a3b8', marginBottom: '0.75rem' }}>Loading JSON...</div>}
      {error && <div style={{ color: '#fca5a5', marginBottom: '0.75rem' }}>Error: {error}</div>}
      <pre style={{
        margin: 0,
        maxHeight: element.maxHeight || '420px',
        overflow: 'auto',
        background: '#0b1220',
        color: '#e2e8f0',
        padding: '0.9rem',
        borderRadius: '6px',
        border: '1px solid #1e293b',
        fontSize: '0.8rem',
        lineHeight: 1.4,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word'
      }}>
        {jsonText}
      </pre>
    </div>
  )
}

/**
 * Build and download a page-specific slot template.
 */
function ContentTemplateBuilderElement({ element }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [templateText, setTemplateText] = useState('')
  const [slotCount, setSlotCount] = useState(0)
  const [fileName, setFileName] = useState('content-template.txt')

  const handleGenerate = async () => {
    const siteEl = document.querySelector('[name="target_site"]')
    const pageEl = document.querySelector('[name="target_page_id"]')
    const site = siteEl ? String(siteEl.value || '').trim() : ''
    const pageId = pageEl ? String(pageEl.value || '').trim() : ''
    if (!site || !pageId) {
      setError('Select site and target page first.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const basePath = import.meta.env.BASE_URL || '/'
      const endpoint = `/api/page-content-template?site_url=${encodeURIComponent(site)}&page_id=${encodeURIComponent(pageId)}`
      const apiUrl = normalizeApiUrl(endpoint, basePath)
      const res = await fetch(apiUrl, { headers: { Accept: 'application/json' } })
      const txt = await res.text()
      let payload = {}
      try {
        payload = JSON.parse(txt)
      } catch (_) {
        throw new Error(`Invalid JSON response: ${txt.substring(0, 180)}`)
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${payload?.detail || txt.substring(0, 200)}`)
      setTemplateText(payload.template_text || '')
      setSlotCount(Number(payload.slot_count || 0))
      setFileName(payload.template_filename || 'content-template.txt')
    } catch (e) {
      setError(e.message || 'Template generation failed')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!templateText) return
    const blob = new Blob([templateText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{
      marginTop: '1rem',
      padding: '1rem',
      borderRadius: '8px',
      border: '1px solid rgba(59,130,246,0.25)',
      background: 'rgba(15, 23, 42, 0.5)',
      ...element.style
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <h4 style={{ margin: 0, color: '#fff' }}>{element.title || 'Page Content Template'}</h4>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={loading}
            style={{ padding: '0.55rem 0.95rem', border: 'none', borderRadius: '6px', background: loading ? '#475569' : '#2563eb', color: '#fff', cursor: loading ? 'not-allowed' : 'pointer' }}
          >
            {loading ? 'Generating...' : 'Generate Template'}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            disabled={!templateText}
            style={{ padding: '0.55rem 0.95rem', border: 'none', borderRadius: '6px', background: templateText ? '#16a34a' : '#475569', color: '#fff', cursor: templateText ? 'pointer' : 'not-allowed' }}
          >
            Download Template
          </button>
        </div>
      </div>
      {slotCount > 0 && <div style={{ color: '#94a3b8', marginTop: '0.6rem' }}>Detected slots: {slotCount}</div>}
      {error && <div style={{ color: '#fca5a5', marginTop: '0.6rem' }}>Error: {error}</div>}
      {templateText && (
        <pre style={{ marginTop: '0.75rem', maxHeight: element.maxHeight || '320px', overflow: 'auto', background: '#0b1220', color: '#e2e8f0', padding: '0.9rem', borderRadius: '6px', border: '1px solid #1e293b', fontSize: '0.8rem' }}>
          {templateText}
        </pre>
      )}
    </div>
  )
}

/**
 * Content Mapping Preview element:
 * compares selected page JSON with CSV doc content JSON.
 */
function ContentMappingPreviewElement({ element }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    const onChanged = () => {
      setRefresh(v => v + 1)
      setResult(null)
      setError(null)
    }
    window.addEventListener('revpublish_target_site_changed', onChanged)
    window.addEventListener('revpublish_existing_page_changed', onChanged)
    return () => {
      window.removeEventListener('revpublish_target_site_changed', onChanged)
      window.removeEventListener('revpublish_existing_page_changed', onChanged)
    }
  }, [])

  const handleGeneratePreview = async () => {
    const siteEl = document.querySelector('[name="target_site"]')
    const pageEl = document.querySelector('[name="target_page_id"]')
    const csvEl = document.querySelector('input[name="csv_file"]')
    const site = siteEl ? String(siteEl.value || '').trim() : ''
    const pageId = pageEl ? String(pageEl.value || '').trim() : ''
    const csvFile = csvEl?.files?.[0]

    if (!site || !pageId) {
      setError('Select a site and target page first.')
      return
    }
    if (!csvFile) {
      setError('Upload a CSV file first.')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const basePath = import.meta.env.BASE_URL || '/'
      const apiUrl = normalizeApiUrl('/api/content-json-preview', basePath)
      const form = new FormData()
      form.append('site_url', site)
      form.append('target_page_id', pageId)
      form.append('csv_file', csvFile)

      const res = await fetch(apiUrl, { method: 'POST', body: form })
      const txt = await res.text()
      let payload = null
      try {
        payload = JSON.parse(txt)
      } catch (_) {
        throw new Error(`Invalid JSON response: ${txt.substring(0, 180)}`)
      }
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${payload?.detail || txt.substring(0, 180)}`)
      }
      setResult(payload)
    } catch (e) {
      setError(e.message || 'Failed to generate preview')
    } finally {
      setLoading(false)
    }
  }

  const cmp = result?.comparison || null
  return (
    <div key={`content-preview-${refresh}`} style={{
      marginTop: '1rem',
      padding: '1rem',
      borderRadius: '8px',
      border: '1px solid rgba(34, 197, 94, 0.3)',
      background: 'rgba(15, 23, 42, 0.55)',
      ...element.style
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        {element.title && <h4 style={{ margin: 0, color: '#fff' }}>{element.title}</h4>}
        <button
          type="button"
          onClick={handleGeneratePreview}
          disabled={loading}
          style={{
            padding: '0.6rem 1rem',
            borderRadius: '6px',
            border: 'none',
            background: loading ? '#475569' : 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
            color: '#fff',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 600
          }}
        >
          {loading ? 'Generating...' : 'Generate Content Mapping Preview'}
        </button>
      </div>

      {error && <div style={{ color: '#fca5a5', marginTop: '0.75rem' }}>Error: {error}</div>}

      {cmp && (
        <div style={{ marginTop: '0.9rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.6rem' }}>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.7rem', borderRadius: '6px', color: '#e2e8f0' }}>
            Template Match: <strong>{cmp.template_match_percent}%</strong>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.7rem', borderRadius: '6px', color: '#e2e8f0' }}>
            Content Usage: <strong>{cmp.content_usage_percent}%</strong>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.7rem', borderRadius: '6px', color: '#e2e8f0' }}>
            Replaced: <strong>{cmp.replaced_total}</strong> / {cmp.found_total}
          </div>
        </div>
      )}

      {result && (
        <div style={{ marginTop: '0.9rem', display: 'grid', gridTemplateColumns: '1fr', gap: '0.8rem' }}>
          <div>
            <div style={{ color: '#94a3b8', marginBottom: '0.35rem' }}>Content JSON (from docs)</div>
            <pre style={{ margin: 0, maxHeight: '250px', overflow: 'auto', background: '#0b1220', color: '#e2e8f0', padding: '0.75rem', borderRadius: '6px', border: '1px solid #1e293b', fontSize: '0.8rem' }}>
              {JSON.stringify(result.content_json, null, 2)}
            </pre>
          </div>
          <div>
            <div style={{ color: '#94a3b8', marginBottom: '0.35rem' }}>Merged Preview JSON (content replaced, style preserved)</div>
            <pre style={{ margin: 0, maxHeight: element.maxHeight || '420px', overflow: 'auto', background: '#0b1220', color: '#e2e8f0', padding: '0.75rem', borderRadius: '6px', border: '1px solid #1e293b', fontSize: '0.8rem' }}>
              {JSON.stringify(result.merged_preview_json, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * DataTable Element - Handles its own data fetching
 */
function DataTableElement({ element, contextData }) {
  const [tableData, setTableData] = useState([])
  const [loading, setLoading] = useState(false) // Start with false, only set true if we're actually fetching
  const [error, setError] = useState(null)

  useEffect(() => {
    // If element has its own dataSource, fetch it
    if (element.dataSource?.endpoint) {
      const basePath = import.meta.env.BASE_URL || '/'
      let apiUrl = element.dataSource.endpoint
      // if (apiUrl.startsWith('/api/')) {
      //   apiUrl = `${basePath}${apiUrl.slice(1)}`
      // }

      if (!apiUrl.startsWith('/api/')) {
        apiUrl = apiUrl.startsWith('/') ? `${basePath}${apiUrl.slice(1)}` : `${basePath}${apiUrl}`
      }

      console.log('📥 DataTable fetching from:', apiUrl)
      // Only show loading if dataSource is required
      const isRequired = element.dataSource?.required !== false
      if (isRequired) {
        setLoading(true)
      }

      fetch(apiUrl)
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          return res.json()
        })
        .then(data => {
          console.log('✅ DataTable received:', data)
          const dataPath = element.dataSource.dataPath || element.dataPath
          const items = dataPath ? data[dataPath] : (Array.isArray(data) ? data : [])
          setTableData(items || [])
          setLoading(false)
        })
        .catch(err => {
          console.error('❌ DataTable error:', err)
          // Only show error if dataSource is required
          const isRequired = element.dataSource?.required !== false
          if (isRequired) {
            setError(err.message)
          } else {
            // For optional dataSource, just log and show empty
            console.log('⚠️ Optional DataTable dataSource failed, showing empty')
            setTableData([])
          }
          setLoading(false)
        })
    } else if (contextData !== null && contextData !== undefined) {
      // Use context data with dataPath - no loading needed, data is already available
      // contextData might be empty object { sites: [], total: 0 } which is valid
      const items = element.dataPath ? (contextData[element.dataPath] || []) : []
      setTableData(Array.isArray(items) ? items : [])
      setLoading(false)
    } else {
      // No data source and no context data - show empty (don't show loading)
      setTableData([])
      setLoading(false)
    }
  }, [element.dataSource, element.dataPath, contextData])

  // Only show loading if we're actually loading AND dataSource is required
  const isRequired = element.dataSource?.required !== false
  if (loading && isRequired) {
    return <div style={{ padding: '1rem', color: '#94a3b8' }}>Loading data...</div>
  }

  if (error) {
    return <div style={{ padding: '1rem', color: '#ef4444' }}>Error: {error}</div>
  }

  if (!tableData || tableData.length === 0) {
    return <div style={{ padding: '1rem', color: '#94a3b8' }}>{element.emptyMessage || 'No data available'}</div>
  }

  // Get badge color for a value
  const getBadgeColor = (col, value) => {
    if (col.colorMap) {
      return col.colorMap[value] || col.colorMap.default || '#64748b'
    }
    return '#64748b'
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      {element.title && <h4 style={{ marginBottom: '1rem', color: '#fff' }}>{element.title}</h4>}
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        ...element.style
      }}>
        <thead>
          <tr style={{ background: '#0f172a' }}>
            {element.columns?.map((col, i) => (
              <th key={i} style={{
                padding: '0.75rem',
                textAlign: 'left',
                borderBottom: '2px solid #334155',
                color: '#94a3b8',
                fontSize: '0.875rem',
                fontWeight: '600',
                width: col.width || 'auto'
              }}>
                {col.label || col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tableData.map((row, i) => (
            <tr key={i} style={{
              borderBottom: '1px solid #334155',
              background: i % 2 === 0 ? 'transparent' : 'rgba(15, 23, 42, 0.5)'
            }}>
              {element.columns?.map((col, j) => {
                const value = row[col.key || col.field]
                const displayValue = typeof value === 'number' && col.key?.includes('performance')
                  ? value.toFixed(1)
                  : value

                return (
                  <td key={j} style={{
                    padding: '0.75rem',
                    color: '#e2e8f0',
                    fontWeight: col.bold ? '600' : '400'
                  }}>
                    {col.type === 'badge' ? (
                      <span style={{
                        display: 'inline-block',
                        padding: '0.25rem 0.5rem',
                        background: `${getBadgeColor(col, value)}22`,
                        color: getBadgeColor(col, value),
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        textTransform: 'capitalize'
                      }}>
                        {displayValue}
                      </span>
                    ) : col.type === 'link' ? (
                      <a href={value} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6' }}>
                        {value}
                      </a>
                    ) : (
                      displayValue
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: '0.75rem', color: '#64748b', fontSize: '0.875rem' }}>
        Showing {tableData.length} rows
      </div>
    </div>
  )
}

/**
 * StatsGrid Element - Handles its own data fetching
 */
function StatsGridElement({ element }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (element.dataSource?.endpoint) {
      const basePath = import.meta.env.BASE_URL || '/'
      let apiUrl = element.dataSource.endpoint
      // 
      if (!apiUrl.startsWith('/api/')) {
        apiUrl = apiUrl.startsWith('/') ? `${basePath}${apiUrl.slice(1)}` : `${basePath}${apiUrl}`
      }

      console.log('📥 StatsGrid fetching from:', apiUrl)

      fetch(apiUrl)
        .then(res => res.json())
        .then(data => {
          console.log('✅ StatsGrid received:', data)
          setStats(data)
          setLoading(false)
        })
        .catch(err => {
          console.error('❌ StatsGrid error:', err)
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [element.dataSource])

  // Get value from nested path like "stats.total_templates"
  const getValue = (dataKey) => {
    if (!stats || !dataKey) return '...'
    const parts = dataKey.split('.')
    let value = stats
    for (const part of parts) {
      value = value?.[part]
    }
    return value ?? '0'
  }

  if (loading) {
    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${element.columns || 4}, 1fr)`,
        gap: element.gap || '1rem'
      }}>
        {element.cards?.map((_, i) => (
          <div key={i} style={{
            background: '#1e293b',
            padding: '1.5rem',
            borderRadius: '8px',
            animation: 'pulse 2s infinite'
          }}>
            <div style={{ height: '2rem', background: '#334155', borderRadius: '4px', marginBottom: '0.5rem' }} />
            <div style={{ height: '1rem', background: '#334155', borderRadius: '4px', width: '60%' }} />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(${element.columns || 4}, 1fr)`,
      gap: element.gap || '1rem'
    }}>
      {element.cards?.map((card, i) => (
        <div key={i} style={{
          background: '#1e293b',
          padding: '1.5rem',
          borderRadius: '8px',
          borderLeft: `4px solid ${card.color || '#3b82f6'}`,
          textAlign: 'center'
        }}>
          {card.icon && (
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>{card.icon}</div>
          )}
          <div style={{
            fontSize: '2rem',
            fontWeight: 'bold',
            color: card.color || '#fff',
            marginBottom: '0.5rem'
          }}>
            {card.dataKey ? getValue(card.dataKey) : (card.value || '0')}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '0.875rem' }}>{card.label}</div>
        </div>
      ))}
    </div>
  )
}

/**
 * Enhanced JSON Render - Full RevFlow OS UI Engine
 * Handles: Forms, Tables, File Uploads, Actions, Modals
 */
export default function JSONRender({ config }) {
  // Start with loading false and initial empty data for optional dataSource
  // Default to optional (not required) if config is not available yet
  const isRequiredInitially = config?.dataSource?.required !== false
  const [data, setData] = useState(isRequiredInitially ? null : { sites: [], total: 0, status: 'success' })
  const [loading, setLoading] = useState(false) // Start with false, only set true if required
  const [error, setError] = useState(null)
  const [formData, setFormData] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)
  const [showAlert, setShowAlert] = useState(false) // Control alert visibility to prevent duplication

  useEffect(() => {
    console.log('📦 JSONRender received config:', config?.name)
    // Workaround: If "All Sites" header is missing dynamicText/textTemplate, add them
    // This handles cases where the JSON file is cached or properties are lost
    if (config?.layout?.children) {
      const allSitesContainer = config.layout.children.find(c => 
        c.type === 'container' && 
        c.children && 
        c.children.some(child => child.type === 'header' && child.text && (child.text.includes('All Sites') || child.text.includes('📊')))
      )
      if (allSitesContainer) {
        const header = allSitesContainer.children.find(c => 
          c.type === 'header' && c.text && (c.text.includes('All Sites') || c.text.includes('📊'))
        )
        if (header && (!header.dynamicText || !header.textTemplate)) {
          console.log('⚠️ All Sites header missing dynamicText/textTemplate, adding them programmatically')
          header.dynamicText = true
          header.textTemplate = '📊 All Sites ({{total}})'
          console.log('✅ Added dynamicText properties to header:', header)
        }
      }
    }
    
    // Only show loading if dataSource is required (not optional)
    const isRequired = config?.dataSource?.required !== false
    
    if (config?.dataSource?.endpoint && isRequired) {
      // Required dataSource - show loading
      setLoading(true)
      setError(null)
      setData(null) // Clear data while loading
      
      // Add a safety timeout - if loading takes too long, show error
      const safetyTimeout = setTimeout(() => {
        console.warn('⚠️ Loading taking too long (15s), forcing error state')
        setError('Loading is taking longer than expected. Please check if backend is running on port 8550.')
        setLoading(false)
      }, 15000) // 15 second safety timeout
      
      loadData(config.dataSource.endpoint, true) // true = set loading state
        .then(() => {
          clearTimeout(safetyTimeout)
        })
        .catch(() => {
          clearTimeout(safetyTimeout)
        })
    } else {
      // If dataSource is optional or doesn't exist, don't show loading
      setLoading(false)
      setError(null)
      // Set initial empty data so page can render immediately
      setData({ sites: [], total: 0, status: 'success' })
      
      // Try to load data in background if endpoint exists (optional)
      // Don't set loading state for optional dataSource
      if (config?.dataSource?.endpoint && !isRequired) {
        loadData(config.dataSource.endpoint, false) // false = don't set loading state
          .then(() => {
            console.log('✅ Optional dataSource loaded successfully')
          })
          .catch(() => {
            // Silently fail for optional dataSource - keep empty data
            console.log('⚠️ Optional dataSource failed, continuing without data')
          })
      }
    }
    // Only re-run when config name or endpoint changes to prevent infinite loops
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.name, config?.dataSource?.endpoint])
  
  // Clear error if data is successfully loaded
  useEffect(() => {
    if (data && error) {
      // If we have data, clear any lingering errors
      console.log('✅ Data available, clearing error state')
      setError(null)
    }
  }, [data, error])

  async function loadData(endpoint, shouldSetLoading = true) {
    try {
      if (!endpoint || !String(endpoint).trim()) {
        console.warn('⚠️ loadData skipped: empty endpoint')
        return
      }
      // For API endpoints, use directly (Vite proxy handles /api -> backend)
      // Vite proxy is configured to forward /api/* to backend, so we don't need basePath
      let apiUrl = endpoint
      
      // Strip any existing basePath if endpoint already has it
      const basePath = import.meta.env.BASE_URL || '/'
      if (endpoint.startsWith(basePath) && endpoint.includes('/api/')) {
        // Remove basePath prefix if it exists
        apiUrl = endpoint.replace(basePath, '/')
      }
      
      // If it's an API endpoint, use it directly (proxy will handle it)
      // Don't prepend basePath for /api/ endpoints - Vite proxy handles it
      if (apiUrl.startsWith('/api/')) {
        // Use as-is, Vite proxy will forward it
        apiUrl = apiUrl
      } else if (!endpoint.startsWith('/api/')) {
        // Only prepend basePath for non-API endpoints
        if (endpoint.startsWith('/')) {
          // Remove leading slash and prepend base path
          apiUrl = `${basePath}${endpoint.slice(1)}`
        } else {
          apiUrl = `${basePath}${endpoint}`
        }
      }

      apiUrl = normalizeApiUrl(apiUrl, basePath)
      if (!apiUrl) {
        console.warn('⚠️ loadData skipped invalid URL. endpoint:', endpoint)
        return
      }
      console.log('📥 Loading data from:', apiUrl, '(endpoint was:', endpoint, ', basePath:', basePath, ')')
      if (shouldSetLoading) {
        setLoading(true)
      }
      setError(null)

      // Create AbortController for timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => {
        console.error('⏱️ Request timeout after 10 seconds')
        controller.abort()
      }, 10000) // 10 second timeout

      let response
      try {
        console.log('🔄 Starting fetch request...')
        response = await fetch(apiUrl, {
          signal: controller.signal,
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          }
        })
        clearTimeout(timeoutId)
        console.log('✅ Fetch completed, status:', response.status)
      } catch (fetchError) {
        clearTimeout(timeoutId)
        console.error('❌ Fetch error:', fetchError)
        if (fetchError.name === 'AbortError') {
          throw new Error(`Request timeout: Backend did not respond within 10 seconds. Please check if backend is running on port 8550.`)
        }
        if (fetchError.message.includes('Failed to fetch') || fetchError.message.includes('NetworkError')) {
          throw new Error(`Cannot connect to backend. Please ensure the backend is running on port 8550 and the Vite proxy is configured correctly.`)
        }
        throw fetchError
      }
      
      // Check if response is OK
      if (!response.ok) {
        // If 500 error, backend might not be running or has an issue
        if (response.status === 500) {
          const errorText = await response.text()
          throw new Error(`Backend server error (${response.status}): ${errorText.substring(0, 200)}`)
        }
        // For 404, provide helpful message
        if (response.status === 404) {
          throw new Error(`Endpoint not found: ${apiUrl}. Please ensure the backend is running on port 8550.`)
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      // Check if response is JSON
      const contentType = response.headers.get('content-type') || ''
      if (!contentType.includes('application/json')) {
        const text = await response.text()
        console.error('❌ Non-JSON response:', text.substring(0, 200))
        console.error('   Content-Type:', contentType)
        console.error('   Status:', response.status)
        console.error('   URL:', apiUrl)
        
        // If it's HTML, it might be an error page - try to extract useful info
        if (contentType.includes('text/html')) {
          // Check if it's a 404 or other error page
          if (response.status === 404) {
            throw new Error(`Endpoint not found: ${apiUrl}. Backend may not be running on port 8550.`)
          }
          // Try to extract title or error message from HTML
          const titleMatch = text.match(/<title[^>]*>([^<]+)<\/title>/i)
          const errorMsg = titleMatch ? titleMatch[1] : 'HTML error page'
          throw new Error(`Backend returned HTML instead of JSON. ${errorMsg}. Please check if backend is running.`)
        }
        throw new Error(`Response is not JSON. Got: ${contentType}. Backend may not be running or endpoint is incorrect.`)
      }
      
      const result = await response.json()
      console.log('✅ Data loaded:', result)
      
      // If result has no sites and fallbackEndpoint exists, try fallback
      if ((!result.sites || result.sites.length === 0) && 
          config?.dataSource?.fallbackEndpoint && 
          endpoint === config.dataSource.endpoint) {
        console.log('⚠️ No sites found, trying fallback endpoint:', config.dataSource.fallbackEndpoint)
        try {
          // Recursively call loadData for fallback (but don't set loading state)
          const fallbackApiUrl = config.dataSource.fallbackEndpoint.startsWith('/api/')
            ? config.dataSource.fallbackEndpoint
            : `${import.meta.env.BASE_URL || '/'}${config.dataSource.fallbackEndpoint.replace(/^\//, '')}`
          
          const fallbackResponse = await fetch(fallbackApiUrl, {
            signal: controller.signal,
            method: 'GET',
            headers: { 'Accept': 'application/json' }
          })
          
          if (fallbackResponse.ok) {
            const fallbackResult = await fallbackResponse.json()
            if (fallbackResult && fallbackResult.sites && fallbackResult.sites.length > 0) {
              console.log('✅ Fallback endpoint returned sites:', fallbackResult.sites.length)
              setData(fallbackResult)
              setError(null)
              if (shouldSetLoading) {
                setLoading(false)
              }
              return
            }
          }
        } catch (fallbackError) {
          console.log('⚠️ Fallback endpoint also failed, using original result:', fallbackError)
        }
      }
      
      // Clear any previous errors on successful load
      setError(null)
      setData(result)
      if (shouldSetLoading) {
        setLoading(false)
      }
    } catch (err) {
      console.error('❌ Data load error:', err)
      console.error('   URL attempted:', apiUrl)
      console.error('   Error type:', err.name)
      console.error('   Error message:', err.message)
      
      // Clear loading state on error (only if we were managing it)
      if (shouldSetLoading) {
        setLoading(false)
      }
      
      // Provide helpful error message
      const errorMessage = err.message || 'Failed to load data'
      setError(errorMessage)
      
      // If dataSource is optional, don't show error (some pages work without it)
      if (!config?.dataSource?.required) {
        console.log('⚠️  DataSource is optional, continuing without data')
        setError(null) // Clear error if dataSource is optional
      }
      
      console.log('✅ Error handled, loading state cleared')
    }
  }

  async function handleFormSubmit(e, formConfig) {
    e.preventDefault()
    setSubmitting(true)
    setSubmitResult(null) // Clear previous result
    setShowAlert(false) // Hide any existing alerts to prevent duplication

    try {
      const form = new FormData(e.target)

      // Prepend base path for API endpoints
      const basePath = import.meta.env.BASE_URL || '/'
      if (!formConfig.endpoint || !String(formConfig.endpoint).trim()) {
        throw new Error('Form endpoint is empty or invalid.')
      }
      let apiUrl = formConfig.endpoint.startsWith('/api/')
        ? formConfig.endpoint
        : (formConfig.endpoint.startsWith('/') ? `${basePath}${formConfig.endpoint.slice(1)}` : `${basePath}${formConfig.endpoint}`)
      apiUrl = normalizeApiUrl(apiUrl, basePath)
      if (!apiUrl) {
        throw new Error('Computed form API URL is invalid.')
      }

      // Replace placeholders in URL with form values (e.g., {site_id} -> actual value)
      const formDataObj = Object.fromEntries(form.entries())
      for (const [key, value] of Object.entries(formDataObj)) {
        const placeholder = `{${key}}`
        if (apiUrl.includes(placeholder)) {
          apiUrl = apiUrl.replace(placeholder, value)
        }
      }

      console.log('📤 Submitting form to:', apiUrl)

      const response = await fetch(apiUrl, {
        method: formConfig.method || 'POST',
        body: form
      })

      let result
      const responseType = response.headers.get('content-type') || ''
      if (responseType.includes('application/json')) {
        result = await response.json()
      } else {
        const rawText = await response.text()
        result = {
          status: 'error',
          error: `Server returned non-JSON response (HTTP ${response.status}): ${rawText.substring(0, 200)}`
        }
      }
      console.log('✅ Form submitted:', result)

      setSubmitResult(result)
      setShowAlert(true) // Show alert only once
      setSubmitting(false)
      
      // Auto-hide success alert after 5 seconds ONLY for simple success messages
      // Keep import results visible (they contain important view/edit links)
      if (result.status === 'success' && !result.error && !result.summary && !result.deployments) {
        // Only auto-hide simple success messages (like "Site credentials updated")
        // Import results with deployments should stay visible
        setTimeout(() => {
          setShowAlert(false)
        }, 5000)
      }
      // Import results with deployments stay visible - user needs to see view/edit links

      // Store selected site in localStorage when credentials are saved
      if (result.status === 'success' && formConfig.endpoint && formConfig.endpoint.includes('/sites/')) {
        // This is a site credentials update - store the site info
        const formDataObj = Object.fromEntries(form.entries())
        const siteId = formDataObj.site_id || formConfig.endpoint.match(/\{site_id\}|sites\/([^\/]+)/)?.[1]
        
        // Get site info from result or form
        let siteInfo = null
        if (result.site) {
          // Use site info from backend response (preferred)
          siteInfo = {
            id: result.site.id || siteId,
            site_id: result.site.site_id || siteId,
            site_url: result.site.site_url || '',
            site_name: result.site.site_name || ''
          }
        } else if (siteId) {
          // Fallback: try to get from form data
          siteInfo = {
            id: siteId,
            site_id: siteId,
            site_url: formDataObj.site_url || '',
            site_name: formDataObj.site_name || ''
          }
        }
        
        if (siteInfo && (siteInfo.site_url || siteInfo.id)) {
          // Store in localStorage as last selected site
          localStorage.setItem('revpublish_last_selected_site', JSON.stringify(siteInfo))
          console.log('💾 Stored last selected site:', siteInfo)
        }
      }

      // Reload data after successful submission to refresh the table
      if (result.status === 'success' && config?.dataSource?.endpoint) {
        console.log('🔄 Reloading data after successful form submission')
        setTimeout(() => loadData(config.dataSource.endpoint), 500)
      }
    } catch (err) {
      console.error('❌ Form submit error:', err)
      setSubmitResult({ error: err.message, status: 'error' })
      setShowAlert(true) // Show error alert
      setSubmitting(false)
    }
  }

  function renderElement(element, key = 0, contextData = null) {
    if (!element) return null

    // Use contextData if provided, otherwise use main data
    // For headers with dynamic text, we need access to the full data object
    const elementData = contextData !== null ? contextData : data
    
    // Make config available to renderElement for statsGrid to use main dataSource
    const renderConfig = config

    console.log('🎨 Rendering element type:', element.type)
    // Debug: log full element for headers to see all properties
    if (element.type === 'header' && element.text && element.text.includes('All Sites')) {
      console.log('📋 Header element full object:', JSON.stringify(element, null, 2))
      console.log('📋 Header element keys:', Object.keys(element))
      console.log('📋 Header dynamicText:', element.dynamicText, 'textTemplate:', element.textTemplate)
    }

    switch (element.type) {
      case 'container':
        console.log('📦 Rendering container with', element.children?.length, 'children')
        return (
          <div key={key} style={element.style || {}}>
            {element.children?.map((child, i) => renderElement(child, i, elementData))}
          </div>
        )

      case 'text':
        console.log('📝 Rendering text:', element.content?.substring(0, 50))
        if (element.dangerouslySetInnerHTML) {
          return (
            <div 
              key={key} 
              style={element.style || {}}
              dangerouslySetInnerHTML={{ __html: element.content }}
            />
          )
        }
        return (
          <div key={key} style={element.style || {}}>
            {element.content}
          </div>
        )

      case 'header':
        const HeadingTag = `h${element.level || 2}`
        let headerText = element.text || ''
        
        // Debug: Check if this is the "All Sites" header and log all properties
        if (headerText && headerText.includes('All Sites')) {
          console.log('🔍 All Sites header - element keys:', Object.keys(element))
          console.log('🔍 All Sites header - full element:', element)
          console.log('🔍 All Sites header - dynamicText:', element.dynamicText, 'type:', typeof element.dynamicText)
          console.log('🔍 All Sites header - textTemplate:', element.textTemplate, 'type:', typeof element.textTemplate)
        }
        
        // Support dynamic text with template variables
        // Check both boolean true and string "true" for dynamicText
        const hasDynamicText = element.dynamicText === true || element.dynamicText === 'true' || element.dynamicText === 1
        if (hasDynamicText && element.textTemplate) {
          console.log('📊 Header has dynamicText, template:', element.textTemplate)
          headerText = element.textTemplate
          
          // Always use main data state for dynamic text (not contextData)
          // This ensures headers inside containers can access the full data object
          // Prioritize main data state, then elementData, then default to empty object
          // The main data state is the source of truth and updates when API responds
          // Force use of main data state if it exists (even if it's the initial empty object)
          const dataForHeader = (data !== null && data !== undefined) 
            ? data 
            : (elementData !== null && elementData !== undefined 
                ? elementData 
                : { sites: [], total: 0 })
          
          console.log('📊 Header dataForHeader:', dataForHeader, 'data:', data, 'elementData:', elementData, 'total:', dataForHeader?.total)
          
          // Get total count from data (always default to 0)
          let totalCount = 0
          if (dataForHeader) {
            if (dataForHeader.total !== undefined && dataForHeader.total !== null) {
              totalCount = Number(dataForHeader.total) || 0
            } else if (dataForHeader.sites && Array.isArray(dataForHeader.sites)) {
              totalCount = dataForHeader.sites.length
            } else if (Array.isArray(dataForHeader)) {
              totalCount = dataForHeader.length
            }
          }
          
          console.log('📊 Header totalCount:', totalCount)
          
          // Replace template variables (use global replace to handle multiple occurrences)
          headerText = headerText.replace(/\{\{total\}\}/g, String(totalCount))
          headerText = headerText.replace(/\{\{count\}\}/g, String(totalCount))
          
          console.log('📊 Header final text:', headerText)
        } else {
          console.log('📊 Header no dynamicText - text:', element.text, 'dynamicText:', element.dynamicText, 'textTemplate:', element.textTemplate)
        }
        
        // Add data-dependent key to force re-render when data changes
        // This ensures the header updates when data loads
        const headerKey = `${key}-${data?.total ?? '0'}-${data?.sites?.length ?? '0'}`
        
        return React.createElement(
          HeadingTag,
          { key: headerKey, style: element.style || {} },
          headerText
        )

      case 'form':
        // Support both 'action' and 'endpoint' for form submission URL
        const formEndpoint = element.endpoint || element.action
        const formSubmitText = element.submitText || element.submitButton?.text || 'Submit'
        // Check if form has file inputs - if so, use multipart/form-data
        const hasFileInput = element.fields?.some(f => f.type === 'file')
        return (
          <form
            key={key}
            onSubmit={(e) => handleFormSubmit(e, { ...element, endpoint: formEndpoint })}
            style={element.style || {}}
            encType={hasFileInput ? 'multipart/form-data' : element.enctype}
          >
            {element.title && <h3>{element.title}</h3>}
            
            {element.fields?.map((field, i) => (
              <div key={i} style={{ 
                marginBottom: '0',
                padding: '1.25rem',
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '10px',
                border: '1px solid rgba(99, 102, 241, 0.15)',
                transition: 'all 0.2s'
              }}>
                <label style={{ 
                  display: 'block', 
                  marginBottom: '0.75rem', 
                  color: '#fff',
                  fontSize: '0.95rem',
                  fontWeight: '500'
                }}>
                  {field.label}
                  {field.required && <span style={{ color: '#ef4444', marginLeft: '0.25rem' }}>*</span>}
                </label>
                {field.description && (
                  <p style={{ 
                    fontSize: '0.875rem', 
                    color: '#94a3b8', 
                    marginBottom: '0.75rem', 
                    marginTop: 0,
                    lineHeight: '1.5'
                  }}>
                    {field.description}
                  </p>
                )}

                {field.type === 'file' ? (
                  <input
                    type="file"
                    name={field.name}
                    accept={field.accept}
                    required={field.required}
                    style={{
                      padding: '0.75rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      background: 'rgba(15, 23, 42, 0.5)',
                      color: '#fff',
                      width: '100%',
                      fontSize: '0.95rem',
                      transition: 'all 0.2s'
                    }}
                  />
                ) : field.type === 'select' ? (
                  field.dataSource ? (
                    <DynamicSelect
                      field={field}
                      basePath={import.meta.env.BASE_URL || '/'}
                    />
                  ) : (
                    <select
                      name={field.name}
                      defaultValue={field.default}
                      required={field.required}
                      style={{
                        padding: '0.5rem',
                        borderRadius: '4px',
                        border: '1px solid #334155',
                        background: '#1e293b',
                        color: '#fff',
                        width: '100%'
                      }}
                    >
                      {field.placeholder && <option value="">{field.placeholder}</option>}
                      {field.options?.map((opt, j) => (
                        <option key={j} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  )
                ) : field.type === 'checkbox' ? (
                  <input
                    type="checkbox"
                    name={field.name}
                    defaultChecked={field.default ?? field.defaultValue ?? false}
                  />
                ) : field.type === 'textarea' ? (
                  <textarea
                    name={field.name}
                    placeholder={field.placeholder}
                    required={field.required}
                    defaultValue={field.default}
                    rows={field.rows || 4}
                    maxLength={field.maxLength}
                      style={{
                        padding: '0.75rem',
                        borderRadius: '8px',
                        border: '1px solid rgba(99, 102, 241, 0.3)',
                        background: 'rgba(15, 23, 42, 0.5)',
                        color: '#fff',
                        width: '100%',
                        resize: 'vertical',
                        fontFamily: 'inherit',
                        fontSize: '0.95rem',
                        transition: 'all 0.2s'
                      }}
                  />
                ) : field.type === 'multiselect' ? (
                  <select
                    name={field.name}
                    multiple
                    required={field.required}
                      style={{
                        padding: '0.75rem',
                        borderRadius: '8px',
                        border: '1px solid rgba(99, 102, 241, 0.3)',
                        background: 'rgba(15, 23, 42, 0.5)',
                        color: '#fff',
                        width: '100%',
                        minHeight: '120px',
                        fontSize: '0.95rem',
                        transition: 'all 0.2s'
                      }}
                  >
                    {field.options?.map((opt, j) => (
                      <option key={j} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.type || 'text'}
                    name={field.name}
                    placeholder={field.placeholder}
                    required={field.required}
                    defaultValue={field.default}
                    style={{
                      padding: '0.75rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      background: 'rgba(15, 23, 42, 0.5)',
                      color: '#fff',
                      width: '100%',
                      fontSize: '0.95rem',
                      transition: 'all 0.2s'
                    }}
                  />
                )}
                
                {field.help && (
                  <small style={{ color: '#94a3b8', display: 'block', marginTop: '0.25rem' }}>
                    {field.help}
                  </small>
                )}
              </div>
            ))}

            <button
              type="submit"
              disabled={submitting}
              style={{
                ...(element.submitButton?.style || {}),
                padding: element.submitButton?.style?.padding || '0.875rem 2rem',
                background: submitting 
                  ? '#64748b' 
                  : (element.submitButton?.style?.background || 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)'),
                color: '#fff',
                border: 'none',
                borderRadius: element.submitButton?.style?.borderRadius || '8px',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontWeight: '600',
                fontSize: element.submitButton?.style?.fontSize || '1rem',
                boxShadow: submitting ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.3)',
                transition: 'all 0.2s',
                alignSelf: 'flex-start',
                marginTop: '0.5rem',
                opacity: submitting ? 0.7 : 1
              }}
              onMouseEnter={(e) => {
                if (!submitting && !e.target.disabled) {
                  e.target.style.transform = 'translateY(-2px)'
                  e.target.style.boxShadow = '0 6px 16px rgba(99, 102, 241, 0.4)'
                }
              }}
              onMouseLeave={(e) => {
                if (!submitting && !e.target.disabled) {
                  e.target.style.transform = 'translateY(0)'
                  e.target.style.boxShadow = '0 4px 12px rgba(99, 102, 241, 0.3)'
                }
              }}
            >
              {submitting ? '⏳ Processing...' : formSubmitText}
            </button>

            {submitResult && showAlert && (
              <div style={{
                marginTop: '1.5rem',
                padding: '1.5rem',
                background: submitResult.error ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                border: `1px solid ${submitResult.error ? '#ef4444' : '#10b981'}`,
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                position: 'relative'
              }}>
                {/* Close button for success alerts */}
                {!submitResult.error && (
                  <button
                    onClick={() => setShowAlert(false)}
                    style={{
                      position: 'absolute',
                      top: '0.75rem',
                      right: '0.75rem',
                      background: 'transparent',
                      border: 'none',
                      color: '#94a3b8',
                      cursor: 'pointer',
                      fontSize: '1.5rem',
                      padding: '0.25rem 0.5rem',
                      lineHeight: '1',
                      borderRadius: '4px',
                      transition: 'all 0.2s',
                      width: '28px',
                      height: '28px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.background = 'rgba(0,0,0,0.2)'
                      e.target.style.color = '#fff'
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = 'transparent'
                      e.target.style.color = '#94a3b8'
                    }}
                    title="Close"
                  >
                    ×
                  </button>
                )}
                {submitResult.error ? (
                  <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fca5a5'}}>
                    <span style={{fontSize: '1.25rem'}}>❌</span>
                    <div>
                      <strong style={{display: 'block', marginBottom: '0.25rem'}}>Error</strong>
                      <span>{submitResult.error}</span>
                    </div>
                  </div>
                ) : submitResult.summary ? (
                  // Only show "Import Complete" for import forms (those with summary)
                  <div>
                    <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem'}}>
                      <span style={{fontSize: '1.5rem'}}>✅</span>
                      <h4 style={{margin: 0, color: '#10b981'}}>Import Complete!</h4>
                    </div>
                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: submitResult.deployments?.length > 0 ? '1rem' : '0'}}>
                      <div style={{background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '6px'}}>
                        <div style={{fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem'}}>Processed</div>
                        <div style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#fff'}}>{submitResult.summary?.total_rows || 0}</div>
                      </div>
                      <div style={{background: 'rgba(16, 185, 129, 0.2)', padding: '0.75rem', borderRadius: '6px'}}>
                        <div style={{fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem'}}>Successful</div>
                        <div style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#10b981'}}>{submitResult.summary?.successful_deployments || 0}</div>
                      </div>
                      {submitResult.summary?.failed_deployments > 0 && (
                        <div style={{background: 'rgba(239, 68, 68, 0.2)', padding: '0.75rem', borderRadius: '6px'}}>
                          <div style={{fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.25rem'}}>Failed</div>
                          <div style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#ef4444'}}>{submitResult.summary?.failed_deployments}</div>
                        </div>
                      )}
                    </div>
                    {submitResult.deployments && submitResult.deployments.length > 0 && (
                      <div style={{marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.1)'}}>
                        <h5 style={{marginBottom: '0.75rem', color: '#fff', fontSize: '1rem'}}>📄 Deployed Pages:</h5>
                        {submitResult.deployments.map((deployment, idx) => {
                          // Show links for both deployed and preview statuses if page_info exists
                          if ((deployment.status === 'deployed' || deployment.status === 'preview') && deployment.page_info) {
                            const isDraft = deployment.page_info.post_status === 'draft'
                            const isPreview = deployment.status === 'preview'
                            
                            return (
                              <div key={idx} style={{
                                marginBottom: '0.75rem',
                                padding: '1rem',
                                background: 'rgba(0,0,0,0.2)',
                                borderRadius: '8px',
                                border: isDraft ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid rgba(99, 102, 241, 0.2)'
                              }}>
                                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem'}}>
                                  <div style={{flex: 1, minWidth: '200px'}}>
                                    <div style={{fontWeight: '600', marginBottom: '0.25rem', color: '#fff', fontSize: '0.95rem'}}>
                                      {deployment.page_info.title || `Page ${deployment.row_number}`}
                                    </div>
                                    <div style={{fontSize: '0.8rem', color: '#94a3b8', display: 'flex', gap: '0.75rem', flexWrap: 'wrap'}}>
                                      <span>
                                        Status: <span style={{
                                          textTransform: 'capitalize',
                                          color: isDraft ? '#f59e0b' : '#10b981',
                                          fontWeight: '500'
                                        }}>{deployment.page_info.post_status || 'draft'}</span>
                                      </span>
                                      {deployment.page_info.wp_post_id && (
                                        <span>• Post ID: {deployment.page_info.wp_post_id}</span>
                                      )}
                                      {deployment.site_info?.site_url && (
                                        <span>• Site: {deployment.site_info.site_url.replace('https://', '').replace('http://', '')}</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem'}}>
                                  {deployment.page_info.wp_admin_url && (
                                    <a 
                                      href={deployment.page_info.wp_admin_url} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: '0.25rem',
                                        padding: '0.5rem 1rem',
                                        background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                        color: 'white',
                                        textDecoration: 'none',
                                        borderRadius: '6px',
                                        fontSize: '0.875rem',
                                        fontWeight: '500',
                                        transition: 'all 0.2s',
                                        boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)'
                                      }}
                                      onMouseEnter={(e) => {
                                        e.target.style.transform = 'translateY(-2px)'
                                        e.target.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.4)'
                                      }}
                                      onMouseLeave={(e) => {
                                        e.target.style.transform = 'translateY(0)'
                                        e.target.style.boxShadow = '0 2px 8px rgba(59, 130, 246, 0.3)'
                                      }}
                                    >
                                      ✏️ Edit in WordPress
                                    </a>
                                  )}
                                  {deployment.page_info.page_url && (
                                    <a 
                                      href={deployment.page_info.page_url} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: '0.25rem',
                                        padding: '0.5rem 1rem',
                                        background: isDraft 
                                          ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                                          : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                        color: 'white',
                                        textDecoration: 'none',
                                        borderRadius: '6px',
                                        fontSize: '0.875rem',
                                        fontWeight: '500',
                                        transition: 'all 0.2s',
                                        boxShadow: isDraft 
                                          ? '0 2px 8px rgba(245, 158, 11, 0.3)'
                                          : '0 2px 8px rgba(16, 185, 129, 0.3)'
                                      }}
                                      onMouseEnter={(e) => {
                                        e.target.style.transform = 'translateY(-2px)'
                                        e.target.style.boxShadow = isDraft
                                          ? '0 4px 12px rgba(245, 158, 11, 0.4)'
                                          : '0 4px 12px rgba(16, 185, 129, 0.4)'
                                      }}
                                      onMouseLeave={(e) => {
                                        e.target.style.transform = 'translateY(0)'
                                        e.target.style.boxShadow = isDraft
                                          ? '0 2px 8px rgba(245, 158, 11, 0.3)'
                                          : '0 2px 8px rgba(16, 185, 129, 0.3)'
                                      }}
                                    >
                                      {isDraft ? '👁️ Preview Draft' : '👁️ View Page'}
                                    </a>
                                  )}
                                  {isPreview && (
                                    <span style={{
                                      padding: '0.5rem 1rem',
                                      background: 'rgba(99, 102, 241, 0.2)',
                                      color: '#a5b4fc',
                                      borderRadius: '6px',
                                      fontSize: '0.875rem',
                                      border: '1px solid rgba(99, 102, 241, 0.3)'
                                    }}>
                                      👁️ Preview Mode (Not Deployed)
                                    </span>
                                  )}
                                </div>
                              </div>
                            )
                          } else if (deployment.status === 'failed') {
                            return (
                              <div key={idx} style={{
                                marginBottom: '0.75rem',
                                padding: '0.75rem',
                                background: 'rgba(239, 68, 68, 0.1)',
                                borderRadius: '4px',
                                border: '1px solid #ef4444'
                              }}>
                                <div style={{fontWeight: '600', color: '#fca5a5', marginBottom: '0.25rem'}}>
                                  ❌ {deployment.page_info?.title || `Row ${deployment.row_number}`}
                                </div>
                                <div style={{fontSize: '0.85rem', color: '#fca5a5'}}>
                                  {deployment.error || deployment.message || 'Deployment failed'}
                                </div>
                              </div>
                            )
                          }
                          return null
                        })}
                      </div>
                    )}
                  </div>
                ) : (
                  // Generic success message for other forms
                  <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem'}}>
                    <span style={{fontSize: '1.5rem'}}>✅</span>
                    <div>
                      <h4 style={{margin: 0, marginBottom: '0.5rem', color: '#10b981'}}>{submitResult.message || 'Success!'}</h4>
                      {submitResult.updated && (
                        <p style={{margin: 0, color: '#94a3b8', fontSize: '0.9rem'}}>Site credentials updated successfully.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </form>
        )

      case 'dataTable':
        // Pass full data context so DataTable can access total, etc.
        return <DataTableElement key={key} element={element} contextData={elementData || data} />

      case 'jsonViewer':
        return <JsonViewerElement key={key} element={element} />
      case 'contentTemplateBuilder':
        return <ContentTemplateBuilderElement key={key} element={element} />
      case 'contentMappingPreview':
        return <ContentMappingPreviewElement key={key} element={element} />

      case 'alert':
        const alertColors = {
          info: { bg: 'rgba(59, 130, 246, 0.1)', border: '#3b82f6', icon: 'ℹ️', text: '#93c5fd' },
          success: { bg: 'rgba(16, 185, 129, 0.1)', border: '#10b981', icon: '✅', text: '#6ee7b7' },
          warning: { bg: 'rgba(245, 158, 11, 0.1)', border: '#f59e0b', icon: '⚠️', text: '#fcd34d' },
          error: { bg: 'rgba(239, 68, 68, 0.1)', border: '#ef4444', icon: '❌', text: '#fca5a5' }
        }
        const alertStyle = alertColors[element.variant] || alertColors.info
        return (
          <div key={key} style={{
            padding: '1.25rem',
            background: alertStyle.bg,
            border: `1px solid ${alertStyle.border}`,
            borderRadius: '12px',
            margin: '1.5rem 0',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            ...element.style
          }}>
            {element.title && (
              <div style={{ 
                fontWeight: '600', 
                marginBottom: '0.75rem',
                color: alertStyle.text,
                fontSize: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                <span style={{ fontSize: '1.25rem' }}>{alertStyle.icon}</span>
                <span>{element.title}</span>
              </div>
            )}
            <div style={{ color: alertStyle.text, lineHeight: '1.6' }}>
              {element.message || element.content}
            </div>
          </div>
        )

      case 'spacer':
        return (
          <div key={key} style={{
            height: element.height || '1rem',
            ...element.style
          }} />
        )

      case 'statsGrid':
        // If element has dataSource or cards, use the smart StatsGridElement
        // Also use it if config has dataSource (to share data with main dataSource)
        if (element.dataSource || element.cards || (config?.dataSource && !element.stats)) {
          // If element doesn't have its own dataSource but config does, use config's dataSource
          const elementWithDataSource = element.dataSource 
            ? element 
            : { ...element, dataSource: config.dataSource }
          return <StatsGridElement key={key} element={elementWithDataSource} />
        }
        // Otherwise use static stats
        return (
          <div key={key} style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem',
            ...element.style
          }}>
            {element.stats?.map((stat, i) => (
              <div key={i} style={{
                background: '#1e293b',
                padding: '1.5rem',
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>{stat.icon}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#fff' }}>{stat.value}</div>
                <div style={{ color: '#94a3b8', fontSize: '0.875rem' }}>{stat.label}</div>
              </div>
            ))}
          </div>
        )

      case 'button':
        const handleButtonClick = async () => {
          if (element.action?.type === 'api' && element.action.endpoint) {
            try {
              const basePath = import.meta.env.BASE_URL || '/'
              let apiUrl = element.action.endpoint
              
              if (apiUrl.startsWith('/api/')) {
                // Use directly, Vite proxy handles it
                apiUrl = apiUrl
              } else if (apiUrl.startsWith('/')) {
                apiUrl = `${basePath}${apiUrl.slice(1)}`
              } else {
                apiUrl = `${basePath}${apiUrl}`
              }
              
              console.log('🔄 Button action: calling', apiUrl)
              
              const response = await fetch(apiUrl, {
                method: element.action.method || 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Accept': 'application/json'
                }
              })
              
              if (!response.ok) {
                const errorText = await response.text()
                throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 100)}`)
              }
              
              const result = await response.json()
              console.log('✅ Button action result:', result)
              
              // If sync was successful, reload data
              if (element.action.endpoint.includes('/hostinger/sync') && config?.dataSource?.endpoint) {
                console.log('🔄 Reloading data after Hostinger sync')
                setTimeout(() => {
                  loadData(config.dataSource.endpoint, false).catch(console.error)
                }, 500)
              }
              
              // Show success message
              alert(result.message || 'Operation completed successfully!')
            } catch (err) {
              console.error('❌ Button action error:', err)
              alert(`Error: ${err.message}`)
            }
          }
        }
        
        return (
          <button
            key={key}
            onClick={handleButtonClick}
            style={{
              ...element.style,
              cursor: 'pointer'
            }}
          >
            {element.text || element.label}
          </button>
        )

      case 'link':
        return (
          <a
            key={key}
            href={element.url}
            target={element.external ? '_blank' : '_self'}
            rel={element.external ? 'noopener noreferrer' : undefined}
            download={element.download ? (element.downloadName || true) : undefined}
            style={{
              color: '#3b82f6',
              textDecoration: 'underline',
              ...element.style
            }}
          >
            {element.icon && <span style={{ marginRight: '0.5rem' }}>{element.icon}</span>}
            {element.label || element.text}
          </a>
        )

      case 'badge':
        const badgeColors = {
          success: { bg: '#064e3b', text: '#10b981' },
          warning: { bg: '#78350f', text: '#f59e0b' },
          error: { bg: '#7f1d1d', text: '#ef4444' },
          info: { bg: '#1e3a5f', text: '#3b82f6' },
          default: { bg: '#334155', text: '#94a3b8' }
        }
        const badgeStyle = badgeColors[element.variant] || badgeColors.default
        return (
          <span key={key} style={{
            display: 'inline-block',
            padding: '0.25rem 0.75rem',
            background: badgeStyle.bg,
            color: badgeStyle.text,
            borderRadius: '9999px',
            fontSize: '0.75rem',
            fontWeight: '600',
            ...element.style
          }}>
            {element.text || element.content}
          </span>
        )

      case 'imageUploadBrowser':
        // Renders the Image Upload Browser component for image management
        // Supports: upload, AI generation, import, geo-tagging, alt text
        return (
          <ImageUploadBrowser
            key={key}
            props={{
              basePath: element.apiBase || '/api/revpublish',
              revimageUrl: element.revimageUrl || '/api/revimage',
              title: element.title,
              description: element.description
            }}
            onImageSelect={element.onImageSelect}
            pageId={element.pageId}
          />
        )

      default:
        console.warn('⚠️  Unknown element type:', element.type)
        return (
          <div key={key} style={{ 
            padding: '1rem', 
            background: '#7f1d1d', 
            color: '#fff',
            borderRadius: '4px',
            margin: '1rem 0'
          }}>
            Unknown element type: {element.type}
          </div>
        )
    }
  }

  if (!config || !config.layout) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
        No schema configuration provided
      </div>
    )
  }

  return (
    <div style={{ padding: '2rem' }}>
      {loading && config?.dataSource?.required !== false && (
        <div style={{ 
          padding: '1rem', 
          textAlign: 'center', 
          color: '#94a3b8',
          marginBottom: '1rem'
        }}>
          Loading data...
        </div>
      )}
      {error && (
        <div style={{ 
          padding: '1rem', 
          marginBottom: '1rem',
          background: '#7f1d1d',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          color: '#fca5a5',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.5rem'
        }}>
          <div>
            <strong>⚠️ Error:</strong> {error}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => {
                setError(null)
                if (config?.dataSource?.endpoint) {
                  loadData(config.dataSource.endpoint)
                }
              }}
              style={{
                padding: '0.25rem 0.75rem',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.85rem'
              }}
            >
              Retry
            </button>
            <button
              onClick={() => setError(null)}
              style={{
                padding: '0.25rem 0.75rem',
                background: '#64748b',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.85rem'
              }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
      {renderElement(config.layout, 0, data)}
    </div>
  )
}
