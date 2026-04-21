import { api } from "./api.js?v=20260421b";

window.refreshIcons = window.refreshIcons || (() => {
    if (window.lucide?.createIcons) {
        window.lucide.createIcons();
        return;
    }

    if (window.feather?.replace) {
        window.feather.replace();
    }
});


const state = {
    user: JSON.parse(localStorage.getItem("qab_user") || "null"),
    isAuthenticated: Boolean(localStorage.getItem("qab_token")),
    currentHash: window.location.hash || "#dashboard",
    health: null
};

const llmOptions = {
    groq: [
        { value: "llama-3.1-8b-instant", label: "Llama 3.1 8B Instant" }
    ],
    gemini: [
        { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" }
    ]
};

const toolOptions = [
    {
        value: "web_search",
        label: "Web Search",
        description: "Lets the agent search the web using the current Tavily-backed tool."
    }
];


function getApp() {
    return document.getElementById("app");
}

function escapeHtml(value = "") {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function renderMarkdown(value = "") {
    let html = escapeHtml(value);

    html = html.replace(/```([\s\S]*?)```/g, (_match, code) => `<pre><code>${code}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    html = html.replace(/\n/g, "<br>");

    return html;
}

function formatDate(value) {
    if (!value) {
        return "Not available";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString();
}

function navigate(hash) {
    window.location.hash = hash;
}

function icon(name, className = "ui-icon") {
    const icons = {
        dashboard: `<path d="M3 13.2h8.2V3H3z"/><path d="M12.8 21H21v-11.2h-8.2z"/><path d="M12.8 10.2H21V3h-8.2z"/><path d="M3 21h8.2v-6.2H3z"/>`,
        bot: `<path d="M9 7V4h6v3"/><rect x="4" y="7" width="16" height="11" rx="3"/><path d="M9 18v2"/><path d="M15 18v2"/><path d="M9 12h.01"/><path d="M15 12h.01"/>`,
        database: `<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/><path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>`,
        book: `<path d="M5 4.5A2.5 2.5 0 0 1 7.5 2H19v18H7.5A2.5 2.5 0 0 0 5 22"/><path d="M5 4.5V22"/><path d="M9 6h7"/><path d="M9 10h7"/>`,
        user: `<path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="8" r="4"/>`,
        logout: `<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>`,
        close: `<path d="M18 6 6 18"/><path d="m6 6 12 12"/>`,
        login: `<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="M10 17l5-5-5-5"/><path d="M15 12H3"/>`,
        register: `<path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/><circle cx="9.5" cy="7" r="4"/><path d="M19 8v6"/><path d="M16 11h6"/>`,
        plus: `<path d="M12 5v14"/><path d="M5 12h14"/>`,
        message: `<path d="M7 10h10"/><path d="M7 14h6"/><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>`,
        eye: `<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z"/><circle cx="12" cy="12" r="3"/>`,
        edit: `<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>`,
        trash: `<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>`,
        search: `<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>`,
        upload: `<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M20 16.5V19a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2.5"/>`,
        back: `<path d="m15 18-6-6 6-6"/><path d="M21 12H9"/>`,
        send: `<path d="M22 2 11 13"/><path d="m22 2-7 20-4-9-9-4Z"/>`,
        folder: `<path d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>`,
        link: `<path d="M10 13a5 5 0 0 0 7.1 0l2.8-2.8a5 5 0 0 0-7.1-7.1L11 5"/><path d="M14 11a5 5 0 0 0-7.1 0l-2.8 2.8a5 5 0 0 0 7.1 7.1L13 19"/>`,
        settings: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1A1.7 1.7 0 0 0 10 3.2V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1Z"/>`,
        file: `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 15h6"/><path d="M9 11h3"/>`,
        retry: `<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>`
    };

    return `
        <svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            ${icons[name] || icons.folder}
        </svg>
    `;
}

function showToast(message, type = "success") {
    const root = document.getElementById("toast-root");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    root.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("toast-hide");
        setTimeout(() => toast.remove(), 240);
    }, 2600);
}

function setLoading(message) {
    getApp().innerHTML = `
        <div class="screen-center">
            <div class="loader-circle"></div>
            <p class="muted">${escapeHtml(message)}</p>
        </div>
    `;
}

function getLayout(content, active = "") {
    return `
        <div class="shell">
            <aside class="sidebar">
                <div class="brand">
                    <div class="brand-mark">Q</div>
                    <div>
                        <h1>QAB</h1>
                        <p>Agent workspace</p>
                    </div>
                </div>
                <nav class="nav">
                    <a href="#dashboard" class="nav-link ${active === "dashboard" ? "active" : ""}">${icon("dashboard")}<span>Dashboard</span></a>
                    <a href="#agents" class="nav-link ${active === "agents" ? "active" : ""}">${icon("bot")}<span>Agents</span></a>
                    <a href="#knowledge-bases" class="nav-link ${active === "knowledge-bases" ? "active" : ""}">${icon("book")}<span>Knowledge Bases</span></a>
                    <a href="#databases" class="nav-link ${active === "databases" ? "active" : ""}">${icon("database")}<span>Databases</span></a>
                </nav>
                <div class="sidebar-footer">
                    <div class="user-chip">
                        <strong>${icon("user", "ui-icon user-chip-icon")}${escapeHtml(state.user?.name || "User")}</strong>
                        <span>${escapeHtml(state.user?.email || "")}</span>
                    </div>
                    <button class="button button-secondary" id="logout-btn">${icon("logout")}<span>Logout</span></button>
                </div>
            </aside>
            <main class="main-panel">
                ${content}
            </main>
        </div>
    `;
}

