/* Delivra — point d'entrée de l'interface : navigation, état global, thème. */
import { h, clear, icon, api, toast, store, initTheme, applyTheme } from './lib.js';
import { briefView } from './brief.js';
import { editorView } from './editor.js';
import { projectsView } from './projects.js';
import { exportsView } from './exports.js';
import { settingsView } from './settings.js';

const NAV = [
  { key: 'brief', label: 'Nouveau livrable', icon: 'sparkle' },
  { key: 'projects', label: 'Mes livrables', icon: 'folder' },
  { key: 'editor', label: 'Éditeur', icon: 'doc' },
  { key: 'exports', label: 'Médias & exports', icon: 'download' },
];

const state = {
  view: store.load().view || 'brief',
  doc: null,
  quality: null,
  catalog: null,
  ...store.load(),
};
const saveState = (patch) => { Object.assign(state, patch); store.save(patch); };

const appEl = document.getElementById('app');
const sidebar = h('aside', { class: 'sidebar' });
const main = h('main', { class: 'main' });
appEl.append(sidebar, main);

/* -------------------------------------------------------------- navigation */
function go(view) {
  state.view = view;
  store.save({ view });
  render();
}

function renderSidebar() {
  clear(sidebar);
  sidebar.append(
    h('div', { class: 'brand' },
      h('div', { class: 'brand-mark' }, 'D'),
      h('div', {},
        h('div', { class: 'brand-name' }, 'Delivra'),
        h('div', { class: 'brand-sub' }, 'agent de livrables'))),
    h('div', { class: 'sidebar-scroll' },
      h('div', { class: 'nav' },
        ...NAV.map((n) => h('button', {
          class: 'nav-item' + (state.view === n.key ? ' active' : ''),
          onclick: () => go(n.key),
          disabled: n.key === 'editor' && !state.doc,
          style: n.key === 'editor' && !state.doc ? { opacity: .45, cursor: 'not-allowed' } : {},
        }, icon(n.icon, 18), h('span', {}, n.label)))),
      h('div', { class: 'nav-sep' }),
      h('div', { class: 'nav-title' }, 'En cours'),
      state.doc ? h('div', { style: { padding: '0 12px' } },
        h('button', {
          class: 'nav-item', style: { padding: '8px 10px' },
          onclick: () => go('editor'),
        },
        h('span', {
          style: {
            width: '8px', height: '8px', borderRadius: '2px', flex: 'none',
            background: 'var(--accent)',
          },
        }),
        h('span', { style: { fontSize: '12.5px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } },
          state.doc.meta?.title || 'Sans titre'))) : h('div', { style: { padding: '0 14px' }, class: 'small muted' }, 'Aucun document ouvert')),
    h('div', { class: 'sidebar-foot' },
      h('button', { class: 'btn btn-icon btn-ghost', id: 'theme-toggle', title: 'Thème clair / sombre', onclick: toggleTheme }),
      h('div', { style: { flex: 1 } },
        h('div', { class: 'small', style: { fontWeight: 650 } }, 'v1.0.0'),
        h('span', {}, 'Hors ligne')),
      h('button', { class: 'btn btn-icon btn-ghost', title: 'Paramètres', onclick: () => go('settings') }, icon('settings', 17))));
  applyTheme(document.documentElement.dataset.theme || 'dark');
}

function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
}

/* -------------------------------------------------------------- contexte */
const ctx = {
  state,
  go,
  catalog: null,
  version: '1.0.0',
  getDoc: () => state.doc,
  getQuality: () => state.quality,
  saveState,
  setDoc: (doc, quality) => {
    state.doc = doc;
    if (quality) state.quality = quality;
    renderSidebar();
  },
  refreshDoc: (doc, quality) => {
    state.doc = doc;
    state.quality = quality || state.quality;
    state.brief = null;
    state.plan = null;
    renderSidebar();
  },
  openProject: async (id) => {
    try {
      const r = await api(`/api/projects/${id}`);
      state.doc = r.document;
      state.quality = r.quality;
      state.currentSection = 0;
      state.editorTab = 'content';
      go('editor');
    } catch (e) { toast(e.message, 'err'); }
  },
};

/* -------------------------------------------------------------- rendu */
function render() {
  renderSidebar();
  clear(main);
  let view;
  if (state.view === 'brief') view = briefView(ctx);
  else if (state.view === 'projects') view = projectsView(ctx);
  else if (state.view === 'exports') view = exportsView(ctx);
  else if (state.view === 'settings') view = settingsView(ctx);
  else if (state.view === 'editor') view = editorView(ctx);
  else view = briefView(ctx);
  if (state.view === 'editor') {
    main.style.overflow = 'hidden';
    main.append(view);
  } else {
    main.style.overflow = 'hidden';
    const scroll = h('div', { class: 'content scroll-thin' }, view);
    main.append(scroll);
  }
}

/* -------------------------------------------------------------- démarrage */
(async () => {
  initTheme();
  try {
    const boot = await api('/api/bootstrap');
    state.catalog = boot.catalog;
    state.playbooks = boot.playbooks;
    ctx.catalog = boot.catalog;
    ctx.version = boot.version;
    if (!boot.ai.available) state.aiLocal = true;
  } catch (e) {
    toast('Le serveur Delivra ne répond pas : ' + e.message, 'err', 9000);
  }
  if (state.doc) {
    try {
      const r = await api(`/api/projects/${state.doc.id}`);
      state.doc = r.document;
      state.quality = r.quality;
    } catch { state.doc = null; }
  }
  render();
})();

/* raccourcis clavier */
window.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
    e.preventDefault();
    document.querySelector('.topbar button[title], .topbar .btn')?.click?.();
  }
});

/* exposition pour le débogage local */
window.delivra = { state, go, api };
