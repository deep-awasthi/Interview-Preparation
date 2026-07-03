/* ============================================
   Interview-Preparation — Application Logic
   B&W Trello-style board with per-user storage
   and optional Firebase cross-device sync
   ============================================ */

// ==========================================
// CONSTANTS
// ==========================================
const APP_KEY = 'interview-prep';
const FIREBASE_CONFIG_KEY = 'interview-prep-firebase-config';
const SESSION_KEY = 'interview-prep-session';

const SECTIONS = ['lld', 'hld', 'java', 'dsa'];
const SECTION_LABELS = { lld: 'Low Level Design', hld: 'High Level Design', java: 'Java', dsa: 'DSA' };
const SECTION_ICONS = { lld: '🧩', hld: '🏗️', java: '☕', dsa: '🧮' };
const STATUS_LABELS = { 'not-started': 'Not Started', 'in-progress': 'In Progress', completed: 'Completed', revision: 'Needs Revision' };
const CATEGORY_ICONS = { article: '📄', video: '🎬', course: '📚', docs: '📖', practice: '💡' };

// ==========================================
// STATE
// ==========================================
let currentUser = null;
let appData = null;
let currentView = 'board';
let currentSection = 'overview';
let currentTodoFilter = 'all';
let activeTopicId = null;
let activeTopicSection = null;
let addingTopicToSection = null;
let editingTodoId = null;
let firebaseApp = null;
let firebaseDb = null;
let firebaseUnsubscribe = null;
let viewingContent = '';

// ==========================================
// UTILITY
// ==========================================
const $ = id => document.getElementById(id);
const uid = () => Date.now().toString(36) + Math.random().toString(36).substr(2, 8);
const todayKey = () => new Date().toISOString().split('T')[0];
const escHtml = s => { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; };

function normalizeUrl(value) {
    const raw = (value || '').trim();
    if (!raw) return null;

    const hasProtocol = /^[a-z][a-z\d+\-.]*:/i.test(raw);
    const candidate = hasProtocol ? raw : `https://${raw}`;

    try {
        const url = new URL(candidate);
        if (!['http:', 'https:'].includes(url.protocol)) return null;
        return url.href;
    } catch {
        return null;
    }
}

function fmtDate(d) {
    if (!d) return '';
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function fmtDateTime(d) {
    if (!d) return '';
    const dt = new Date(d);
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' +
           dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function timeAgo(d) {
    const ms = Date.now() - new Date(d).getTime();
    const min = Math.floor(ms / 60000);
    if (min < 1) return 'now';
    if (min < 60) return min + 'm';
    const hr = Math.floor(ms / 3600000);
    if (hr < 24) return hr + 'h';
    return Math.floor(ms / 86400000) + 'd';
}

function hashStr(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++) {
        h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    }
    return 'u' + Math.abs(h).toString(36);
}

// ==========================================
// TOAST
// ==========================================
function toast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    $('toastContainer').appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

// ==========================================
// MODAL
// ==========================================
function openModal(id) { $(id).classList.add('show'); }
function closeModal(id) { $(id).classList.remove('show'); }

document.querySelectorAll('.modal-overlay').forEach(o => {
    o.addEventListener('click', e => { if (e.target === o) o.classList.remove('show'); });
});
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal-overlay.show').forEach(m => m.classList.remove('show'));
});

// ==========================================
// DATA LAYER
// ==========================================
function defaultData() {
    return {
        sections: {
            lld: { topics: [] },
            hld: { topics: [] },
            java: { topics: [] },
            dsa: { topics: [] }
        },
        todos: [],
        reminders: { enabled: false, time: '09:00', custom: [] },
        activity: [],
        streak: { count: 0, lastDate: null }
    };
}

function storageKey() { return APP_KEY + '-' + currentUser.id; }

function loadLocal() {
    try {
        const d = localStorage.getItem(storageKey());
        if (d) {
            const parsed = JSON.parse(d);
            // Merge with defaults for forward compat
            const def = defaultData();
            SECTIONS.forEach(s => {
                if (!parsed.sections[s]) parsed.sections[s] = def.sections[s];
                if (!Array.isArray(parsed.sections[s].topics)) parsed.sections[s].topics = [];
            });
            parsed.todos = parsed.todos || [];
            parsed.reminders = { ...def.reminders, ...(parsed.reminders || {}) };
            parsed.activity = parsed.activity || [];
            parsed.streak = parsed.streak || def.streak;
            return parsed;
        }
    } catch (e) { console.error('Load error:', e); }
    return defaultData();
}

function saveLocal() {
    try { localStorage.setItem(storageKey(), JSON.stringify(appData)); } catch (e) { console.error('Save error:', e); }
}

function saveData() {
    saveLocal();
    syncToFirebase();
}

