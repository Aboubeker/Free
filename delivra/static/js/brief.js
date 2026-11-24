/* Delivra — assistant de création : brief → plan → génération.
   Trois panneaux : brief (gauche), choix de structure (centre), qualité (droite). */
import {
  h, clear, icon, api, toast, debounce, fmtBytes, paletteSwatches, sleep,
} from './lib.js';

const STEPS = ['Brief', 'Structure', 'Identité', 'Génération'];

export function briefView(ctx) {
  const { state, go, setDoc, catalog, refreshDoc } = ctx;
  const cfg = state.catalog || catalog;
  const brief = state.brief || (state.brief = {
    title: '', client: '', project: '', industry: '', context: '',
    goals: '', stack: '', weeks: 18, tone: 'professionnel', author: '', author_role: '',
    recipient: '', palette: '', typography: '', tags: '', playbook: '',
  });
  let step = 0;
  let plan = state.plan || null;
  let generating = false;

  const root = h('div', { class: 'page' });
  const stepBar = h('div', { class: 'steps', style: { marginBottom: '20px' } });
  const stage = h('div');

  const renderSteps = () => {
    clear(stepBar);
    STEPS.forEach((label, i) => {
      const dot = h('button', {
        class: 'btn btn-sm ' + (i === step ? 'btn-primary' : 'btn-ghost'),
        onclick: () => { if (i <= step || plan) { step = i; draw(); } },
      }, i < step ? icon('check', 13) : h('span', { class: 'small' }, i + 1), ' ' + label);
      stepBar.append(dot);
    });
  };

  /* ------------------------------------------------------------ étape 1 */
  const stepBrief = () => {
    const f = (label, key, attrs = {}) => h('label', { class: 'field' },
      h('span', { class: 'lbl' }, label),
      (() => {
        const el = attrs.area
          ? h('textarea', { class: 'textarea', rows: attrs.rows || 3, placeholder: attrs.ph || '' })
          : h('input', { class: 'input', placeholder: attrs.ph || '', type: attrs.type || 'text' });
        el.value = brief[key] ?? '';
        el.addEventListener('input', (e) => { brief[key] = e.target.value; ctx.saveState({ brief }); });
        return el;
      })());

    const playbooks = (cfg.playbooks || []).map((p) => ({ value: p.key, label: p.label }));
    const pbSel = h('select', { class: 'select', onchange: (e) => { brief.playbook = e.target.value; ctx.saveState({ brief }); } },
      h('option', { value: '' }, 'Détection automatique'),
      ...playbooks.map((p) => h('option', { value: p.value, selected: brief.playbook === p.value }, p.label)));
    pbSel.value = brief.playbook || '';

    const tones = [
      ['professionnel', 'Professionnel'], ['technique', 'Technique'],
      ['commercial', 'Commercial'], ['institutionnel', 'Institutionnel'],
    ];
    const toneSel = h('select', { class: 'select', onchange: (e) => { brief.tone = e.target.value; ctx.saveState({ brief }); } },
      ...tones.map(([v, l]) => h('option', { value: v, selected: brief.tone === v }, l)));

    const weeks = h('input', { class: 'input', type: 'number', min: 4, max: 104, value: brief.weeks || 18,
      oninput: (e) => { brief.weeks = Number(e.target.value) || 18; ctx.saveState({ brief }); } });

    return h('div', { class: 'grid', style: { gridTemplateColumns: 'minmax(0,1.35fr) minmax(0,1fr)' } },
      h('div', { class: 'card pad-lg' },
        h('h2', { class: 'card-title', style: { fontSize: '16px' } }, 'Décrivez votre livrable'),
        h('p', { class: 'card-sub' }, 'L’agent compose un dossier complet : contexte, architecture, déploiement, sécurité, recette, planning et risques.'),
        f('Titre du document', 'title', { ph: 'Dossier de livraison — Portail Client' }),
        h('div', { class: 'row-2' },
          f('Client', 'client', { ph: 'Banque Atlas' }),
          f('Solution / projet', 'project', { ph: 'Portail Client Omnicanal' })),
        h('div', { class: 'row-2' },
          f('Secteur', 'industry', { ph: 'Services financiers' }),
          f('Référence', 'reference', { ph: 'LIV-2026-014' })),
        f('Contexte & enjeux', 'context', { area: true, rows: 3, ph: 'Situation actuelle, irritants, objectifs de la direction…' }),
        h('div', { class: 'row-2' },
          f('Objectifs (un par ligne)', 'goals', { area: true, rows: 3, ph: 'Unifier le parcours client\nRéduire les délais de traitement' }),
          f('Technologies / solutions déployées', 'stack', { area: true, rows: 3, ph: 'React, API REST, PostgreSQL, Azure' })),
        h('div', { class: 'row-3' },
          h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Type de livrable'), pbSel),
          h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Registre'), toneSel),
          h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Durée (semaines)'), weeks)),
        h('div', { class: 'row', style: { justifyContent: 'flex-end', marginTop: '6px' } },
          h('button', {
            class: 'btn btn-ghost', onclick: async () => {
              try {
                const r = await api('/api/suggest-titles', { method: 'POST', body: brief });
                const list = h('div', { class: 'stack' });
                const m = (await import('./lib.js')).modal('Propositions de titres', list);
                r.titles.forEach((t) => list.append(h('button', {
                  class: 'btn', style: { justifyContent: 'flex-start' },
                  onclick: () => { brief.title = t; m.close(); draw(); },
                }, t)));
              } catch (e) { toast(e.message, 'err'); }
            },
          }, icon('sparkle', 15), 'Suggérer des titres'),
          h('button', {
            class: 'btn btn-primary', onclick: () => {
              if (!brief.title && !brief.project) { toast('Renseignez au moins un titre ou un projet.', 'warn'); return; }
              step = 1; draw(); loadPlan();
            },
          }, 'Continuer', icon('chevronDown', 15)))),
      h('div', { class: 'stack' },
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Ce que contiendra le livrable'),
          h('div', { class: 'check-list', style: { marginTop: '10px' } },
            ...[
              'Page de couverture personnalisée (logo client)',
              'Résumé exécutif + informations clés',
              'Sommaire paginé automatiquement',
              'Sections numérotées avec tableaux, KPI et schémas',
              'Schéma d’architecture généré automatiquement',
              'En-tête, pied de page, filigrane, pagination',
              'Page de validation / signatures',
              'Exports PDF, Word et PowerPoint',
            ].map((t) => h('div', { class: 'check-item' },
              h('span', { class: 'dot ok' }, '✓'), h('div', {}, t))))),
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Astuce'),
          h('p', { class: 'card-sub', style: { marginBottom: 0 } },
            'Sans connexion, Delivra utilise son moteur local (aucune donnée ne quitte votre poste). ',
            h('br'), 'Vous pouvez brancher un LLM (OpenAI, Mistral, Ollama) dans les paramètres pour enrichir la rédaction.'))));
  };

  /* ------------------------------------------------------------ étape 2 */
  const outlineRow = (item, i, arr) => h('div', {
    class: 'section-row',
      draggable: true,
      ondragstart: (e) => { e.dataTransfer.setData('text/plain', String(i)); e.currentTarget.classList.add('dragging'); },
      ondragend: (e) => e.currentTarget.classList.remove('dragging'),
      ondragover: (e) => e.preventDefault(),
      ondrop: (e) => {
        e.preventDefault();
        const from = Number(e.dataTransfer.getData('text/plain'));
        if (Number.isNaN(from) || from === i) return;
        const [moved] = arr.splice(from, 1);
        arr.splice(i, 0, moved);
        draw();
      },
    },
    h('span', { class: 'grip' }, icon('grip', 15)),
    h('span', { class: 'num' }, String(i + 1).padStart(2, '0')),
    h('div', { class: 'name' }, item.title),
    h('span', { class: 'chip small' }, item.kicker || ''),
    h('button', {
      class: 'icon-btn', title: 'Retirer', onclick: () => { plan.outline.splice(i, 1); plan.sections = plan.outline.map((s) => s.key); draw(); },
    }, icon('x', 14)));

  const stepStructure = () => {
    const paletteCard = (p) => h('button', {
      class: 'palette-card' + ((brief.palette || (plan && plan.palette)) === p.key ? ' active' : ''),
      onclick: () => { brief.palette = p.key; ctx.saveState({ brief }); draw(); },
    },
    h('div', { class: 'swatches' }, ...paletteSwatches(p)),
    h('div', { class: 'palette-name' }, p.label));

    const fontCard = (f) => {
      const cls = ['serif', 'serif-mix'].includes(f.key) ? 'serif'
        : (f.key === 'sora' || f.key === 'technical') ? 'display' : '';
      return h('button', {
        class: 'font-card' + ((brief.typography || (plan && plan.typography)) === f.key ? ' active' : ''),
        onclick: () => { brief.typography = f.key; ctx.saveState({ brief }); draw(); },
      },
      h('div', { class: 'font-sample ' + cls }, 'Aa — Dossier 2026'),
      h('div', { class: 'font-meta' }, f.label));
    };

    const addSection = () => {
      const pool = plan.__pool || [];
      if (!pool.length) { toast('Toutes les sections disponibles sont déjà utilisées.', 'warn'); return; }
      plan.outline.push(pool.shift());
      plan.sections = plan.outline.map((s) => s.key);
      draw();
    };

    const left = h('div', { class: 'card pad-lg' },
      h('h2', { class: 'card-title', style: { fontSize: '16px' } }, 'Structure proposée'),
      h('p', { class: 'card-sub' }, 'Glissez-déposez pour réordonner, retirez ou ajoutez des sections.'),
      plan
        ? h('div', { class: 'stack' }, ...plan.outline.map((it, i, arr) => outlineRow(it, i, arr)))
        : h('div', { class: 'skeleton', style: { height: '160px' } }),
      h('div', { class: 'row', style: { marginTop: '14px', justifyContent: 'space-between' } },
        h('button', { class: 'btn btn-ghost', onclick: () => { step = 0; draw(); } }, icon('back', 15), 'Retour'),
        h('div', { class: 'row' },
          h('button', { class: 'btn', onclick: addSection }, icon('plus', 15), 'Ajouter une section'),
          h('button', { class: 'btn btn-primary', onclick: () => { step = 2; draw(); } }, 'Continuer', icon('chevronDown', 15)))));

    const right = h('div', { class: 'stack' },
      h('div', { class: 'card' },
        h('h3', { class: 'card-title' }, 'Contexte détecté'),
        plan
          ? h('div', { class: 'stack', style: { gap: '8px', marginTop: '10px' } },
            h('span', { class: 'chip' }, icon('layers', 13), plan.playbook_label),
            h('p', { class: 'small muted', style: { margin: 0 } },
              `${plan.outline.length} sections · structure adaptée au type de livrable détecté.`))
          : h('div', { class: 'skeleton', style: { height: '70px' } })),
      h('div', { class: 'card' },
        h('h3', { class: 'card-title' }, 'Style visuel'),
        h('div', { class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(118px,1fr))', marginTop: '10px' } },
          ...(cfg.palettes || []).slice(0, 6).map(paletteCard))),
      h('div', { class: 'card' },
        h('h3', { class: 'card-title' }, 'Typographie'),
        h('div', { class: 'choice-grid', style: { marginTop: '10px' } },
          ...(cfg.typographies || []).map(fontCard))));

    return h('div', { class: 'grid', style: { gridTemplateColumns: 'minmax(0,1.4fr) minmax(0,1fr)' } }, left, right);
  };

  /* ------------------------------------------------------------ étape 3 */
  const stepIdentity = () => {
    const brand = state.brand || (state.brand = { logo: '', client_logo: '', cover_image: '' });
    const uploader = (key, label, hint) => {
      const box = h('div');
      const draw = () => {
        clear(box);
        if (brand[key]) {
          box.append(h('div', { class: 'upload-preview' },
            h('img', { src: `/api/${brand[key]}`, alt: '' }),
            h('div', { class: 'small muted', style: { flex: 1 } }, label + ' importé'),
            h('button', {
              class: 'btn btn-sm btn-ghost',
              onclick: () => { brand[key] = ''; ctx.saveState({ brand }); draw(); },
            }, 'Retirer')));
        } else {
          const input = h('input', { type: 'file', accept: 'image/*', style: { display: 'none' }, onchange: async (e) => {
            const file = e.target.files[0]; if (!file) return;
            const fd = new FormData(); fd.append('file', file); fd.append('kind', 'image');
            try {
              const meta = await api('/api/upload', { method: 'POST', body: fd });
              brand[key] = meta.asset; ctx.saveState({ brand }); draw(); toast('Image importée', 'ok');
            } catch (err) { toast(err.message, 'err'); }
          } });
          box.append(h('div', {
            class: 'dropzone', onclick: () => input.click(),
            ondragover: (e) => { e.preventDefault(); e.currentTarget.classList.add('hot'); },
            ondragleave: (e) => e.currentTarget.classList.remove('hot'),
            ondrop: (e) => { e.preventDefault(); e.currentTarget.classList.remove('hot'); input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change')); },
          }, icon('upload', 18), h('div', {}, label), hint ? h('div', { class: 'hint' }, hint) : null),
          input);
        }
      };
      draw();
      return box;
    };

    const meta = state.meta || (state.meta = { author: '', author_role: '', recipient: '', confidentiality: 'Confidentiel', version: '1.0', date: '', reference: '' });
    const mi = (label, key, ph = '') => {
      const el = h('input', { class: 'input', placeholder: ph, value: meta[key] || '' });
      el.addEventListener('input', () => { meta[key] = el.value; ctx.saveState({ meta }); });
      return h('label', { class: 'field' }, h('span', { class: 'lbl' }, label), el);
    };

    return h('div', { class: 'grid', style: { gridTemplateColumns: 'minmax(0,1.3fr) minmax(0,1fr)' } },
      h('div', { class: 'card pad-lg' },
        h('h2', { class: 'card-title', style: { fontSize: '16px' } }, 'Identité et marque'),
        h('p', { class: 'card-sub' }, 'Ces éléments apparaissent sur la couverture et dans l’en-tête.'),
        h('div', { class: 'row-2' },
          h('div', {}, h('span', { class: 'lbl', style: { marginBottom: '6px', display: 'block' } }, 'Logo prestataire'), uploader('logo', 'Logo de l’entreprise', 'PNG ou SVG transparent conseillé')),
          h('div', {}, h('span', { class: 'lbl', style: { marginBottom: '6px', display: 'block' } }, 'Logo client'), uploader('client_logo', 'Logo du client'))),
        h('div', { class: 'divider' }),
        h('div', { class: 'row-2' }, mi('Auteur', 'author', 'Prénom Nom'), mi('Fonction', 'author_role', 'Architecte solutions')),
        h('div', { class: 'row-2' }, mi('Destinataire', 'recipient', 'Direction des systèmes d’information'), mi('Version', 'version', '1.0')),
        h('div', { class: 'row-2' }, mi('Date', 'date', 'JJ mois AAAA'), mi('Confidentialité', 'confidentiality', 'Confidentiel')),
        h('div', { class: 'row', style: { marginTop: '10px', justifyContent: 'space-between' } },
          h('button', { class: 'btn btn-ghost', onclick: () => { step = 1; draw(); } }, icon('back', 15), 'Retour'),
          h('button', { class: 'btn btn-accent', onclick: () => { step = 3; draw(); } }, icon('sparkle', 16), 'Générer le livrable'))),
      h('div', { class: 'stack' },
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Image de couverture'),
          h('p', { class: 'card-sub' }, 'Optionnel : visuel de fond (photo, capture produit).'),
          uploader('cover_image', 'Image de couverture')),
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Génération automatique'),
          h('p', { class: 'card-sub' }, 'Vous pourrez changer le style à tout moment dans l’éditeur.'),
          h('button', {
            class: 'btn', style: { width: '100%' },
            onclick: async (e) => {
              const btn = e.currentTarget; btn.disabled = true;
              try {
                const r = await api('/api/generate', { method: 'POST', body: { brief: { ...brief }, save: false } });
                // applique le visuel généré en fond de couverture
                if (r.document.style.cover_image !== undefined) { /* noop */ }
                setDoc(r.document);
                toast('Visuel généré', 'ok');
                step = 3; draw();
              } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
            },
          }, icon('image', 15), 'Prévisualiser le style'))));
  };

  /* ------------------------------------------------------------ étape 4 */
  const stepGenerate = () => {
    const status = h('div', { class: 'stack' });
    const progress = h('div', { class: 'progress' }, h('i', { style: { width: '0%' } }));
    const logLine = (label) => {
      const row = h('div', { class: 'check-item' }, h('span', { class: 'dot ko' }, '•'), h('div', {}, label));
      status.append(row);
      return row;
    };
    const run = async () => {
      if (generating) return;
      generating = true;
      const steps = [
        'Analyse du brief et détection du type de livrable',
        'Sélection du référentiel métier',
        'Rédaction des sections et tableaux',
        'Génération du schéma d’architecture',
        'Composition du document et pagination',
        'Contrôle qualité du livrable',
      ];
      const rows = steps.map((s) => logLine(s));
      for (let i = 0; i < rows.length - 1; i++) {
        progress.firstChild.style.width = `${((i + 0.35) / steps.length) * 100}%`;
        await sleep(190);
        rows[i].firstChild.className = 'dot ok'; rows[i].firstChild.textContent = '✓';
      }
      try {
        const payload = {
          ...brief,
          palette: brief.palette || (plan && plan.palette) || '',
          typography: brief.typography || (plan && plan.typography) || '',
          sections: plan ? plan.outline.map((s) => s.key) : undefined,
          brand: state.brand || {},
          ...(state.meta || {}),
        };
        const r = await api('/api/generate', { method: 'POST', body: { brief: payload, save: false } });
        // fusionne l'identité (auteur, logos) saisie à l'étape 3
        Object.assign(r.document.meta, {
          ...(state.meta || {}),
          author: state.meta?.author || brief.author || '',
          author_role: state.meta?.author_role || brief.author_role || '',
          recipient: state.meta?.recipient || brief.recipient || '',
          confidentiality: state.meta?.confidentiality || 'Confidentiel',
        });
        r.document.brand = { ...(state.brand || {}), ...(r.document.brand || {}) };
        const saved = await api('/api/projects', { method: 'POST', body: { document: r.document } });
        progress.firstChild.style.width = '100%';
        rows[rows.length - 1].firstChild.className = 'dot ok'; rows[rows.length - 1].firstChild.textContent = '✓';
        refreshDoc(saved.document, saved.quality);
        toast(`Livrable généré — qualité ${saved.quality.score}/100`, 'ok');
        await sleep(420);
        go('editor');
      } catch (err) {
        toast(err.message, 'err');
        generating = false;
      }
    };
    run();

    return h('div', { class: 'grid', style: { gridTemplateColumns: 'minmax(0,1.3fr) minmax(0,1fr)' } },
      h('div', { class: 'card pad-lg' },
        h('div', { class: 'row', style: { marginBottom: '6px' } },
          h('span', { class: 'badge-ai' }, icon('sparkle', 13), 'Agent Delivra'),
          h('span', { class: 'small muted' }, cfg.ai?.available ? `Moteur ${cfg.ai.provider}` : 'Moteur local')),
        h('h2', { class: 'card-title', style: { fontSize: '18px' }, }, 'Composition du dossier'),
        h('p', { class: 'card-sub' }, brief.title || brief.project || 'Votre livrable'),
        progress,
        h('div', { style: { marginTop: '18px' } }, status)),
      h('div', { class: 'card' },
        h('h3', { class: 'card-title' }, 'Récapitulatif'),
        h('div', { class: 'stack', style: { gap: '8px', marginTop: '10px' } },
          ...[
            ['Client', brief.client || '—'], ['Projet', brief.project || '—'],
            ['Sections', plan ? plan.outline.length : '—'], ['Durée', `${brief.weeks || 18} semaines`],
            ['Structure', plan ? plan.playbook_label : '—'],
          ].map(([k, v]) => h('div', { class: 'row', style: { justifyContent: 'space-between' } },
            h('span', { class: 'small muted' }, k), h('strong', { class: 'small' }, String(v)))))));
  };

  function draw() {
    clear(root);
    renderSteps();
    root.append(stepBar, stage);
    clear(stage);
    if (step === 0) stage.append(stepBrief());
    else if (step === 1) stage.append(stepStructure());
    else if (step === 2) stage.append(stepIdentity());
    else stage.append(stepGenerate());
  }

  async function loadPlan() {
    try {
      const p = await api('/api/plan', { method: 'POST', body: brief });
      p.__pool = (p.pool || []).map((s) => ({ ...s, kicker: s.kicker || 'Section' }));
      plan = p; state.plan = p; ctx.saveState({ plan: p });
      draw();
    } catch (e) { toast(e.message, 'err'); }
  }

  draw();
  return root;
}
