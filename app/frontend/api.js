const API_BASE_URL = window.location.origin;
const CHAT_RUN_TIMEOUT_MS = 120000;
const REQUEST_TIMEOUT_MESSAGE = "Request timed out";

function formatValidationItems(items) {
    return items
        .map((item) => {
            const location = Array.isArray(item?.loc) ? item.loc.slice(1).join(".") : "";
            return location ? `${location}: ${item.msg}` : item?.msg;
        })
        .filter(Boolean)
        .join(" | ");
}

function formatErrorMessage(data) {
    const detail = data?.detail;
    const errorItems = Array.isArray(data?.data) ? data.data : null;

    if (typeof data?.message === "string" && errorItems?.length) {
        const formattedItems = formatValidationItems(errorItems);
        if (formattedItems) {
            return formattedItems;
        }
    }

    if (typeof detail?.message === "string") {
        return detail.message;
    }

    if (Array.isArray(detail) && detail.length > 0) {
        return formatValidationItems(detail);
    }

    return data?.message || "Request failed";
}


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
        const timeoutMs = options.timeoutMs;
        const timeoutController = timeoutMs ? new AbortController() : null;
        let timeoutId = null;
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
        delete nextOptions.timeoutMs;

        if (timeoutController) {
            nextOptions.signal = timeoutController.signal;
            timeoutId = window.setTimeout(() => timeoutController.abort(), timeoutMs);
        }

        if (!options.isFormData && nextOptions.body && typeof nextOptions.body === "object") {
            nextOptions.body = JSON.stringify(nextOptions.body);
        }

        let response = null;
        let data = null;

        try {
            response = await fetch(url, nextOptions);
            data = await response.json();
        } catch (error) {
            if (error?.name === "AbortError") {
                throw new Error(REQUEST_TIMEOUT_MESSAGE);
            }
            if (!response) {
                throw error;
            }
            data = null;
        } finally {
            if (timeoutId) {
                window.clearTimeout(timeoutId);
            }
        }

        if (!response.ok) {
            if (response.status === 401 && !endpoint.startsWith("/auth/login")) {
                window.dispatchEvent(new CustomEvent("qab-unauthorized"));
            }

            const message = formatErrorMessage(data);
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

    async register(name, email, password) {
        return this.request("/auth/register", {
            method: "POST",
            body: { name, email, password }
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

    async runAgent(agentId, query, history = []) {
        return this.request(`/chat/run/${agentId}`, {
            method: "POST",
            timeoutMs: CHAT_RUN_TIMEOUT_MS,
            body: {
                query,
                history
            }
        });
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

    async inspectDBSources(dbId) {
        return this.request(`/data-query/inspect/${dbId}`, {
            method: "POST"
        });
    }

    async getDataQueries() {
        return this.request("/data-query/all");
    }

    async getDataQuery(dataQueryId) {
        return this.request(`/data-query/${dataQueryId}`);
    }

    async createDataQuery(payload) {
        return this.request("/data-query/create", {
            method: "POST",
            body: payload
        });
    }

    async updateDataQuery(dataQueryId, payload) {
        return this.request(`/data-query/update/${dataQueryId}`, {
            method: "PATCH",
            body: payload
        });
    }

    async deleteDataQuery(dataQueryId) {
        return this.request(`/data-query/delete/${dataQueryId}`, {
            method: "DELETE"
        });
    }

    async getToolsCatalog() {
        return this.request("/tools/catalog");
    }

    async getGoogleConnectUrl() {
        return this.request("/tools/google/connect-url");
    }

    async disconnectTool(toolKey) {
        return this.request(`/tools/disconnect/${toolKey}`, {
            method: "DELETE"
        });
    }
}


export const api = new ApiClient();