function bindLayoutEvents() {
    const logoutButton = document.getElementById("logout-btn");
    if (logoutButton) {
        logoutButton.onclick = () => {
            api.clearToken();
            localStorage.removeItem("qab_user");
            state.user = null;
            state.isAuthenticated = false;
            showToast("Logged out");
            navigate("#login");
        };
    }
}

function openModal(title, content) {
    const root = document.getElementById("modal-root");
    root.innerHTML = `
        <div class="modal-backdrop" id="modal-backdrop">
            <div class="modal-card">
                <div class="modal-header">
                    <div>
                        <h3>${escapeHtml(title)}</h3>
                    </div>
                    <button class="icon-button" id="modal-close" aria-label="Close">${icon("close")}</button>
                </div>
                <div class="modal-body">${content}</div>
            </div>
        </div>
    `;

    document.getElementById("modal-close").onclick = closeModal;
    document.getElementById("modal-backdrop").onclick = (event) => {
        if (event.target.id === "modal-backdrop") {
            closeModal();
        }
    };
}

function closeModal() {
    document.getElementById("modal-root").innerHTML = "";
}

function getModelOptions(provider, selectedValue) {
    return llmOptions[provider]
        .map((option) => `
            <option value="${option.value}" ${selectedValue === option.value ? "selected" : ""}>
                ${escapeHtml(option.label)}
            </option>
        `)
        .join("");
}

function bindProviderModelSelects(providerId, modelId, selectedModel) {
    const providerSelect = document.getElementById(providerId);
    const modelSelect = document.getElementById(modelId);

    const renderModels = (provider, initialModel) => {
        const providerModels = llmOptions[provider] || [];
        const preferred = providerModels.find((item) => item.value === initialModel)?.value || providerModels[0]?.value;
        modelSelect.innerHTML = getModelOptions(provider, preferred);
    };

    renderModels(providerSelect.value, selectedModel);
    providerSelect.onchange = () => renderModels(providerSelect.value, null);
}

function getKbSetupGuideMarkup() {
    return `
        <div class="stack">
            <div class="detail-card">
                <span>MongoDB Atlas Vector Search JSON</span>
                <strong>Use this in the Atlas vector search JSON editor:</strong>
                <pre><code>{
  "fields": [
    {
      "numDimensions": 384,
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    },
    {
      "path": "owner_id",
      "type": "filter"
    },
    {
      "path": "knowledge_base_id",
      "type": "filter"
    }
  ]
}</code></pre>
            </div>
            <div class="detail-card">
                <span>MongoDB Collection Path</span>
                <strong>For custom MongoDB in this backend, embeddings are written to <code>qab_test.embeddings</code>.</strong>
            </div>
            <div class="detail-card">
                <span>PostgreSQL / Supabase SQL</span>
                <strong>Run this in the SQL editor before using pgvector:</strong>
                <pre><code>create extension if not exists vector with schema extensions;</code></pre>
            </div>
        </div>
    `;
}

async function renderLogin() {
    getApp().innerHTML = `
        <section class="auth-shell">
            <div class="auth-hero">
                <div class="eyebrow">Blue and white, rebuilt cleanly</div>
                <h1>Query-driven agent builder with KB-aware retrieval.</h1>
                <p>Sign in to manage agents, databases, embeddings, and vector search tests from one UI.</p>
            </div>
            <div class="auth-card auth-card-themed">
                <div class="auth-topbar-link">
                    <span>Need an account?</span>
                    <a class="button button-primary" href="#register">${icon("register")}<span>Register</span></a>
                </div>
                <h2>Welcome Back</h2>
                <p class="muted auth-copy">Please enter your credentials to access your account.</p>
                <form id="login-form" class="stack">
                    <label class="field">
                        <span>Email</span>
                        <input id="login-email" type="email" required placeholder="name@example.com">
                    </label>
                    <label class="field">
                        <span>Password</span>
                        <input id="login-password" type="password" required placeholder="Password">
                    </label>
                    <button class="button button-dark wide-button" type="submit">${icon("login")}<span>Sign In</span></button>
                </form>
            </div>
        </section>
    `;

    document.getElementById("login-form").onsubmit = async (event) => {
        event.preventDefault();

        try {
            await api.login(
                document.getElementById("login-email").value,
                document.getElementById("login-password").value
            );

            state.user = JSON.parse(localStorage.getItem("qab_user") || "null");
            state.isAuthenticated = true;
            showToast("Login successful");
            navigate("#dashboard");
        } catch (error) {
            showToast(error.message, "error");
        }
    };
}

