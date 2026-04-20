import { api } from './api.js';

/**
 * QAB Frontend Application Logic
 * Vanila JS SPA with Hash Routing
 */

// --- Global State ---
const state = {
    user: JSON.parse(localStorage.getItem('qab_user')) || null,
    isAuthenticated: !!localStorage.getItem('qab_token'),
    currentPath: window.location.hash || '#dashboard',
    agents: [],
    kbs: [],
    dbs: []
};

// --- Utilities ---
const showToast = (message, type = 'success') => {
    const root = document.getElementById('toast-root');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? 'check-circle' : 'alert-circle';
    toast.innerHTML = `<i data-lucide="${icon}"></i> <span>${message}</span>`;
    root.appendChild(toast);
    window.refreshIcons();
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
};

const navigate = (hash) => {
    window.location.hash = hash;
};

// --- UI Components ---
const Sidebar = () => `
    <div class="sidebar">
        <div class="sidebar-logo">
            <i data-lucide="zap"></i> QAB
        </div>
        <nav class="sidebar-nav">
            <a href="#dashboard" class="nav-link ${state.currentPath === '#dashboard' ? 'active' : ''}">
                <i data-lucide="layout-dashboard"></i> Dashboard
            </a>
            <a href="#agents" class="nav-link ${state.currentPath.startsWith('#agents') ? 'active' : ''}">
                <i data-lucide="users"></i> Agents
            </a>
            <a href="#knowledge-bases" class="nav-link ${state.currentPath.startsWith('#knowledge-base') ? 'active' : ''}">
                <i data-lucide="database"></i> Knowledge Base
            </a>
            <a href="#databases" class="nav-link ${state.currentPath === '#databases' ? 'active' : ''}">
                <i data-lucide="server"></i> Databases
            </a>
        </nav>
        <div class="sidebar-footer">
            <button id="logout-btn" class="nav-link" style="width: 100%; text-align: left; background: none; border: none; cursor: pointer;">
                <i data-lucide="log-out"></i> Logout
            </button>
        </div>
    </div>
`;

const Layout = (content) => `
    <div class="main-layout">
        ${Sidebar()}
        <main class="content">
            ${content}
        </main>
    </div>
`;

const Modal = (title, content, id) => {
    const root = document.getElementById('modal-root');
    root.innerHTML = `
        <div class="modal-overlay" id="${id}-overlay">
            <div class="modal">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="btn-link" onclick="document.getElementById('${id}-overlay').remove()">
                        <i data-lucide="x"></i>
                    </button>
                </div>
                <div class="modal-body">${content}</div>
            </div>
        </div>
    `;
    window.refreshIcons();
};

// --- Page Renderers ---

const renderLogin = () => {
    document.getElementById('app').innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h1 class="auth-title">Welcome Back</h1>
                <p class="auth-subtitle">Login to manage your AI agents</p>
                <form id="login-form">
                    <div class="form-group">
                        <label>Email Address</label>
                        <input type="email" id="login-email" required placeholder="name@company.com">
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <input type="password" id="login-password" required placeholder="••••••••">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: 100%">Sign In</button>
                </form>
                <p style="text-align: center; margin-top: 1.5rem; font-size: 0.875rem; color: var(--text-muted)">
                    Don't have an account? <a href="#register" class="btn-link">Register here</a>
                </p>
            </div>
        </div>
    `;
    document.getElementById('login-form').onsubmit = async (e) => {
        e.preventDefault();
        try {
            await api.login(
                document.getElementById('login-email').value,
                document.getElementById('login-password').value
            );
            state.isAuthenticated = true;
            state.user = JSON.parse(localStorage.getItem('qab_user'));
            showToast('Login successful!');
            navigate('#dashboard');
        } catch (err) {
            showToast(err.message, 'error');
        }
    };
};

const renderRegister = () => {
    document.getElementById('app').innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h1 class="auth-title">Create Account</h1>
                <p class="auth-subtitle">Get started with QAB today</p>
                <form id="register-form">
                    <div class="form-group">
                        <label>Full Name</label>
                        <input type="text" id="reg-name" required placeholder="John Doe">
                    </div>
                    <div class="form-group">
                        <label>Email Address</label>
                        <input type="email" id="reg-email" required placeholder="john@example.com">
                    </div>
                    <div class="form-group">
                        <label>Mobile Number</label>
                        <input type="text" id="reg-mobile" required placeholder="10-digit number">
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <input type="password" id="reg-password" required placeholder="At least 8 chars">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: 100%">Create Account</button>
                </form>
                <p style="text-align: center; margin-top: 1.5rem; font-size: 0.875rem; color: var(--text-muted)">
                    Already have an account? <a href="#login" class="btn-link">Login here</a>
                </p>
            </div>
        </div>
    `;
    document.getElementById('register-form').onsubmit = async (e) => {
        e.preventDefault();
        try {
            await api.register(
                document.getElementById('reg-name').value,
                document.getElementById('reg-email').value,
                document.getElementById('reg-mobile').value,
                document.getElementById('reg-password').value
            );
            showToast('Registration successful! Please login.');
            navigate('#login');
        } catch (err) {
            showToast(err.message, 'error');
        }
    };
};

