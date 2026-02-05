import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
        'x-api-key': 'unsafe-secret-key-change-me' // In prod, use env var
    }
});

// Retry Logic
api.interceptors.response.use(null, async (error) => {
    const config = error.config;

    // If config does not exist or the retry option is not set, reject
    if (!config || !config.retry) {
        if (!config) return Promise.reject(error);
        config.retry = 3; // Default 3 retries
        config.retryDelay = 1000;
    }

    config.retry -= 1;

    if (config.retry === 0) {
        return Promise.reject(error);
    }

    // Exponential Backoff
    const delay = config.retryDelay || 1000;
    config.retryDelay = delay * 2;

    await new Promise((resolve) => setTimeout(resolve, delay));

    return api(config);
});

export const fetchSessions = async (filters = {}) => {
    try {
        const response = await api.get('/sessions', {
            retry: 3,
            params: filters
        });
        return response.data;
    } catch (e) {
        console.warn("API Error fetching sessions", e);
        return [];
    }
};

export const fetchSession = async (sessionId) => {
    try {
        const response = await api.get(`/sessions/${sessionId}`, { retry: 3 });
        return response.data;
    } catch (e) {
        console.error("API Error fetching session detail", e);
        return null;
    }
};

export const simulateScamMessage = async (sessionId, text) => {
    try {
        const payload = {
            sessionId: sessionId,
            message: {
                sender: "scammer",
                text: text,
                timestamp: Date.now()
            },
            conversationHistory: [],
            metadata: {
                channel: "Simulation",
                language: "English"
            }
        };

        const response = await api.post('/message', payload);
        return response.data;
    } catch (e) {
        console.error("API Error sending message", e);
        return null;
    }
};

export default api;
