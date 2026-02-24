import React, { useState } from 'react'

/**
 * Image Upload Browser Component
 * Handles image upload, AI generation, import, geo-tagging, and alt text
 */
export default function ImageUploadBrowser({ props = {}, onImageSelect, pageId }) {
  const {
    basePath = '/api/revpublish',
    revimageUrl = '/api/revimage',
    title = 'Image Browser',
    description = 'Upload or select images for your content'
  } = props

  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedImage, setSelectedImage] = useState(null)
  const [uploading, setUploading] = useState(false)

  const handleImageSelect = (image) => {
    setSelectedImage(image)
    if (onImageSelect) {
      onImageSelect(image)
    }
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('image', file)
      if (pageId) {
        formData.append('pageId', pageId)
      }

      const response = await fetch(`${basePath}/images/upload`, {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        const result = await response.json()
        setImages([...images, result])
        handleImageSelect(result)
      } else {
        console.error('Upload failed:', response.statusText)
      }
    } catch (error) {
      console.error('Upload error:', error)
    } finally {
      setUploading(false)
    }
  }

  const handleAIGenerate = async () => {
    // Placeholder for AI image generation
    console.log('AI image generation not yet implemented')
  }

  return (
    <div className="image-upload-browser" style={{
      padding: '1.5rem',
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      backgroundColor: '#f8fafc'
    }}>
      <div style={{ marginBottom: '1rem' }}>
        <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem', fontWeight: '600' }}>
          {title}
        </h3>
        {description && (
          <p style={{ margin: 0, color: '#64748b', fontSize: '0.875rem' }}>
            {description}
          </p>
        )}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
        gap: '1rem',
        marginBottom: '1rem',
        minHeight: '200px',
        padding: '1rem',
        border: '1px dashed #cbd5e1',
        borderRadius: '6px',
        backgroundColor: '#fff'
      }}>
        {images.length === 0 ? (
          <div style={{
            gridColumn: '1 / -1',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#94a3b8',
            textAlign: 'center'
          }}>
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ marginBottom: '0.5rem' }}
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <p style={{ margin: 0 }}>No images yet</p>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem' }}>
              Upload or generate images to get started
            </p>
          </div>
        ) : (
          images.map((image, index) => (
            <div
              key={index}
              onClick={() => handleImageSelect(image)}
              style={{
                position: 'relative',
                aspectRatio: '1',
                border: selectedImage?.id === image.id ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                borderRadius: '6px',
                overflow: 'hidden',
                cursor: 'pointer',
                backgroundColor: '#f1f5f9'
              }}
            >
              {image.url ? (
                <img
                  src={image.url}
                  alt={image.alt || `Image ${index + 1}`}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover'
                  }}
                />
              ) : (
                <div style={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#94a3b8'
                }}>
                  Image {index + 1}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div style={{
        display: 'flex',
        gap: '0.75rem',
        flexWrap: 'wrap'
      }}>
        <label style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '0.5rem 1rem',
          backgroundColor: '#3b82f6',
          color: 'white',
          borderRadius: '6px',
          cursor: uploading ? 'not-allowed' : 'pointer',
          opacity: uploading ? 0.6 : 1,
          fontSize: '0.875rem',
          fontWeight: '500'
        }}>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            disabled={uploading}
            style={{ display: 'none' }}
          />
          {uploading ? 'Uploading...' : 'Upload Image'}
        </label>

        <button
          onClick={handleAIGenerate}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#8b5cf6',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: '500'
          }}
        >
          AI Generate
        </button>

        <button
          onClick={() => {
            // Placeholder for import functionality
            console.log('Import images not yet implemented')
          }}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: '500'
          }}
        >
          Import
        </button>
      </div>

      {selectedImage && (
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem',
          backgroundColor: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: '6px',
          fontSize: '0.875rem'
        }}>
          <strong>Selected:</strong> {selectedImage.url || selectedImage.name || 'Image selected'}
        </div>
      )}
    </div>
  )
}

