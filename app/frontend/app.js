import { api } from "./api.js?v=20260428e";

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
    currentHash: window.location.hash || "#home",
    health: null
};

const llmOptions = {
    groq: [
        { value: "llama-3.3-70b-versatile", label: "Llama 3.3 70B Versatile" }
    ],
    gemini: [
        { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" }
    ]
};

const SESSION_CHAT_HISTORY_LIMIT = 12;


function getApp() {
    return document.getElementById("app");
}

function brandWordmark(className = "") {
    return `<div class="${className}">qAb</div>`;
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

function getTypingIndicatorMarkup() {
    return `
        <div class="typing-indicator-wrap" aria-label="AI is typing" title="AI is typing">
            <div class="typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
            <div class="typing-timer" data-role="thinking-timer">Thinking 0s</div>
        </div>
    `;
}

function formatExecutionTime(ms) {
    const seconds = ms / 1000;
    if (seconds < 10) {
        return `${seconds.toFixed(1)}s`;
    }

    return `${Math.round(seconds)}s`;
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

function getChatSessionKey(agentId) {
    return `qab_chat_session_${agentId}`;
}

function loadChatSession(agentId) {
    try {
        const raw = sessionStorage.getItem(getChatSessionKey(agentId));
        if (!raw) {
            return [];
        }

        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) {
            return [];
        }

        return parsed.filter((item) =>
            item &&
            (item.role === "user" || item.role === "assistant") &&
            typeof item.content === "string"
        );
    } catch (_error) {
        return [];
    }
}

function saveChatSession(agentId, messages) {
    const trimmedMessages = messages.slice(-SESSION_CHAT_HISTORY_LIMIT);
    sessionStorage.setItem(
        getChatSessionKey(agentId),
        JSON.stringify(trimmedMessages)
    );
    return trimmedMessages;
}

function clearChatSession(agentId) {
    sessionStorage.removeItem(getChatSessionKey(agentId));
}

function clearAllChatSessions() {
    const keysToRemove = [];

    for (let index = 0; index < sessionStorage.length; index += 1) {
        const key = sessionStorage.key(index);
        if (key && key.startsWith("qab_chat_session_")) {
            keysToRemove.push(key);
        }
    }

    keysToRemove.forEach((key) => sessionStorage.removeItem(key));
}

function getHashParts(hash = window.location.hash || "#home") {
    const [path, queryString = ""] = hash.split("?");
    return {
        path: path || "#home",
        params: new URLSearchParams(queryString)
    };
}

function replaceHash(path) {
    const baseUrl = `${window.location.pathname}${window.location.search}`;
    window.history.replaceState(null, "", `${baseUrl}${path}`);
}

function decodeBase64Url(value = "") {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4));
    return atob(`${normalized}${padding}`);
}

function normalizeDbConnectionUri(provider, value = "") {
    const trimmed = value.trim();

    if (provider === "postgres" && trimmed.includes("://")) {
        const [scheme, rest] = trimmed.split("://");
        if (scheme.includes("+")) {
            return `${scheme.split("+")[0]}://${rest}`;
        }
    }

    return trimmed;
}

async function sha256Hex(value) {
    if (!window.crypto?.subtle?.digest) {
        return null;
    }

    const encoded = new TextEncoder().encode(value);
    const digest = await window.crypto.subtle.digest("SHA-256", encoded);
    return Array.from(new Uint8Array(digest))
        .map((byte) => byte.toString(16).padStart(2, "0"))
        .join("");
}

async function buildDbConnectionFingerprint(provider, connectionUri) {
    const normalizedUri = normalizeDbConnectionUri(provider, connectionUri);
    return sha256Hex(`${provider}:${normalizedUri}`);
}

