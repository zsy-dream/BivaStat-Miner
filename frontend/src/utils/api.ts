const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
    DATA: `${API_BASE_URL}/api/data`,
    ALGORITHM: `${API_BASE_URL}/api/algorithm`,
};

export default API_BASE_URL;
