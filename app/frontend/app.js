const state = {
    token: localStorage.getItem("qab_token") || "",
    user: JSON.parse(localStorage.getItem("qab_user") || "null"),
    dbs: [],
    kbs: [],
    agents: [],
};

const modelMap = {
    groq: ["llama-3.1-8b-instant"],
    gemini: ["gemini-2.5-flash"],
};

const sessionStatus = document.getElementById("sessionStatus");
const logoutBtn = document.getElementById("logoutBtn");
const registerForm = document.getElementById("registerForm");
const loginForm = document.getElementById("loginForm");
const dbForm = document.getElementById("dbForm");
const kbForm = document.getElementById("kbForm");
const agentForm = document.getElementById("agentForm");
const dbList = document.getElementById("dbList");
const kbList = document.getElementById("kbList");
const agentList = document.getElementById("agentList");
const kbDbSelect = document.getElementById("kbDbSelect");
const agentKbSelect = document.getElementById("agentKbSelect");
const knowledgeBaseToggle = document.getElementById("knowledgeBaseToggle");
const providerSelect = document.getElementById("providerSelect");
const modelSelect = document.getElementById("modelSelect");
const toast = document.getElementById("toast");


function showToast(message, isError = false) {
    toast.textContent = message;
    toast.classList.remove("hidden");
    toast.style.background = isError ? "rgba(163, 49, 49, 0.95)" : "rgba(31, 27, 24, 0.92)";
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.add("hidden"), 3200);
}


function updateSessionView() {
    if (state.token && state.user) {
        sessionStatus.textContent = `Logged in as ${state.user.email}`;
        return;
    }
    sessionStatus.textContent = "Not logged in";
}


function saveSession(data) {
    state.token = data.jwt_tokens.access_token;
    state.user = data.user_info;
    localStorage.setItem("qab_token", state.token);
    localStorage.setItem("qab_user", JSON.stringify(state.user));
    updateSessionView();
}


function clearSession() {
    state.token = "";
    state.user = null;
    localStorage.removeItem("qab_token");
    localStorage.removeItem("qab_user");
    state.dbs = [];
    state.kbs = [];
    state.agents = [];
    updateSessionView();
    renderDbList();
    renderKbList();
    renderAgentList();
    fillDbSelects();
}


function fillModelOptions() {
    const models = modelMap[providerSelect.value] || [];
    modelSelect.innerHTML = models.map((model) => `<option value="${model}">${model}</option>`).join("");
}


function fillDbSelects() {
    const dbOptions = [
        { db_id: "default", name: "Default DB" },
        ...state.dbs,
    ];

    kbDbSelect.innerHTML = dbOptions
        .map((db) => `<option value="${db.db_id}">${db.name}</option>`)
        .join("");

    agentKbSelect.innerHTML = [
        '<option value="">Select knowledge base</option>',
        ...state.kbs.map((kb) => `<option value="${kb.kb_id}">${kb.name} (${kb.db_name})</option>`)
    ].join("");
}


function parseError(data) {
    if (!data) return "Request failed";
    if (data.detail?.message) return data.detail.message;
    if (data.detail?.detail?.message) return data.detail.detail.message;
    if (data.message) return data.message;
    return "Request failed";
}


async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});

    if (state.token) {
        headers.set("Authorization", `Bearer ${state.token}`);
    }

    const response = await fetch(path, {
        ...options,
        headers,
    });

    let data = null;
    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        throw new Error(parseError(data));
    }

    return data;
}


async function loadDbs() {
    if (!state.token) return;
    const response = await api("/custom-db/mydb");
    state.dbs = response.data || [];
    renderDbList();
    fillDbSelects();
}


async function loadKbs() {
    if (!state.token) return;
    const response = await api("/knowledge-base/all");
    state.kbs = response.data || [];
    renderKbList();
    fillDbSelects();
}


async function loadAgents() {
    if (!state.token) return;
    const response = await api("/agent/all");
    state.agents = response.data || [];
    renderAgentList();
}


async function loadAllProtectedData() {
    await Promise.all([loadDbs(), loadKbs(), loadAgents()]);
}


