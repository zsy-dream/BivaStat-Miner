import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';

const Home = lazy(() => import('./pages/Home'));
const DataManagement = lazy(() => import('./pages/DataManagement'));
const AlgorithmConfig = lazy(() => import('./pages/AlgorithmConfig'));
const AnalysisResult = lazy(() => import('./pages/AnalysisResult'));

function App() {
  return (
    <Router>
      <Layout>
        <Suspense fallback={<div className="flex items-center justify-center min-h-screen">加载中...</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/data" element={<DataManagement />} />
            <Route path="/algorithm" element={<AlgorithmConfig />} />
            <Route path="/analysis" element={<AnalysisResult />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </Layout>
    </Router>
  );
}

export default App;