// ==========================================
// AUTH (Local user system)
// ==========================================
function handleLogin() {
    const username = $('loginUsername').value.trim().toLowerCase();
    const passphrase = $('loginPassphrase').value;

    if (!username || username.length < 2) {
        $('loginError').textContent = 'Username must be at least 2 characters.';
        return;
    }
    if (!passphrase || passphrase.length < 3) {
        $('loginError').textContent = 'Passphrase must be at least 3 characters.';
        return;
    }

    const userId = hashStr(username + ':' + passphrase);

    // Check if user exists
    const existingUsers = JSON.parse(localStorage.getItem(APP_KEY + '-users') || '{}');

    if (existingUsers[username]) {
        // Verify passphrase
        if (existingUsers[username] !== userId) {
            $('loginError').textContent = 'Incorrect passphrase for this username.';
            return;
        }
    } else {
        // New user
        existingUsers[username] = userId;
        localStorage.setItem(APP_KEY + '-users', JSON.stringify(existingUsers));
    }

    currentUser = { username, id: userId };
    localStorage.setItem(SESSION_KEY, JSON.stringify(currentUser));

    appData = loadLocal();
    enterApp();
}

function handleLogout() {
    if (firebaseUnsubscribe) { firebaseUnsubscribe(); firebaseUnsubscribe = null; }
    currentUser = null;
    appData = null;
    localStorage.removeItem(SESSION_KEY);
    $('app').style.display = 'none';
    $('loginScreen').style.display = 'flex';
    $('loginUsername').value = '';
    $('loginPassphrase').value = '';
    $('loginError').textContent = '';
}

function checkSession() {
    try {
        const s = localStorage.getItem(SESSION_KEY);
        if (s) {
            currentUser = JSON.parse(s);
            appData = loadLocal();
            enterApp();
            return;
        }
    } catch (e) {}
    $('loginScreen').style.display = 'flex';
}

function enterApp() {
    $('loginScreen').style.display = 'none';
    $('app').style.display = '';
    $('userBadge').textContent = currentUser.username.charAt(0).toUpperCase();
    $('streakNum').textContent = appData.streak.count || 0;
    renderBoard();
    initFirebaseIfConfigured();
    scheduleReminder();
    checkOverdue();
}

// ==========================================
// FIREBASE SYNC
// ==========================================
function getFirebaseConfig() {
    try {
        const c = localStorage.getItem(FIREBASE_CONFIG_KEY);
        return c ? JSON.parse(c) : null;
    } catch { return null; }
}

function toggleSyncSetup() {
    const el = $('syncSetup');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
    const existing = getFirebaseConfig();
    if (existing) $('firebaseConfigInput').value = JSON.stringify(existing, null, 2);
}

function saveFirebaseConfig() {
    try {
        const raw = $('firebaseConfigInput').value.trim();
        const config = JSON.parse(raw);
        if (!config.apiKey || !config.projectId) throw new Error('Missing fields');
        localStorage.setItem(FIREBASE_CONFIG_KEY, JSON.stringify(config));
        $('syncStatus').textContent = '✓ Config saved! Login to start syncing.';
        $('syncStatus').style.color = '#1a1a2e';
        toast('Firebase config saved');
    } catch (e) {
        $('syncStatus').textContent = '✗ Invalid config JSON. ' + e.message;
        $('syncStatus').style.color = '#d32f2f';
    }
}

function saveFirebaseConfigFromSettings() {
    try {
        const raw = $('settingsFirebaseConfig').value.trim();
        const config = JSON.parse(raw);
        if (!config.apiKey || !config.projectId) throw new Error('Missing fields');
        localStorage.setItem(FIREBASE_CONFIG_KEY, JSON.stringify(config));
        toast('Firebase config saved! Connecting...');
        initFirebaseIfConfigured();
    } catch (e) {
        toast('Invalid config: ' + e.message);
    }
}

function disconnectFirebase() {
    if (firebaseUnsubscribe) { firebaseUnsubscribe(); firebaseUnsubscribe = null; }
    localStorage.removeItem(FIREBASE_CONFIG_KEY);
    firebaseApp = null;
    firebaseDb = null;
    updateSyncStatusUI();
    toast('Firebase disconnected');
}