async function renderRegister() {
    getApp().innerHTML = `
        <section class="auth-shell">
            <div class="auth-hero">
                <div class="eyebrow">Create your workspace</div>
                <h1>Register once, then manage the full QAB backend from the browser.</h1>
                <p>The frontend talks directly to auth, agent, KB, DB, health, and chat endpoints.</p>
            </div>
            <div class="auth-card auth-card-themed">
                <div class="auth-topbar-link">
                    <span>Already registered?</span>
                    <a class="button button-primary" href="#login">${icon("login")}<span>Login</span></a>
                </div>
                <h2>Create Account</h2>
                <p class="muted auth-copy">Let's get started with your journey.</p>
                <form id="register-form" class="stack">
                    <label class="field">
                        <span>Name</span>
                        <input id="register-name" type="text" required placeholder="Your name">
                    </label>
                    <label class="field">
                        <span>Email</span>
                        <input id="register-email" type="email" required placeholder="name@example.com">
                    </label>
                    <label class="field">
                        <span>Password</span>
                        <input id="register-password" type="password" required placeholder="Strong password">
                    </label>
                    <button class="button button-dark wide-button" type="submit">${icon("register")}<span>Create Account</span></button>
                </form>
            </div>
        </section>
    `;

    document.getElementById("register-form").onsubmit = async (event) => {
        event.preventDefault();

        try {
            await api.register(
                document.getElementById("register-name").value,
                document.getElementById("register-email").value,
                document.getElementById("register-password").value
            );
            showToast("Registration successful");
            navigate("#login");
        } catch (error) {
            showToast(error.message, "error");
        }
    };
}

async function renderDashboard() {
    setLoading("Loading dashboard");

    const [agentsRes, kbRes, dbRes] = await Promise.all([
        api.getAgents(),
        api.getKBs(),
        api.getDBs()
    ]);

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Overview</div>
                <h2>Dashboard</h2>
                <p class="muted">Live status and quick entry points.</p>
            </div>
        </section>
        <section class="stats-grid">
            <article class="stat-card">
                <span class="stat-label">${icon("bot")}<span>Agents</span></span>
                <strong>${agentsRes.data.length}</strong>
            </article>
            <article class="stat-card">
                <span class="stat-label">${icon("book")}<span>Knowledge Bases</span></span>
                <strong>${kbRes.data.length}</strong>
            </article>
            <article class="stat-card">
                <span class="stat-label">${icon("database")}<span>Databases</span></span>
                <strong>${dbRes.data.length}</strong>
            </article>
        </section>
        <section class="two-col">
            <article class="panel">
                <div class="panel-head">
                    <h3>Recent Knowledge Bases</h3>
                    <a href="#knowledge-bases">${icon("book", "ui-icon inline-icon")}<span>Open all</span></a>
                </div>
                <div class="list-stack">
                    ${kbRes.data.slice(0, 4).map((kb) => `
                        <button class="list-card list-button open-kb" data-id="${kb.kb_id}">
                            <div>
                                <strong>${escapeHtml(kb.name)}</strong>
                                <span>${escapeHtml(kb.embedding_label)} • ${escapeHtml(kb.db_name)}</span>
                            </div>
                            <small>${kb.file_count} files</small>
                        </button>
                    `).join("") || `<div class="empty-card">No KBs yet.</div>`}
                </div>
            </article>
            <article class="panel">
                <div class="panel-head">
                    <h3>Recent Agents</h3>
                    <a href="#agents">${icon("settings", "ui-icon inline-icon")}<span>Manage</span></a>
                </div>
                <div class="list-stack">
                    ${agentsRes.data.slice(0, 4).map((agent) => `
                        <button class="list-card list-button open-chat" data-id="${agent._id}">
                            <div>
                                <strong>${escapeHtml(agent.name)}</strong>
                                <span>${escapeHtml(agent.llm_provider)} • ${escapeHtml(agent.llm_model)}</span>
                            </div>
                            <small>${agent.knowledge_base ? "RAG on" : "RAG off"}</small>
                        </button>
                    `).join("") || `<div class="empty-card">No agents yet.</div>`}
                </div>
            </article>
        </section>
    `, "dashboard");

    document.querySelectorAll(".open-kb").forEach((button) => {
        button.onclick = () => navigate(`#knowledge-bases/${button.dataset.id}`);
    });

    document.querySelectorAll(".open-chat").forEach((button) => {
        button.onclick = () => navigate(`#chat/${button.dataset.id}`);
    });

    bindLayoutEvents();
}

