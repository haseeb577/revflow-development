import React, { useEffect, useState } from 'react';
import JSONRender from '@/components/JSONRender';

// Fetch data from backend APIs
async function fetchMetricsData() {
  try {
    const [statsRes, modulesRes] = await Promise.all([
      fetch('/api/revmetrics/stats').catch(() => null),
      fetch('/api/revmetrics/modules').catch(() => null)
    ]);

    const stats = statsRes?.ok ? await statsRes.json() : null;
    const modules = modulesRes?.ok ? await modulesRes.json() : null;

    return { stats, modules };
  } catch (err) {
    console.error('Failed to fetch metrics data:', err);
    return { stats: null, modules: null };
  }
}

export default function RevmetricsApp() {
  const [backendData, setBackendData] = useState<any>(null);

  useEffect(() => {
    fetchMetricsData().then(setBackendData);

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchMetricsData().then(setBackendData);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="revmetrics-app">
      <JSONRender
        schemaPath="revmetrics.json"
        context={{
          module: 'revmetrics',
          backendData
        }}
      />
    </div>
  );
}