async function initFirebaseIfConfigured() {
    const config = getFirebaseConfig();
    if (!config) { updateSyncStatusUI(); return; }

    // Load Firebase SDK if not loaded
    if (!window.firebase) {
        await loadScript('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
        await loadScript('https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore-compat.js');
    }

    try {
        if (!firebaseApp) {
            // Check if already initialized
            if (firebase.apps.length) {
                firebaseApp = firebase.apps[0];
            } else {
                firebaseApp = firebase.initializeApp(config);
            }
            firebaseDb = firebase.firestore();
        }

        // Listen for real-time updates
        const docRef = firebaseDb.collection('users').doc(currentUser.id);

        if (firebaseUnsubscribe) firebaseUnsubscribe();

        firebaseUnsubscribe = docRef.onSnapshot(doc => {
            if (doc.exists) {
                const remoteData = doc.data().data;
                if (remoteData) {
                    const remoteTs = doc.data().updatedAt || 0;
                    const localTs = appData._updatedAt || 0;
                    if (remoteTs > localTs) {
                        // Remote is newer, merge
                        const parsed = JSON.parse(remoteData);
                        parsed._updatedAt = remoteTs;
                        appData = parsed;
                        saveLocal();
                        renderCurrentView();
                        console.log('📥 Synced from cloud');
                    }
                }
            }
        }, err => {
            console.error('Firestore listen error:', err);
        });

        // Push local data to cloud on first connect
        syncToFirebase();
        updateSyncStatusUI();
        toast('Connected to Firebase ☁️');
    } catch (e) {
        console.error('Firebase init error:', e);
        toast('Firebase error: ' + e.message);
    }
}

function syncToFirebase() {
    if (!firebaseDb || !currentUser) return;

    const ts = Date.now();
    appData._updatedAt = ts;
    saveLocal(); // update local with timestamp

    const docRef = firebaseDb.collection('users').doc(currentUser.id);
    docRef.set({
        username: currentUser.username,
        data: JSON.stringify(appData),
        updatedAt: ts
    }).catch(err => console.error('Sync error:', err));
}

function loadScript(src) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
        const s = document.createElement('script');
        s.src = src;
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
    });
}

function updateSyncStatusUI() {
    const label = $('settingsSyncStatus');
    const uname = $('settingsUsername');
    if (label) {
        const isConnected = !!firebaseDb;
        label.textContent = isConnected ? 'Cloud Synced ☁️' : 'Local Only';
        label.className = 'sync-label' + (isConnected ? ' connected' : '');
    }
    if (uname && currentUser) uname.textContent = currentUser.username;

    const configArea = $('settingsFirebaseConfig');
    if (configArea) {
        const existing = getFirebaseConfig();
        if (existing) configArea.value = JSON.stringify(existing, null, 2);
    }
}

// ==========================================
// VIEWS
// ==========================================
function switchView(view, btn) {
    currentView = view;
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    $('view-' + view).classList.add('active');

    renderCurrentView();
}

function renderCurrentView() {
    switch (currentView) {
        case 'board': renderBoard(); break;
        case 'todo': renderTodos(); break;
        case 'reminders': renderRemindersView(); break;
        case 'settings': updateSyncStatusUI(); break;
    }
    $('streakNum').textContent = appData.streak.count || 0;
}