const renderDashboard = async () => {
    const app = document.getElementById('app');
    app.innerHTML = Layout(`
        <div class="content-header">
            <div>
                <h1 class="heading">Dashboard</h1>
                <p class="text-muted">Welcome back, ${state.user?.name || 'User'}</p>
            </div>
            <div style="display: flex; gap: 1rem;">
                <button class="btn btn-outline" onclick="window.location.hash = '#knowledge-bases'">
                    <i data-lucide="plus"></i> New KB
                </button>
                <button class="btn btn-primary" onclick="window.location.hash = '#agents'">
                    <i data-lucide="plus"></i> Create Agent
                </button>
            </div>
        </div>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon"><i data-lucide="users"></i></div>
                <div>
                    <div class="stat-value" id="stat-agents">-</div>
                    <div class="stat-label">Total Agents</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon"><i data-lucide="database"></i></div>
                <div>
                    <div class="stat-value" id="stat-kbs">-</div>
                    <div class="stat-label">Knowledge Bases</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon"><i data-lucide="server"></i></div>
                <div>
                    <div class="stat-value" id="stat-dbs">-</div>
                    <div class="stat-label">Linked DBs</div>
                </div>
            </div>
        </div>
        <div class="card" style="padding: 2rem; border-style: dashed; border-width: 2px; text-align: center;">
            <h3 style="margin-bottom: 0.5rem;">Getting Started</h3>
            <p class="text-muted">Connect a database, upload your documents, and launch your first AI agent in minutes.</p>
        </div>
    `);

    // Fetch stats
    try {
        const [agents, kbs, dbs] = await Promise.all([
            api.getAgents(),
            api.getKBs(),
            api.getDBs()
        ]);
        document.getElementById('stat-agents').innerText = agents.data.length;
        document.getElementById('stat-kbs').innerText = kbs.data.length;
        document.getElementById('stat-dbs').innerText = dbs.data.length;
    } catch (e) {
        console.error('Stats fetch failed', e);
    }
};