function getAgentFormMarkup(agent, kbs) {
    const isEdit = Boolean(agent);
    const selectedTools = new Set(agent?.tools || []);

    return `
        <form id="${isEdit ? "edit-agent-form" : "create-agent-form"}" class="stack">
            <label class="field">
                <span>Name</span>
                <input id="agent-name" required value="${escapeHtml(agent?.name || "")}" placeholder="Sales assistant">
            </label>
            <label class="field">
                <span>Description</span>
                <input id="agent-description" required value="${escapeHtml(agent?.description || "")}" placeholder="Short user-facing description">
            </label>
            <label class="field">
                <span>Role</span>
                <input id="agent-role" required value="${escapeHtml(agent?.role || "")}" placeholder="Expert support agent">
            </label>
            <label class="field">
                <span>Instructions</span>
                <textarea id="agent-instruction" required rows="4" placeholder="What should the agent do?">${escapeHtml(agent?.instruction || "")}</textarea>
            </label>
            <div class="form-row">
                <label class="field">
                    <span>Provider</span>
                    <select id="agent-provider">
                        <option value="groq" ${agent?.llm_provider === "groq" || !agent ? "selected" : ""}>Groq</option>
                        <option value="gemini" ${agent?.llm_provider === "gemini" ? "selected" : ""}>Gemini</option>
                    </select>
                </label>
                <label class="field">
                    <span>Model</span>
                    <select id="agent-model"></select>
                </label>
            </div>
            <label class="field">
                <span>Temperature</span>
                <input id="agent-temperature" type="number" min="0" max="1" step="0.1" value="${escapeHtml(agent?.temperature ?? 0.7)}">
            </label>
            <div class="field">
                <span>Tools</span>
                <div class="tool-grid">
                    ${toolOptions.map((tool) => `
                        <label class="tool-option">
                            <div class="tool-option-head">
                                <input
                                    class="agent-tool-checkbox"
                                    type="checkbox"
                                    value="${tool.value}"
                                    ${selectedTools.has(tool.value) ? "checked" : ""}
                                >
                                <strong>${escapeHtml(tool.label)}</strong>
                            </div>
                            <small>${escapeHtml(tool.description)}</small>
                        </label>
                    `).join("")}
                </div>
            </div>
            <div class="inline-check">
                <input id="agent-kb-enabled" type="checkbox" ${agent?.knowledge_base ? "checked" : ""}>
                <span>Attach a knowledge base</span>
            </div>
            <label class="field">
                <span>Knowledge Base</span>
                <select id="agent-kb-id" ${agent?.knowledge_base ? "" : "disabled"}>
                    <option value="">Select knowledge base</option>
                    ${kbs.map((kb) => `
                        <option value="${kb.kb_id}" ${agent?.knowledge_base_id === kb.kb_id ? "selected" : ""}>
                            ${escapeHtml(kb.name)}
                        </option>
                    `).join("")}
                </select>
            </label>
            <button class="button button-primary" type="submit">${icon(isEdit ? "edit" : "plus")}<span>${isEdit ? "Save changes" : "Create agent"}</span></button>
        </form>
    `;
}

async function openAgentModal(agent = null, onDone) {
    const kbs = (await api.getKBs()).data;
    const title = agent ? "Edit Agent" : "Create Agent";

    openModal(title, getAgentFormMarkup(agent, kbs));
    bindProviderModelSelects("agent-provider", "agent-model", agent?.llm_model);

    const kbEnabled = document.getElementById("agent-kb-enabled");
    const kbSelect = document.getElementById("agent-kb-id");
    kbEnabled.onchange = () => {
        kbSelect.disabled = !kbEnabled.checked;
        if (!kbEnabled.checked) {
            kbSelect.value = "";
        }
    };

    const form = document.querySelector("form");
    form.onsubmit = async (event) => {
        event.preventDefault();

        const selectedTools = Array.from(document.querySelectorAll(".agent-tool-checkbox:checked"))
            .map((node) => node.value);

        const payload = {
            name: document.getElementById("agent-name").value,
            description: document.getElementById("agent-description").value,
            role: document.getElementById("agent-role").value,
            instruction: document.getElementById("agent-instruction").value,
            llm_provider: document.getElementById("agent-provider").value,
            llm_model: document.getElementById("agent-model").value,
            temperature: Number(document.getElementById("agent-temperature").value),
            knowledge_base: kbEnabled.checked,
            knowledge_base_id: kbEnabled.checked ? document.getElementById("agent-kb-id").value || null : null,
            tools: selectedTools
        };

        try {
            if (agent) {
                await api.updateAgent(agent._id, payload);
                showToast("Agent updated");
            } else {
                await api.createAgent(payload);
                showToast("Agent created");
            }

            closeModal();
            await onDone();
        } catch (error) {
            showToast(error.message, "error");
        }
    };
}

