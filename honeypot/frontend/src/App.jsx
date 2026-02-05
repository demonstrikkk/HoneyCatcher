import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard.jsx';
import SessionView from './pages/SessionView.jsx';
import Playground from './pages/Playground.jsx';
import VoicePlayground from './pages/VoicePlayground.jsx';
import LandingPage from './pages/LandingPage.jsx';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/playground" element={<Playground />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/session/:id" element={<SessionView />} />
        <Route path="/voice" element={<VoicePlayground />} />
      </Routes>
    </Router>
  );
}

export default App;
