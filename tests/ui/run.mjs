import { Window } from 'happy-dom';
import './prepare.mjs';
const BASE = 'http://127.0.0.1:8080';
const win = new Window({ url: BASE + '/', width: 1440, height: 900,
  settings: { fetch: { disableSameOriginPolicy: true } } });
globalThis.window = win;
globalThis.document = win.document;
Object.defineProperty(globalThis, 'navigator', { value: win.navigator, configurable: true });
globalThis.localStorage = win.localStorage;
globalThis.HTMLElement = win.HTMLElement;
globalThis.Element = win.Element;
globalThis.Node = win.Node;
globalThis.Event = win.Event;
globalThis.CustomEvent = win.CustomEvent;
globalThis.FormData = win.FormData;
globalThis.URL = win.URL;
globalThis.AbortController = win.AbortController;
globalThis.FileReader = win.FileReader;
globalThis.fetch = (...a) => win.fetch(...a);
globalThis.getComputedStyle = win.getComputedStyle.bind(win);

document.body.innerHTML = '<div id="app" class="app"></div>';
const errors = [];
process.on('unhandledRejection', (e) => errors.push('unhandled: ' + (e?.message || e)));
win.addEventListener('error', (e) => errors.push('error: ' + (e?.message || e)));

const lib = await import('./mods/lib.mjs');
const briefMod = await import('./mods/brief.mjs');
const editorMod = await import('./mods/editor.mjs');
const projectsMod = await import('./mods/projects.mjs');
const exportsMod = await import('./mods/exports.mjs');
const settingsMod = await import('./mods/settings.mjs');
const blocksMod = await import('./mods/blocks.mjs');
console.log('✓ 7 modules importés nativement');

const boot = await (await fetch(BASE + '/api/bootstrap')).json();
console.log('✓ bootstrap :', boot.catalog.palettes.length, 'palettes ·', boot.catalog.typographies.length,
            'typos ·', boot.playbooks.length, 'playbooks · moteur', boot.ai.provider);

const state = { doc: null, quality: null, view: 'brief', catalog: boot.catalog };
const ctx = { state, catalog: boot.catalog, version: boot.version,
  go: (v) => { state.view = v; }, getDoc: () => state.doc, getQuality: () => state.quality,
  saveState: () => {}, setDoc: (d, q) => { state.doc = d; state.quality = q; },
  refreshDoc: (d, q) => { state.doc = d; state.quality = q; }, openProject: async () => {} };

const app = document.getElementById('app');
// vue 1 : assistant
const v1 = briefMod.briefView(ctx);
app.append(v1);
console.log('✓ vue assistant :', v1.querySelectorAll('input,textarea,select').length, 'champs');

// remplissage du brief
const inputs = [...v1.querySelectorAll('input')];
inputs[0].value = 'Dossier de livraison — Portail Client Omnicanal';
inputs[0].dispatchEvent(new win.Event('input'));
inputs[1].value = 'Banque Atlas';
inputs[1].dispatchEvent(new win.Event('input'));
inputs[2].value = 'Portail Client Omnicanal';
inputs[2].dispatchEvent(new win.Event('input'));

const nextBtn = [...v1.querySelectorAll('button')].find((b) => b.textContent.includes('Continuer'));
nextBtn.click();
await new Promise((r) => setTimeout(r, 2200));
const v2 = app.firstElementChild;
console.log('✓ étape 2 (structure) :', v2.textContent.includes('Structure proposée') ? 'affichée' : 'ÉCHEC',
            '·', v2.querySelectorAll('.section-row').length, 'sections listées');

// génération réelle + éditeur
const gen = await (await fetch(BASE + '/api/generate', { method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ brief: JSON.parse(JSON.stringify(state.brief || {})), save: true }) })).json();
state.doc = gen.document; state.quality = gen.quality;
const v3 = editorMod.editorView(ctx);
app.append(v3);
console.log('✓ éditeur :', v3.querySelectorAll('.section-row').length, 'sections ·',
            v3.textContent.includes('Contenu') ? 'onglets OK' : 'onglets manquants');
await new Promise((r) => setTimeout(r, 3000));
const imgs = [...v3.querySelectorAll('img')].filter((i) => String(i.src).startsWith('data:image'));
console.log('✓ aperçu A4 :', imgs.length ? `image ${Math.round(imgs[0].src.length / 1024)} Ko` : 'AUCUNE');

const v4 = projectsMod.projectsView(ctx);
app.append(v4);
await new Promise((r) => setTimeout(r, 1500));
console.log('✓ vue projets :', v4.querySelectorAll('.project-thumb').length, 'livrables');

const v5 = exportsMod.exportsView(ctx);
app.append(v5);
await new Promise((r) => setTimeout(r, 1200));
console.log('✓ vue médias/exports :', v5.querySelectorAll('.card').length, 'cartes');

const v6 = settingsMod.settingsView(ctx);
app.append(v6);
await new Promise((r) => setTimeout(r, 900));
console.log('✓ vue paramètres :', v6.textContent.includes('Moteur de génération') ? 'rendue' : 'ÉCHEC');

console.log('\nERREURS JS :', errors.length ? errors : 'aucune');
process.exit(errors.length ? 1 : 0);
