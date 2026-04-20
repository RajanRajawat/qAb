/**
 * API Utility for QAB
 * Handles fetch requests, authorization headers, and global error handling.
 */

const API_BASE_URL = window.location.origin;

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('qab_token') || null;
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('qab_token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('qab_token');
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        // Special handling for multipart/form-data (uploads)
        if (options.isFormData) {
            delete headers['Content-Type'];
        } else if (options.body && typeof options.body === 'object') {
            options.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const data = await response.json();

            if (!response.ok) {
                // Handle unauthorized
                if (response.status === 401 && !url.includes('/auth/login')) {
                    window.dispatchEvent(new CustomEvent('qab-unauthorized'));
                }
                
                let errorMessage = data.message || 'Something went wrong';
                if (data.detail) {
                    if (typeof data.detail === 'string') {
                        errorMessage = data.detail;
                    } else if (Array.isArray(data.detail)) {
                        errorMessage = data.detail.map(d => d.msg || JSON.stringify(d)).join(', ');
                    } else {
                        errorMessage = JSON.stringify(data.detail);
                    }
                }
                throw new Error(errorMessage);
            }

            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // Auth
    async login(email, password) {
        const res = await this.request('/auth/login', {
            method: 'POST',
            body: { email, password }
        });
        if (res.data?.jwt_tokens?.access_token) {
            this.setToken(res.data.jwt_tokens.access_token);
            localStorage.setItem('qab_user', JSON.stringify(res.data.user_info));
        }
        return res;
    }

    async register(name, email, mobile, password) {
        return await this.request('/auth/register', {
            method: 'POST',
            body: { name, email, mobile, password }
        });
    }

    // Agents
    async getAgents() {
        return await this.request('/agent/all');
    }

    async createAgent(agentData) {
        return await this.request('/agent/create', {
            method: 'POST',
            body: agentData
        });
    }

    async updateAgent(id, agentData) {
        return await this.request(`/agent/update/${id}`, {
            method: 'PATCH',
            body: agentData
        });
    }

    async deleteAgent(id) {
        return await this.request(`/agent/delete/${id}`, {
            method: 'DELETE'
        });
    }

    // Knowledge Base
    async getKBs() {
        return await this.request('/knowledge-base/all');
    }

    async createKB(kbData) {
        return await this.request('/knowledge-base/create', {
            method: 'POST',
            body: kbData
        });
    }

    async deleteKB(id) {
        return await this.request(`/knowledge-base/delete/${id}`, {
            method: 'DELETE'
        });
    }

    async addFileToKB(kbId, file) {
        const formData = new FormData();
        formData.append('file', file);
        return await this.request(`/knowledge-base/add-file/${kbId}`, {
            method: 'POST',
            body: formData,
            isFormData: true
        });
    }

    async removeFileFromKB(kbId, fileName) {
        return await this.request(`/knowledge-base/remove-file/${kbId}?file_name=${encodeURIComponent(fileName)}`, {
            method: 'DELETE'
        });
    }

    // Databases
    async getDBs() {
        return await this.request('/custom-db/mydb');
    }

    async linkDB(dbData) {
        return await this.request('/custom-db/add', {
            method: 'POST',
            body: dbData
        });
    }

    async unlinkDB(id) {
        return await this.request(`/custom-db/delete/${id}`, {
            method: 'DELETE'
        });
    }

    // Chat
    async runAgent(agentId, query, threadId) {
        return await this.request(`/chat/run/${agentId}`, {
            method: 'POST',
            body: { query, thread_id: threadId }
        });
    }
}

export const api = new ApiClient();
