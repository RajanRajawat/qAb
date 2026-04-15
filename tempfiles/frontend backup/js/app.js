// UI Utilities Alert
function showAlert(message, type = 'success') {
    const container = document.getElementById('alert-container');
    const alertEl = document.createElement('div');
    alertEl.className = `alert ${type}`;
    
    let icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    alertEl.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    
    container.appendChild(alertEl);
    setTimeout(() => {
        alertEl.style.animation = 'slideOut 0.3s ease-in forwards';
        setTimeout(() => alertEl.remove(), 300);
    }, 3000);
}

// Wait function
const sleep = ms => new Promise(r => setTimeout(r, ms));

class App {
    constructor() {
        this.agents = [];
        this.init();
    }

    init() {
        this.bindNavigation();
        this.bindAuth();
        this.bindAgents();
        this.bindChat();
        this.bindCustomDb();
        this.bindKnowledgeBase();
        this.checkAuthStatus();
        this.setupLogout();
    }

    // --- Navigation ---
    bindNavigation() {
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
                
                const targetId = btn.getAttribute('data-target');
                btn.classList.add('active');
                document.getElementById(targetId).classList.add('active');
                
                if(targetId === 'agents-section' && this.isAuthenticated()) {
                    this.loadAgents();
                }
            });
        });
    }

    // --- State ---
    isAuthenticated() {
        return !!localStorage.getItem('access_token');
    }

    checkAuthStatus() {
        const isAuth = this.isAuthenticated();
        const statusEl = document.getElementById('auth-status');
        const statusText = document.getElementById('auth-status-text');
        const tokenDisplay = document.getElementById('token-display-box');
        const logoutBtn = document.getElementById('logout-btn');

        if (isAuth) {
            statusEl.classList.remove('offline');
            statusEl.classList.add('online');
            statusText.textContent = 'Online';
            
            tokenDisplay.style.display = 'block';
            document.getElementById('access-token-display').textContent = localStorage.getItem('access_token');
            document.getElementById('refresh-token-display').textContent = localStorage.getItem('refresh_token');
            logoutBtn.style.display = 'block';
            
            // Auto load agents if agents tab is active
            if(document.getElementById('agents-section').classList.contains('active')){
                this.loadAgents();
            }
        } else {
            statusEl.classList.add('offline');
            statusEl.classList.remove('online');
            statusText.textContent = 'Not Logged In';
            tokenDisplay.style.display = 'none';
            logoutBtn.style.display = 'none';
        }
    }

    setupLogout() {
        document.getElementById('logout-btn').addEventListener('click', () => {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            this.checkAuthStatus();
            showAlert('Logged out successfully', 'success');
            
            // Redirect to auth view
            document.querySelector('[data-target="auth-section"]').click();
        });
    }

    setLoading(btn, isLoading) {
        const text = btn.querySelector('.btn-text');
        const loader = btn.querySelector('.loader');
        
        if (isLoading) {
            btn.disabled = true;
            if(text) text.style.display = 'none';
            if(loader) loader.style.display = 'block';
        } else {
            btn.disabled = false;
            if(text) text.style.display = 'block';
            if(loader) loader.style.display = 'none';
        }
    }

    // --- Auth View ---
    bindAuth() {
        const loginForm = document.getElementById('login-form');
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = loginForm.querySelector('button[type="submit"]');
            this.setLoading(btn, true);
            
            try {
                const credentials = {
                    email: document.getElementById('login-email').value,
                    password: document.getElementById('login-password').value
                };
                
                const res = await api.auth.login(credentials);
                if (res.data && res.data.jwt_tokens) {
                    localStorage.setItem('access_token', res.data.jwt_tokens.access_token);
                    localStorage.setItem('refresh_token', res.data.jwt_tokens.refresh_token);
                    this.checkAuthStatus();
                    showAlert('Logged in successfully!');
                    loginForm.reset();
                    // Go to agents
                    document.querySelector('[data-target="agents-section"]').click();
                } else {
                    showAlert(res.message, 'error');
                }
            } catch (error) {
                showAlert(error.message, 'error');
            } finally {
                this.setLoading(btn, false);
            }
        });

        const registerForm = document.getElementById('register-form');
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = registerForm.querySelector('button[type="submit"]');
            this.setLoading(btn, true);
            
            try {
                const data = {
                    name: document.getElementById('reg-name').value,
                    email: document.getElementById('reg-email').value,
                    mobile: document.getElementById('reg-mobile').value,
                    password: document.getElementById('reg-password').value
                };
                
                await api.auth.register(data);
                showAlert('Registration successful! You can now log in.');
                registerForm.reset();
            } catch (error) {
                showAlert(error.message, 'error');
            } finally {
                this.setLoading(btn, false);
            }
        });
    }

    // --- Agents View ---
    bindAgents() {
        const formContainer = document.getElementById('agent-form-container');
        const showBtn = document.getElementById('show-create-agent-btn');
        const hideBtn = document.getElementById('close-agent-form');
        const cancelBtn = document.getElementById('cancel-agent-btn');
        
        const openForm = (isNew = true) => {
            if(!this.isAuthenticated()){
                showAlert("Please login first.", "error"); return;
            }
            formContainer.style.display = 'block';
            if (isNew) {
                document.getElementById('agent-form').reset();
                document.getElementById('agent-id').value = '';
                document.getElementById('agent-form-title').textContent = 'Create New Agent';
            }
            formContainer.scrollIntoView({ behavior: 'smooth' });
        };
        
        const closeForm = () => {
            formContainer.style.display = 'none';
        };

        showBtn.addEventListener('click', () => openForm(true));
        hideBtn.addEventListener('click', closeForm);
        cancelBtn.addEventListener('click', closeForm);

        const form = document.getElementById('agent-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            this.setLoading(btn, true);
            
            try {
                // Gather tool values
                const toolCheckboxes = document.querySelectorAll('input[name="agent-tools"]:checked');
                const tools = Array.from(toolCheckboxes).map(cb => cb.value);

                const data = {
                    name: document.getElementById('agent-name').value,
                    role: document.getElementById('agent-role').value,
                    description: document.getElementById('agent-description').value,
                    instruction: document.getElementById('agent-instruction').value,
                    llm_provider: document.getElementById('agent-provider').value,
                    llm_model: document.getElementById('agent-model').value,
                    temperature: parseFloat(document.getElementById('agent-temperature').value),
                    knowledge_base: document.getElementById('agent-knowledge').checked,
                    tools: tools
                };
                
                const id = document.getElementById('agent-id').value;
                if (id) {
                    await api.agents.update(id, data);
                    showAlert('Agent updated successfully!');
                } else {
                    await api.agents.create(data);
                    showAlert('Agent created successfully!');
                }
                
                closeForm();
                this.loadAgents();
            } catch (error) {
                showAlert(error.message, 'error');
            } finally {
                this.setLoading(btn, false);
            }
        });
    }

    async loadAgents() {
        if (!this.isAuthenticated()) return;
        
        const listContainer = document.getElementById('agents-list');
        listContainer.innerHTML = '<div class="agent-empty-state"><div class="loader m-auto"></div><p>Loading...</p></div>';
        
        try {
            const res = await api.agents.getAll();
            this.agents = res.data || [];
            this.renderAgents();
            this.populateChatSelect();
        } catch (error) {
            showAlert('Failed to load agents: ' + error.message, 'error');
            listContainer.innerHTML = '<div class="agent-empty-state"><p>Error loading agents.</p></div>';
        }
    }

    renderAgents() {
        const listContainer = document.getElementById('agents-list');
        
        if (this.agents.length === 0) {
            listContainer.innerHTML = `
                <div class="agent-empty-state">
                    <i class="fa-solid fa-robot"></i>
                    <p>No agents found. Create one to get started.</p>
                </div>
            `;
            return;
        }

        listContainer.innerHTML = '';
        
        this.agents.forEach(agent => {
            const card = document.createElement('div');
            card.className = 'agent-card';
            card.innerHTML = `
                <div class="agent-card-header">
                    <h3 class="m-0">${agent.name}</h3>
                    <span class="agent-badge">${agent.llm_provider}</span>
                </div>
                <div class="text-xs text-muted">ID: ${agent._id}</div>
                <div class="fw-bold text-accent text-xs">${agent.role}</div>
                <p class="text-sm m-0">${agent.description}</p>
                <div class="mt-1 d-flex gap-1">
                    <button class="btn btn-outline flex-1 edit-agent-btn" data-id="${agent._id}">
                        <i class="fa-solid fa-pen"></i> Edit
                    </button>
                    <button class="btn btn-danger btn-icon delete-agent-btn" data-id="${agent._id}">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            `;
            listContainer.appendChild(card);
        });

        // Bind events
        document.querySelectorAll('.edit-agent-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.editAgent(e.currentTarget.getAttribute('data-id')));
        });
        
        document.querySelectorAll('.delete-agent-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.deleteAgent(e.currentTarget.getAttribute('data-id')));
        });
    }

    editAgent(id) {
        const agent = this.agents.find(a => a._id === id);
        if (!agent) return;

        document.getElementById('agent-form').reset();
        
        document.getElementById('agent-id').value = agent._id;
        document.getElementById('agent-form-title').textContent = 'Update Agent';
        
        document.getElementById('agent-name').value = agent.name;
        document.getElementById('agent-role').value = agent.role;
        document.getElementById('agent-description').value = agent.description;
        document.getElementById('agent-instruction').value = agent.instruction;
        document.getElementById('agent-provider').value = agent.llm_provider;
        
        // Timeout to allow model options to reflect provider if we had dynamic loading (for now it's static)
        document.getElementById('agent-model').value = agent.llm_model;
        document.getElementById('agent-temperature').value = agent.temperature;
        document.getElementById('agent-knowledge').checked = agent.knowledge_base;
        
        // Reset and set tools checkboxes
        document.querySelectorAll('input[name="agent-tools"]').forEach(cb => cb.checked = false);
        if (agent.tools) {
            agent.tools.forEach(tool => {
                const cb = document.querySelector(`input[name="agent-tools"][value="${tool}"]`);
                if(cb) cb.checked = true;
            });
        }
        
        document.getElementById('agent-form-container').style.display = 'block';
        document.getElementById('agent-form-container').scrollIntoView({ behavior: 'smooth' });
    }

    async deleteAgent(id) {
        if (!confirm('Are you sure you want to delete this agent?')) return;
        
        try {
            await api.agents.delete(id);
            showAlert('Agent deleted successfully');
            this.loadAgents();
        } catch (error) {
            showAlert('Deletion failed: ' + error.message, 'error');
        }
    }

    // --- Custom DB View ---
    bindCustomDb() {
        if (!document.getElementById('custom-db-form')) return;
        const form = document.getElementById('custom-db-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if(!this.isAuthenticated()){
                showAlert("Please login first.", "error"); return;
            }
            const btn = form.querySelector('button[type="submit"]');
            this.setLoading(btn, true);
            
            try {
                const data = {
                    connection_uri: document.getElementById('db-uri').value,
                    db_name: document.getElementById('db-name').value,
                    collection_name: document.getElementById('db-collection').value
                };
                
                await api.customDb.linkMongo(data);
                showAlert('MongoDB linked successfully!');
                form.reset();
            } catch (error) {
                showAlert(error.message, 'error');
            } finally {
                this.setLoading(btn, false);
            }
        });
    }

    // --- Knowledge Base View ---
    bindKnowledgeBase() {
        const form = document.getElementById('kb-upload-form');
        if (!form) return;
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if(!this.isAuthenticated()){
                showAlert("Please login first.", "error"); return;
            }
            const fileInput = document.getElementById('kb-file');
            if(!fileInput.files.length) {
                showAlert("Please select a file.", "error"); return;
            }
            
            const btn = form.querySelector('button[type="submit"]');
            this.setLoading(btn, true);
            
            try {
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                await api.knowledgeBase.upload(formData);
                showAlert('File uploaded! Processing in background...');
                form.reset();
            } catch (error) {
                showAlert(error.message, 'error');
            } finally {
                this.setLoading(btn, false);
            }
        });
    }

    // --- Chat View ---
    populateChatSelect() {
        const select = document.getElementById('chat-agent-select');
        select.innerHTML = '<option value="" disabled selected>Select an agent...</option>';
        
        this.agents.forEach(agent => {
            const opt = document.createElement('option');
            opt.value = agent._id;
            opt.textContent = agent.name;
            select.appendChild(opt);
        });
        
        select.addEventListener('change', (e) => {
            const id = e.target.value;
            const agent = this.agents.find(a => a._id === id);
            const infoCard = document.getElementById('chat-agent-info');
            if (agent) {
                document.getElementById('info-agent-name').textContent = agent.name;
                document.getElementById('info-agent-role').textContent = agent.role;
                infoCard.style.display = 'block';
            }
        });
    }

    bindChat() {
        const chatForm = document.getElementById('chat-form');
        const clearBtn = document.getElementById('clear-chat-btn');
        const messagesContainer = document.getElementById('chat-messages');
        
        clearBtn.addEventListener('click', () => {
            messagesContainer.innerHTML = '<div class="message system-msg">Chat cleared.</div>';
        });

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if(!this.isAuthenticated()){
                showAlert("Please login first.", "error"); return;
            }

            const agentId = document.getElementById('chat-agent-select').value;
            if (!agentId) {
                showAlert('Please select an agent first.', 'error');
                return;
            }

            const inputField = document.getElementById('chat-input');
            const query = inputField.value.trim();
            if (!query) return;

            const threadId = document.getElementById('chat-thread-id').value.trim() || undefined;

            // Render user msg
            this.appendMessage('user', query);
            inputField.value = '';
            
            const btn = document.getElementById('chat-send-btn');
            const originalIcon = btn.innerHTML;
            btn.innerHTML = '<div class="loader"></div>';
            btn.disabled = true;

            try {
                const payload = { query };
                if (threadId) payload.thread_id = threadId;

                const res = await api.chat.run(agentId, payload);
                
                if (res.data && res.data.response) {
                    this.appendMessage('ai', res.data.response);
                    
                    // update thread id field in case the backend returns a new one
                    if (res.data.thread_id && !threadId) {
                        document.getElementById('chat-thread-id').value = res.data.thread_id;
                    }
                } else {
                    this.appendMessage('system', 'Received empty response or error.');
                }
            } catch (error) {
                this.appendMessage('system', `Error: ${error.message}`);
                showAlert('Chat failed: ' + error.message, 'error');
            } finally {
                btn.innerHTML = originalIcon;
                btn.disabled = false;
                inputField.focus();
            }
        });
    }

    appendMessage(role, text) {
        const container = document.getElementById('chat-messages');
        
        // Remove system placeholder if it exists initially
        const placeholder = container.querySelector('.system-msg');
        if (placeholder && placeholder.textContent.includes('Select an agent')) {
            placeholder.remove();
        }

        const msgEl = document.createElement('div');
        if (role === 'user') {
            msgEl.className = 'message user-msg';
        } else if (role === 'ai') {
            msgEl.className = 'message ai-msg';
        } else {
            msgEl.className = 'message system-msg';
        }

        // Extremely simple formatting for linebreaks
        msgEl.innerHTML = text.replace(/\n/g, '<br>');
        
        container.appendChild(msgEl);
        container.scrollTop = container.scrollHeight;
    }
}

// Init App on Load
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