async function renderAgents() {
    setLoading("Loading agents");

    const response = await api.getAgents();
    const agents = response.data;

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Agents</div>
                <h2>Agent management</h2>
                <p class="muted">Create, inspect, update, delete, and chat with each agent.</p>
            </div>
            <button class="button button-primary" id="create-agent-button">${icon("plus")}<span>Create agent</span></button>
        </section>
        <section class="card-grid">
            ${agents.map((agent) => `
                <article class="panel card-panel">
                    <div class="panel-head">
                        <div>
                            <h3>${escapeHtml(agent.name)}</h3>
                            <p class="muted">${escapeHtml(agent.description)}</p>
                        </div>
                        <details class="card-menu">
                            <summary>•••</summary>
                            <div class="card-menu-list">
                                <button class="card-menu-action edit-agent" data-id="${agent._id}">${icon("edit", "ui-icon inline-icon")}<span>Edit</span></button>
                                <button class="card-menu-action delete-agent delete" data-id="${agent._id}">${icon("trash", "ui-icon inline-icon")}<span>Delete</span></button>
                            </div>
                        </details>
                    </div>
                    <div class="meta-grid">
                        <div><span>Model</span><strong>${escapeHtml(agent.llm_model)}</strong></div>
                        <div><span>KB</span><strong>${agent.knowledge_base ? "Connected" : "None"}</strong></div>
                        <div><span>Temp</span><strong>${escapeHtml(agent.temperature)}</strong></div>
                        <div><span>Created</span><strong>${escapeHtml(formatDate(agent.created_at))}</strong></div>
                    </div>
                    <div class="panel-actions">
                        <button class="button button-secondary chat-agent" data-id="${agent._id}">${icon("message")}<span>Chat</span></button>
                        <button class="button button-secondary view-agent" data-id="${agent._id}">${icon("eye")}<span>View</span></button>
                    </div>
                </article>
            `).join("") || `<div class="empty-card">No agents created yet.</div>`}
        </section>
    `, "agents");

    const refresh = async () => renderAgents();

    document.getElementById("create-agent-button").onclick = async () => {
        await openAgentModal(null, refresh);
    };

    document.querySelectorAll(".chat-agent").forEach((button) => {
        button.onclick = () => navigate(`#chat/${button.dataset.id}`);
    });

    document.querySelectorAll(".view-agent").forEach((button) => {
        button.onclick = async () => {
            try {
                const responseDetail = await api.getAgent(button.dataset.id);
                const agent = responseDetail.data;

                openModal("Agent Details", `
                    <div class="stack">
                        <div class="detail-card"><span>Name</span><strong>${escapeHtml(agent.name)}</strong></div>
                        <div class="detail-card"><span>Description</span><strong>${escapeHtml(agent.description)}</strong></div>
                        <div class="detail-card"><span>Role</span><strong>${escapeHtml(agent.role)}</strong></div>
                        <div class="detail-card"><span>Instructions</span><strong>${escapeHtml(agent.instruction)}</strong></div>
                        <div class="detail-card"><span>Tools</span><strong>${escapeHtml((agent.tools || []).join(", ") || "No tools selected")}</strong></div>
                    </div>
                `);
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    });

    document.querySelectorAll(".edit-agent").forEach((button) => {
        button.onclick = async () => {
            try {
                const responseDetail = await api.getAgent(button.dataset.id);
                await openAgentModal(responseDetail.data, refresh);
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    });

    document.querySelectorAll(".delete-agent").forEach((button) => {
        button.onclick = async () => {
            if (!window.confirm("Delete this agent and its stored chat history?")) {
                return;
            }

            try {
                await api.deleteAgent(button.dataset.id);
                showToast("Agent deleted");
                await refresh();
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    });

    bindLayoutEvents();
}

async function openCreateKBModal(onDone) {
    const [dbs, embeddingOptions] = await Promise.all([
        api.getDBs(),
        api.getEmbeddingOptions()
    ]);

    openModal("Create Knowledge Base", `
        <form id="create-kb-form" class="stack">
            <label class="field">
                <span>Name</span>
                <input id="kb-name" required placeholder="Customer docs">
            </label>
            <label class="field">
                <span>Embedding model</span>
                <select id="kb-embedding-model">
                    ${embeddingOptions.data.map((option) => `
                        <option value="${option.value}" ${option.is_default ? "selected" : ""}>
                            ${escapeHtml(option.label)}
                        </option>
                    `).join("")}
                </select>
                <small class="field-note" id="embedding-note"></small>
            </label>
            <label class="field">
                <span>Storage database</span>
                <select id="kb-db">
                    <option value="default">Default DB</option>
                    ${dbs.data.map((db) => `
                        <option value="${db.db_id}">${escapeHtml(db.name)} (${escapeHtml(db.provider)})</option>
                    `).join("")}
                </select>
            </label>
            <button class="button button-primary" type="submit">${icon("plus")}<span>Create knowledge base</span></button>
        </form>
    `);

    const embeddingSelect = document.getElementById("kb-embedding-model");
    const embeddingNote = document.getElementById("embedding-note");
    const notes = Object.fromEntries(embeddingOptions.data.map((item) => [item.value, item.description]));

    const setNote = () => {
        embeddingNote.textContent = notes[embeddingSelect.value] || "";
    };

    setNote();
    embeddingSelect.onchange = setNote;

    document.getElementById("create-kb-form").onsubmit = async (event) => {
        event.preventDefault();

        try {
            await api.createKB({
                name: document.getElementById("kb-name").value,
                db_id: document.getElementById("kb-db").value,
                embedding_model: embeddingSelect.value
            });

            showToast("Knowledge base created");
            closeModal();
            await onDone();
        } catch (error) {
            showToast(error.message, "error");
        }
    };
}

async function renderKnowledgeBases() {
    setLoading("Loading knowledge bases");

    const response = await api.getKBs();
    const kbs = response.data;

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Knowledge Bases</div>
                <h2>Embedding-aware document stores</h2>
                <p class="muted">Each KB persists its own embedding model and can be tested with live vector search.</p>
            </div>
            <div class="hero-actions">
                <button class="button button-secondary" id="kb-guide-page">${icon("book")}<span>Setup Guide</span></button>
                <button class="button button-primary" id="create-kb-button">${icon("plus")}<span>Create KB</span></button>
            </div>
        </section>
        <section class="card-grid">
            ${kbs.map((kb) => `
                <article class="panel card-panel">
                    <div class="panel-head">
                        <div>
                            <h3>${escapeHtml(kb.name)}</h3>
                            <p class="muted">${escapeHtml(kb.embedding_label)} • ${escapeHtml(kb.db_name)}</p>
                        </div>
                        <details class="card-menu">
                            <summary>•••</summary>
                            <div class="card-menu-list">
                                <button class="card-menu-action rename-kb" data-id="${kb.kb_id}" data-name="${escapeHtml(kb.name)}">${icon("edit", "ui-icon inline-icon")}<span>Edit</span></button>
                                <button class="card-menu-action delete-kb delete" data-id="${kb.kb_id}">${icon("trash", "ui-icon inline-icon")}<span>Delete</span></button>
                            </div>
                        </details>
                    </div>
                    <div class="kb-tags">
                        <span class="tag">${escapeHtml(kb.db_name)}</span>
                        <span class="tag">${escapeHtml(kb.embedding_model)}</span>
                    </div>
                    <div class="panel-actions">
                        <button class="button button-secondary open-kb-detail" data-id="${kb.kb_id}">${icon("folder")}<span>Open</span></button>
                        <button class="button button-secondary kb-test" data-id="${kb.kb_id}">${icon("search")}<span>Test Search</span></button>
                    </div>
                </article>
            `).join("") || `<div class="empty-card">No knowledge bases created yet.</div>`}
        </section>
    `, "knowledge-bases");

    const refresh = async () => renderKnowledgeBases();

    document.getElementById("create-kb-button").onclick = async () => {
        await openCreateKBModal(refresh);
    };

    document.getElementById("kb-guide-page").onclick = () => {
        openModal("Knowledge Base Setup Guide", getKbSetupGuideMarkup());
    };

    document.querySelectorAll(".open-kb-detail").forEach((button) => {
        button.onclick = () => navigate(`#knowledge-bases/${button.dataset.id}`);
    });

    document.querySelectorAll(".kb-test").forEach((button) => {
        button.onclick = () => navigate(`#knowledge-bases/${button.dataset.id}`);
    });

    document.querySelectorAll(".rename-kb").forEach((button) => {
        button.onclick = () => {
            openModal("Rename Knowledge Base", `
                <form id="rename-kb-form" class="stack">
                    <label class="field">
                        <span>Name</span>
                        <input id="rename-kb-name" required value="${button.dataset.name}">
                    </label>
                    <button class="button button-primary" type="submit">${icon("edit")}<span>Save name</span></button>
                </form>
            `);

            document.getElementById("rename-kb-form").onsubmit = async (event) => {
                event.preventDefault();

                try {
                    await api.updateKB(button.dataset.id, {
                        name: document.getElementById("rename-kb-name").value
                    });
                    closeModal();
                    showToast("Knowledge base updated");
                    await refresh();
                } catch (error) {
                    showToast(error.message, "error");
                }
            };
        };
    });

    document.querySelectorAll(".delete-kb").forEach((button) => {
        button.onclick = async () => {
            if (!window.confirm("Delete this knowledge base and its embeddings?")) {
                return;
            }

            try {
                await api.deleteKB(button.dataset.id);
                showToast("Knowledge base deleted");
                await refresh();
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    });

    bindLayoutEvents();
}

async function renderKnowledgeBaseDetail(kbId) {
    setLoading("Loading knowledge base");

    const response = await api.getKB(kbId);
    const kb = response.data;

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Knowledge Base Detail</div>
                <h2>${escapeHtml(kb.name)}</h2>
                <p class="muted">${escapeHtml(kb.embedding_label)} stored in ${escapeHtml(kb.db_name)}</p>
            </div>
            <div class="hero-actions">
                <a class="button button-secondary" href="#knowledge-bases">${icon("back")}<span>Back</span></a>
                <button class="button button-secondary" id="rename-kb-detail">${icon("edit")}<span>Edit name</span></button>
            </div>
        </section>
        <section class="two-col detail-layout">
            <article class="panel">
                <div class="panel-head">
                    <h3>Files</h3>
                    <label class="button button-primary upload-label" for="kb-upload-input">${icon("upload")}<span>Upload file</span></label>
                    <input id="kb-upload-input" type="file" hidden accept=".txt,.pdf">
                </div>
                <div class="list-stack">
                    ${kb.files.map((file) => `
                        <div class="list-card">
                            <div>
                                <strong>${escapeHtml(file)}</strong>
                                <span>${escapeHtml(kb.embedding_label)}</span>
                            </div>
                            <button class="button button-danger remove-kb-file" data-file="${escapeHtml(file)}">${icon("trash")}<span>Remove</span></button>
                        </div>
                    `).join("") || `<div class="empty-card">No files uploaded yet.</div>`}
                </div>
            </article>
            <article class="panel">
                <div class="panel-head">
                    <h3>Test Vector Search</h3>
                    <span class="tag">Top chunks</span>
                </div>
                <form id="kb-search-form" class="stack">
                    <label class="field">
                        <span>Query</span>
                        <textarea id="kb-search-query" rows="4" placeholder="Ask a question to inspect the retrieved chunks"></textarea>
                    </label>
                    <label class="field">
                        <span>Limit</span>
                        <input id="kb-search-limit" type="number" min="1" max="10" value="3">
                    </label>
                    <button class="button button-primary" type="submit">${icon("search")}<span>Test search</span></button>
                </form>
                <div id="kb-search-results" class="search-results muted">No test run yet.</div>
            </article>
        </section>
        <section class="panel">
            <div class="meta-grid">
                <div><span>Embedding model</span><strong>${escapeHtml(kb.embedding_model)}</strong></div>
                <div><span>Embedding label</span><strong>${escapeHtml(kb.embedding_label)}</strong></div>
                <div><span>Storage DB</span><strong>${escapeHtml(kb.db_name)}</strong></div>
                <div><span>Created</span><strong>${escapeHtml(formatDate(kb.created_at))}</strong></div>
            </div>
        </section>
    `, "knowledge-bases");

    const refresh = async () => renderKnowledgeBaseDetail(kbId);

    document.getElementById("rename-kb-detail").onclick = () => {
        openModal("Rename Knowledge Base", `
            <form id="rename-kb-detail-form" class="stack">
                <label class="field">
                    <span>Name</span>
                    <input id="rename-kb-detail-name" required value="${escapeHtml(kb.name)}">
                </label>
                <button class="button button-primary" type="submit">${icon("edit")}<span>Save</span></button>
            </form>
        `);

        document.getElementById("rename-kb-detail-form").onsubmit = async (event) => {
            event.preventDefault();

            try {
                await api.updateKB(kbId, {
                    name: document.getElementById("rename-kb-detail-name").value
                });
                closeModal();
                showToast("Knowledge base updated");
                await refresh();
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    };

    document.getElementById("kb-upload-input").onchange = async (event) => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }

        try {
            await api.addFileToKB(kbId, file);
            showToast("File uploaded. Background embedding started");
            await refresh();
        } catch (error) {
            showToast(error.message, "error");
        }
    };

    document.querySelectorAll(".remove-kb-file").forEach((button) => {
        button.onclick = async () => {
            if (!window.confirm(`Remove ${button.dataset.file}?`)) {
                return;
            }

            try {
                await api.removeFileFromKB(kbId, button.dataset.file);
                showToast("File removed");
                await refresh();
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    });

    document.getElementById("kb-search-form").onsubmit = async (event) => {
        event.preventDefault();

        const resultsNode = document.getElementById("kb-search-results");
        resultsNode.innerHTML = `<div class="loader-inline"></div>`;

        try {
            const result = await api.testKBSearch(kbId, {
                query: document.getElementById("kb-search-query").value,
                limit: Number(document.getElementById("kb-search-limit").value)
            });

            const results = result.data.results;
            resultsNode.innerHTML = results.length
                ? results.map((item, index) => `
                    <article class="search-card">
                        <div class="search-head">
                            <strong>Chunk ${index + 1}</strong>
                            <span>${item.score !== null ? `Score: ${Number(item.score).toFixed(4)}` : "Score unavailable"}</span>
                        </div>
                        <div class="search-meta">${escapeHtml(item.metadata.file_name || "Unknown file")} • ${escapeHtml(item.metadata.embedding_model || "")}</div>
                        <pre>${escapeHtml(item.content)}</pre>
                    </article>
                `).join("")
                : `<div class="empty-card">No chunks returned for that query.</div>`;
        } catch (error) {
            resultsNode.textContent = error.message;
            resultsNode.classList.remove("muted");
        }
    };

    bindLayoutEvents();
}

async function renderDatabases() {
    setLoading("Loading databases");

    const response = await api.getDBs();
    const dbs = response.data;

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Databases</div>
                <h2>Custom vector stores</h2>
                <p class="muted">Link a database, rename it later, or unlink it with cleanup.</p>
            </div>
            <button class="button button-primary" id="link-db-button">${icon("link")}<span>Link database</span></button>
        </section>
        <section class="card-grid">
            ${dbs.map((db) => `
                <article class="panel card-panel">
                    <div class="panel-head">
                        <div>
                            <h3>${escapeHtml(db.name)}</h3>
                            <p class="muted">${escapeHtml(db.provider)}</p>
                        </div>
                        <span class="tag">Linked</span>
                    </div>
                    <div class="panel-actions">
                        <button class="button button-secondary edit-db" data-id="${db.db_id}" data-name="${escapeHtml(db.name)}">${icon("edit")}<span>Edit</span></button>
                        <button class="button button-danger unlink-db" data-id="${db.db_id}">${icon("trash")}<span>Unlink</span></button>
                    </div>
                </article>
            `).join("") || `<div class="empty-card">No custom databases linked yet.</div>`}
        </section>
    `, "databases");

    const refresh = async () => renderDatabases();

    document.getElementById("link-db-button").onclick = () => {
        openModal("Link Database", `
            <form id="link-db-form" class="stack">
                <label class="field">
                    <span>Name</span>
                    <input id="db-name" required placeholder="Atlas cluster">
                </label>
                <label class="field">
                    <span>Provider</span>
                    <select id="db-provider">
                        <option value="mongo">MongoDB</option>
                        <option value="postgres">PostgreSQL</option>
                    </select>
                </label>
                <label class="field">
                    <span>Connection URI</span>
                    <input id="db-uri" required placeholder="mongodb+srv://... or postgres://...">
                </label>
                <button class="button button-primary" type="submit">${icon("link")}<span>Link database</span></button>
            </form>
        `);

        document.getElementById("link-db-form").onsubmit = async (event) => {
            event.preventDefault();

            try {
                await api.linkDB({
                    name: document.getElementById("db-name").value,
                    db: document.getElementById("db-provider").value,
                    connection_uri: document.getElementById("db-uri").value
                });
                closeModal();
                showToast("Database linked");
                await refresh();
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    };

    document.querySelectorAll(".edit-db").forEach((button) => {
        button.onclick = () => {
            openModal("Edit Database", `
                <form id="edit-db-form" class="stack">
                    <label class="field">
                        <span>Name</span>
                        <input id="edit-db-name" required value="${button.dataset.name}">
                    </label>
                    <button class="button button-primary" type="submit">${icon("edit")}<span>Save name</span></button>
                </form>
            `);

            document.getElementById("edit-db-form").onsubmit = async (event) => {
                event.preventDefault();

                try {
                    await api.updateDB(button.dataset.id, {
                        name: document.getElementById("edit-db-name").value
                    });
                    closeModal();
                    showToast("Database updated");
                    await refresh();
                } catch (error) {
                    showToast(error.message, "error");
                }
            };
        };
    });

    document.querySelectorAll(".unlink-db").forEach((button) => {
        button.onclick = async () => {
            if (!window.confirm("Unlink this DB? Any KBs stored in it will also be cleaned up.")) {
                return;
            }

            try {
                await api.unlinkDB(button.dataset.id);
                showToast("Database unlinked");
                await refresh();
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    });

    bindLayoutEvents();
}

async function renderChat(agentId) {
    setLoading("Loading chat");

    const [agentResponse, oldChatResponse] = await Promise.all([
        api.getAgent(agentId),
        api.loadOldChat(agentId)
    ]);
    const agent = agentResponse.data;
    const oldChat = oldChatResponse.data;

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Chat</div>
                <h2>${escapeHtml(agent.name)}</h2>
                <p class="muted">${escapeHtml(agent.llm_model)} • ${agent.knowledge_base ? "Knowledge base attached" : "No knowledge base"}</p>
            </div>
            <a class="button button-secondary" href="#agents">${icon("back")}<span>Back to agents</span></a>
        </section>
        <section class="chat-panel">
            <div class="chat-stream" id="chat-stream">
                <div class="message assistant-message">Ask anything. If the agent has a KB selected, the backend will inject retrieved context from that KB's embedding model.</div>
            </div>
            <form class="chat-form" id="chat-form">
                <textarea id="chat-input" rows="2" placeholder="Type your message"></textarea>
                <button class="button button-primary" type="submit">${icon("send")}<span>Send</span></button>
            </form>
        </section>
    `, "agents");

    let threadId = oldChat.thread_id || localStorage.getItem(`thread_${agentId}`) || null;
    const chatStream = document.getElementById("chat-stream");

    const addMessage = (text, type) => {
        const node = document.createElement("div");
        node.className = `message ${type === "user" ? "user-message" : "assistant-message"}`;
        node.innerHTML = renderMarkdown(text);
        chatStream.appendChild(node);
        chatStream.scrollTop = chatStream.scrollHeight;
        return node;
    };

    if (threadId) {
        localStorage.setItem(`thread_${agentId}`, threadId);
    }

    if (oldChat.messages.length > 0) {
        chatStream.innerHTML = "";
        oldChat.messages.forEach((message) => {
            addMessage(message.content, message.role);
        });
    }

    document.getElementById("chat-form").onsubmit = async (event) => {
        event.preventDefault();

        const input = document.getElementById("chat-input");
        const query = input.value.trim();
        if (!query) {
            return;
        }

        addMessage(query, "user");
        input.value = "";

        const pending = addMessage("Thinking...", "assistant");

        try {
            const response = await api.runAgent(agentId, query, threadId);
            pending.innerHTML = renderMarkdown(response.data.response);

            if (response.data.thread_id) {
                threadId = response.data.thread_id;
                localStorage.setItem(`thread_${agentId}`, threadId);
            }
        } catch (error) {
            pending.innerHTML = renderMarkdown(`Error: ${error.message}`);
        }
    };

    bindLayoutEvents();
}

async function route() {
    const hash = window.location.hash || "#dashboard";
    state.currentHash = hash;

    const publicRoutes = new Set(["#login", "#register"]);
    if (!state.isAuthenticated && !publicRoutes.has(hash)) {
        navigate("#login");
        return;
    }

    if (state.isAuthenticated && publicRoutes.has(hash)) {
        navigate("#dashboard");
        return;
    }

    try {
        if (hash === "#login") {
            await renderLogin();
            return;
        }

        if (hash === "#register") {
            await renderRegister();
            return;
        }

        if (hash === "#dashboard") {
            await renderDashboard();
            return;
        }

        if (hash === "#agents") {
            await renderAgents();
            return;
        }

        if (hash === "#knowledge-bases") {
            await renderKnowledgeBases();
            return;
        }

        if (hash.startsWith("#knowledge-bases/")) {
            await renderKnowledgeBaseDetail(hash.split("/")[1]);
            return;
        }

        if (hash === "#databases") {
            await renderDatabases();
            return;
        }

        if (hash.startsWith("#chat/")) {
            await renderChat(hash.split("/")[1]);
            return;
        }

        navigate("#dashboard");
    } catch (error) {
        showToast(error.message, "error");
        getApp().innerHTML = `
            <div class="screen-center">
                <h2>Something failed</h2>
                <p class="muted">${escapeHtml(error.message)}</p>
                <button class="button button-secondary" id="retry-route">${icon("retry")}<span>Retry</span></button>
            </div>
        `;

        const retry = document.getElementById("retry-route");
        if (retry) {
            retry.onclick = route;
        }
    }
}


window.addEventListener("hashchange", route);
window.addEventListener("qab-unauthorized", () => {
    api.clearToken();
    localStorage.removeItem("qab_user");
    state.user = null;
    state.isAuthenticated = false;
    navigate("#login");
    showToast("Session expired", "error");
});

route();
