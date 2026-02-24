import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';

// FIXED: Use the ACTUAL working Admin API on port 8888
const API_URL = '/api';  // Uses nginx proxy to port 8888

function Dashboard() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [modules, setModules] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboard = async () => {
    try {
      // Load system status
      const statusRes = await axios.get(`${API_URL}/system/status`);
      setSystemStatus(statusRes.data);

      // Load modules
      const modulesRes = await axios.get(`${API_URL}/modules`);
      setModules(modulesRes.data.modules);

      // Load services health
      const servicesRes = await axios.get(`${API_URL}/services/health`);
      setServices(servicesRes.data.services);

      setLoading(false);
    } catch (err) {
      console.error('Error loading dashboard:', err);
      setLoading(false);
    }
  };

  if (loading) return <div style={styles.loading}>Loading RevFlow OS...</div>;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1>RevFlow OS - Admin Dashboard</h1>
        <p>Server: {systemStatus?.server} | Uptime: {systemStatus?.uptime}</p>
      </div>

      <div style={styles.stats}>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>Services Online</div>
          <div style={styles.statValue}>{systemStatus?.services?.length || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>Docker Containers</div>
          <div style={styles.statValue}>{systemStatus?.docker_containers?.length || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>Active Modules</div>
          <div style={styles.statValue}>{modules.length}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>Database</div>
          <div style={styles.statValue}>{systemStatus?.database || 'Unknown'}</div>
        </div>
      </div>

      <div style={styles.servicesSection}>
        <h2>Services</h2>
        {services.map(s => (
          <div key={s.id} style={styles.serviceItem}>
            <span>{s.name} (:{s.port})</span>
            <span style={{color: s.status === 'online' ? '#48bb78' : '#f56565', fontWeight: 'bold'}}>
              {s.status.toUpperCase()}
            </span>
          </div>
        ))}
      </div>

      <div style={styles.modulesSection}>
        <h2>Modules</h2>
        <div style={styles.modulesGrid}>
          {modules.map(m => (
            <div key={m.id} style={{...styles.moduleCard, borderLeft: `4px solid ${m.color}`}}>
              <h3>{m.name}</h3>
              <p>{m.description}</p>
              <div>
                {m.features.map((f, i) => (
                  <span key={i} style={styles.feature}>• {f}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: { padding: '20px', fontFamily: 'system-ui', maxWidth: '1400px', margin: '0 auto' },
  header: { background: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  stats: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '20px' },
  statCard: { background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  statLabel: { fontSize: '14px', color: '#666', marginBottom: '5px' },
  statValue: { fontSize: '32px', fontWeight: 'bold', color: '#2d3748' },
  servicesSection: { background: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  serviceItem: { display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #e2e8f0' },
  modulesSection: { background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  modulesGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginTop: '20px' },
  moduleCard: { background: '#f7fafc', padding: '20px', borderRadius: '8px' },
  feature: { display: 'block', fontSize: '14px', color: '#666', margin: '5px 0' },
  loading: { textAlign: 'center', padding: '40px', fontSize: '24px' }
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