function icon(name, className = "ui-icon") {
    const icons = {
        dashboard: `<path d="M3 13.2h8.2V3H3z"/><path d="M12.8 21H21v-11.2h-8.2z"/><path d="M12.8 10.2H21V3h-8.2z"/><path d="M3 21h8.2v-6.2H3z"/>`,
        bot: `<path d="M9 7V4h6v3"/><rect x="4" y="7" width="16" height="11" rx="3"/><path d="M9 18v2"/><path d="M15 18v2"/><path d="M9 12h.01"/><path d="M15 12h.01"/>`,
        database: `<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/><path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>`,
        table: `<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18"/><path d="M9 5v14"/><path d="M15 5v14"/>`,
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
        loader: `<path d="M21 12a9 9 0 1 1-6.2-8.56"/>`,
        folder: `<path d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>`,
        link: `<path d="M10 13a5 5 0 0 0 7.1 0l2.8-2.8a5 5 0 0 0-7.1-7.1L11 5"/><path d="M14 11a5 5 0 0 0-7.1 0l-2.8 2.8a5 5 0 0 0 7.1 7.1L13 19"/>`,
        wrench: `<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-3 3-3-3 3-3Z"/>`,
        mail: `<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>`,
        settings: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1A1.7 1.7 0 0 0 10 3.2V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1Z"/>`,
        file: `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 15h6"/><path d="M9 11h3"/>`,
        retry: `<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>`,
        more: `<circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/><circle cx="5" cy="12" r="1.5"/>`,
        github: `<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9a3.4 3.4 0 0 0-.9-2.6c3-.3 6.1-1.5 6.1-6.8A5.3 5.3 0 0 0 20 4.8 4.9 4.9 0 0 0 19.9 1S18.7.7 16 2.5a13.4 13.4 0 0 0-7 0C6.3.7 5.1 1 5.1 1A4.9 4.9 0 0 0 5 4.8a5.3 5.3 0 0 0-1.2 3.9c0 5.3 3.1 6.5 6.1 6.8A3.4 3.4 0 0 0 9 18.1V22"/>`,
        linkedin: `<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6Z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/>`,
        portfolio: `<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10"/>`
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

function setButtonLoading(button, isLoading, loadingLabel = "Loading...") {
    if (!button) {
        return;
    }

    if (isLoading) {
        if (!button.dataset.originalHtml) {
            button.dataset.originalHtml = button.innerHTML;
        }
        button.disabled = true;
        button.classList.add("button-loading");
        button.innerHTML = `<span class="button-spinner" aria-hidden="true"></span><span>${escapeHtml(loadingLabel)}</span>`;
        return;
    }

    button.disabled = false;
    button.classList.remove("button-loading");
    if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
        delete button.dataset.originalHtml;
    }
}

function getAuthSocialLinksMarkup() {
    const links = [
        { href: "https://www.linkedin.com/in/rajanrajawat/", label: "LinkedIn", iconName: "linkedin" },
        { href: "https://github.com/RajanRajawat/", label: "GitHub", iconName: "github" },
        { href: "https://www.rajanrajawat.in/", label: "Portfolio", iconName: "portfolio" }
    ];

    return `
        <div class="auth-social-links">
            ${links.map((item) => `
                <a class="auth-social-link" href="${item.href}" target="_blank" rel="noopener noreferrer">
                    ${icon(item.iconName, "ui-icon")}
                    <span>${item.label}</span>
                </a>
            `).join("")}
        </div>
    `;
}

function getPasswordFieldMarkup(inputId, placeholder) {
    return `
        <div class="password-input-wrap">
            <input id="${inputId}" type="password" required placeholder="${escapeHtml(placeholder)}">
            <button
                class="password-toggle"
                type="button"
                data-password-target="${inputId}"
                aria-label="Show password"
                aria-pressed="false"
            >
                <span>Show</span>
            </button>
        </div>
    `;
}

function bindPasswordToggles() {
    document.querySelectorAll("[data-password-target]").forEach((button) => {
        button.onclick = () => {
            const input = document.getElementById(button.dataset.passwordTarget);
            if (!input) {
                return;
            }

            const isVisible = input.type === "text";
            input.type = isVisible ? "password" : "text";
            button.setAttribute("aria-pressed", String(!isVisible));
            button.setAttribute("aria-label", isVisible ? "Show password" : "Hide password");
            button.innerHTML = `<span>${isVisible ? "Show" : "Hide"}</span>`;
            input.focus();
        };
    });
}

function getLayout(content, active = "") {
    return `
        <div class="shell">
            <aside class="sidebar">
                <div class="brand">
                    <img class="sidebar-brand-logo" src="/static/media/qab_rectangle_logo.png" alt="qAb Quick Agent Builder">
                </div>
                <nav class="nav">
                    <a href="#dashboard" class="nav-link ${active === "dashboard" ? "active" : ""}">${icon("dashboard")}<span>Dashboard</span></a>
                    <a href="#agents" class="nav-link ${active === "agents" ? "active" : ""}">${icon("bot")}<span>Agents</span></a>
                    <a href="#knowledge-bases" class="nav-link ${active === "knowledge-bases" ? "active" : ""}">${icon("book")}<span>Knowledge Bases</span></a>
                    <a href="#databases" class="nav-link ${active === "databases" ? "active" : ""}">${icon("database")}<span>Databases</span></a>
                    <a href="#tools" class="nav-link ${active === "tools" ? "active" : ""}">${icon("wrench")}<span>Tools</span></a>
                    <a href="#data-queries" class="nav-link ${active === "data-queries" ? "active" : ""}">${icon("table")}<span>Data Queries</span></a>
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
            clearAllChatSessions();
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

function hydrateDataQuerySources(inspectedSources, savedSources = []) {
    const savedByName = new Map(savedSources.map((source) => [source.name, source]));

    return inspectedSources.map((source) => {
        const saved = savedByName.get(source.name);
        const savedColumns = new Map((saved?.columns || []).map((column) => [column.name, column]));

        return {
            ...source,
            selected: Boolean(saved),
            expanded: Boolean(saved),
            description: saved?.description || "",
            columns: (source.columns || []).map((column) => ({
                ...column,
                description: savedColumns.get(column.name)?.description || ""
            }))
        };
    });
}

function getDataQuerySourcesMarkup(sources) {
    if (!sources.length) {
        return `<div class="empty-card">No tables or collections found for this database.</div>`;
    }

    return sources.map((source, index) => `
        <article class="source-card ${source.selected ? "selected" : ""}">
            <div class="source-card-head">
                <label class="source-select">
                    <input class="dq-source-toggle" type="checkbox" data-index="${index}" ${source.selected ? "checked" : ""}>
                    <div>
                        <strong>${escapeHtml(source.name)}</strong>
                        <span>${escapeHtml(source.source_type)} &bull; ${source.column_count} columns</span>
                    </div>
                </label>
                <button class="button button-secondary dq-config-toggle" type="button" data-index="${index}">
                    ${icon("settings")}
                    <span>Configure</span>
                </button>
            </div>
            ${source.expanded ? `
                <div class="source-config-panel">
                    <label class="field">
                        <span>Description</span>
                        <textarea class="dq-source-description" data-index="${index}" rows="2" placeholder="Describe what this ${escapeHtml(source.source_type)} contains">${escapeHtml(source.description || "")}</textarea>
                    </label>
                    <div class="column-config-list">
                        ${source.columns.map((column) => `
                            <label class="field column-config-row">
                                <span>${escapeHtml(column.name)}${column.data_type ? ` (${escapeHtml(column.data_type)})` : ""}</span>
                                <input class="dq-column-description" data-index="${index}" data-column="${escapeHtml(column.name)}" value="${escapeHtml(column.description || "")}" placeholder="What should the agent know about this field?">
                            </label>
                        `).join("")}
                    </div>
                    ${source.preview_rows?.length ? `
                        <div class="preview-block">
                            <span>Preview rows</span>
                            <pre>${escapeHtml(JSON.stringify(source.preview_rows, null, 2))}</pre>
                        </div>
                    ` : ""}
                </div>
            ` : ""}
        </article>
    `).join("");
}

function getSelectedDataQuerySources(sources) {
    return sources
        .filter((source) => source.selected)
        .map((source) => ({
            name: source.name,
            source_type: source.source_type,
            description: source.description || "",
            columns: source.columns.map((column) => ({
                name: column.name,
                data_type: column.data_type || null,
                description: column.description || ""
            }))
        }));
}

function getLandingFeatureCard(iconName, title, copy) {
    return `
        <article class="landing-feature-card">
            <div class="landing-feature-icon">${icon(iconName)}</div>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(copy)}</p>
        </article>
    `;
}

async function renderHome() {
    getApp().innerHTML = `
        <section class="landing-shell">
            <header class="landing-topbar">
                <a class="landing-brand" href="#home">
                    <img class="landing-brand-logo" src="/static/media/qab_rectangle_logo.png" alt="qAb Quick Agent Builder">
                </a>
                <nav class="landing-nav">
                    <a href="#home">Home</a>
                    <a href="#login">Login</a>
                    <a href="#register" class="button button-primary landing-cta-nav">${icon("register")}<span>Get Started</span></a>
                </nav>
            </header>

            <section class="landing-hero">
                <div class="landing-copy">
                    <div class="landing-chip">A complete workspace to build and run real AI agents</div>
                    <h1>Build custom AI agents, connect your data, and chat with them in one place.</h1>
                    <p>
                        qAb helps you create agents, attach knowledge bases, connect databases, define data queries,
                        and enable practical tools like Gmail and web search from a single workspace.
                    </p>
                    <div class="landing-actions">
                        <a class="button button-primary" href="#register">${icon("register")}<span>Create Account</span></a>
                        <a class="button button-secondary" href="#login">${icon("login")}<span>Login</span></a>
                    </div>
                    <div class="landing-proof">
                        <span>${icon("bot", "ui-icon inline-icon")} Custom Agents</span>
                        <span>${icon("book", "ui-icon inline-icon")} Knowledge Bases</span>
                        <span>${icon("database", "ui-icon inline-icon")} Linked Databases</span>
                    </div>
                </div>

                <div class="landing-visual">
                    <div class="landing-stack-card landing-stack-top">
                        <div class="landing-stack-title">Your qAb Workspace</div>
                        <div class="landing-stack-grid">
                            <div class="landing-stack-pill">${icon("bot", "ui-icon inline-icon")} Agents</div>
                            <div class="landing-stack-pill">${icon("book", "ui-icon inline-icon")} KBs</div>
                            <div class="landing-stack-pill">${icon("table", "ui-icon inline-icon")} Data Queries</div>
                            <div class="landing-stack-pill">${icon("database", "ui-icon inline-icon")} Databases</div>
                            <div class="landing-stack-pill">${icon("wrench", "ui-icon inline-icon")} Tools</div>
                            <div class="landing-stack-pill">${icon("message", "ui-icon inline-icon")} Chat</div>
                        </div>
                    </div>
                    <div class="landing-stack-card landing-stack-mid">
                        <div class="landing-flow-line"></div>
                        <div class="landing-mini-card">
                            <strong>Agent Builder</strong>
                            <span>Configure model, instructions, KB, Data Query, and tools.</span>
                        </div>
                        <div class="landing-mini-card">
                            <strong>Knowledge Base + Data Query</strong>
                            <span>Ground replies with uploaded files and linked databases.</span>
                        </div>
                        <div class="landing-mini-card">
                            <strong>Agent Chat</strong>
                            <span>Run the agent, keep session memory, and iterate quickly.</span>
                        </div>
                    </div>
                    <div class="landing-stack-card landing-stack-bottom">
                        <div class="landing-stack-row">
                            <span class="landing-stack-badge">Groq</span>
                            <span class="landing-stack-badge">Gemini</span>
                            <span class="landing-stack-badge">Gmail</span>
                            <span class="landing-stack-badge">Web Search</span>
                        </div>
                        <p>Everything shown here already exists inside this project.</p>
                    </div>
                </div>
            </section>

            <section class="landing-section">
                <div class="landing-section-head">
                    <div>
                        <div class="eyebrow landing-eyebrow">What You Can Do</div>
                        <h2>A complete toolkit for building AI agents</h2>
                    </div>
                </div>
                <div class="landing-feature-grid">
                    ${getLandingFeatureCard("bot", "Create and manage agents", "Set instructions, provider, model, temperature, tools, and optional knowledge sources.")}
                    ${getLandingFeatureCard("book", "Attach knowledge bases", "Upload text or PDF files and use semantic retrieval to ground agent responses.")}
                    ${getLandingFeatureCard("database", "Connect custom databases", "Link MongoDB or PostgreSQL databases and manage them from the workspace.")}
                    ${getLandingFeatureCard("table", "Define data queries", "Choose approved tables or collections and expose safe read-only context to agents.")}
                    ${getLandingFeatureCard("wrench", "Enable tools", "Connect Gmail and use built-in tools like web search, weather, datetime, and Wikipedia.")}
                    ${getLandingFeatureCard("message", "Chat with your agent", "Run your configured agent with session-based memory and see responses in a focused chat view.")}
                </div>
            </section>

            <section class="landing-section landing-workflow">
                <div class="landing-section-head">
                    <div>
                        <div class="eyebrow landing-eyebrow">Workflow</div>
                        <h2>From setup to usable agent in a few clear steps</h2>
                    </div>
                </div>
                <div class="landing-steps">
                    <article class="landing-step">
                        <span>01</span>
                        <h3>Create your agent</h3>
                        <p>Pick the model, define the role, and add instructions.</p>
                    </article>
                    <article class="landing-step">
                        <span>02</span>
                        <h3>Connect context</h3>
                        <p>Attach a knowledge base, a read-only data query, or both.</p>
                    </article>
                    <article class="landing-step">
                        <span>03</span>
                        <h3>Turn on tools</h3>
                        <p>Use built-in capabilities and external integrations that are configured in qAb.</p>
                    </article>
                    <article class="landing-step">
                        <span>04</span>
                        <h3>Start chatting</h3>
                        <p>Open chat, test responses, and refine the setup based on real usage.</p>
                    </article>
                </div>
            </section>

            <section class="landing-bottom-cta">
                <div>
                    <div class="eyebrow landing-eyebrow">Ready</div>
                    <h2>Start building inside qAb</h2>
                    <p>Create an account to begin building agents, or sign in and continue from your dashboard.</p>
                </div>
                <div class="landing-actions">
                    <a class="button button-primary" href="#register">${icon("register")}<span>Create Account</span></a>
                    <a class="button button-secondary" href="#login">${icon("login")}<span>Login</span></a>
                </div>
            </section>

            <footer class="landing-footer">
                <div class="landing-footer-copy">
                    <strong>project by RajanRajawat</strong>
                    <p>Quick Agent Builder for creating agents, connecting data, and chatting with them in one focused workspace.</p>
                </div>
                <div class="landing-footer-links">
                    <a class="landing-footer-link" href="https://www.linkedin.com/in/rajanrajawat/" target="_blank" rel="noopener noreferrer">
                        ${icon("linkedin")}
                        <span>LinkedIn</span>
                    </a>
                    <a class="landing-footer-link" href="https://github.com/RajanRajawat/" target="_blank" rel="noopener noreferrer">
                        ${icon("github")}
                        <span>GitHub</span>
                    </a>
                    <a class="landing-footer-link" href="https://www.rajanrajawat.in/" target="_blank" rel="noopener noreferrer">
                        ${icon("portfolio")}
                        <span>Portfolio</span>
                    </a>
                </div>
            </footer>
        </section>
    `;
}

async function renderLogin() {
    getApp().innerHTML = `
        <section class="auth-shell">
            <div class="auth-hero">
                <h1>Quick Agent Builder - Build Agents with ease.</h1>
                <p>Sign in to create custom agents, connect databases, and unlock advanced capabilities.</p>
                <div class="eyebrow">project by @RajanRajawat</div>
                ${getAuthSocialLinksMarkup()}
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
                        ${getPasswordFieldMarkup("login-password", "Password")}
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

    bindPasswordToggles();
}

