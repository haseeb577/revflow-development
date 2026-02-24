import React, { useState, useEffect } from 'react'
import ImageUploadBrowser from './ImageUploadBrowser'

/**
 * Dynamic Select Component - Fetches options from API
 */
function DynamicSelect({ field, basePath }) {
  const [options, setOptions] = useState(field.options || [])
  const [loading, setLoading] = useState(false)
  const [selectedValue, setSelectedValue] = useState(field.default || '')

  useEffect(() => {
    if (field.dataSource) {
      setLoading(true)

      // Handle dataSource as string URL or object with url property
      const url = typeof field.dataSource === 'string'
        ? field.dataSource
        : (field.dataSource.url || field.dataSource)

      // Build the full API URL
      let apiUrl = url
      if (url.startsWith('/')) {
        // For absolute paths starting with /, don't add basePath
        apiUrl = url
      }

      console.log('📥 DynamicSelect fetching from:', apiUrl)

      fetch(apiUrl)
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          return res.json()
        })
        .then(data => {
          console.log('📦 DynamicSelect received data:', data)

          // Get dataPath from field.dataPath or field.dataSource.dataPath
          const dataPath = field.dataPath ||
            (typeof field.dataSource === 'object' ? field.dataSource.dataPath : null)

          // Extract items array from response
          let items = []
          if (dataPath && data[dataPath]) {
            items = data[dataPath]
          } else if (Array.isArray(data)) {
            items = data
          } else if (data.sites) {
            items = data.sites
          } else if (data.data) {
            items = data.data
          }

          // Get label and value field names
          const labelKey = field.labelField ||
            (typeof field.dataSource === 'object' ? field.dataSource.labelKey : null) ||
            'site_name'
          const valueKey = field.valueField ||
            (typeof field.dataSource === 'object' ? field.dataSource.valueKey : null) ||
            'id'

          console.log(`📋 Using labelKey=${labelKey}, valueKey=${valueKey}, items count=${items.length}`)

          const dynamicOptions = items.map(item => ({
            label: item[labelKey] || item.name || item.label || 'Unknown',
            value: item[valueKey] || item.id || item.value
          }))

          console.log(`✅ DynamicSelect loaded ${dynamicOptions.length} options`)
          setOptions(dynamicOptions)
          setLoading(false)
        })
        .catch(err => {
          console.error('❌ DynamicSelect error:', err)
          // Fall back to static options if available
          if (field.options && field.options.length > 0) {
            console.log('📋 Falling back to static options')
            setOptions(field.options)
          }
          setLoading(false)
        })
    }
  }, [field.dataSource, basePath, field.dataPath, field.labelField, field.valueField])

  const handleChange = (e) => {
    setSelectedValue(e.target.value)
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
 * DataTable Element - Handles its own data fetching
 */
function DataTableElement({ element, contextData }) {
  const [tableData, setTableData] = useState([])
  const [loading, setLoading] = useState(true)
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
      setLoading(true)

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
          setError(err.message)
          setLoading(false)
        })
    } else if (contextData) {
      // Use context data with dataPath
      const items = element.dataPath ? contextData[element.dataPath] : []
      setTableData(items || [])
      setLoading(false)
    } else {
      setLoading(false)
    }
  }, [element.dataSource, element.dataPath, contextData])

  if (loading) {
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
          borderLeft: `4px solid ${card.color || '#3b82f6'}`
        }}>
          <div style={{
            fontSize: '2rem',
            fontWeight: 'bold',
            color: card.color || '#fff',
            marginBottom: '0.5rem'
          }}>
            {getValue(card.dataKey)}
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
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [formData, setFormData] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)

  useEffect(() => {
    console.log('📦 JSONRender received config:', config?.name)
    
    if (config?.dataSource?.endpoint) {
      loadData(config.dataSource.endpoint)
    } else {
      setLoading(false)
    }
  }, [config])

  async function loadData(endpoint) {
    try {
      // Prepend base path for API endpoints
      const basePath = import.meta.env.BASE_URL || '/'
      // 
      const apiUrl = endpoint.startsWith('/api/')
        ? endpoint
        : (endpoint.startsWith('/') ? `${basePath}${endpoint.slice(1)}` : `${basePath}${endpoint}`)

      console.log('📥 Loading data from:', apiUrl)
      setLoading(true)
      setError(null)

      const response = await fetch(apiUrl)
      
      // Check if response is OK
      if (!response.ok) {
        // If 500 error, backend might not be running or has an issue
        if (response.status === 500) {
          throw new Error(`Backend server error (${response.status}). Please ensure the backend is running on port 8550.`)
        }
        throw new Error(`HTTP ${response.status}`)
      }
      
      // Check if response is JSON
      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Response is not JSON. Backend may not be running.')
      }
      
      const result = await response.json()
      console.log('✅ Data loaded:', result)
      
      setData(result)
      setLoading(false)
    } catch (err) {
      console.error('❌ Data load error:', err)
      // Provide helpful error message
      const errorMessage = err.message || 'Failed to load data'
      setError(errorMessage)
      setLoading(false)
    }
  }

  async function handleFormSubmit(e, formConfig) {
    e.preventDefault()
    setSubmitting(true)
    setSubmitResult(null)

    try {
      const form = new FormData(e.target)

      // Prepend base path for API endpoints
      const basePath = import.meta.env.BASE_URL || '/'
      // 
      const apiUrl = formConfig.endpoint.startsWith('/api/')
        ? formConfig.endpoint
        : (formConfig.endpoint.startsWith('/') ? `${basePath}${formConfig.endpoint.slice(1)}` : `${basePath}${formConfig.endpoint}`)

      console.log('📤 Submitting form to:', apiUrl)

      const response = await fetch(apiUrl, {
        method: formConfig.method || 'POST',
        body: form
      })

      const result = await response.json()
      console.log('✅ Form submitted:', result)

      setSubmitResult(result)
      setSubmitting(false)

      // Reload data after successful submission to refresh the table
      if (result.status === 'success' && config?.dataSource?.endpoint) {
        console.log('🔄 Reloading data after successful form submission')
        setTimeout(() => loadData(config.dataSource.endpoint), 500)
      }
    } catch (err) {
      console.error('❌ Form submit error:', err)
      setSubmitResult({ error: err.message })
      setSubmitting(false)
    }
  }

  function renderElement(element, key = 0, contextData = null) {
    if (!element) return null

    const elementData = contextData || data

    console.log('🎨 Rendering element type:', element.type)

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
        return React.createElement(
          HeadingTag,
          { key, style: element.style || {} },
          element.text
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
              <div key={i} style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: '#fff' }}>
                  {field.label}
                </label>
                {field.description && (
                  <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.5rem', marginTop: 0 }}>
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
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #334155',
                      background: '#1e293b',
                      color: '#fff',
                      width: '100%'
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
                    defaultChecked={field.default}
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
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #334155',
                      background: '#1e293b',
                      color: '#fff',
                      width: '100%',
                      resize: 'vertical',
                      fontFamily: 'inherit'
                    }}
                  />
                ) : field.type === 'multiselect' ? (
                  <select
                    name={field.name}
                    multiple
                    required={field.required}
                    style={{
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #334155',
                      background: '#1e293b',
                      color: '#fff',
                      width: '100%',
                      minHeight: '120px'
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
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #334155',
                      background: '#1e293b',
                      color: '#fff',
                      width: '100%'
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
                padding: '0.75rem 1.5rem',
                background: submitting ? '#64748b' : '#3b82f6',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
              }}
            >
              {submitting ? 'Submitting...' : formSubmitText}
            </button>

            {submitResult && (
              <div style={{
                marginTop: '1rem',
                padding: '1rem',
                background: submitResult.error ? '#7f1d1d' : '#064e3b',
                border: `1px solid ${submitResult.error ? '#ef4444' : '#10b981'}`,
                borderRadius: '4px'
              }}>
                {submitResult.error ? (
                  <div>Error: {submitResult.error}</div>
                ) : (
                  <div>
                    <h4>✅ Import Complete!</h4>
                    <p>Processed: {submitResult.summary?.total_rows} rows</p>
                    <p>Successful: {submitResult.summary?.successful_deployments}</p>
                  </div>
                )}
              </div>
            )}
          </form>
        )

      case 'dataTable':
        return <DataTableElement key={key} element={element} contextData={elementData} />

      case 'alert':
        const alertColors = {
          info: { bg: '#1e3a5f', border: '#3b82f6', icon: 'ℹ️' },
          success: { bg: '#064e3b', border: '#10b981', icon: '✅' },
          warning: { bg: '#78350f', border: '#f59e0b', icon: '⚠️' },
          error: { bg: '#7f1d1d', border: '#ef4444', icon: '❌' }
        }
        const alertStyle = alertColors[element.variant] || alertColors.info
        return (
          <div key={key} style={{
            padding: '1rem',
            background: alertStyle.bg,
            border: `1px solid ${alertStyle.border}`,
            borderRadius: '8px',
            margin: '1rem 0',
            ...element.style
          }}>
            {element.title && (
              <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
                {alertStyle.icon} {element.title}
              </div>
            )}
            <div>{element.message || element.content}</div>
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
        // If element has dataSource, use the smart StatsGridElement
        if (element.dataSource) {
          return <StatsGridElement key={key} element={element} />
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
      {loading && <div>Loading data...</div>}
      {error && <div style={{ color: '#ef4444' }}>Error: {error}</div>}
      {renderElement(config.layout)}
    </div>
  )
}
