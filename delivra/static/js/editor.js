/* Delivra — éditeur de livrable : identité, structure, style, contenu,
   plus un aperçu A4 fidèle rendu côté serveur (pypdfium2). */
import {
  h, clear, icon, api, toast, debounce, confirmBox, esc, store, paletteSwatches, download,
} from './lib.js';
import { BLOCK_LIBRARY, blankBlock, blockEditor } from './blocks.js';

const TABS = [
  { key: 'content', label: 'Contenu', icon: 'doc' },
  { key: 'identity', label: 'Identité', icon: 'user' },
  { key: 'style', label: 'Style', icon: 'palette' },
  { key: 'options', label: 'Options', icon: 'settings' },
  { key: 'quality', label: 'Qualité', icon: 'check' },
];

export function editorView(ctx) {
  const { state, go, setDoc, refreshDoc, catalog } = ctx;
  const cfg = state.catalog || catalog;
  let doc = ctx.getDoc();
  if (!doc) {
    return h('div', { class: 'page' }, h('div', { class: 'card' },
      h('h2', { class: 'card-title' }, 'Aucun document ouvert'),
      h('p', { class: 'card-sub' }, 'Créez un livrable via l’assistant ou choisissez un projet existant.'),
      h('button', { class: 'btn btn-primary', onclick: () => go('brief') }, icon('sparkle', 15), 'Créer un livrable')));
  }
  let tab = state.editorTab || 'content';
  let currentSection = state.currentSection || 0;
  let previewPage = 1;
  let previewTotal = 1;
  let saving = false;
  let lastSaved = null;

  const root = h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(380px,44%)', height: '100%' } });
  const leftPane = h('div', { class: 'content scroll-thin' });
  const previewPane = h('div', { class: 'preview-wrap scroll-thin' });
  root.append(leftPane, previewPane);

  const saveNow = async () => {
    saving = true; renderSaveState();
    try {
      const r = await api(`/api/projects/${doc.id}`, { method: 'PUT', body: { document: doc } });
      doc = r.document; lastSaved = new Date();
      ctx.setDoc(doc, r.quality);
    } catch (e) { toast('Sauvegarde impossible : ' + e.message, 'err'); }
    saving = false; renderSaveState();
  };
  const autosave = debounce(saveNow, 900);
  const changed = () => { autosave(); schedulePreview(); };

  const saveState = h('span', { class: 'small muted' }, '');
  const renderSaveState = () => {
    clear(saveState);
    if (saving) saveState.append('Enregistrement…');
    else if (lastSaved) saveState.append(`Enregistré à ${lastSaved.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`);
    else saveState.append('');
  };

  /* ------------------------------------------------------------- aperçu */
  const previewScroll = h('div', { class: 'preview-scroll scroll-thin' });
  const previewInfo = h('span', { class: 'small muted' }, '');
  let previewBusy = false;
  let previewPending = false;

  const renderPreview = async () => {
    if (previewBusy) { previewPending = true; return; }
    previewBusy = true;
    try {
      const r = await api('/api/preview', { method: 'POST', body: { document: doc, pages: [previewPage], scale: 1.5 } });
      previewTotal = r.total || 1;
      clear(previewScroll);
      if (!r.pages.length) {
        previewScroll.append(h('div', { class: 'small muted' }, 'Aperçu indisponible.'));
      } else {
        for (const pg of r.pages) {
          previewScroll.append(h('div', { class: 'page-sheet' },
            h('img', { src: pg.image, alt: `Page ${pg.page}` }),
            h('span', { class: 'page-label' }, `page ${pg.page} / ${pg.total}`)));
        }
      }
      clear(previewInfo).append(`${previewPage} / ${previewTotal}`);
    } catch (e) {
      clear(previewScroll).append(h('div', { class: 'card', style: { maxWidth: '420px' } },
        h('strong', {}, 'Aperçu impossible'), h('p', { class: 'small muted' }, e.message)));
    } finally {
      previewBusy = false;
      if (previewPending) { previewPending = false; renderPreview(); }
    }
  };
  const schedulePreview = debounce(renderPreview, 1100);

  const previewHead = h('div', { class: 'preview-head' },
    icon('eye', 16),
    h('strong', { class: 'small' }, 'Aperçu'),
    h('div', { style: { flex: 1 } }),
    h('button', { class: 'icon-btn', title: 'Page précédente', onclick: () => { previewPage = Math.max(1, previewPage - 1); renderPreview(); } }, icon('back', 15)),
    previewInfo,
    h('button', { class: 'icon-btn', title: 'Page suivante', onclick: () => { previewPage = Math.min(previewTotal, previewPage + 1); renderPreview(); } }, h('span', { style: { transform: 'rotate(180deg)', display: 'inline-flex' } }, icon('back', 15))),
    h('button', { class: 'btn btn-sm btn-ghost', onclick: renderPreview }, icon('refresh', 14), 'Actualiser'));

  previewPane.append(previewHead, previewScroll);

  /* ------------------------------------------------------------- onglets */
  const tabBar = h('div', { class: 'row', style: { padding: '12px 26px 0', gap: '4px', flexWrap: 'wrap' } });
  const body = h('div', { class: 'page', style: { paddingTop: '14px' } });

  const renderTabs = () => {
    clear(tabBar);
    TABS.forEach((t) => tabBar.append(h('button', {
      class: 'nav-item' + (tab === t.key ? ' active' : ''),
      style: { width: 'auto', padding: '7px 12px' },
      onclick: () => { tab = t.key; state.editorTab = tab; draw(); },
    }, icon(t.icon, 15), h('span', {}, t.label))));
    tabBar.append(h('div', { style: { flex: 1 } }));
    tabBar.append(saveState);
  };

  /* ------------------------------------------------------------- onglet contenu */
  const sectionList = h('div', { class: 'stack', style: { gap: '6px' } });

  const renderSections = () => {
    clear(sectionList);
    (doc.sections || []).forEach((sec, i) => {
      const active = i === currentSection;
      sectionList.append(h('div', {
        class: 'section-row' + (active ? ' active' : ''),
        style: active ? { borderColor: 'var(--primary)', background: 'var(--primary-soft)' } : {},
        onclick: () => { currentSection = i; state.currentSection = i; draw(); },
      },
      h('span', { class: 'grip' }, icon('grip', 15)),
      h('span', { class: 'num' }, String(i + 1).padStart(2, '0')),
      h('div', { class: 'name' }, sec.title || 'Section'),
      h('span', { class: 'chip small' }, `${(sec.blocks || []).length} blocs`),
      h('button', {
        class: 'icon-btn', title: 'Monter',
        onclick: (e) => { e.stopPropagation(); if (i === 0) return; [doc.sections[i - 1], doc.sections[i]] = [doc.sections[i], doc.sections[i - 1]]; currentSection = i - 1; changed(); draw(); },
      }, icon('arrowUp', 13)),
      h('button', {
        class: 'icon-btn', title: 'Descendre',
        onclick: (e) => { e.stopPropagation(); if (i === doc.sections.length - 1) return; [doc.sections[i + 1], doc.sections[i]] = [doc.sections[i], doc.sections[i + 1]]; currentSection = i + 1; changed(); draw(); },
      }, icon('arrowDown', 13)),
      h('button', {
        class: 'icon-btn', title: 'Supprimer',
        onclick: (e) => {
          e.stopPropagation();
          confirmBox('Supprimer la section', `« ${sec.title} » et son contenu seront retirés du document.`, () => {
            doc.sections.splice(i, 1); currentSection = Math.max(0, currentSection - 1); changed(); draw();
          });
        },
      }, icon('trash', 13))));
    });
    sectionList.append(h('div', { class: 'row', style: { marginTop: '8px' } },
      h('button', {
        class: 'btn btn-sm', onclick: () => {
          doc.sections.push({
            id: `sec-${Math.random().toString(36).slice(2, 9)}`,
            title: 'Nouvelle section', kicker: 'Section', intro: '',
            page_break: true, blocks: [],
          });
          currentSection = doc.sections.length - 1; changed(); draw();
        },
      }, icon('plus', 14), 'Section'),
      h('button', {
        class: 'btn btn-sm btn-ghost', onclick: async () => {
          try {
            const r = await api('/api/plan', { method: 'POST', body: {
              title: doc.meta.title, project: doc.meta.project, client: doc.meta.client,
              industry: doc.meta.industry, context: doc.meta.executive_summary, playbook: doc.meta.playbook,
            } });
            doc.sections.push({
              id: `sec-${Math.random().toString(36).slice(2, 9)}`,
              title: 'Section générée', kicker: 'Agent', intro: '',
              page_break: true, blocks: [],
            });
            const m = (await import('./lib.js')).modal('Sections disponibles',
              h('div', { class: 'stack' }, ...(r.pool || []).map((s) => h('button', {
                class: 'btn', style: { justifyContent: 'flex-start' },
                onclick: () => { doc.sections[doc.sections.length - 1].title = s.title; changed(); m.close(); draw(); },
              }, s.title))));
          } catch (e) { toast(e.message, 'err'); }
        },
      }, icon('sparkle', 14), 'Suggestion')));
  };

  const sectionEditor = () => {
    const sec = doc.sections[currentSection];
    if (!sec) return h('div', { class: 'card' }, h('p', { class: 'muted' }, 'Sélectionnez une section.'));
    const wrap = h('div', { class: 'stack' });
    const titleInput = h('input', { class: 'input', value: sec.title || '', oninput: (e) => { sec.title = e.target.value; changed(); renderSections(); } });
    const kickerInput = h('input', { class: 'input', value: sec.kicker || '', oninput: (e) => { sec.kicker = e.target.value; changed(); } });
    const intro = h('textarea', { class: 'textarea', rows: 3, oninput: (e) => { sec.intro = e.target.value; changed(); } });
    intro.value = sec.intro || '';

    wrap.append(h('div', { class: 'card' },
      h('div', { class: 'row-2' },
        h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Titre de la section'), titleInput),
        h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Chapeau (kicker)'), kickerInput)),
      h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Introduction'), intro)));

    const blocksWrap = h('div', {});
    const renderBlocks = () => {
      clear(blocksWrap);
      (sec.blocks || []).forEach((block, bi) => {
        blocksWrap.append(blockEditor(block, {
          onChange: changed,
          onReplace: () => { renderBlocks(); },
          onDelete: () => { sec.blocks.splice(bi, 1); changed(); renderBlocks(); },
          onMove: (dir) => {
            const j = bi + dir;
            if (j < 0 || j >= sec.blocks.length) return;
            [sec.blocks[bi], sec.blocks[j]] = [sec.blocks[j], sec.blocks[bi]];
            changed(); renderBlocks();
          },
        }));
      });
      if (!(sec.blocks || []).length) {
        blocksWrap.append(h('div', { class: 'dropzone', style: { marginBottom: '10px' } }, 'Aucun bloc — ajoutez du contenu ci-dessous.'));
      }
      const lib = h('div', { class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '6px' } },
        ...BLOCK_LIBRARY.map((b) => h('button', {
          class: 'btn btn-sm', style: { justifyContent: 'flex-start' },
          title: b.hint || b.label,
          onclick: () => {
            sec.blocks = sec.blocks || [];
            sec.blocks.push(blankBlock(b.type));
            changed(); renderBlocks();
          },
        }, icon(b.icon, 14), b.label)));
      blocksWrap.append(h('div', { class: 'card', style: { padding: '12px' } },
        h('div', { class: 'small muted', style: { marginBottom: '8px', fontWeight: 700 } }, 'Ajouter un bloc'), lib));
    };
    renderBlocks();
    wrap.append(blocksWrap);
    return wrap;
  };

  const contentTab = () => h('div', { class: 'stack' },
    h('div', { class: 'card' },
      h('div', { class: 'row', style: { marginBottom: '10px' } },
        h('h3', { class: 'card-title', style: { margin: 0 } }, 'Plan du document'),
        h('div', { style: { flex: 1 } }),
        h('span', { class: 'small muted' }, `${(doc.sections || []).length} sections`)),
      sectionList),
    sectionEditor());

  /* ------------------------------------------------------------- onglet identité */
  const identityTab = () => {
    const meta = doc.meta || (doc.meta = {});
    const f = (label, key, ph, area) => {
      const el = area ? h('textarea', { class: 'textarea', rows: 4, placeholder: ph || '' })
        : h('input', { class: 'input', placeholder: ph || '' });
      el.value = meta[key] ?? '';
      el.addEventListener('input', () => { meta[key] = el.value; changed(); });
      return h('label', { class: 'field' }, h('span', { class: 'lbl' }, label), el);
    };
    const uploader = (key, label, hint) => {
      const box = h('div');
      const draw = () => {
        clear(box);
        const val = key.startsWith('brand.') ? (doc.brand || {})[key.split('.')[1]] : meta[key];
        if (val) {
          box.append(h('div', { class: 'upload-preview' },
            h('img', { src: `/api/${val}`, alt: '' }),
            h('div', { class: 'small muted', style: { flex: 1 } }, 'Importé'),
            h('button', {
              class: 'btn btn-sm btn-ghost',
              onclick: () => {
                if (key.startsWith('brand.')) doc.brand[key.split('.')[1]] = '';
                else meta[key] = '';
                changed(); draw();
              },
            }, 'Retirer')));
        } else {
          const input = h('input', { type: 'file', accept: 'image/*', style: { display: 'none' }, onchange: async (e) => {
            const file = e.target.files[0]; if (!file) return;
            const fd = new FormData(); fd.append('file', file); fd.append('kind', 'image');
            try {
              const r = await api('/api/upload', { method: 'POST', body: fd });
              if (key.startsWith('brand.')) { doc.brand = doc.brand || {}; doc.brand[key.split('.')[1]] = r.asset; }
              else meta[key] = r.asset;
              changed(); draw(); toast('Image importée', 'ok');
            } catch (err) { toast(err.message, 'err'); }
          } });
          box.append(h('div', {
            class: 'dropzone', onclick: () => input.click(),
            ondragover: (e) => { e.preventDefault(); e.currentTarget.classList.add('hot'); },
            ondragleave: (e) => e.currentTarget.classList.remove('hot'),
            ondrop: (e) => { e.preventDefault(); e.currentTarget.classList.remove('hot'); input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change')); },
          }, icon('upload', 16), h('div', {}, label), hint ? h('div', { class: 'hint' }, hint) : null), input);
        }
      };
      draw();
      return box;
    };
    return h('div', { class: 'grid grid-2' },
      h('div', { class: 'stack' },
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Informations du document'),
          f('Titre', 'title', 'Dossier de livraison — …'),
          f('Sous-titre', 'subtitle', 'Solution déployée pour…'),
          h('div', { class: 'row-2' }, f('Client', 'client', 'Nom du client'), f('Projet / solution', 'project', 'Nom de la solution')),
          h('div', { class: 'row-2' }, f('Secteur', 'industry', 'Secteur d’activité'), f('Référence', 'reference', 'LIV-2026-014')),
          h('div', { class: 'row-2' }, f('Version', 'version', '1.0'), f('Date', 'date', '24 novembre 2026')),
          h('div', { class: 'row-2' }, f('Auteur', 'author', 'Prénom Nom'), f('Fonction', 'author_role', 'Architecte solutions')),
          h('div', { class: 'row-2' }, f('Destinataire', 'recipient', 'Direction …'), f('Confidentialité', 'confidentiality', 'Confidentiel')),
          f('Résumé exécutif', 'executive_summary', 'Synthèse de 3 à 6 lignes…', true),
          h('div', { class: 'row', style: { marginTop: '4px' } },
            h('button', {
              class: 'btn btn-sm btn-ghost',
              onclick: async (e) => {
                const btn = e.currentTarget; btn.disabled = true;
                try {
                  const r = await api('/api/rewrite', { method: 'POST', body: { text: meta.executive_summary || '', tone: doc.options?.tone || 'professionnel' } });
                  meta.executive_summary = r.text; changed(); draw();
                  toast('Résumé reformulé', 'ok');
                } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
              },
            }, icon('sparkle', 14), 'Améliorer le résumé')))),
      h('div', { class: 'stack' },
        h('div', { class: 'card' },
          h('h3', { class: 'card-title', style: { marginBottom: '12px' } }, 'Logos et couverture'),
          h('span', { class: 'lbl', style: { display: 'block', marginBottom: '6px' } }, 'Logo de l’entreprise'),
          uploader('brand.logo', 'Importer le logo', 'PNG ou SVG, fond transparent'),
          h('div', { style: { height: '14px' } }),
          h('span', { class: 'lbl', style: { display: 'block', marginBottom: '6px' } }, 'Logo client'),
          uploader('brand.client_logo', 'Importer le logo client'),
          h('div', { style: { height: '14px' } }),
          h('span', { class: 'lbl', style: { display: 'block', marginBottom: '6px' } }, 'Image de couverture'),
          uploader('brand.cover_image', 'Importer un visuel de fond')),
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Jeu de couleurs'),
          h('p', { class: 'card-sub' }, 'Les couleurs se propagent au document entier.'),
          h('div', { class: 'row-2' },
            h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Couleur principale'),
              h('input', { type: 'color', class: 'input', style: { height: '40px', padding: '4px' }, value: doc.style?.primary || '#0B5FFF',
                oninput: (e) => { doc.style = { ...(doc.style || {}), primary: e.target.value }; changed(); } })),
            h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Couleur d’accent'),
              h('input', { type: 'color', class: 'input', style: { height: '40px', padding: '4px' }, value: doc.style?.accent || '#00C2A8',
                oninput: (e) => { doc.style = { ...(doc.style || {}), accent: e.target.value }; changed(); } }))))));
  };

  /* ------------------------------------------------------------- onglet style */
  const styleTab = () => {
    const style = doc.style || (doc.style = {});
    const palettes = cfg.palettes || [];
    const fonts = cfg.typographies || [];
    return h('div', { class: 'grid grid-2' },
      h('div', { class: 'card' },
        h('h3', { class: 'card-title' }, 'Palette'),
        h('p', { class: 'card-sub' }, 'Choisissez une harmonie de couleurs professionnelle.'),
        h('div', { class: 'grid palette-grid', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(120px,1fr))' } },
          ...palettes.map((p) => h('button', {
            class: 'palette-card' + ((style.palette || 'ocean') === p.key ? ' active' : ''),
            onclick: () => { style.palette = p.key; style.primary = null; style.accent = null; changed(); draw(); },
          }, h('div', { class: 'swatches' }, ...paletteSwatches(p)), h('div', { class: 'palette-name' }, p.label))))),
      h('div', { class: 'stack' },
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Typographie'),
          h('p', { class: 'card-sub' }, 'Polices embarquées — rendu identique à l’écran et à l’impression.'),
          h('div', { class: 'choice-grid' },
            ...fonts.map((f) => h('button', {
              class: 'font-card' + ((style.typography || 'manrope') === f.key ? ' active' : ''),
              onclick: () => { style.typography = f.key; changed(); draw(); },
            }, h('div', { class: 'font-sample ' + (['serif', 'serif-mix'].includes(f.key) ? 'serif' : ['sora', 'technical'].includes(f.key) ? 'display' : '') }, 'Aa Dossier 2026'),
              h('div', { class: 'font-meta' }, f.label))))),
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Mise en page'),
          h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Densité du texte'),
            (() => {
              const el = h('select', { class: 'select', onchange: (e) => { style.density = e.target.value; changed(); } },
                ...[['compact', 'Compact'], ['normal', 'Équilibré'], ['aere', 'Aéré']].map(([v, l]) => h('option', { value: v, selected: (style.density || 'normal') === v }, l)));
              el.value = style.density || 'normal';
              return el;
            })()),
          h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Format de page'),
            (() => {
              const el = h('select', { class: 'select', onchange: (e) => { style.paper = e.target.value; changed(); } },
                ...[['A4', 'A4 · 210 × 297 mm'], ['Letter', 'US Letter · 8.5 × 11 in']].map(([v, l]) => h('option', { value: v, selected: (style.paper || 'A4') === v }, l)));
              el.value = style.paper || 'A4';
              return el;
            })()),
          h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Style de couverture'),
            (() => {
              const el = h('select', { class: 'select', onchange: (e) => { style.cover_style = e.target.value; changed(); } },
                ...[['deep', 'Pleine couleur'], ['gradient', 'Dégradé'], ['minimal', 'Minimaliste']].map(([v, l]) => h('option', { value: v, selected: (style.cover_style || '') === v }, l)));
              el.value = style.cover_style || '';
              return el;
            })()))));
  };

  /* ------------------------------------------------------------- onglet options */
  const optionsTab = () => {
    const o = doc.options || (doc.options = {});
    const toggle = (key, label, hint) => h('label', {
      class: 'row', style: { padding: '10px 0', borderBottom: '1px solid var(--line-soft)', cursor: 'pointer' },
    },
    h('input', { type: 'checkbox', checked: o[key] !== false && o[key] !== '', onchange: (e) => { o[key] = e.target.checked; changed(); } }),
    h('div', { style: { flex: 1 } }, h('div', { style: { fontWeight: 650, fontSize: '13px' } }, label),
      hint ? h('div', { class: 'small muted' }, hint) : null));
    return h('div', { class: 'grid grid-2' },
      h('div', { class: 'card' },
        h('h3', { class: 'card-title' }, 'Éléments inclus'),
        toggle('cover', 'Page de couverture', 'Logo, titre, client, date, référence'),
        toggle('toc', 'Sommaire paginé', 'Numéros de page calculés automatiquement'),
        toggle('header', 'En-tête', 'Client et référence sur chaque page'),
        toggle('page_numbers', 'Numérotation des pages'),
        toggle('summary_box', 'Encadré de synthèse', 'Mise en avant du résumé exécutif'),
        toggle('signature', 'Page de validation', 'Bloc de signature en fin de document'),
        toggle('annexes', 'Fiche de contrôle', 'Annexe avec le score de complétude')),
      h('div', { class: 'card' },
        h('h3', { class: 'card-title' }, 'Habillage'),
        h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Filigrane'),
          h('input', { class: 'input', placeholder: 'Ex. BROUILLON, CONFIDENTIEL', value: o.watermark || '',
            oninput: (e) => { o.watermark = e.target.value; changed(); } })),
        h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Texte de pied de page'),
          h('input', { class: 'input', value: o.footer_text || '', oninput: (e) => { o.footer_text = e.target.value; changed(); } })),
        h('div', { class: 'divider' }),
        h('h3', { class: 'card-title' }, 'Text to image'),
        h('p', { class: 'card-sub' }, 'Génère un visuel de couverture abstrait à partir du style courant.'),
        h('div', { class: 'row' },
          h('button', {
            class: 'btn btn-sm', onclick: async (e) => {
              const btn = e.currentTarget; btn.disabled = true;
              try {
                const r = await api('/api/visual', { method: 'POST', body: { kind: 'cover', style: doc.style || {} } });
                doc.brand = doc.brand || {}; doc.brand.cover_image = r.asset; changed();
                toast('Visuel de couverture généré', 'ok');
              } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
            },
          }, icon('image', 14), 'Visuel de couverture'),
          h('button', {
            class: 'btn btn-sm', onclick: async (e) => {
              const btn = e.currentTarget; btn.disabled = true;
              try {
                const r = await api('/api/visual', { method: 'POST', body: { kind: 'architecture', style: doc.style || {},
                  layers: (doc.sections || []).flatMap((s) => (s.blocks || []).filter((b) => b.type === 'architecture')).flatMap((b) => b.layers || []) } });
                download(`/api/${r.asset}`, 'architecture.png');
              } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
            },
          }, icon('layers', 14), 'Schéma PNG'))));
  };

  /* ------------------------------------------------------------- onglet qualité */
  const qualityTab = () => {
    const q = ctx.getQuality() || { score: 0, grade: '—', checks: [], words: 0, sections: 0, blocks: 0 };
    return h('div', { class: 'grid', style: { gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)' } },
      h('div', { class: 'card' },
        h('h3', { class: 'card-title' }, 'Score de complétude'),
        h('div', { class: 'score-ring', style: { margin: '12px 0' } },
          h('div', { class: 'ring', style: { '--v': q.score } }, h('span', {}, String(q.score))),
          h('div', {}, h('div', { style: { fontWeight: 750, fontSize: '15px' } }, q.grade),
            h('div', { class: 'small muted' }, `${q.sections} sections · ${q.blocks} blocs · ${q.words} mots`))),
        h('div', { class: 'check-list' },
          ...q.checks.map((c) => h('div', { class: 'check-item' },
            h('span', { class: 'dot ' + (c.ok ? 'ok' : 'ko') }, c.ok ? '✓' : '!'),
            h('div', {}, c.label, !c.ok ? h('small', {}, c.hint) : null))))),
      h('div', { class: 'stack' },
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Exports'),
          h('p', { class: 'card-sub' }, 'Le PDF est prêt à être signé ; Word reste éditable.'),
          h('div', { class: 'stack', style: { gap: '8px' } },
            ...[['pdf', 'PDF', 'download', 'btn-primary'],
              ['docx', 'Word (.docx)', 'file', ''],
              ['pptx', 'PowerPoint (.pptx)', 'layout', ''],
              ['md', 'Markdown', 'doc', 'btn-ghost']].map(([fmt, label, ico, cls]) =>
              h('button', {
                class: `btn ${cls}`, style: { justifyContent: 'flex-start' },
                onclick: async (e) => {
                  const btn = e.currentTarget; btn.disabled = true;
                  try {
                    await saveNow();
                    const res = await api(`/api/export/${fmt}`, { method: 'POST', body: { document: doc }, raw: true });
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const name = (res.headers.get('content-disposition') || '').match(/filename="?([^";]+)/)?.[1] || `livrable.${fmt}`;
                    download(url, name);
                    setTimeout(() => URL.revokeObjectURL(url), 4000);
                    toast(`Export ${label} prêt`, 'ok');
                  } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
                },
              }, icon(ico, 15), label)))),
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Assistant de rédaction'),
          h('p', { class: 'card-sub' }, 'Ajoute ou enrichit des sections automatiquement.'),
          h('button', {
            class: 'btn', style: { width: '100%' },
            onclick: async (e) => {
              const btn = e.currentTarget; btn.disabled = true;
              try {
                const r = await api('/api/generate', { method: 'POST', body: { brief: {
                  title: doc.meta.title, client: doc.meta.client, project: doc.meta.project,
                  industry: doc.meta.industry, context: doc.meta.executive_summary,
                  playbook: doc.meta.playbook, palette: doc.style?.palette, typography: doc.style?.typography,
                }, save: false } });
                const existing = new Set((doc.sections || []).map((s) => s.title));
                const added = (r.document.sections || []).filter((s) => !existing.has(s.title));
                if (!added.length) { toast('Toutes les sections proposées existent déjà.', 'warn'); }
                else {
                  doc.sections.push(...added);
                  toast(`${added.length} sections générées`, 'ok');
                  changed(); draw();
                }
              } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
            },
          }, icon('sparkle', 15), 'Régénérer les sections manquantes'))));
  };

  function draw() {
    clear(leftPane);
    const toolbar = h('div', { class: 'topbar', style: { borderBottom: '1px solid var(--line)' } },
      h('button', { class: 'btn btn-ghost btn-sm', onclick: () => go('projects') }, icon('back', 15), 'Projets'),
      h('div', {},
        h('h1', { style: { fontSize: '14px' } }, doc.meta.title || 'Sans titre'),
        h('div', { class: 'crumb' }, [doc.meta.client, doc.meta.project, `v${doc.meta.version || '1.0'}`].filter(Boolean).join(' · '))),
      h('div', { class: 'spacer' }),
      h('button', { class: 'btn btn-sm', onclick: async () => { await saveNow(); toast('Document enregistré', 'ok'); } }, icon('save', 14), 'Enregistrer'),
      h('button', {
        class: 'btn btn-primary btn-sm', onclick: async (e) => {
          const btn = e.currentTarget; btn.disabled = true;
          try {
            await saveNow();
            const res = await api('/api/export/pdf', { method: 'POST', body: { document: doc }, raw: true });
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            download(url, (doc.meta.title || 'livrable').replace(/\s+/g, '_') + '.pdf');
            setTimeout(() => URL.revokeObjectURL(url), 4000);
            toast('PDF généré', 'ok');
          } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
        },
      }, icon('download', 14), 'Exporter le PDF'));
    leftPane.append(toolbar, tabBar, body);
    renderTabs();
    clear(body);
    if (tab === 'content') { renderSections(); body.append(contentTab()); }
    else if (tab === 'identity') body.append(identityTab());
    else if (tab === 'style') body.append(styleTab());
    else if (tab === 'options') body.append(optionsTab());
    else body.append(qualityTab());
    renderSaveState();
    renderPreview();
  }

  draw();
  return root;
}