async function renderRegister() {
    getApp().innerHTML = `
        <section class="auth-shell">
            <div class="auth-hero">
                <h1>Register today to build your own custom agents.</h1>
                <p>Your one-stop solution for building and managing custom agents.</p>
                <div class="eyebrow">project by @RajanRajawat</div>
                ${getAuthSocialLinksMarkup()}
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
                        ${getPasswordFieldMarkup("register-password", "Strong password")}
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

    bindPasswordToggles();
}

async function renderDashboard() {
    setLoading("Loading dashboard");

    const [agentsRes, kbRes, dbRes, dataQueryRes] = await Promise.all([
        api.getAgents(),
        api.getKBs(),
        api.getDBs(),
        api.getDataQueries()
    ]);

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Overview</div>
                <h2>Dashboard</h2>
                <p class="muted">Overview and quick entry points.</p>
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
            <article class="stat-card">
                <span class="stat-label">${icon("table")}<span>Data Queries</span></span>
                <strong>${dataQueryRes.data.length}</strong>
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
                                <span>${escapeHtml(kb.embedding_label)} &bull; ${escapeHtml(kb.db_name)}</span>
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
                                <span>${escapeHtml(agent.llm_provider)} &bull; ${escapeHtml(agent.llm_model)}</span>
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

function getToolStatusMarkup(tool) {
    if (tool.connected) {
        return `<span class="status-pill success">Connected</span>`;
    }

    if (tool.config_required) {
        return `<span class="status-pill warning">Needs setup</span>`;
    }

    return `<span class="status-pill online">Ready</span>`;
}

function getToolCardMarkup(tool) {
    const iconName = tool.key === "gmail" ? "mail" : "search";
    const actionLabel = tool.connected ? "Manage" : (tool.config_required ? "Connect" : "Included");

    return `
        <article class="panel card-panel tool-card" data-tool-key="${tool.key}">
            <div class="panel-head">
                <div class="tool-card-headline">
                    <div class="tool-avatar">${icon(iconName, "ui-icon")}</div>
                    <div>
                        <h3>${escapeHtml(tool.label)}</h3>
                        <p class="muted">${escapeHtml(tool.provider)}</p>
                    </div>
                </div>
                ${getToolStatusMarkup(tool)}
            </div>
            <p class="tool-card-copy">${escapeHtml(tool.description)}</p>
            <div class="kb-tags">
                <span class="tag">${escapeHtml(tool.category)}</span>
                <span class="tag">${tool.capabilities.length} capabilities</span>
            </div>
            <div class="panel-actions">
                <button class="button button-secondary open-tool-detail" data-tool-key="${tool.key}">
                    ${icon("settings")}
                    <span>${escapeHtml(actionLabel)}</span>
                </button>
            </div>
        </article>
    `;
}

async function openToolDetailsModal(tool, onChange) {
    const canDisconnect = tool.key === "gmail" && tool.connected;
    const canConnect = tool.key === "gmail" && !tool.connected;

    openModal(tool.label, `
        <div class="stack">
            <div class="tool-detail-top">
                <div>
                    <div class="tool-detail-head">
                        <h3>${escapeHtml(tool.label)}</h3>
                        ${getToolStatusMarkup(tool)}
                    </div>
                    <p class="muted">${escapeHtml(tool.description)}</p>
                </div>
                ${tool.configuration?.account_email ? `
                    <div class="detail-card">
                        <span>Connected account</span>
                        <strong>${escapeHtml(tool.configuration.account_email)}</strong>
                    </div>
                ` : ""}
            </div>
                    <div class="detail-card">
                        <span>Capabilities</span>
                        <div class="capability-list">
                            ${tool.capabilities.map((capability) => `
                        <div class="capability-item">
                            <span class="capability-bullet" aria-hidden="true"></span>
                            <strong>${escapeHtml(capability)}</strong>
                        </div>
                    `).join("")}
                        </div>
                    </div>
            <div class="detail-card">
                <span>Agent availability</span>
                <strong>${tool.connected || !tool.config_required ? "This tool can be added to agents right now." : "Connect this tool first, then it becomes selectable in agent setup."}</strong>
            </div>
            <div class="modal-inline-actions tool-modal-actions">
                <button class="button button-secondary" id="tool-modal-close">${icon("close")}<span>Close</span></button>
                ${canConnect ? `<button class="button button-primary" id="tool-connect-google">${icon("link")}<span>Connect Google</span></button>` : ""}
                ${canDisconnect ? `<button class="button button-danger" id="tool-disconnect-google">${icon("trash")}<span>Disconnect</span></button>` : ""}
            </div>
        </div>
    `);

    document.getElementById("tool-modal-close").onclick = closeModal;

    const connectButton = document.getElementById("tool-connect-google");
    if (connectButton) {
        connectButton.onclick = async () => {
            try {
                setButtonLoading(connectButton, true, "Redirecting...");
                const response = await api.getGoogleConnectUrl();
                window.location.href = response.data.auth_url;
            } catch (error) {
                setButtonLoading(connectButton, false);
                showToast(error.message, "error");
            }
        };
    }

    const disconnectButton = document.getElementById("tool-disconnect-google");
    if (disconnectButton) {
        disconnectButton.onclick = async () => {
            try {
                setButtonLoading(disconnectButton, true, "Disconnecting...");
                await api.disconnectTool(tool.key);
                closeModal();
                showToast("Gmail disconnected");
                await onChange();
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                setButtonLoading(disconnectButton, false);
            }
        };
    }
}

async function renderTools() {
    setLoading("Loading tools");

    const response = await api.getToolsCatalog();
    const tools = response.data;
    const { params } = getHashParts();
    const googleStatus = params.get("google_status");
    const encodedMessage = params.get("message");
    let decodedMessage = null;

    if (encodedMessage) {
        try {
            decodedMessage = decodeBase64Url(encodedMessage);
        } catch (_error) {
            decodedMessage = null;
        }
    }

    if (googleStatus && decodedMessage) {
        showToast(decodedMessage, googleStatus === "connected" ? "success" : "error");
        replaceHash("#tools");
    }

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Tools</div>
                <h2>External tool connections</h2>
                <p class="muted">Configure shared tools here first, then add only ready tools to your agents.</p>
            </div>
        </section>
        <section class="card-grid">
            ${tools.map((tool) => getToolCardMarkup(tool)).join("") || `<div class="empty-card">No tools available yet.</div>`}
        </section>
    `, "tools");

    const refresh = async () => renderTools();
    document.querySelectorAll(".open-tool-detail").forEach((button) => {
        button.onclick = async () => {
            const tool = tools.find((item) => item.key === button.dataset.toolKey);
            if (tool) {
                await openToolDetailsModal(tool, refresh);
            }
        };
    });

    bindLayoutEvents();
}