function renderDbList() {
    if (!state.dbs.length) {
        dbList.innerHTML = '<div class="item-card">No custom DB linked yet.</div>';
        return;
    }

    dbList.innerHTML = state.dbs.map((db) => `
        <div class="item-card">
            <h3>${db.name}</h3>
            <div class="meta">${db.provider}</div>
            <div class="inline-actions">
                <button class="danger-btn" onclick="deleteDb('${db.db_id}')">Delete</button>
            </div>
        </div>
    `).join("");
}


function renderKbList() {
    if (!state.kbs.length) {
        kbList.innerHTML = '<div class="item-card"><div class="meta">No knowledge base created yet.</div></div>';
        return;
    }

    kbList.innerHTML = state.kbs.map((kb) => `
        <div class="item-card">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <h3>${kb.name}</h3>
                    <div class="meta">Store: ${kb.db_name}</div>
                    <div class="meta">Entries: ${kb.files.length}</div>
                </div>
                <button class="danger-btn" onclick="deleteKb('${kb.kb_id}')">Delete</button>
            </div>
            
            <div class="files">
                ${kb.files.length ? kb.files.map((file) => `
                    <span class="file-tag">
                        ${file}
                        <button style="background:transparent; padding:0; border:none; color:inherit; cursor:pointer;" onclick="removeKbFile('${kb.kb_id}', '${encodeURIComponent(file)}')">×</button>
                    </span>
                `).join("") : '<div class="meta" style="margin: 0.5rem 0;">Empty Knowledge Base</div>'}
            </div>
            
            <form class="stack" onsubmit="uploadKbFile(event, '${kb.kb_id}')" style="margin-top: 1rem; border-top: 1px solid var(--glass-border); padding-top: 1rem;">
                <div class="meta">Add Source (.txt, .pdf)</div>
                <div style="display: flex; gap: 0.5rem;">
                    <input type="file" name="file" accept=".txt,.pdf" required style="flex:1; font-size: 0.8rem;">
                    <button type="submit" style="padding: 0.5rem 1rem;">Upload</button>
                </div>
            </form>
        </div>
    `).join("");
}


function renderAgentList() {
    if (!state.agents.length) {
        agentList.innerHTML = '<div class="item-card"><div class="meta">No agent deployed yet.</div></div>';
        return;
    }

    agentList.innerHTML = state.agents.map((agent) => `
        <div class="item-card glass">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <h3>${agent.name}</h3>
                    <div class="meta">${agent.llm_provider.toUpperCase()} | ${agent.llm_model}</div>
                    <div class="meta">RAG: ${agent.knowledge_base ? "Enabled" : "Disabled"}</div>
                </div>
                <button class="danger-btn" onclick="deleteAgent('${agent._id}')">Terminate</button>
            </div>
            
            <div style="margin: 1rem 0;">
                <textarea id="query-${agent._id}" placeholder="Type your query for ${agent.name}..." rows="2" style="width:100%; margin-bottom: 0.5rem;"></textarea>
                <button onclick="runAgent('${agent._id}')" id="btn-${agent._id}" style="width: 100%;">Execute Runner</button>
            </div>
            
            <div id="output-${agent._id}" class="agent-output hidden"></div>
        </div>
    `).join("");
}

async function deleteDb(dbId) {
    try {
        const response = await api(`/custom-db/delete/${dbId}`, { method: "DELETE" });
        showToast(response.message);
        await loadAllProtectedData();
    } catch (error) {
        showToast(error.message, true);
    }
}


async function deleteKb(kbId) {
    try {
        const response = await api(`/knowledge-base/delete/${kbId}`, { method: "DELETE" });
        showToast(response.message);
        await loadAllProtectedData();
    } catch (error) {
        showToast(error.message, true);
    }
}


async function removeKbFile(kbId, fileName) {
    try {
        const response = await api(`/knowledge-base/remove-file/${kbId}?file_name=${fileName}`, { method: "DELETE" });
        showToast(response.message);
        await loadKbs();
    } catch (error) {
        showToast(error.message, true);
    }
}


