import React from 'react';
import { JSONRenderer } from '../../../frontend/src/JSONRenderer';
import '../../../frontend/src/App.css';

export default function RevauditApp() {
  return (
    <div className="revaudit-app">
      <JSONRenderer 
        schemaPath="revaudit/dashboard.json"
        context={{ module: 'revaudit' }}
      />
    </div>
  );
}