function getAgentFormMarkup(agent, kbs, dataQueries, toolsCatalog) {
    const isEdit = Boolean(agent);
    const selectedTools = new Set(agent?.tools || []);
    const selectableToolCount = toolsCatalog.filter((tool) => tool.connected || !tool.config_required).length;

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
                <small class="field-note">${selectableToolCount ? "Only ready tools can be attached to agents." : "Set up a tool from the Tools page to make it available here."}</small>
                <div class="tool-grid">
                    ${toolsCatalog.map((tool) => `
                        <label class="tool-option">
                            <div class="tool-option-head">
                                <input
                                    class="agent-tool-checkbox"
                                    type="checkbox"
                                    value="${tool.key}"
                                    ${selectedTools.has(tool.key) ? "checked" : ""}
                                    ${(tool.connected || !tool.config_required) ? "" : "disabled"}
                                >
                                <strong>${escapeHtml(tool.label)}</strong>
                            </div>
                            <small>${escapeHtml(tool.connected || !tool.config_required ? tool.description : `${tool.description} Configure it in Tools first.`)}</small>
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
            <div class="inline-check">
                <input id="agent-dq-enabled" type="checkbox" ${agent?.data_query ? "checked" : ""}>
                <span>Attach a Data Query</span>
            </div>
            <label class="field">
                <span>Data Query</span>
                <select id="agent-dq-id" ${agent?.data_query ? "" : "disabled"}>
                    <option value="">Select Data Query</option>
                    ${dataQueries.map((item) => `
                        <option value="${item.data_query_id}" ${agent?.data_query_id === item.data_query_id ? "selected" : ""}>
                            ${escapeHtml(item.name)}
                        </option>
                    `).join("")}
                </select>
            </label>
            <button class="button button-primary" id="agent-submit-button" type="submit">${icon(isEdit ? "edit" : "plus")}<span>${isEdit ? "Save changes" : "Create agent"}</span></button>
        </form>
    `;
}

async function openAgentModal(agent = null, onDone) {
    const [kbs, dataQueries, toolsCatalog] = await Promise.all([
        api.getKBs().then((response) => response.data),
        api.getDataQueries().then((response) => response.data),
        api.getToolsCatalog().then((response) => response.data)
    ]);
    const title = agent ? "Edit Agent" : "Create Agent";

    openModal(title, getAgentFormMarkup(agent, kbs, dataQueries, toolsCatalog));
    bindProviderModelSelects("agent-provider", "agent-model", agent?.llm_model);

    const kbEnabled = document.getElementById("agent-kb-enabled");
    const kbSelect = document.getElementById("agent-kb-id");
    kbEnabled.onchange = () => {
        kbSelect.disabled = !kbEnabled.checked;
        if (!kbEnabled.checked) {
            kbSelect.value = "";
        }
    };

    const dqEnabled = document.getElementById("agent-dq-enabled");
    const dqSelect = document.getElementById("agent-dq-id");
    dqEnabled.onchange = () => {
        dqSelect.disabled = !dqEnabled.checked;
        if (!dqEnabled.checked) {
            dqSelect.value = "";
        }
    };

    const form = document.getElementById(agent ? "edit-agent-form" : "create-agent-form");
    const submitButton = document.getElementById("agent-submit-button");
    let isSaving = false;

    form.onsubmit = async (event) => {
        event.preventDefault();

        if (isSaving) {
            return;
        }

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
            data_query: dqEnabled.checked,
            data_query_id: dqEnabled.checked ? document.getElementById("agent-dq-id").value || null : null,
            tools: selectedTools
        };

        try {
            isSaving = true;
            setButtonLoading(submitButton, true, agent ? "Saving..." : "Creating...");

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
        } finally {
            isSaving = false;
            setButtonLoading(submitButton, false);
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
                            <summary aria-label="More actions">${icon("more", "ui-icon inline-icon")}</summary>
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
                        <div class="detail-card"><span>Knowledge Base</span><strong>${agent.knowledge_base_id ? escapeHtml(agent.knowledge_base_id) : "None"}</strong></div>
                        <div class="detail-card"><span>Data Query</span><strong>${agent.data_query_id ? escapeHtml(agent.data_query_id) : "None"}</strong></div>
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
                <h2>RAG Knowledge Base</h2>
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
                            <p class="muted">${escapeHtml(kb.embedding_label)} &bull; ${escapeHtml(kb.db_name)}</p>
                        </div>
                        <details class="card-menu">
                            <summary aria-label="More actions">${icon("more", "ui-icon inline-icon")}</summary>
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
                        <div class="search-meta">${escapeHtml(item.metadata.file_name || "Unknown file")} &bull; ${escapeHtml(item.metadata.embedding_model || "")}</div>
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

async function openDataQueryModal(dataQuery = null, onDone) {
    const dbs = (await api.getDBs()).data;

    openModal(dataQuery ? "Edit Data Query" : "Create Data Query", `
        <form id="data-query-form" class="stack">
            <label class="field">
                <span>Name</span>
                <input id="data-query-name" required value="${escapeHtml(dataQuery?.name || "")}" placeholder="Customer DB">
            </label>
            <label class="field">
                <span>Linked database</span>
                <select id="data-query-db" ${dataQuery ? "disabled" : ""}>
                    <option value="">Select a linked database</option>
                    ${dbs.map((db) => `
                        <option value="${db.db_id}" ${dataQuery?.db_id === db.db_id ? "selected" : ""}>
                            ${escapeHtml(db.name)} (${escapeHtml(db.provider)})
                        </option>
                    `).join("")}
                </select>
            </label>
            <div class="modal-inline-actions">
                <button class="button button-secondary" id="load-data-query-sources" type="button">${icon("database")}<span>Load sources</span></button>
                <span class="field-note">The agent will only get read-only access to the selected tables or collections.</span>
            </div>
            <div id="data-query-sources" class="stack"></div>
            <button class="button button-primary" id="data-query-submit" type="submit">${icon(dataQuery ? "edit" : "plus")}<span>${dataQuery ? "Save Data Query" : "Create Data Query"}</span></button>
        </form>
    `);

    const dbSelect = document.getElementById("data-query-db");
    const loadButton = document.getElementById("load-data-query-sources");
    const submitButton = document.getElementById("data-query-submit");
    const sourcesRoot = document.getElementById("data-query-sources");
    let sourceState = [];
    let isSaving = false;

    const bindSourceEvents = () => {
        document.querySelectorAll(".dq-source-toggle").forEach((input) => {
            input.onchange = () => {
                const source = sourceState[Number(input.dataset.index)];
                source.selected = input.checked;
                if (source.selected) {
                    source.expanded = true;
                }
                renderSources();
            };
        });

        document.querySelectorAll(".dq-config-toggle").forEach((button) => {
            button.onclick = () => {
                const source = sourceState[Number(button.dataset.index)];
                source.expanded = !source.expanded;
                renderSources();
            };
        });

        document.querySelectorAll(".dq-source-description").forEach((textarea) => {
            textarea.oninput = () => {
                sourceState[Number(textarea.dataset.index)].description = textarea.value;
            };
        });

        document.querySelectorAll(".dq-column-description").forEach((input) => {
            input.oninput = () => {
                const source = sourceState[Number(input.dataset.index)];
                const column = source.columns.find((item) => item.name === input.dataset.column);
                if (column) {
                    column.description = input.value;
                }
            };
        });
    };

    const renderSources = () => {
        sourcesRoot.innerHTML = getDataQuerySourcesMarkup(sourceState);
        bindSourceEvents();
    };

    const loadSources = async () => {
        const dbId = dataQuery?.db_id || dbSelect.value;
        if (!dbId) {
            showToast("Select a linked database first", "error");
            return;
        }

        sourcesRoot.innerHTML = `<div class="loader-inline"></div>`;

        try {
            const inspection = await api.inspectDBSources(dbId);
            sourceState = hydrateDataQuerySources(inspection.data.sources, dataQuery?.sources || []);
            renderSources();
        } catch (error) {
            sourcesRoot.innerHTML = `<div class="empty-card">${escapeHtml(error.message)}</div>`;
        }
    };

    loadButton.onclick = loadSources;

    if (dataQuery?.db_id) {
        await loadSources();
    }

    document.getElementById("data-query-form").onsubmit = async (event) => {
        event.preventDefault();

        if (isSaving) {
            return;
        }

        const selectedSources = getSelectedDataQuerySources(sourceState);
        if (!selectedSources.length) {
            showToast("Select at least one table or collection", "error");
            return;
        }

        const payload = {
            name: document.getElementById("data-query-name").value,
            db_id: dataQuery?.db_id || dbSelect.value,
            sources: selectedSources
        };

        try {
            isSaving = true;
            setButtonLoading(submitButton, true, dataQuery ? "Saving..." : "Creating...");

            if (dataQuery) {
                await api.updateDataQuery(dataQuery.data_query_id, {
                    name: payload.name,
                    sources: payload.sources
                });
                showToast("Data Query updated");
            } else {
                await api.createDataQuery(payload);
                showToast("Data Query created");
            }

            closeModal();
            await onDone();
        } catch (error) {
            showToast(error.message, "error");
        } finally {
            isSaving = false;
            setButtonLoading(submitButton, false);
        }
    };
}

async function renderDataQueries() {
    setLoading("Loading data queries");

    const response = await api.getDataQueries();
    const dataQueries = response.data;

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Data Queries</div>
                <h2>Read-only database contexts</h2>
                <p class="muted">Select tables or collections from a linked database and describe their schema for the agent.</p>
            </div>
            <button class="button button-primary" id="create-data-query-button">${icon("plus")}<span>Create Data Query</span></button>
        </section>
        <section class="card-grid">
            ${dataQueries.map((item) => `
                <article class="panel card-panel">
                    <div class="panel-head">
                        <div>
                            <h3>${escapeHtml(item.name)}</h3>
                            <p class="muted">${escapeHtml(item.db_name)} &bull; ${escapeHtml(item.provider)}</p>
                        </div>
                        <details class="card-menu">
                            <summary aria-label="More actions">${icon("more", "ui-icon inline-icon")}</summary>
                            <div class="card-menu-list">
                                <button class="card-menu-action edit-data-query" data-id="${item.data_query_id}">${icon("edit", "ui-icon inline-icon")}<span>Edit</span></button>
                                <button class="card-menu-action delete-data-query delete" data-id="${item.data_query_id}">${icon("trash", "ui-icon inline-icon")}<span>Delete</span></button>
                            </div>
                        </details>
                    </div>
                    <div class="kb-tags">
                        <span class="tag">${item.sources.length} sources</span>
                        <span class="tag">${escapeHtml(item.provider)}</span>
                    </div>
                    <div class="panel-actions">
                        <button class="button button-secondary open-data-query" data-id="${item.data_query_id}">${icon("folder")}<span>Open</span></button>
                    </div>
                </article>
            `).join("") || `<div class="empty-card">No data queries created yet.</div>`}
        </section>
    `, "data-queries");

    const refresh = async () => renderDataQueries();

    document.getElementById("create-data-query-button").onclick = async () => {
        await openDataQueryModal(null, refresh);
    };

    document.querySelectorAll(".open-data-query").forEach((button) => {
        button.onclick = () => navigate(`#data-queries/${button.dataset.id}`);
    });

    document.querySelectorAll(".edit-data-query").forEach((button) => {
        button.onclick = async () => {
            try {
                const responseDetail = await api.getDataQuery(button.dataset.id);
                await openDataQueryModal(responseDetail.data, refresh);
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    });

    document.querySelectorAll(".delete-data-query").forEach((button) => {
        button.onclick = async () => {
            if (!window.confirm("Delete this Data Query? Agents using it will be detached from it.")) {
                return;
            }

            try {
                await api.deleteDataQuery(button.dataset.id);
                showToast("Data Query deleted");
                await refresh();
            } catch (error) {
                showToast(error.message, "error");
            }
        };
    });

    bindLayoutEvents();
}

async function renderDataQueryDetail(dataQueryId) {
    setLoading("Loading data query");

    const response = await api.getDataQuery(dataQueryId);
    const dataQuery = response.data;

    getApp().innerHTML = getLayout(`
        <section class="page-head">
            <div>
                <div class="eyebrow">Data Query Detail</div>
                <h2>${escapeHtml(dataQuery.name)}</h2>
                <p class="muted">${escapeHtml(dataQuery.db_name)} &bull; ${escapeHtml(dataQuery.provider)}</p>
            </div>
            <div class="hero-actions">
                <a class="button button-secondary" href="#data-queries">${icon("back")}<span>Back</span></a>
                <button class="button button-secondary" id="edit-data-query-detail">${icon("edit")}<span>Edit</span></button>
            </div>
        </section>
        <section class="stack">
            ${dataQuery.sources.map((source) => `
                <article class="panel">
                    <div class="panel-head">
                        <div>
                            <h3>${escapeHtml(source.name)}</h3>
                            <p class="muted">${escapeHtml(source.source_type)}</p>
                        </div>
                        <span class="tag">${source.columns.length} columns</span>
                    </div>
                    <div class="detail-card">
                        <span>Description</span>
                        <strong>${escapeHtml(source.description || "No description added.")}</strong>
                    </div>
                    <div class="column-summary-grid">
                        ${source.columns.map((column) => `
                            <div class="detail-card">
                                <span>${escapeHtml(column.name)}${column.data_type ? ` (${escapeHtml(column.data_type)})` : ""}</span>
                                <strong>${escapeHtml(column.description || "No description added.")}</strong>
                            </div>
                        `).join("")}
                    </div>
                </article>
            `).join("") || `<div class="empty-card">No configured sources.</div>`}
        </section>
    `, "data-queries");

    document.getElementById("edit-data-query-detail").onclick = async () => {
        await openDataQueryModal(dataQuery, async () => renderDataQueryDetail(dataQueryId));
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
                <h2>Custom DB / Vector Stores</h2>
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
                        <span class="status-pill success">Linked</span>
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
                <small class="field-note">Each database connection can only be linked once.</small>
                <button class="button button-primary" type="submit">${icon("link")}<span>Link database</span></button>
            </form>
        `);

        document.getElementById("link-db-form").onsubmit = async (event) => {
            event.preventDefault();
            const submitButton = event.currentTarget.querySelector('button[type="submit"]');
            const provider = document.getElementById("db-provider").value;
            const connectionUri = document.getElementById("db-uri").value;

            try {
                const fingerprint = await buildDbConnectionFingerprint(provider, connectionUri);
                const alreadyLinked = fingerprint
                    ? dbs.some((item) =>
                        item.provider === provider && item.connection_fingerprint === fingerprint
                    )
                    : false;

                if (alreadyLinked) {
                    showToast("This database connection is already linked.", "error");
                    return;
                }

                setButtonLoading(submitButton, true, "Verifying connection...");
                await api.linkDB({
                    name: document.getElementById("db-name").value,
                    db: provider,
                    connection_uri: connectionUri
                });
                closeModal();
                showToast("Database linked");
                await refresh();
            } catch (error) {
                showToast(error.message, "error");
            } finally {
                setButtonLoading(submitButton, false);
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
        button.onclick = () => {
            openModal("Unlink Database", `
                <div class="stack">
                    <p class="modal-copy">Unlink this DB? Any KBs stored in it will also be cleaned up.</p>
                    <div class="modal-footer">
                        <button class="button button-secondary" type="button" id="cancel-unlink-db">Cancel</button>
                        <button class="button button-danger" type="button" id="confirm-unlink-db">${icon("trash")}<span>Unlink</span></button>
                    </div>
                </div>
            `);

            document.getElementById("cancel-unlink-db").onclick = () => {
                closeModal();
            };

            document.getElementById("confirm-unlink-db").onclick = async (event) => {
                const confirmButton = event.currentTarget;

                try {
                    setButtonLoading(confirmButton, true, "Unlinking...");
                    await api.unlinkDB(button.dataset.id);
                    closeModal();
                    showToast("Database unlinked");
                    await refresh();
                } catch (error) {
                    showToast(error.message, "error");
                    setButtonLoading(confirmButton, false);
                }
            };
        };
    });

    bindLayoutEvents();
}

async function renderChat(agentId) {
    setLoading("Loading chat");

    const agentResponse = await api.getAgent(agentId);
    const agent = agentResponse.data;
    let sessionMessages = loadChatSession(agentId);

    getApp().innerHTML = getLayout(`
        <div class="chat-view">
            <section class="page-head chat-page-head">
                <div>
                    <div class="eyebrow">Chat</div>
                    <h2>${escapeHtml(agent.name)}</h2>
                    <p class="muted">${escapeHtml(agent.llm_model)} &bull; ${agent.knowledge_base ? "Knowledge base attached" : "No knowledge base"}</p>
                </div>
                <div class="hero-actions">
                    <button class="button button-secondary" type="button" id="clear-chat-button">${icon("trash")}<span>Clear chat</span></button>
                    <a class="button button-secondary" href="#agents">${icon("back")}<span>Back to agents</span></a>
                </div>
            </section>
            <section class="chat-panel">
                <div class="chat-stream" id="chat-stream"></div>
                <form class="chat-form" id="chat-form">
                    <div class="chat-input-shell">
                        <textarea id="chat-input" rows="1" placeholder="Type your message"></textarea>
                        <button class="chat-send-button" type="submit" id="chat-send-button" aria-label="Send message" title="Send">
                            ${icon("send")}
                        </button>
                    </div>
                </form>
            </section>
        </div>
    `, "agents");

    document.querySelector(".main-panel")?.classList.add("main-panel-chat");

    const chatStream = document.getElementById("chat-stream");

    const addMessage = (text, type) => {
        const node = document.createElement("div");
        node.className = `message ${type === "user" ? "user-message" : "assistant-message"}`;
        node.innerHTML = renderMarkdown(text);
        chatStream.appendChild(node);
        chatStream.scrollTop = chatStream.scrollHeight;
        return node;
    };

    const addTypingMessage = () => {
        const node = document.createElement("div");
        node.className = "message assistant-message assistant-message-typing";
        node.innerHTML = getTypingIndicatorMarkup();
        chatStream.appendChild(node);
        chatStream.scrollTop = chatStream.scrollHeight;
        return node;
    };

    if (sessionMessages.length > 0) {
        chatStream.innerHTML = "";
        sessionMessages.forEach((message) => {
            addMessage(message.content, message.role);
        });
    }

    const chatForm = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const sendButton = document.getElementById("chat-send-button");
    const clearChatButton = document.getElementById("clear-chat-button");
    let isSending = false;

    const setSendingState = (sending) => {
        isSending = sending;
        sendButton.disabled = sending;
        sendButton.classList.toggle("is-loading", sending);
        sendButton.setAttribute("aria-label", sending ? "Waiting for response" : "Send message");
        sendButton.title = sending ? "Waiting for response" : "Send";
        sendButton.innerHTML = sending
            ? icon("loader", "ui-icon send-loader-icon")
            : icon("send");
    };

    const resizeChatInput = () => {
        input.style.height = "auto";
        input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
    };

    resizeChatInput();
    input.focus();

    input.addEventListener("input", resizeChatInput);
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            if (!isSending) {
                chatForm.requestSubmit();
            }
        }
    });

    clearChatButton.onclick = () => {
        clearChatSession(agentId);
        sessionMessages = [];
        chatStream.innerHTML = "";
        input.focus();
        showToast("Chat cleared");
    };

    chatForm.onsubmit = async (event) => {
        event.preventDefault();

        if (isSending) {
            return;
        }

        const query = input.value.trim();
        if (!query) {
            return;
        }

        setSendingState(true);
        addMessage(query, "user");
        sessionMessages.push({
            role: "user",
            content: query
        });
        sessionMessages = saveChatSession(agentId, sessionMessages);

        input.value = "";
        resizeChatInput();

        const pending = addTypingMessage();
        const startedAt = Date.now();
        const timerNode = pending.querySelector('[data-role="thinking-timer"]');
        const timer = window.setInterval(() => {
            const elapsedMs = Date.now() - startedAt;
            if (timerNode) {
                timerNode.textContent = `Thinking ${formatExecutionTime(elapsedMs)}`;
            }
        }, 100);

        try {
            const history = sessionMessages.slice(0, -1).slice(-SESSION_CHAT_HISTORY_LIMIT);
            const response = await api.runAgent(agentId, query, history);
            const elapsedMs = Date.now() - startedAt;
            pending.innerHTML = `
                ${renderMarkdown(response.data.response)}
                <div class="message-meta">Executed in ${formatExecutionTime(elapsedMs)}</div>
            `;
            pending.classList.remove("assistant-message-typing");
            sessionMessages.push({
                role: "assistant",
                content: response.data.response
            });
            sessionMessages = saveChatSession(agentId, sessionMessages);
        } catch (error) {
            const errorMessage = error?.message === "Request timed out"
                ? "Request timed out"
                : "Aw, Snap! Something went wrong, please try again later.";
            pending.innerHTML = renderMarkdown(errorMessage);
            pending.classList.remove("assistant-message-typing");
            sessionMessages = sessionMessages.slice(0, -1);
            sessionMessages = saveChatSession(agentId, sessionMessages);
        } finally {
            window.clearInterval(timer);
            setSendingState(false);
            input.focus();
        }
    };

    bindLayoutEvents();
}

async function route() {
    const hash = window.location.hash || "#home";
    const { path } = getHashParts(hash);
    state.currentHash = path;

    const publicRoutes = new Set(["#home", "#login", "#register"]);
    if (!state.isAuthenticated && !publicRoutes.has(path)) {
        navigate("#home");
        return;
    }

    if (state.isAuthenticated && publicRoutes.has(path)) {
        navigate("#dashboard");
        return;
    }

    try {
        if (path === "#home") {
            await renderHome();
            return;
        }

        if (path === "#login") {
            await renderLogin();
            return;
        }

        if (path === "#register") {
            await renderRegister();
            return;
        }

        if (path === "#dashboard") {
            await renderDashboard();
            return;
        }

        if (path === "#agents") {
            await renderAgents();
            return;
        }

        if (path === "#knowledge-bases") {
            await renderKnowledgeBases();
            return;
        }

        if (path.startsWith("#knowledge-bases/")) {
            await renderKnowledgeBaseDetail(path.split("/")[1]);
            return;
        }

        if (path === "#databases") {
            await renderDatabases();
            return;
        }

        if (path === "#tools") {
            await renderTools();
            return;
        }

        if (path === "#data-queries") {
            await renderDataQueries();
            return;
        }

        if (path.startsWith("#data-queries/")) {
            await renderDataQueryDetail(path.split("/")[1]);
            return;
        }

        if (path.startsWith("#chat/")) {
            await renderChat(path.split("/")[1]);
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
    clearAllChatSessions();
    state.user = null;
    state.isAuthenticated = false;
    navigate("#login");
    showToast("Session expired", "error");
});

route();