function switchSection(section, btn) {
    currentSection = section;
    document.querySelectorAll('.section-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderBoard();
}

// ==========================================
// BOARD: OVERVIEW
// ==========================================
function renderBoard() {
    // Hide all boards first
    $('board-overview').style.display = 'none';
    document.querySelectorAll('.section-board').forEach(b => b.style.display = 'none');

    if (currentSection === 'overview') {
        renderOverview();
        $('board-overview').style.display = 'flex';
    } else {
        renderSectionBoard(currentSection);
        $('board-' + currentSection).style.display = 'flex';
    }
}

function renderOverview() {
    const board = $('board-overview');
    let html = '';

    SECTIONS.forEach(s => {
        const topics = appData.sections[s].topics;
        const total = topics.length;
        const completed = topics.filter(t => t.status === 'completed').length;
        const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

        html += `
        <div class="list">
            <div class="list-header">
                <span class="list-title">${SECTION_ICONS[s]} ${SECTION_LABELS[s]}</span>
                <span class="list-count">${total}</span>
            </div>
            <div class="list-body">
                <div class="overview-card" onclick="switchSection('${s}', document.querySelector('.section-btn[data-section=${s}]'))">
                    <div class="overview-percent">${pct}%</div>
                    <div class="overview-progress"><div class="overview-progress-fill" style="width:${pct}%"></div></div>
                    <div class="overview-card-stat">${completed} of ${total} topics completed</div>
                </div>
                ${topics.slice(0, 5).map(t => renderTrelloCard(s, t)).join('')}
            </div>
            <div class="list-footer">
                <button class="add-card-btn" onclick="openAddTopic('${s}')">+ Add topic</button>
            </div>
        </div>`;
    });

    // Todo column
    const pendingTodos = appData.todos.filter(t => !t.completed);
    html += `
    <div class="list">
        <div class="list-header">
            <span class="list-title">📋 Todo</span>
            <span class="list-count">${pendingTodos.length}</span>
        </div>
        <div class="list-body">
            ${pendingTodos.slice(0, 8).map(t => `
                <div class="trello-card" onclick="switchView('todo', document.querySelector('.nav-tab[data-view=todo]'))">
                    <div class="trello-card-title">${escHtml(t.text)}</div>
                    <div class="trello-card-meta">
                        <span class="todo-cat">${t.category}</span>
                        ${t.dueDate ? `<span class="card-badge ${t.dueDate < todayKey() ? 'badge-priority-high' : 'badge-priority-low'}">${fmtDate(t.dueDate)}</span>` : ''}
                    </div>
                </div>
            `).join('') || '<p style="text-align:center;color:#8993a4;font-size:12px;padding:20px;">No pending tasks</p>'}
        </div>
        <div class="list-footer">
            <button class="add-card-btn" onclick="switchView('todo', document.querySelector('.nav-tab[data-view=todo]')); setTimeout(openTodoModal, 200);">+ Add task</button>
        </div>
    </div>`;

    board.innerHTML = html;
}

// ==========================================
// BOARD: SECTION (Kanban by Status)
// ==========================================
function renderSectionBoard(section) {
    const board = $('board-' + section);
    const topics = appData.sections[section].topics;
    const statuses = ['not-started', 'in-progress', 'completed', 'revision'];
    let html = '';

    statuses.forEach(status => {
        const filtered = topics.filter(t => t.status === status);
        html += `
        <div class="list">
            <div class="list-header">
                <span class="list-title">${STATUS_LABELS[status]}</span>
                <span class="list-count">${filtered.length}</span>
            </div>
            <div class="list-body">
                ${filtered.map(t => renderTrelloCard(section, t)).join('')}
            </div>
            ${status === 'not-started' ? `
            <div class="list-footer">
                <button class="add-card-btn" onclick="openAddTopic('${section}')">+ Add topic</button>
            </div>` : ''}
        </div>`;
    });

    board.innerHTML = html;
}

function renderTrelloCard(section, topic) {
    const linkCount = (topic.links || []).length;
    const noteCount = (topic.notes || []).length;
    const snippetCount = (topic.snippets || []).length;

    return `
    <div class="trello-card" onclick="openCardDetail('${section}', '${topic.id}')">
        <div class="trello-card-title">${escHtml(topic.name)}</div>
        <div class="trello-card-meta">
            <span class="card-badge badge-priority-${topic.priority}">${topic.priority}</span>
            ${(linkCount + noteCount + snippetCount) > 0 ? `
            <span class="card-indicators">
                ${linkCount ? `<span class="card-indicator">🔗${linkCount}</span>` : ''}
                ${noteCount ? `<span class="card-indicator">📝${noteCount}</span>` : ''}
                ${snippetCount ? `<span class="card-indicator">💻${snippetCount}</span>` : ''}
            </span>` : ''}
        </div>
        <button class="card-delete" onclick="event.stopPropagation(); deleteTopic('${section}', '${topic.id}')">✕</button>
    </div>`;
}

// ==========================================
// ADD / DELETE TOPIC
// ==========================================
function openAddTopic(section) {
    addingTopicToSection = section;
    $('newTopicName').value = '';
    $('newTopicPriority').value = 'medium';
    openModal('addTopicModal');
    $('newTopicName').focus();
}

function saveNewTopic() {
    const name = $('newTopicName').value.trim();
    const priority = $('newTopicPriority').value;
    if (!name) { toast('Enter a topic name'); return; }

    appData.sections[addingTopicToSection].topics.push({
        id: uid(), name, priority,
        status: 'not-started',
        links: [], notes: [], snippets: [],
        createdAt: new Date().toISOString()
    });

    addActivity(`Added "${name}" to ${addingTopicToSection.toUpperCase()}`);
    saveData();
    closeModal('addTopicModal');
    renderBoard();
    updateStreak();
    toast('Topic added');
}

function deleteTopic(section, id) {
    const t = appData.sections[section].topics.find(x => x.id === id);
    if (!t || !confirm(`Delete "${t.name}"?`)) return;
    appData.sections[section].topics = appData.sections[section].topics.filter(x => x.id !== id);
    addActivity(`Deleted "${t.name}" from ${section.toUpperCase()}`);
    saveData();
    renderBoard();
    toast('Topic deleted');
}

// ==========================================
// CARD DETAIL (Links, Notes, Snippets)
// ==========================================
function openCardDetail(section, id) {
    const topic = appData.sections[section].topics.find(t => t.id === id);
    if (!topic) return;

    activeTopicId = id;
    activeTopicSection = section;

    $('cardDetailTitle').textContent = topic.name;
    $('cardDetailStatus').value = topic.status;

    renderCardLinks();
    renderCardNotes();
    renderCardSnippets();

    // Hide all inline forms
    $('addLinkForm').style.display = 'none';
    $('addNoteForm').style.display = 'none';
    $('addSnippetForm').style.display = 'none';

    openModal('cardDetailModal');
}

function getActiveTopic() {
    return appData.sections[activeTopicSection]?.topics.find(t => t.id === activeTopicId);
}

function updateCardStatus() {
    const topic = getActiveTopic();
    if (!topic) return;
    const oldStatus = topic.status;
    topic.status = $('cardDetailStatus').value;
    if (oldStatus !== topic.status) {
        addActivity(`Changed "${topic.name}" to ${STATUS_LABELS[topic.status]}`);
        saveData();
        renderBoard();
        if (topic.status === 'completed') toast('🎉 Topic completed!');
    }
}

// --- Links ---
function renderCardLinks() {
    const topic = getActiveTopic();
    const container = $('cardLinks');
    if (!topic || !topic.links || !topic.links.length) {
        container.innerHTML = '<p style="font-size:12px;color:#8993a4;">No links yet</p>';
        return;
    }
    container.innerHTML = topic.links.map((link, i) => {
        const safeUrl = normalizeUrl(link.url);
        return `
        <div class="detail-item">
            <span class="detail-item-icon">${CATEGORY_ICONS[link.category] || '🔗'}</span>
            <div class="detail-item-body">
                <div class="detail-item-title">${escHtml(link.title)}</div>
                <a class="detail-item-sub" href="${escHtml(safeUrl || '#')}" target="_blank" rel="noopener">${escHtml(link.url)}</a>
            </div>
            <div class="detail-item-actions">
                <button class="btn-icon" onclick="openSavedLink(${i})" title="Open" ${safeUrl ? '' : 'disabled'}>↗</button>
                <button class="btn-icon" onclick="deleteLink(${i})" title="Delete">✕</button>
            </div>
        </div>`;
    }).join('');
}

function openSavedLink(i) {
    const topic = getActiveTopic();
    const url = topic?.links?.[i] ? normalizeUrl(topic.links[i].url) : null;
    if (!url) { toast('Invalid link URL'); return; }
    window.open(url, '_blank', 'noopener');
}

function addLinkInline() { $('addLinkForm').style.display = 'flex'; $('inlineLinkTitle').focus(); }
function cancelLinkInline() { $('addLinkForm').style.display = 'none'; }

function saveLinkInline() {
    const topic = getActiveTopic();
    if (!topic) return;
    const title = $('inlineLinkTitle').value.trim();
    const url = normalizeUrl($('inlineLinkUrl').value);
    const cat = $('inlineLinkCat').value;
    if (!title || !url) { toast('Enter a title and valid http(s) URL'); return; }

    if (!topic.links) topic.links = [];
    topic.links.push({ id: uid(), title, url, category: cat, createdAt: new Date().toISOString() });
    addActivity(`Added link "${title}" to ${topic.name}`);
    saveData();
    renderCardLinks();
    renderBoard();
    cancelLinkInline();
    $('inlineLinkTitle').value = '';
    $('inlineLinkUrl').value = '';
    toast('Link saved');
}

function deleteLink(i) {
    const topic = getActiveTopic();
    if (!topic) return;
    topic.links.splice(i, 1);
    saveData();
    renderCardLinks();
    renderBoard();
}

// --- Notes ---
function renderCardNotes() {
    const topic = getActiveTopic();
    const container = $('cardNotes');
    if (!topic || !topic.notes || !topic.notes.length) {
        container.innerHTML = '<p style="font-size:12px;color:#8993a4;">No notes yet</p>';
        return;
    }
    container.innerHTML = topic.notes.map((note, i) => `
        <div class="detail-item">
            <span class="detail-item-icon">📝</span>
            <div class="detail-item-body">
                <div class="detail-item-title">${escHtml(note.title)}</div>
                <div class="detail-item-content" onclick="event.stopPropagation(); viewContent('${escHtml(note.title)}', ${i}, 'note')">${escHtml(note.content.substring(0, 200))}</div>
            </div>
            <div class="detail-item-actions">
                <button class="btn-icon" onclick="viewContent('${escHtml(note.title)}', ${i}, 'note')" title="View">👁</button>
                <button class="btn-icon" onclick="deleteNote(${i})" title="Delete">✕</button>
            </div>
        </div>
    `).join('');
}

function addNoteInline() { $('addNoteForm').style.display = 'flex'; $('inlineNoteTitle').focus(); }
function cancelNoteInline() { $('addNoteForm').style.display = 'none'; }

function saveNoteInline() {
    const topic = getActiveTopic();
    if (!topic) return;
    const title = $('inlineNoteTitle').value.trim();
    const content = $('inlineNoteContent').value.trim();
    if (!title || !content) { toast('Fill in title and content'); return; }

    if (!topic.notes) topic.notes = [];
    topic.notes.push({ id: uid(), title, content, createdAt: new Date().toISOString() });
    addActivity(`Added note "${title}" to ${topic.name}`);
    saveData();
    renderCardNotes();
    renderBoard();
    cancelNoteInline();
    $('inlineNoteTitle').value = '';
    $('inlineNoteContent').value = '';
    toast('Note saved');
}

function deleteNote(i) {
    const topic = getActiveTopic();
    if (!topic) return;
    topic.notes.splice(i, 1);
    saveData();
    renderCardNotes();
    renderBoard();
}

// --- Snippets ---
function renderCardSnippets() {
    const topic = getActiveTopic();
    const container = $('cardSnippets');
    if (!topic || !topic.snippets || !topic.snippets.length) {
        container.innerHTML = '<p style="font-size:12px;color:#8993a4;">No code/docs yet</p>';
        return;
    }
    container.innerHTML = topic.snippets.map((s, i) => `
        <div class="detail-item">
            <span class="detail-item-icon">${s.type === 'code' ? '💻' : '📐'}</span>
            <div class="detail-item-body">
                <div class="detail-item-title">${escHtml(s.title)}</div>
                <div class="detail-item-content" onclick="event.stopPropagation(); viewContent('${escHtml(s.title)}', ${i}, 'snippet')">${escHtml(s.content.substring(0, 200))}</div>
            </div>
            <div class="detail-item-actions">
                <button class="btn-icon" onclick="viewContent('${escHtml(s.title)}', ${i}, 'snippet')" title="View">👁</button>
                <button class="btn-icon" onclick="deleteSnippet(${i})" title="Delete">✕</button>
            </div>
        </div>
    `).join('');
}

function addSnippetInline() { $('addSnippetForm').style.display = 'flex'; $('inlineSnippetTitle').focus(); }
function cancelSnippetInline() { $('addSnippetForm').style.display = 'none'; }

function saveSnippetInline() {
    const topic = getActiveTopic();
    if (!topic) return;
    const title = $('inlineSnippetTitle').value.trim();
    const type = $('inlineSnippetType').value;
    const content = $('inlineSnippetContent').value.trim();
    if (!title || !content) { toast('Fill in title and content'); return; }

    if (!topic.snippets) topic.snippets = [];
    topic.snippets.push({ id: uid(), title, type, content, createdAt: new Date().toISOString() });
    addActivity(`Added ${type === 'code' ? 'code snippet' : 'design doc'} "${title}" to ${topic.name}`);
    saveData();
    renderCardSnippets();
    renderBoard();
    cancelSnippetInline();
    $('inlineSnippetTitle').value = '';
    $('inlineSnippetContent').value = '';
    toast('Saved!');
}

function deleteSnippet(i) {
    const topic = getActiveTopic();
    if (!topic) return;
    topic.snippets.splice(i, 1);
    saveData();
    renderCardSnippets();
    renderBoard();
}

// --- View Content Full ---
function viewContent(title, index, type) {
    const topic = getActiveTopic();
    if (!topic) return;
    let content = '';
    if (type === 'note') content = topic.notes[index]?.content || '';
    if (type === 'snippet') content = topic.snippets[index]?.content || '';

    $('viewContentTitle').textContent = title;
    $('viewContentBody').textContent = content;
    viewingContent = content;
    openModal('viewContentModal');
}

function copyViewContent() {
    navigator.clipboard.writeText(viewingContent).then(() => toast('Copied!')).catch(() => toast('Copy failed'));
}

// ==========================================
// TODO LIST
// ==========================================
function openTodoModal() {
    editingTodoId = null;
    $('todoModalTitle').textContent = 'Add Task';
    $('todoText').value = '';
    $('todoCategory').value = 'general';
    $('todoDueDate').value = todayKey();
    $('todoPriority').value = 'medium';
    openModal('addTodoModal');
    $('todoText').focus();
}

function saveTodo() {
    const text = $('todoText').value.trim();
    const category = $('todoCategory').value;
    const dueDate = $('todoDueDate').value;
    const priority = $('todoPriority').value;
    if (!text) { toast('Enter a task'); return; }

    if (editingTodoId) {
        const todo = appData.todos.find(t => t.id === editingTodoId);
        if (todo) { todo.text = text; todo.category = category; todo.dueDate = dueDate; todo.priority = priority; }
        toast('Task updated');
    } else {
        appData.todos.push({
            id: uid(), text, category, dueDate, priority,
            completed: false, createdAt: new Date().toISOString()
        });
        addActivity(`Added task "${text}"`);
        toast('Task added');
    }

    saveData();
    closeModal('addTodoModal');
    renderTodos();
    renderBoard();
    updateStreak();
}

function toggleTodo(id, checked) {
    const todo = appData.todos.find(t => t.id === id);
    if (!todo) return;
    todo.completed = checked;
    addActivity(`${checked ? 'Completed' : 'Reopened'} task "${todo.text}"`);
    saveData();
    renderTodos();
    renderBoard();
    updateStreak();
    if (checked) toast('Task done! ✓');
}

function editTodo(id) {
    const todo = appData.todos.find(t => t.id === id);
    if (!todo) return;
    editingTodoId = id;
    $('todoModalTitle').textContent = 'Edit Task';
    $('todoText').value = todo.text;
    $('todoCategory').value = todo.category;
    $('todoDueDate').value = todo.dueDate || '';
    $('todoPriority').value = todo.priority;
    openModal('addTodoModal');
}

function deleteTodo(id) {
    appData.todos = appData.todos.filter(t => t.id !== id);
    saveData();
    renderTodos();
    renderBoard();
    toast('Task deleted');
}

function filterTodos(filter, btn) {
    currentTodoFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderTodos();
}

function renderTodos() {
    const container = $('todoList');
    const today = todayKey();
    let todos = [...appData.todos];

    switch (currentTodoFilter) {
        case 'pending': todos = todos.filter(t => !t.completed); break;
        case 'today': todos = todos.filter(t => !t.completed && t.dueDate === today); break;
        case 'overdue': todos = todos.filter(t => !t.completed && t.dueDate && t.dueDate < today); break;
        case 'done': todos = todos.filter(t => t.completed); break;
    }

    // Sort: overdue first, then priority
    const po = { high: 0, medium: 1, low: 2 };
    todos.sort((a, b) => {
        if (a.completed !== b.completed) return a.completed ? 1 : -1;
        const aOd = !a.completed && a.dueDate && a.dueDate < today;
        const bOd = !b.completed && b.dueDate && b.dueDate < today;
        if (aOd !== bOd) return aOd ? -1 : 1;
        return (po[a.priority] || 1) - (po[b.priority] || 1);
    });

    if (!todos.length) {
        container.innerHTML = '<p style="text-align:center;color:#8993a4;padding:40px;font-size:13px;">No tasks match this filter</p>';
        return;
    }

    container.innerHTML = todos.map(t => {
        const isOverdue = !t.completed && t.dueDate && t.dueDate < today;
        return `
        <div class="todo-item ${t.completed ? 'completed' : ''} ${isOverdue ? 'overdue' : ''}">
            <input type="checkbox" class="todo-check" ${t.completed ? 'checked' : ''} onchange="toggleTodo('${t.id}', this.checked)">
            <div class="todo-item-info">
                <div class="todo-item-text">${escHtml(t.text)}</div>
                <div class="todo-item-meta">
                    <span class="todo-cat">${t.category}</span>
                    ${t.dueDate ? `<span>${isOverdue ? '⚠ Overdue: ' : ''}${fmtDate(t.dueDate)}</span>` : ''}
                    <span>${t.priority}</span>
                </div>
            </div>
            <div class="todo-item-actions">
                <button class="btn-icon" onclick="editTodo('${t.id}')" title="Edit">✎</button>
                <button class="btn-icon" onclick="deleteTodo('${t.id}')" title="Delete">✕</button>
            </div>
        </div>`;
    }).join('');
}

// ==========================================
// REMINDERS & NOTIFICATIONS
// ==========================================
const QUOTES = [
    '"The only way to do great work is to love what you do." — Steve Jobs',
    '"First, solve the problem. Then, write the code." — John Johnson',
    '"Talk is cheap. Show me the code." — Linus Torvalds',
    '"Any fool can write code that a computer can understand. Good programmers write code that humans can understand." — Martin Fowler',
    '"The expert in anything was once a beginner." — Helen Hayes',
    '"Simplicity is the soul of efficiency." — Austin Freeman',
    '"It does not matter how slowly you go as long as you do not stop." — Confucius',
    '"Hard work beats talent when talent doesn\'t work hard." — Tim Notke',
    '"Give me six hours to chop down a tree and I will spend the first four sharpening the axe." — Abraham Lincoln',
    '"The best time to plant a tree was 20 years ago. The second best time is now." — Chinese Proverb',
    '"Preparation is the key to success." — Alexander Graham Bell',
    '"The more I practice, the luckier I get." — Gary Player',
    '"Programs must be written for people to read, and only incidentally for machines to execute." — Harold Abelson',
];

function newQuote() {
    $('quoteBlock').textContent = QUOTES[Math.floor(Math.random() * QUOTES.length)];
}

function requestNotifPermission() {
    if (!('Notification' in window)) { toast('Notifications not supported'); return; }
    Notification.requestPermission().then(p => {
        if (p === 'granted') { toast('Notifications enabled!'); updateNotifUI(); }
        else toast('Permission denied');
    });
}

function updateNotifUI() {
    const btn = $('btnNotifPermission');
    if ('Notification' in window && Notification.permission === 'granted') {
        btn.textContent = 'Enabled ✓';
        btn.disabled = true;
    }
}

function toggleDaily() {
    appData.reminders.enabled = $('toggleDailyReminder').checked;
    saveData();
    scheduleReminder();
    toast(appData.reminders.enabled ? 'Daily reminder on' : 'Daily reminder off');
}

function updateReminderTime() {
    appData.reminders.time = $('reminderTimeInput').value;
    saveData();
    scheduleReminder();
}

function renderRemindersView() {
    $('toggleDailyReminder').checked = appData.reminders.enabled;
    $('reminderTimeInput').value = appData.reminders.time || '09:00';
    updateNotifUI();
    newQuote();
    renderCustomReminders();
}

function addCustomReminder() {
    const text = $('customRemText').value.trim();
    const dt = $('customRemDate').value;
    if (!text || !dt) { toast('Fill in message and date'); return; }

    appData.reminders.custom.push({ id: uid(), text, dateTime: dt, notified: false });
    saveData();
    $('customRemText').value = '';
    $('customRemDate').value = '';
    renderCustomReminders();
    toast('Reminder set');
}

function deleteReminder(id) {
    appData.reminders.custom = appData.reminders.custom.filter(r => r.id !== id);
    saveData();
    renderCustomReminders();
}

function renderCustomReminders() {
    const list = $('customRemList');
    const rems = appData.reminders.custom || [];
    if (!rems.length) { list.innerHTML = '<p style="font-size:12px;color:#8993a4;">No custom reminders</p>'; return; }

    list.innerHTML = rems.map(r => `
        <div class="custom-rem-item">
            <div>
                <div class="custom-rem-text">${escHtml(r.text)}</div>
                <div class="custom-rem-time">${fmtDateTime(r.dateTime)}</div>
            </div>
            <button class="btn-icon" onclick="deleteReminder('${r.id}')">✕</button>
        </div>
    `).join('');
}

// Reminder scheduler
let reminderTimer = null;

function scheduleReminder() {
    if (reminderTimer) clearTimeout(reminderTimer);
    if (!appData.reminders.enabled) return;

    const now = new Date();
    const [h, m] = (appData.reminders.time || '09:00').split(':').map(Number);
    const target = new Date();
    target.setHours(h, m, 0, 0);
    if (target <= now) target.setDate(target.getDate() + 1);

    reminderTimer = setTimeout(() => {
        sendNotification();
        scheduleReminder(); // next day
    }, target - now);
}

function sendNotification() {
    if (Notification.permission !== 'granted') return;

    const pending = appData.todos.filter(t => !t.completed).length;
    const overall = SECTIONS.reduce((s, sec) => {
        const t = appData.sections[sec].topics;
        return s + (t.length ? Math.round(t.filter(x => x.status === 'completed').length / t.length * 100) : 0);
    }, 0) / 4;

    new Notification('📋 Interview-Preparation', {
        body: `Progress: ${Math.round(overall)}% | ${pending} pending tasks\n${QUOTES[Math.floor(Math.random() * QUOTES.length)]}`,
        tag: 'daily'
    });
}

function checkCustomReminders() {
    const now = new Date();
    (appData.reminders.custom || []).forEach(r => {
        if (r.notified) return;
        if (now >= new Date(r.dateTime)) {
            r.notified = true;
            saveData();
            if (Notification.permission === 'granted') {
                new Notification('⏰ Reminder', { body: r.text, tag: 'custom-' + r.id });
            }
            toast('Reminder: ' + r.text);
        }
    });
}

function checkOverdue() {
    const today = todayKey();
    const overdue = appData.todos.filter(t => !t.completed && t.dueDate && t.dueDate < today);
    if (overdue.length && Notification.permission === 'granted') {
        setTimeout(() => {
            new Notification('⚠ Overdue Tasks', {
                body: `You have ${overdue.length} overdue task${overdue.length > 1 ? 's' : ''}`,
                tag: 'overdue'
            });
        }, 2000);
    }
}

// ==========================================
// ACTIVITY & STREAK
// ==========================================
function addActivity(text) {
    appData.activity.unshift({ text, ts: new Date().toISOString() });
    if (appData.activity.length > 30) appData.activity = appData.activity.slice(0, 30);
}

function updateStreak() {
    const today = todayKey();
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yk = yesterday.toISOString().split('T')[0];

    if (appData.streak.lastDate === today) return;
    if (appData.streak.lastDate === yk) appData.streak.count += 1;
    else appData.streak.count = 1;
    appData.streak.lastDate = today;
    saveData();
    $('streakNum').textContent = appData.streak.count;
}

// ==========================================
// DATA EXPORT / IMPORT
// ==========================================
function exportData() {
    const blob = new Blob([JSON.stringify(appData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `interview-prep-${currentUser.username}-${todayKey()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast('Data exported');
}

function importData(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        try {
            const imported = JSON.parse(e.target.result);
            if (imported.sections && imported.todos) {
                appData = imported;
                saveData();
                renderCurrentView();
                toast('Data imported!');
            } else {
                toast('Invalid file format');
            }
        } catch { toast('Failed to parse file'); }
    };
    reader.readAsText(file);
    event.target.value = '';
}

function clearAllData() {
    if (!confirm('Delete ALL your data? This cannot be undone.')) return;
    if (!confirm('Are you sure? This will erase everything.')) return;
    appData = defaultData();
    saveData();
    renderCurrentView();
    toast('All data cleared');
}

// ==========================================
// INIT
// ==========================================
function init() {
    checkSession();
    setInterval(checkCustomReminders, 60000);
}

// Tab key support in code textareas
document.addEventListener('keydown', e => {
    if (e.key === 'Tab' && e.target.id === 'inlineSnippetContent') {
        e.preventDefault();
        const s = e.target.selectionStart;
        e.target.value = e.target.value.substring(0, s) + '    ' + e.target.value.substring(e.target.selectionEnd);
        e.target.selectionStart = e.target.selectionEnd = s + 4;
    }
});

// Enter key on login
document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.target.id === 'loginUsername' || e.target.id === 'loginPassphrase')) {
        handleLogin();
    }
});

init();
