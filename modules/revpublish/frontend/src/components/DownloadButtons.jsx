import React from 'react';

const DownloadButtons = () => {
  const buttons = [
    {
      text: '⬇️ CSV Template (5 Sites)',
      url: '/templates/SiteData_v2_Feb2026.csv',
      filename: 'SiteData_v2_Feb2026.csv',
      color: '#22c55e'
    },
    {
      text: '⬇️ Service Template',
      url: '/templates/Template_Service.yaml',
      filename: 'Template_Service.yaml',
      color: '#3b82f6'
    },
    {
      text: '⬇️ Location Template',
      url: '/templates/Template_Location.yaml',
      filename: 'Template_Location.yaml',
      color: '#a855f7'
    }
  ];

  const handleDownload = async (url, filename) => {
    try {
      const cacheBuster = `?t=${Date.now()}`;
      const response = await fetch(url + cacheBuster, { cache: 'no-store' });
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      {buttons.map((btn, idx) => (
        <button
          key={idx}
          onClick={() => handleDownload(btn.url, btn.filename)}
          style={{
            display: 'inline-block',
            background: btn.color,
            color: '#fff',
            padding: '0.75rem 1.5rem',
            borderRadius: '6px',
            textDecoration: 'none',
            fontWeight: '600',
            cursor: 'pointer',
            border: 'none'
          }}
        >
          {btn.text}
        </button>
      ))}
    </div>
  );
};

export default DownloadButtons;
