Based on my analysis of the frontend codebase, here are the answers to your questions:
1. Exact Base URL Configuration
The frontend has multiple conflicting base URLs configured:
Primary Configuration (src/path.js):
export const path = "http://127.0.0.1:8081";
export const path1 = "http://127.0.0.1:8081";
Vite Proxy Configuration (vite.config.js):
proxy: {
  '/api': {
    target: 'https://dev.api.hrms.vaics-consulting.com',
    // target: 'http://127.0.0.1:8081',  // commented out
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
    secure: false,
  }
}2. Configuration Location
The base URL is configured in multiple places:
Primary: src/path.js (imported as { path } throughout the app)
Proxy: vite.config.js (for /api prefixed requests)
Hardcoded: Several individual components have their own base URLs
3. Exact API Endpoint Path
For the 404 error you're experiencing, the exact endpoint being constructed is:http://127.0.0.1:8081/candidates/user-role-accessThis is built in src/component/settings/settings.jsx at lines 384-386:
// PUT request (edit mode)
await axios.put(`${path}/candidates/user-role-access${accessId ? `/${accessId}` : ''}`, requestPayload);

// POST request (create mode)  
await axios.post(`${path}/candidates/user-role-access`, requestPayload);4. Recent Changes Analysis
Looking at the git status, there have been recent modifications to key API-related files:
Staged Changes:
src/path.js - Modified (likely the base URL configuration)
src/main.jsx - Modified
src/App.jsx - Modified
Unstaged Changes:
src/component/settings/settings.jsx - Modified (the file with the 404 endpoint)
Key Issues Identified
Configuration Inconsistency: The vite proxy points to the production URL (dev.api.hrms.vaics-consulting.com) while path.js points to local development (127.0.0.1:8081)
Mixed Base URLs: Different components use different base URLs:
Most components: http://127.0.0.1:8081 (via path.js)
Document upload: http://localhost:8000/
Candidate context: https://dev.api.hrms.vaics-consulting.com
Recent Changes: The fact that src/path.js shows as modified in git suggests recent changes to the API configuration

python -m uvicorn app.main:app --reload --log-level debug