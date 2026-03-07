const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const API_ENDPOINTS = {
    DATA: `${API_BASE_URL}/api/data`,
    ALGORITHM: `${API_BASE_URL}/api/algorithm`,
    ANALYSIS: `${API_BASE_URL}/api/analysis`,
    REPORT: `${API_BASE_URL}/api/report`,
    VISUALIZATION: `${API_BASE_URL}/api/visualization`,
    AI: `${API_BASE_URL}/api/ai`,
};

export default API_BASE_URL;