async function uploadKbFile(event, kbId) {
    event.preventDefault();
    const form = event.target;
    const fileInput = form.querySelector('input[type="file"]');

    if (!fileInput.files.length) {
        showToast("Please choose a file.", true);
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";

    try {
        const response = await api(`/knowledge-base/add-file/${kbId}`, {
            method: "POST",
            body: formData,
        });
        showToast(response.message);
        form.reset();
        await loadKbs();
    } catch (error) {
        showToast(error.message, true);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}


async function deleteAgent(agentId) {
    try {
        const response = await api(`/agent/delete/${agentId}`, { method: "DELETE" });
        showToast(response.message);
        await loadAgents();
    } catch (error) {
        showToast(error.message, true);
    }
}


async function runAgent(agentId) {
    const input = document.getElementById(`query-${agentId}`);
    const output = document.getElementById(`output-${agentId}`);
    const btn = document.getElementById(`btn-${agentId}`);

    if (!input.value.trim()) {
        showToast("Please enter a query.", true);
        return;
    }

    const originalBtnText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Processing...";
    output.classList.remove("hidden");
    output.style.opacity = "0.6";
    output.textContent = "Thinking...";

    try {
        const response = await api(`/chat/run/${agentId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: input.value }),
        });
        output.style.opacity = "1";
        output.textContent = response.data.response || "No response";
        showToast(response.message);
    } catch (error) {
        output.style.opacity = "1";
        output.textContent = "Error: " + error.message;
        showToast(error.message, true);
    } finally {
        btn.disabled = false;
        btn.textContent = originalBtnText;
    }
}


registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(registerForm);
    const payload = Object.fromEntries(formData.entries());

    try {
        const response = await api("/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        showToast(response.message);
        registerForm.reset();
    } catch (error) {
        showToast(error.message, true);
    }
});


loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    const payload = Object.fromEntries(formData.entries());

    try {
        const response = await api("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        saveSession(response.data);
        showToast(response.message);
        loginForm.reset();
        await loadAllProtectedData();
    } catch (error) {
        showToast(error.message, true);
    }
});


dbForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(dbForm);
    const payload = Object.fromEntries(formData.entries());

    try {
        const response = await api("/custom-db/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        showToast(response.message);
        dbForm.reset();
        await loadDbs();
    } catch (error) {
        showToast(error.message, true);
    }
});


kbForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(kbForm);
    const payload = {
        name: formData.get("name"),
        db_id: formData.get("db_id") || "default",
    };

    try {
        const response = await api("/knowledge-base/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        showToast(response.message);
        kbForm.reset();
        fillDbSelects();
        await loadKbs();
    } catch (error) {
        showToast(error.message, true);
    }
});


agentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(agentForm);
    const tools = Array.from(document.querySelectorAll('input[name="tools"]:checked')).map((input) => input.value);
    const useKb = knowledgeBaseToggle.checked;

    const payload = {
        name: formData.get("name"),
        description: formData.get("description"),
        role: formData.get("role"),
        instruction: formData.get("instruction"),
        llm_provider: formData.get("llm_provider"),
        llm_model: formData.get("llm_model"),
        temperature: Number(formData.get("temperature")),
        knowledge_base: useKb,
        knowledge_base_id: useKb ? formData.get("knowledge_base_id") || null : null,
        tools,
    };

    try {
        const response = await api("/agent/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        showToast(response.message);
        agentForm.reset();
        knowledgeBaseToggle.checked = false;
        agentKbSelect.disabled = true;
        fillModelOptions();
        await loadAgents();
    } catch (error) {
        showToast(error.message, true);
    }
});


knowledgeBaseToggle.addEventListener("change", () => {
    agentKbSelect.disabled = !knowledgeBaseToggle.checked;
});


providerSelect.addEventListener("change", fillModelOptions);


document.getElementById("refreshDbBtn").addEventListener("click", loadDbs);
document.getElementById("refreshKbBtn").addEventListener("click", loadKbs);
document.getElementById("refreshAgentBtn").addEventListener("click", loadAgents);
logoutBtn.addEventListener("click", () => {
    clearSession();
    showToast("Logged out.");
});


window.deleteDb = deleteDb;
window.deleteKb = deleteKb;
window.removeKbFile = removeKbFile;
window.uploadKbFile = uploadKbFile;
window.deleteAgent = deleteAgent;
window.runAgent = runAgent;


fillModelOptions();
updateSessionView();
fillDbSelects();

if (state.token) {
    loadAllProtectedData().catch((error) => {
        clearSession();
        showToast(error.message, true);
    });
}
