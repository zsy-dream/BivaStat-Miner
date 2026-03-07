import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { RefreshCw, Activity } from 'lucide-react';
import Layout from './components/Layout';
import { ToastProvider } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';

const Home = lazy(() => import('./pages/Home'));
const DataManagement = lazy(() => import('./pages/DataManagement'));
const AlgorithmConfig = lazy(() => import('./pages/AlgorithmConfig'));
const AnalysisResult = lazy(() => import('./pages/AnalysisResult'));
const Visualization = lazy(() => import('./pages/Visualization'));
const ReportGeneration = lazy(() => import('./pages/ReportGeneration'));
const History = lazy(() => import('./pages/History'));
const Help = lazy(() => import('./pages/Help'));

function App() {
  return (
    <Router>
      <ToastProvider>
      <Layout>
        <ErrorBoundary>
        <Suspense fallback={
          <div className="flex flex-col items-center justify-center min-h-[60vh] w-full gap-4 text-[#787774] animate-in fade-in duration-500">
            <div className="relative">
              <RefreshCw className="w-10 h-10 animate-spin opacity-20" />
              <Activity className="w-5 h-5 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[#2383e2]" />
            </div>
            <p className="text-sm font-bold tracking-tight animate-pulse uppercase">构件解析中 · Parsing Engine Hub</p>
          </div>
        }>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/data" element={<DataManagement />} />
            <Route path="/algorithm" element={<AlgorithmConfig />} />
            <Route path="/analysis_result" element={<AnalysisResult />} />
            <Route path="/visualization" element={<Visualization />} />
            <Route path="/report" element={<ReportGeneration />} />
            <Route path="/history" element={<History />} />
            <Route path="/help" element={<Help />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
        </ErrorBoundary>
      </Layout>
      </ToastProvider>
    </Router>
  );
}

export default App;
