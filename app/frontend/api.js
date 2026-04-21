const API_BASE_URL = window.location.origin;


class ApiClient {
    constructor() {
        this.token = localStorage.getItem("qab_token") || null;
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem("qab_token", token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem("qab_token");
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const headers = {
            ...(options.headers || {})
        };

        if (!options.isFormData) {
            headers["Content-Type"] = headers["Content-Type"] || "application/json";
        }

        if (this.token) {
            headers["Authorization"] = `Bearer ${this.token}`;
        }

        const nextOptions = {
            ...options,
            headers
        };

        if (!options.isFormData && nextOptions.body && typeof nextOptions.body === "object") {
            nextOptions.body = JSON.stringify(nextOptions.body);
        }

        const response = await fetch(url, nextOptions);
        let data = null;

        try {
            data = await response.json();
        } catch (error) {
            data = null;
        }

        if (!response.ok) {
            if (response.status === 401 && !endpoint.startsWith("/auth/login")) {
                window.dispatchEvent(new CustomEvent("qab-unauthorized"));
            }

            const detail = data?.detail;
            const detailMessage = typeof detail?.message === "string" ? detail.message : null;
            const message = data?.message || detailMessage || "Request failed";
            throw new Error(message);
        }

        return data;
    }

    async getHealth() {
        return this.request("/health");
    }

    async login(email, password) {
        const response = await this.request("/auth/login", {
            method: "POST",
            body: { email, password }
        });

        const accessToken = response?.data?.jwt_tokens?.access_token;
        if (accessToken) {
            this.setToken(accessToken);
            localStorage.setItem("qab_user", JSON.stringify(response.data.user_info));
        }

        return response;
    }

    async register(name, email, mobile, password) {
        return this.request("/auth/register", {
            method: "POST",
            body: { name, email, mobile, password }
        });
    }

    async getAgents() {
        return this.request("/agent/all");
    }

    async getAgent(agentId) {
        return this.request(`/agent/${agentId}`);
    }

    async createAgent(payload) {
        return this.request("/agent/create", {
            method: "POST",
            body: payload
        });
    }

    async updateAgent(agentId, payload) {
        return this.request(`/agent/update/${agentId}`, {
            method: "PATCH",
            body: payload
        });
    }

    async deleteAgent(agentId) {
        return this.request(`/agent/delete/${agentId}`, {
            method: "DELETE"
        });
    }

    async runAgent(agentId, query, threadId) {
        return this.request(`/chat/run/${agentId}`, {
            method: "POST",
            body: {
                query,
                thread_id: threadId
            }
        });
    }

    async loadOldChat(agentId) {
        return this.request(`/chat/load-old-chat/${agentId}`);
    }

    async getKBs() {
        return this.request("/knowledge-base/all");
    }

    async getKB(kbId) {
        return this.request(`/knowledge-base/${kbId}`);
    }

    async getEmbeddingOptions() {
        return this.request("/knowledge-base/embedding-options");
    }

    async createKB(payload) {
        return this.request("/knowledge-base/create", {
            method: "POST",
            body: payload
        });
    }

    async updateKB(kbId, payload) {
        return this.request(`/knowledge-base/update/${kbId}`, {
            method: "PATCH",
            body: payload
        });
    }

    async addFileToKB(kbId, file) {
        const formData = new FormData();
        formData.append("file", file);

        return this.request(`/knowledge-base/add-file/${kbId}`, {
            method: "POST",
            body: formData,
            isFormData: true
        });
    }

    async removeFileFromKB(kbId, fileName) {
        return this.request(`/knowledge-base/remove-file/${kbId}?file_name=${encodeURIComponent(fileName)}`, {
            method: "DELETE"
        });
    }

    async testKBSearch(kbId, payload) {
        return this.request(`/knowledge-base/test-search/${kbId}`, {
            method: "POST",
            body: payload
        });
    }

    async deleteKB(kbId) {
        return this.request(`/knowledge-base/delete/${kbId}`, {
            method: "DELETE"
        });
    }

    async getDBs() {
        return this.request("/custom-db/mydb");
    }

    async linkDB(payload) {
        return this.request("/custom-db/add", {
            method: "POST",
            body: payload
        });
    }

    async updateDB(dbId, payload) {
        return this.request(`/custom-db/update/${dbId}`, {
            method: "PATCH",
            body: payload
        });
    }

    async unlinkDB(dbId) {
        return this.request(`/custom-db/delete/${dbId}`, {
            method: "DELETE"
        });
    }
}


export const api = new ApiClient();