const renderAgents = async () => {
    const app = document.getElementById('app');
    app.innerHTML = Layout(`
        <div class="content-header">
            <div>
                <h1 class="heading">Agents</h1>
                <p class="text-muted">Manage your AI workforce</p>
            </div>
            <button class="btn btn-primary" id="btn-create-agent">
                <i data-lucide="plus"></i> Create Agent
            </button>
        </div>
        <div class="card-grid" id="agents-list">
            <div class="text-muted">Loading agents...</div>
        </div>
    `);

    const refreshAgents = async () => {
        const list = document.getElementById('agents-list');
        try {
            const res = await api.getAgents();
            const agents = res.data;
            if (agents.length === 0) {
                list.innerHTML = '<div class="text-muted">No agents yet. Create one to get started!</div>';
                return;
            }
            list.innerHTML = agents.map(a => `
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                        <h3 class="card-title">${a.name}</h3>
                        <span class="badge badge-blue">${a.llm_provider}</span>
                    </div>
                    <p class="card-desc">${a.description}</p>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 1rem;">
                        <strong>Model:</strong> ${a.llm_model} <br>
                        <strong>KB:</strong> ${a.knowledge_base ? 'Linked' : 'None'}
                    </div>
                    <div class="card-footer">
                        <a href="#chat/${a._id}" class="btn btn-outline" style="padding: 0.5rem 1rem; font-size: 0.875rem;">
                            <i data-lucide="message-square"></i> Chat
                        </a>
                        <div style="display: flex; gap: 0.25rem;">
                            <button class="btn btn-link edit-agent" data-id="${a._id}" title="Edit Agent"><i data-lucide="edit-3" style="color: var(--primary)"></i></button>
                            <button class="btn btn-link delete-agent" data-id="${a._id}" title="Delete Agent"><i data-lucide="trash-2" style="color: var(--error)"></i></button>
                        </div>
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.delete-agent').forEach(btn => {
                btn.onclick = async () => {
                    if (confirm('Are you sure you want to delete this agent?')) {
                        try {
                            await api.deleteAgent(btn.dataset.id);
                            showToast('Agent deleted');
                            refreshAgents();
                        } catch (e) { showToast(e.message, 'error'); }
                    }
                };
            });

            document.querySelectorAll('.edit-agent').forEach(btn => {
                btn.onclick = async () => {
                    const id = btn.dataset.id;
                    try {
                        const res = await api.request(`/agent/${id}`);
                        const agent = res.data;
                        let kbs = [];
                        try { kbs = (await api.getKBs()).data; } catch (e) { }

                        const formHtml = `
                            <form id="edit-agent-form">
                                <div class="form-group">
                                    <label>Agent Name</label>
                                    <input id="e-name" required value="${agent.name}">
                                </div>
                                <div class="form-group">
                                    <label>Description</label>
                                    <input id="e-desc" required value="${agent.description}">
                                </div>
                                <div class="form-group">
                                    <label>Role</label>
                                    <input id="e-role" required value="${agent.role}">
                                </div>
                                <div class="form-group">
                                    <label>System Instructions</label>
                                    <textarea id="e-instr" required rows="3">${agent.instruction}</textarea>
                                </div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                                    <div class="form-group">
                                        <label>Provider</label>
                                        <select id="e-prov">
                                            <option value="groq" ${agent.llm_provider === 'groq' ? 'selected' : ''}>Groq</option>
                                            <option value="gemini" ${agent.llm_provider === 'gemini' ? 'selected' : ''}>Gemini</option>
                                        </select>
                                    </div>
                                    <div class="form-group">
                                        <label>Model</label>
                                        <select id="e-model">
                                            <option value="llama-3.1-8b-instant" ${agent.llm_model === 'llama-3.1-8b-instant' ? 'selected' : ''}>Llama 3.1 8B (Groq)</option>
                                            <option value="gemini-2.5-flash" ${agent.llm_model === 'gemini-2.5-flash' ? 'selected' : ''}>Gemini 2.5 Flash</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="form-group">
                                    <label>Temperature (${agent.temperature})</label>
                                    <input type="number" step="0.1" min="0" max="1" id="e-temp" value="${agent.temperature}">
                                </div>
                                <div class="form-group">
                                    <label>Knowledge Base</label>
                                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                                        <input type="checkbox" id="e-kb-link" style="width: auto;" ${agent.knowledge_base ? 'checked' : ''}>
                                        <select id="e-kb-id" ${!agent.knowledge_base ? 'disabled' : ''}>
                                            <option value="">Select KB...</option>
                                            ${kbs.map(k => `<option value="${k.kb_id}" ${agent.knowledge_base_id === k.kb_id ? 'selected' : ''}>${k.name}</option>`).join('')}
                                        </select>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 1rem;">Save Changes</button>
                            </form>
                        `;
                        Modal('Edit Agent', formHtml, 'edit-agent');

                        const kbLink = document.getElementById('e-kb-link');
                        const kbSelect = document.getElementById('e-kb-id');
                        kbLink.onchange = () => kbSelect.disabled = !kbLink.checked;

                        document.getElementById('edit-agent-form').onsubmit = async (e) => {
                            e.preventDefault();
                            try {
                                await api.updateAgent(id, {
                                    name: document.getElementById('e-name').value,
                                    description: document.getElementById('e-desc').value,
                                    role: document.getElementById('e-role').value,
                                    instruction: document.getElementById('e-instr').value,
                                    llm_provider: document.getElementById('e-prov').value,
                                    llm_model: document.getElementById('e-model').value,
                                    temperature: parseFloat(document.getElementById('e-temp').value),
                                    knowledge_base: kbLink.checked,
                                    knowledge_base_id: kbLink.checked ? kbSelect.value : null
                                });
                                showToast('Agent updated!');
                                document.getElementById('edit-agent-overlay').remove();
                                refreshAgents();
                            } catch (err) { showToast(err.message, 'error'); }
                        };
                    } catch (e) { showToast(e.message, 'error'); }
                };
            });
            window.refreshIcons();
        } catch (e) { list.innerHTML = '<div class="text-error">Failed to load agents</div>'; }
    };

    refreshAgents();

    document.getElementById('btn-create-agent').onclick = async () => {
        let kbs = [];
        try { kbs = (await api.getKBs()).data; } catch (e) { }

        const formHtml = `
            <form id="create-agent-form">
                <div class="form-group">
                    <label>Agent Name</label>
                    <input id="a-name" required placeholder="e.g. Sales Assistant">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <input id="a-desc" required placeholder="What does this agent do?">
                </div>
                <div class="form-group">
                    <label>Role</label>
                    <input id="a-role" required placeholder="e.g. Expert Salesperson">
                </div>
                <div class="form-group">
                    <label>System Instructions</label>
                    <textarea id="a-instr" required rows="3" placeholder="Be polite and helpful..."></textarea>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="form-group">
                        <label>Provider</label>
                        <select id="a-prov">
                            <option value="groq">Groq</option>
                            <option value="gemini">Gemini</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Model</label>
                        <select id="a-model">
                            <option value="llama-3.1-8b-instant">Llama 3.1 8B (Groq)</option>
                            <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Temperature (0 to 1)</label>
                    <input type="number" step="0.1" min="0" max="1" id="a-temp" value="0.7">
                </div>
                <div class="form-group">
                    <label>Knowledge Base</label>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <input type="checkbox" id="a-kb-link" style="width: auto;">
                        <select id="a-kb-id" disabled>
                            <option value="">Select KB...</option>
                            ${kbs.map(k => `<option value="${k.kb_id}">${k.name}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 1rem;">Create Agent</button>
            </form>
        `;
        Modal('Create New Agent', formHtml, 'agent');

        const kbLink = document.getElementById('a-kb-link');
        const kbSelect = document.getElementById('a-kb-id');
        kbLink.onchange = () => kbSelect.disabled = !kbLink.checked;

        document.getElementById('create-agent-form').onsubmit = async (e) => {
            e.preventDefault();
            try {
                await api.createAgent({
                    name: document.getElementById('a-name').value,
                    description: document.getElementById('a-desc').value,
                    role: document.getElementById('a-role').value,
                    instruction: document.getElementById('a-instr').value,
                    llm_provider: document.getElementById('a-prov').value,
                    llm_model: document.getElementById('a-model').value,
                    temperature: parseFloat(document.getElementById('a-temp').value),
                    knowledge_base: kbLink.checked,
                    knowledge_base_id: kbLink.checked ? kbSelect.value : null,
                    tools: []
                });
                showToast('Agent created!');
                document.getElementById('agent-overlay').remove();
                refreshAgents();
            } catch (err) { showToast(err.message, 'error'); }
        };
    };
};

const renderKnowledgeBases = async () => {
    const app = document.getElementById('app');
    app.innerHTML = Layout(`
        <div class="content-header">
            <div>
                <h1 class="heading">Knowledge Base</h1>
                <p class="text-muted">Manage your documents and data</p>
            </div>
            <button class="btn btn-primary" id="btn-create-kb">
                <i data-lucide="plus"></i> New KB
            </button>
        </div>
        <div class="card-grid" id="kb-list">
            <div class="text-muted">Loading KBs...</div>
        </div>
    `);

    const refreshKBs = async () => {
        const list = document.getElementById('kb-list');
        try {
            const res = await api.getKBs();
            const kbs = res.data;
            if (kbs.length === 0) {
                list.innerHTML = '<div class="text-muted">No knowledge bases yet.</div>';
                return;
            }
            list.innerHTML = kbs.map(k => `
                <div class="card">
                    <h3 class="card-title">${k.name}</h3>
                    <div style="font-size: 0.875rem; color: var(--text-muted); margin-bottom:1rem;">
                        <strong>DB:</strong> ${k.db_name} <br>
                        <strong>Files:</strong> ${k.files.length}
                    </div>
                    <div id="file-list-${k.kb_id}" style="max-height: 100px; overflow-y: auto; margin-bottom: 1rem; border-top: 1px solid var(--border); padding-top: 0.5rem;">
                        ${k.files.map(f => `
                            <div style="font-size: 0.75rem; display: flex; justify-content: space-between; align-items: center; padding: 0.25rem 0;">
                                ${f} <button class="btn-link rm-file" data-kb="${k.kb_id}" data-file="${f}"><i data-lucide="x" style="width: 12px; color: var(--error)"></i></button>
                            </div>
                        `).join('')}
                    </div>
                    <div class="card-footer">
                        <div style="display: flex; gap: 0.5rem;">
                             <input type="file" id="file-input-${k.kb_id}" style="display: none;" accept=".pdf,.txt">
                             <button class="btn btn-outline upload-trigger" data-id="${k.kb_id}" style="padding: 0.4rem 0.8rem; font-size: 0.75rem;">
                                <i data-lucide="upload"></i> Upload
                             </button>
                        </div>
                        <button class="btn btn-link delete-kb" data-id="${k.kb_id}"><i data-lucide="trash-2" style="color: var(--error)"></i></button>
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.upload-trigger').forEach(btn => {
                const id = btn.dataset.id;
                const input = document.getElementById(`file-input-${id}`);
                btn.onclick = () => input.click();
                input.onchange = async () => {
                    if (input.files.length > 0) {
                        try {
                            showToast('Uploading file...');
                            await api.addFileToKB(id, input.files[0]);
                            showToast('File uploaded successfully');
                            refreshKBs();
                        } catch (e) { showToast(e.message, 'error'); }
                    }
                };
            });

            document.querySelectorAll('.rm-file').forEach(btn => {
                btn.onclick = async () => {
                    try {
                        await api.removeFileFromKB(btn.dataset.kb, btn.dataset.file);
                        showToast('File removed');
                        refreshKBs();
                    } catch (e) { showToast(e.message, 'error'); }
                };
            });

            document.querySelectorAll('.delete-kb').forEach(btn => {
                btn.onclick = async () => {
                    if (confirm('Delete this Knowledge Base and all its embeddings?')) {
                        try {
                            await api.deleteKB(btn.dataset.id);
                            showToast('Knowledge Base deleted');
                            refreshKBs();
                        } catch (e) { showToast(e.message, 'error'); }
                    }
                };
            });
            window.refreshIcons();
        } catch (e) { list.innerHTML = '<div class="text-error">Failed to load Knowledge Bases</div>'; }
    };

    refreshKBs();

    document.getElementById('btn-create-kb').onclick = async () => {
        let dbs = [];
        try { dbs = (await api.getDBs()).data; } catch (e) { }
        const formHtml = `
            <form id="create-kb-form">
                <div class="form-group">
                    <label>KB Name</label>
                    <input id="kb-name" required placeholder="e.g. Company Docs">
                </div>
                <div class="form-group">
                    <label>Database Storage</label>
                    <select id="kb-db">
                        <option value="default">Default MongoDB</option>
                        ${dbs.map(d => `<option value="${d.db_id}">${d.name} (${d.provider})</option>`).join('')}
                    </select>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 1rem;">Create KB</button>
            </form>
        `;
        Modal('Create New Knowledge Base', formHtml, 'kb');
        document.getElementById('create-kb-form').onsubmit = async (e) => {
            e.preventDefault();
            try {
                await api.createKB({
                    name: document.getElementById('kb-name').value,
                    db_id: document.getElementById('kb-db').value
                });
                showToast('KB created!');
                document.getElementById('kb-overlay').remove();
                refreshKBs();
            } catch (err) { showToast(err.message, 'error'); }
        };
    };
};

const renderDatabases = async () => {
    const app = document.getElementById('app');
    app.innerHTML = Layout(`
        <div class="content-header">
            <div>
                <h1 class="heading">Databases</h1>
                <p class="text-muted">Link custom vector stores</p>
            </div>
            <button class="btn btn-primary" id="btn-link-db">
                <i data-lucide="link"></i> Link Database
            </button>
        </div>
        <div class="card-grid" id="db-list">
            <div class="text-muted">Loading databases...</div>
        </div>
    `);

    const refreshDBs = async () => {
        const list = document.getElementById('db-list');
        try {
            const res = await api.getDBs();
            const dbs = res.data;
            if (dbs.length === 0) {
                list.innerHTML = '<div class="text-muted">No custom databases linked. Using default store.</div>';
                return;
            }
            list.innerHTML = dbs.map(d => `
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                        <h3 class="card-title">${d.name}</h3>
                        <span class="badge badge-blue">${d.provider}</span>
                    </div>
                    <div class="card-footer">
                        <button class="btn btn-outline delete-db" data-id="${d.db_id}" style="width: 100%; border-color: var(--error); color: var(--error)">
                            <i data-lucide="trash-2"></i> Unlink Database
                        </button>
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.delete-db').forEach(btn => {
                btn.onclick = async () => {
                    if (confirm('Unlinking will also delete all Knowledge Bases stored in this DB. Proceed?')) {
                        try {
                            await api.unlinkDB(btn.dataset.id);
                            showToast('Database unlinked');
                            refreshDBs();
                        } catch (e) { showToast(e.message, 'error'); }
                    }
                };
            });
            window.refreshIcons();
        } catch (e) { list.innerHTML = '<div class="text-error">Failed to load databases</div>'; }
    };

    refreshDBs();

    document.getElementById('btn-link-db').onclick = () => {
        const formHtml = `
            <form id="link-db-form">
                <div class="form-group">
                    <label>DB Name</label>
                    <input id="db-name" required placeholder="e.g. My Atlas Cluster">
                </div>
                <div class="form-group">
                    <label>Provider</label>
                    <select id="db-provider">
                        <option value="mongo">MongoDB</option>
                        <option value="postgres">PostgreSQL (PGVector)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Connection URI</label>
                    <input id="db-uri" required placeholder="mongodb+srv://... or postgres://...">
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 1rem;">Link Database</button>
            </form>
        `;
        Modal('Link Custom Database', formHtml, 'db');
        document.getElementById('link-db-form').onsubmit = async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            const originalText = btn.innerHTML;

            try {
                btn.disabled = true;
                btn.innerHTML = `<span class="loader-circle" style="width:16px; height:16px; border-width:2px;"></span> Verifying & Linking...`;

                await api.linkDB({
                    name: document.getElementById('db-name').value,
                    db: document.getElementById('db-provider').value,
                    connection_uri: document.getElementById('db-uri').value
                });
                showToast('Database linked!');
                document.getElementById('db-overlay').remove();
                refreshDBs();
            } catch (err) {
                showToast(err.message, 'error');
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        };
    };
};

const renderChat = async (agentId) => {
    const app = document.getElementById('app');
    let agent = null;
    try {
        agent = (await api.request(`/agent/${agentId}`)).data;
    } catch (e) {
        navigate('#agents');
        return;
    }

    app.innerHTML = Layout(`
        <div class="chat-container">
            <div class="chat-header">
                <div>
                    <h3 style="margin: 0">${agent.name}</h3>
                    <small class="text-muted">${agent.llm_model} • ${agent.knowledge_base ? 'RAG Enabled' : 'Standard'}</small>
                </div>
                <a href="#agents" class="btn-link">Close Chat</a>
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="message message-agent">Hello! I am ${agent.name}. How can I assist you today?</div>
            </div>
            <form class="chat-input-area" id="chat-form">
                <input type="text" id="chat-input" placeholder="Type your message..." autocomplete="off">
                <button type="submit" class="btn btn-primary" id="chat-submit">
                    <i data-lucide="send"></i>
                </button>
            </form>
        </div>
    `);

    const messagesDiv = document.getElementById('chat-messages');
    const input = document.getElementById('chat-input');
    let threadId = localStorage.getItem(`thread_${agentId}`) || null;

    const appendMessage = (content, role) => {
        const msg = document.createElement('div');
        msg.className = `message message-${role}`;
        msg.innerText = content;
        messagesDiv.appendChild(msg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    };

    document.getElementById('chat-form').onsubmit = async (e) => {
        e.preventDefault();
        const query = input.value.trim();
        if (!query) return;

        appendMessage(query, 'user');
        input.value = '';
        input.disabled = true;
        document.getElementById('chat-submit').disabled = true;

        const loadingMsg = document.createElement('div');
        loadingMsg.className = 'message message-agent';
        loadingMsg.innerHTML = '<span class="loader-circle" style="width:20px;height:20px;border-width:2px;display:inline-block"></span>';
        messagesDiv.appendChild(loadingMsg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        try {
            const res = await api.runAgent(agentId, query, threadId);
            loadingMsg.remove();
            appendMessage(res.data.response, 'agent');
            if (res.data.thread_id) {
                threadId = res.data.thread_id;
                localStorage.setItem(`thread_${agentId}`, threadId);
            }
        } catch (err) {
            loadingMsg.remove();
            showToast(err.message, 'error');
            appendMessage('Error: ' + err.message, 'agent');
        } finally {
            input.disabled = false;
            document.getElementById('chat-submit').disabled = false;
            input.focus();
        }
    };
    window.refreshIcons();
};

// --- Router ---
const routes = {
    '#login': renderLogin,
    '#register': renderRegister,
    '#dashboard': renderDashboard,
    '#agents': renderAgents,
    '#knowledge-bases': renderKnowledgeBases,
    '#databases': renderDatabases,
    '#chat': renderChat
};

const router = async () => {
    const hash = window.location.hash || '#dashboard';
    state.currentPath = hash;

    // Protected Routes
    const publicRoutes = ['#login', '#register'];
    if (!state.isAuthenticated && !publicRoutes.includes(state.currentPath)) {
        navigate('#login');
        return;
    }
    if (state.isAuthenticated && publicRoutes.includes(state.currentPath)) {
        navigate('#dashboard');
        return;
    }

    // Dynamic Route for Chat
    if (hash.startsWith('#chat/')) {
        const id = hash.split('/')[1];
        await renderChat(id);
    } else if (routes[hash]) {
        await routes[hash]();
    } else {
        navigate('#dashboard');
    }

    // Logout handling
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            api.clearToken();
            localStorage.removeItem('qab_user');
            state.isAuthenticated = false;
            state.user = null;
            showToast('Logged out');
            navigate('#login');
        };
    }
    window.refreshIcons();
};

// --- Initialization ---
window.addEventListener('hashchange', router);
window.addEventListener('qab-unauthorized', () => {
    api.clearToken();
    state.isAuthenticated = false;
    navigate('#login');
    showToast('Session expired. Please login again.', 'error');
});

// Start the app
router();
