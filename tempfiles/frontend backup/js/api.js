const BASE_URL = 'http://192.168.45.98:8000';

function getHeaders(requireAuth = true) {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (requireAuth) {
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
    }
    return headers;
}

function getAuthHeaders() {
    const headers = {};
    const token = localStorage.getItem('access_token');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

async function handleResponse(res) {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        let errorMsg = data.message || data.detail || 'An unexpected error occurred.';
        if (typeof errorMsg === 'object') {
            errorMsg = JSON.stringify(errorMsg);
        }
        throw new Error(errorMsg);
    }
    return data;
}

const api = {
    auth: {
        register: async (userData) => {
            const res = await fetch(`${BASE_URL}/auth/register`, {
                method: 'POST',
                headers: getHeaders(false),
                body: JSON.stringify(userData)
            });
            return handleResponse(res);
        },
        login: async (credentials) => {
            const res = await fetch(`${BASE_URL}/auth/login`, {
                method: 'POST',
                headers: getHeaders(false),
                body: JSON.stringify(credentials)
            });
            return handleResponse(res);
        }
    },
    agents: {
        getAll: async () => {
            const res = await fetch(`${BASE_URL}/agent/all`, {
                method: 'GET',
                headers: getHeaders(true)
            });
            return handleResponse(res);
        },
        create: async (agentData) => {
            const res = await fetch(`${BASE_URL}/agent/create`, {
                method: 'POST',
                headers: getHeaders(true),
                body: JSON.stringify(agentData)
            });
            return handleResponse(res);
        },
        update: async (agentId, agentData) => {
            const res = await fetch(`${BASE_URL}/agent/update/${agentId}`, {
                method: 'PATCH',
                headers: getHeaders(true),
                body: JSON.stringify(agentData)
            });
            return handleResponse(res);
        },
        delete: async (agentId) => {
            const res = await fetch(`${BASE_URL}/agent/delete/${agentId}`, {
                method: 'DELETE',
                headers: getHeaders(true)
            });
            return handleResponse(res);
        }
    },
    chat: {
        run: async (agentId, requestData) => {
            const res = await fetch(`${BASE_URL}/chat/run/${agentId}`, {
                method: 'POST',
                headers: getHeaders(true),
                body: JSON.stringify(requestData)
            });
            return handleResponse(res);
        }
    },
    customDb: {
        linkMongo: async (data) => {
            const res = await fetch(`${BASE_URL}/custom-db/add/mongo`, {
                method: 'POST',
                headers: getHeaders(true),
                body: JSON.stringify(data)
            });
            return handleResponse(res);
        }
    },
    knowledgeBase: {
        upload: async (formData) => {
            const res = await fetch(`${BASE_URL}/knowledge-base/upload`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: formData
            });
            return handleResponse(res);
        }
    }
};
