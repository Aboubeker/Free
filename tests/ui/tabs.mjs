import { Window } from 'happy-dom';
import './prepare.mjs';
const BASE = 'http://127.0.0.1:8080';
const win = new Window({ url: BASE + '/', settings: { fetch: { disableSameOriginPolicy: true } } });
Object.assign(globalThis, { window: win, document: win.document, localStorage: win.localStorage,
  HTMLElement: win.HTMLElement, Element: win.Element, Node: win.Node, Event: win.Event,
  CustomEvent: win.CustomEvent, FormData: win.FormData, URL: win.URL,
  AbortController: win.AbortController, FileReader: win.FileReader });
Object.defineProperty(globalThis, 'navigator', { value: win.navigator, configurable: true });
globalThis.fetch = (...a) => win.fetch(...a);
document.body.innerHTML = '<div id="app"></div>';
const errors = [];
process.on('unhandledRejection', (e) => errors.push(String(e?.message || e)));
win.addEventListener('error', (e) => errors.push(String(e?.message || e)));

const editorMod = await import('./mods/editor.mjs');
const boot = await (await fetch(BASE + '/api/bootstrap')).json();
state0: {
  const gen = await (await fetch(BASE + '/api/generate', { method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ brief: { title: 'Dossier test', client: 'Client Test',
      project: 'Projet', industry: 'Industrie', stack: 'Azure, Kubernetes' }, save: true }) })).json();
  var doc = gen.document, quality = gen.quality;
}
const state = { doc, quality, catalog: boot.catalog, editorTab: 'content' };
const ctx = { state, catalog: boot.catalog, version: '1.0', go: () => {},
  getDoc: () => state.doc, getQuality: () => state.quality,
  saveState: () => {}, setDoc: (d, q) => { state.doc = d; state.quality = q; },
  refreshDoc: (d, q) => { state.doc = d; state.quality = q; }, openProject: async () => {} };
const app = document.getElementById('app');
const view = editorMod.editorView(ctx);
app.append(view);
await new Promise((r) => setTimeout(r, 2500));

for (const tab of ['Contenu', 'Identité', 'Style', 'Options', 'Qualité']) {
  const btn = [...view.querySelectorAll('button')].find((b) => b.textContent.trim() === tab);
  if (!btn) { console.log('✗ onglet introuvable :', tab); continue; }
  btn.click();
  await new Promise((r) => setTimeout(r, 400));
  const text = view.textContent;
  const markers = {
    Contenu: 'Plan du document', Identité: 'Informations du document',
    Style: 'Palette', Options: 'Éléments inclus', Qualité: 'Score de complétude',
  };
  console.log(text.includes(markers[tab]) ? `✓ onglet ${tab}` : `✗ onglet ${tab} (contenu absent)`);
}

// interaction : ajout d'un bloc paragraphe puis vérification
const addBtn = [...view.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Contenu');
addBtn.click(); await new Promise((r) => setTimeout(r, 400));
const before = state.doc.sections[0].blocks.length;
const paraBtn = [...view.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Paragraphe');
paraBtn.click(); await new Promise((r) => setTimeout(r, 300));
console.log(before + 1 === state.doc.sections[0].blocks.length
  ? `✓ ajout de bloc (${before} → ${state.doc.sections[0].blocks.length})` : '✗ ajout de bloc');

console.log('\nERREURS JS :', errors.length ? errors : 'aucune');
process.exit(errors.length ? 1 : 0);
