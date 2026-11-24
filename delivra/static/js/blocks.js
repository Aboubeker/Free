/* Delivra — éditeurs de blocs de contenu.
   Chaque bloc expose : un libellé, une icône, un modèle vierge et un éditeur.
   `onChange` déclenche la sauvegarde automatique du document. */
import { h, clear, icon, uid, toast, download } from './lib.js';

export const BLOCK_LIBRARY = [
  { type: 'heading', label: 'Titre', icon: 'type', hint: 'Sous-titre numéroté' },
  { type: 'paragraph', label: 'Paragraphe', icon: 'doc', hint: 'Texte courant' },
  { type: 'bullets', label: 'Liste à puces', icon: 'grid' },
  { type: 'numbered', label: 'Liste numérotée', icon: 'grid' },
  { type: 'callout', label: 'Encadré', icon: 'info', hint: 'Note, alerte, validation' },
  { type: 'table', label: 'Tableau', icon: 'layout' },
  { type: 'kpi', label: 'Chiffres clés', icon: 'bolt' },
  { type: 'timeline', label: 'Planning / jalons', icon: 'clock' },
  { type: 'image', label: 'Capture d’écran', icon: 'image' },
  { type: 'architecture', label: 'Schéma d’architecture', icon: 'layers' },
  { type: 'two_col', label: 'Deux colonnes', icon: 'layout' },
  { type: 'checklist', label: 'Checklist', icon: 'check' },
  { type: 'quote', label: 'Citation', icon: 'info' },
  { type: 'code', label: 'Bloc de code', icon: 'server' },
  { type: 'signature', label: 'Signatures', icon: 'user' },
  { type: 'divider', label: 'Séparateur', icon: 'x' },
];

export function blankBlock(type) {
  const base = { id: uid('blk'), type };
  switch (type) {
    case 'heading': return { ...base, text: 'Nouveau sous-titre', level: 2, number: true };
    case 'paragraph': return { ...base, text: '' };
    case 'bullets':
    case 'numbered': return { ...base, items: ['Premier point', 'Deuxième point'] };
    case 'callout': return { ...base, tone: 'info', title: 'À noter', text: '' };
    case 'table': return { ...base, caption: '', columns: ['Colonne 1', 'Colonne 2'], rows: [['', '']] };
    case 'kpi': return { ...base, items: [{ label: 'Indicateur', value: '0', hint: '' }, { label: 'Indicateur', value: '0', hint: '' }] };
    case 'timeline': return { ...base, items: [{ when: 'S1', title: 'Étape', text: '', status: 'planned' }] };
    case 'image': return { ...base, asset: '', caption: '', layout: 'framed' };
    case 'architecture': return {
      ...base, caption: 'Schéma d’architecture', flow: true,
      layers: [
        { title: 'Sources', nodes: ['Système A', 'Système B'], tone: 'neutral' },
        { title: 'Traitement', nodes: ['Service principal'], tone: 'primary' },
        { title: 'Restitution', nodes: ['Portail', 'Reporting'], tone: 'accent' },
      ],
    };
    case 'two_col': return {
      ...base,
      left: { title: 'Inclus', items: ['Élément 1'] },
      right: { title: 'Exclu', items: ['Élément 1'] },
    };
    case 'checklist': return { ...base, items: [{ text: 'Point de contrôle', done: false }] };
    case 'quote': return { ...base, text: '', author: '' };
    case 'code': return { ...base, language: 'bash', text: '' };
    case 'signature': return { ...base, parties: [{ role: 'Pour le client', name: '', place: '', date: '' }, { role: 'Pour le prestataire', name: '', place: '', date: '' }] };
    case 'divider': return { ...base, style: 'accent' };
    default: return { ...base, text: '' };
  }
}

/* ------------------------------------------------------------------ inputs */
const field = (label, input, hint) => h('label', { class: 'field' },
  h('span', { class: 'lbl' }, label), input, hint ? h('div', { class: 'hint' }, hint) : null);

const text = (value, onInput, attrs = {}) => h('input', {
  class: 'input', value: value ?? '', oninput: (e) => onInput(e.target.value), ...attrs,
});
const area = (value, onInput, rows = 4, attrs = {}) => {
  const el = h('textarea', { class: 'textarea', rows, oninput: (e) => onInput(e.target.value), ...attrs });
  el.value = value ?? '';
  return el;
};
const select = (value, options, onChange) => {
  const el = h('select', { class: 'select', onchange: (e) => onChange(e.target.value) },
    ...options.map((o) => h('option', { value: o.value, selected: o.value === value }, o.label)));
  el.value = value;
  return el;
};
function listEditor(items, onChange, placeholder = 'Élément') {
  const wrap = h('div');
  const render = () => {
    clear(wrap);
    items.forEach((it, i) => {
      const input = h('input', {
        class: 'input', value: typeof it === 'string' ? it : it.text ?? '',
        oninput: (e) => {
          if (typeof it === 'string') items[i] = e.target.value;
          else items[i] = { ...it, text: e.target.value };
          onChange();
        },
      });
      wrap.append(h('div', { class: 'item-row' },
        input,
        h('button', {
          class: 'icon-btn', title: 'Supprimer', onclick: () => { items.splice(i, 1); onChange(); render(); },
        }, icon('x', 14)),
      ));
    });
    wrap.append(h('button', {
      class: 'btn btn-sm', onclick: () => {
        items.push(typeof (items[0] ?? '') === 'string' ? '' : { text: '', done: false });
        onChange(); render();
      },
    }, icon('plus', 14), placeholder));
  };
  render();
  return wrap;
}

/* ------------------------------------------------------- éditeur principal */
export function blockEditor(block, { onChange, onReplace, onDelete, onMove }) {
  const body = h('div', { class: 'block-body' });
  const set = (patch) => { Object.assign(block, patch); onChange(); };
  const t = block.type;

  if (t === 'heading') {
    body.append(text(block.text, (v) => set({ text: v })));
    body.append(h('div', { class: 'row', style: { marginTop: '8px' } },
      select(String(block.level || 2), [{ value: '2', label: 'Niveau 2' }, { value: '3', label: 'Niveau 3' }], (v) => set({ level: Number(v) })),
      h('label', { class: 'row small muted', style: { gap: '6px' } },
        h('input', { type: 'checkbox', checked: block.number !== false, onchange: (e) => set({ number: e.target.checked }) }),
        'Numéroté')));
  } else if (t === 'paragraph') {
    body.append(area(block.text, (v) => set({ text: v }), 5, { placeholder: 'Rédigez le contenu… ou utilisez « Améliorer » pour reformuler.' }));
    body.append(h('div', { class: 'row', style: { marginTop: '8px' } },
      h('button', {
        class: 'btn btn-sm btn-ghost', onclick: async (e) => {
          const btn = e.currentTarget; btn.disabled = true;
          try {
            const { api } = await import('./lib.js');
            const r = await api('/api/rewrite', { method: 'POST', body: { text: block.text, tone: 'professionnel' } });
            block.text = r.text; onChange(); onReplace?.();
            toast(r.engine === 'local' ? 'Texte reformulé (moteur local)' : `Texte reformulé (${r.engine})`, 'ok');
          } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
        },
      }, icon('sparkle', 14), 'Améliorer le style'),
      h('label', { class: 'row small muted', style: { gap: '6px' } },
        h('input', { type: 'checkbox', checked: !!block.lead, onchange: (e) => set({ lead: e.target.checked }) }),
        'Chapeau')));
  } else if (t === 'bullets' || t === 'numbered') {
    block.items = block.items || [];
    body.append(listEditor(block.items, () => onChange(), 'Ajouter un point'));
    body.append(h('div', { class: 'row', style: { marginTop: '8px' } },
      h('label', { class: 'row small muted', style: { gap: '6px' } },
        h('input', {
          type: 'checkbox', checked: block.columns === 2,
          onchange: (e) => set({ columns: e.target.checked ? 2 : 1 }),
        }), 'Sur deux colonnes')));
  } else if (t === 'callout') {
    body.append(select(block.tone || 'info', [
      { value: 'info', label: 'Information' }, { value: 'success', label: 'Point validé' },
      { value: 'warning', label: 'Attention' }, { value: 'danger', label: 'Point bloquant' },
    ], (v) => set({ tone: v })));
    body.append(field('Titre', text(block.title, (v) => set({ title: v }))));
    body.append(area(block.text, (v) => set({ text: v }), 3));
  } else if (t === 'table') {
    block.columns = block.columns || [];
    block.rows = block.rows || [];
    body.append(field('Légende', text(block.caption, (v) => set({ caption: v }))));
    const grid = h('div', { style: { overflowX: 'auto' } });
    const draw = () => {
      clear(grid);
      const table = h('table', { class: 'mini-table' });
      const head = h('tr');
      block.columns.forEach((c, ci) => {
        head.append(h('th', {},
          h('div', { class: 'row', style: { gap: '4px' } },
            h('input', {
              class: 'input', value: c, oninput: (e) => { block.columns[ci] = e.target.value; onChange(); },
            }),
            block.columns.length > 1 ? h('button', {
              class: 'icon-btn', onclick: () => {
                block.columns.splice(ci, 1);
                block.rows.forEach((r) => r.splice(ci, 1));
                onChange(); draw();
              },
            }, icon('x', 12)) : null)));
      });
      head.append(h('th'));
      table.append(h('thead', {}, head));
      const tb = h('tbody');
      block.rows.forEach((row, ri) => {
        const tr = h('tr');
        block.columns.forEach((_, ci) => {
          tr.append(h('td', {}, h('input', {
            class: 'input', value: row[ci] ?? '',
            oninput: (e) => { row[ci] = e.target.value; onChange(); },
          })));
        });
        tr.append(h('td', {}, h('button', {
          class: 'icon-btn', onclick: () => { block.rows.splice(ri, 1); onChange(); draw(); },
        }, icon('trash', 13))));
        tb.append(tr);
      });
      table.append(tb);
      grid.append(table);
      grid.append(h('div', { class: 'row', style: { marginTop: '8px' } },
        h('button', {
          class: 'btn btn-sm', onclick: () => {
            block.rows.push(block.columns.map(() => '')); onChange(); draw();
          },
        }, icon('plus', 13), 'Ligne'),
        h('button', {
          class: 'btn btn-sm', onclick: () => {
            block.columns.push(`Colonne ${block.columns.length + 1}`);
            block.rows.forEach((r) => r.push(''));
            onChange(); draw();
          },
        }, icon('plus', 13), 'Colonne'),
        h('button', {
          class: 'btn btn-sm btn-ghost', onclick: async () => {
            try {
              const { api } = await import('./lib.js');
              const csv = [block.columns.join(';'), ...block.rows.map((r) => r.join(';'))].join('\n');
              await navigator.clipboard.writeText(csv);
              toast('Tableau copié (CSV, séparateur « ; »)', 'ok');
            } catch { toast('Copie impossible', 'err'); }
          },
        }, icon('copy', 13), 'Copier CSV')));
    };
    draw();
    body.append(grid);
    body.append(h('div', { class: 'hint' }, 'Astuce : collez un tableau Excel dans une cellule — les colonnes sont détectées par « ; » ou tabulation.'));
  } else if (t === 'kpi') {
    block.items = block.items || [];
    const grid = h('div', { class: 'grid grid-2' });
    const draw = () => {
      clear(grid);
      block.items.forEach((it, i) => {
        grid.append(h('div', { class: 'card', style: { padding: '10px' } },
          h('div', { class: 'row', style: { marginBottom: '6px' } },
            h('strong', { class: 'small' }, `Chiffre ${i + 1}`),
            h('div', { style: { flex: 1 } }),
            h('button', {
              class: 'icon-btn', onclick: () => { block.items.splice(i, 1); onChange(); draw(); },
            }, icon('x', 13))),
          text(it.value, (v) => { it.value = v; onChange(); }, { placeholder: 'Valeur (ex. 99,9 %)' }),
          h('div', { style: { height: '6px' } }),
          text(it.label, (v) => { it.label = v; onChange(); }, { placeholder: 'Libellé' }),
          h('div', { style: { height: '6px' } }),
          text(it.hint, (v) => { it.hint = v; onChange(); }, { placeholder: 'Précision (optionnel)' })));
      });
    };
    draw();
    body.append(grid);
    if (block.items.length < 4) {
      body.append(h('button', {
        class: 'btn btn-sm', style: { marginTop: '8px' },
        onclick: () => { block.items.push({ value: '', label: '', hint: '' }); onChange(); draw(); },
      }, icon('plus', 13), 'Ajouter un chiffre (max. 4)'));
    }
  } else if (t === 'timeline') {
    block.items = block.items || [];
    const list = h('div');
    const draw = () => {
      clear(list);
      block.items.forEach((it, i) => {
        list.append(h('div', { class: 'card', style: { padding: '10px', marginBottom: '8px' } },
          h('div', { class: 'row', style: { marginBottom: '6px' } },
            h('span', { class: 'chip' }, `Étape ${i + 1}`),
            h('div', { style: { flex: 1 } }),
            h('button', { class: 'icon-btn', onclick: () => { block.items.splice(i, 1); onChange(); draw(); } }, icon('trash', 13))),
          h('div', { class: 'row-2' },
            text(it.when, (v) => { it.when = v; onChange(); }, { placeholder: 'Quand (S1, 12/06…)' }),
            select(it.status || 'planned', [
              { value: 'planned', label: 'À venir' }, { value: 'in_progress', label: 'En cours' },
              { value: 'done', label: 'Terminé' }, { value: 'late', label: 'En retard' },
            ], (v) => { it.status = v; onChange(); })),
          h('div', { style: { height: '6px' } }),
          text(it.title, (v) => { it.title = v; onChange(); }, { placeholder: 'Titre' }),
          h('div', { style: { height: '6px' } }),
          text(it.text, (v) => { it.text = v; onChange(); }, { placeholder: 'Description' })));
      });
      list.append(h('button', {
        class: 'btn btn-sm', onclick: () => {
          block.items.push({ when: '', title: '', text: '', status: 'planned' }); onChange(); draw();
        },
      }, icon('plus', 13), 'Ajouter une étape'));
    };
    draw();
    body.append(list);
  } else if (t === 'image') {
    body.append(field('Légende', text(block.caption, (v) => set({ caption: v }))));
    body.append(h('div', { class: 'row' },
      select(block.layout || 'framed', [
        { value: 'framed', label: 'Encadrée' }, { value: 'full', label: 'Pleine largeur' },
        { value: 'half', label: 'Réduite' },
      ], (v) => set({ layout: v }))));
    body.append(h('div', { style: { height: '8px' } }));
    const thumb = h('div');
    const drawThumb = () => {
      clear(thumb);
      if (block.asset) {
        thumb.append(h('div', { class: 'upload-preview' },
          h('img', { src: `/api/${block.asset}`, alt: '' }),
          h('div', { class: 'small muted', style: { flex: 1 } }, block.caption || 'Image sélectionnée'),
          h('button', { class: 'btn btn-sm btn-ghost', onclick: () => { block.asset = ''; onChange(); drawThumb(); } }, 'Retirer')));
      } else {
        const input = h('input', { type: 'file', accept: 'image/*', style: { display: 'none' }, onchange: async (e) => {
          const file = e.target.files[0]; if (!file) return;
          const fd = new FormData(); fd.append('file', file); fd.append('kind', 'image');
          try {
            const { api } = await import('./lib.js');
            const meta = await api('/api/upload', { method: 'POST', body: fd });
            block.asset = meta.asset; onChange(); drawThumb();
            toast('Capture ajoutée', 'ok');
          } catch (err) { toast(err.message, 'err'); }
        } });
        thumb.append(h('div', {
          class: 'dropzone', onclick: () => input.click(),
          ondragover: (e) => { e.preventDefault(); e.currentTarget.classList.add('hot'); },
          ondragleave: (e) => e.currentTarget.classList.remove('hot'),
          ondrop: async (e) => {
            e.preventDefault(); e.currentTarget.classList.remove('hot');
            const file = e.dataTransfer.files[0]; if (!file) return;
            input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change'));
          },
        }, icon('upload', 18), h('div', {}, 'Glissez une capture d’écran ou cliquez pour parcourir')),
        input);
      }
    };
    drawThumb();
    body.append(thumb);
  } else if (t === 'architecture') {
    body.append(field('Légende', text(block.caption, (v) => set({ caption: v }))));
    const list = h('div');
    const draw = () => {
      clear(list);
      (block.layers || []).forEach((layer, li) => {
        list.append(h('div', { class: 'card', style: { padding: '10px', marginBottom: '8px' } },
          h('div', { class: 'row', style: { gap: '6px', marginBottom: '6px' } },
            h('span', { class: 'chip' }, `Couche ${li + 1}`),
            h('div', { style: { flex: 1 } }),
            h('button', {
              class: 'icon-btn', onclick: () => { block.layers.splice(li, 1); onChange(); draw(); },
            }, icon('trash', 13))),
          text(layer.title, (v) => { layer.title = v; onChange(); }, { placeholder: 'Titre de la couche' }),
          h('div', { style: { height: '6px' } }),
          text((layer.nodes || []).join(', '), (v) => {
            layer.nodes = v.split(',').map((s) => s.trim()).filter(Boolean);
            onChange();
          }, { placeholder: 'Composants séparés par des virgules' }),
          h('div', { style: { height: '6px' } }),
          select(layer.tone || 'neutral', [
            { value: 'neutral', label: 'Neutre' }, { value: 'primary', label: 'Primaire' },
            { value: 'dark', label: 'Sombre' }, { value: 'accent', label: 'Accent' },
          ], (v) => { layer.tone = v; onChange(); draw(); })));
      });
      list.append(h('div', { class: 'row' },
        h('button', {
          class: 'btn btn-sm', onclick: () => {
            block.layers.push({ title: 'Nouvelle couche', nodes: [], tone: 'neutral' });
            onChange(); draw();
          },
        }, icon('plus', 13), 'Couche'),
        h('button', {
          class: 'btn btn-sm btn-accent', onclick: async () => {
            try {
              const { api } = await import('./lib.js');
              const r = await api('/api/ai/architecture', { method: 'POST', body: { description: block.caption || '' } });
              block.layers = r.layers; onChange(); draw();
              toast('Architecture proposée', 'ok');
            } catch (err) { toast(err.message, 'err'); }
          },
        }, icon('sparkle', 13), 'Proposer une architecture')));
    };
    draw();
    body.append(list);
  } else if (t === 'two_col') {
    const side = (data, label) => h('div', { class: 'card', style: { padding: '10px' } },
      h('div', { class: 'small', style: { fontWeight: 700, marginBottom: '6px' } }, label),
      text(data.title, (v) => { data.title = v; onChange(); }, { placeholder: 'Titre' }),
      h('div', { style: { height: '8px' } }),
      listEditor(data.items || (data.items = []), () => onChange(), 'Ajouter'));
    body.append(h('div', { class: 'grid grid-2' }, side(block.left, 'Colonne gauche'), side(block.right, 'Colonne droite')));
  } else if (t === 'checklist') {
    block.items = block.items || [];
    const list = h('div');
    const draw = () => {
      clear(list);
      block.items.forEach((it, i) => {
        list.append(h('div', { class: 'item-row' },
          h('input', {
            type: 'checkbox', checked: !!it.done, style: { width: '18px' },
            onchange: (e) => { it.done = e.target.checked; onChange(); },
          }),
          h('input', { class: 'input', value: it.text, oninput: (e) => { it.text = e.target.value; onChange(); } }),
          h('button', { class: 'icon-btn', onclick: () => { block.items.splice(i, 1); onChange(); draw(); } }, icon('x', 13))));
      });
      list.append(h('button', {
        class: 'btn btn-sm', onclick: () => { block.items.push({ text: '', done: false }); onChange(); draw(); },
      }, icon('plus', 13), 'Point de contrôle'));
    };
    draw();
    body.append(list);
  } else if (t === 'quote') {
    body.append(area(block.text, (v) => set({ text: v }), 3, { placeholder: 'Citation…' }));
    body.append(h('div', { style: { height: '8px' } }));
    body.append(text(block.author, (v) => set({ author: v }), { placeholder: 'Auteur, fonction' }));
  } else if (t === 'code') {
    body.append(h('div', { class: 'row', style: { marginBottom: '8px' } },
      select(block.language || 'bash', ['bash', 'sql', 'yaml', 'json', 'python', 'javascript', 'terraform', 'text']
        .map((v) => ({ value: v, label: v })), (v) => set({ language: v }))));
    const ta = h('textarea', {
      class: 'textarea mono', rows: 6, spellcheck: false,
      style: { background: '#12161f', color: '#e6edf7' },
      oninput: (e) => set({ text: e.target.value }),
    });
    ta.value = block.text || '';
    body.append(ta);
  } else if (t === 'signature') {
    block.parties = block.parties || [];
    const list = h('div');
    const draw = () => {
      clear(list);
      block.parties.forEach((p, i) => {
        list.append(h('div', { class: 'card', style: { padding: '10px', marginBottom: '8px' } },
          h('div', { class: 'row', style: { marginBottom: '6px' } },
            h('span', { class: 'chip' }, `Signataire ${i + 1}`),
            h('div', { style: { flex: 1 } }),
            h('button', { class: 'icon-btn', onclick: () => { block.parties.splice(i, 1); onChange(); draw(); } }, icon('trash', 13))),
          h('div', { class: 'row-2' },
            text(p.role, (v) => { p.role = v; onChange(); }, { placeholder: 'Rôle' }),
            text(p.name, (v) => { p.name = v; onChange(); }, { placeholder: 'Nom' })),
          h('div', { class: 'row-2', style: { marginTop: '6px' } },
            text(p.place, (v) => { p.place = v; onChange(); }, { placeholder: 'Lieu' }),
            text(p.date, (v) => { p.date = v; onChange(); }, { placeholder: 'Date' }))));
      });
      list.append(h('button', {
        class: 'btn btn-sm', onclick: () => {
          block.parties.push({ role: '', name: '', place: '', date: '' }); onChange(); draw();
        },
      }, icon('plus', 13), 'Signataire'));
    };
    draw();
    body.append(list);
  } else if (t === 'divider') {
    body.append(select(block.style || 'accent', [
      { value: 'accent', label: 'Trait accentué' }, { value: 'line', label: 'Filet discret' },
    ], (v) => set({ style: v })));
  }

  const meta = BLOCK_LIBRARY.find((b) => b.type === t) || { label: t, icon: 'doc' };
  return h('div', { class: 'block' },
    h('div', { class: 'block-head' },
      icon(meta.icon, 14),
      h('span', { class: 'block-type' }, meta.label),
      h('div', { class: 'block-actions' },
        h('button', { class: 'icon-btn', title: 'Monter', onclick: () => onMove?.(-1) }, icon('arrowUp', 13)),
        h('button', { class: 'icon-btn', title: 'Descendre', onclick: () => onMove?.(1) }, icon('arrowDown', 13)),
        h('button', { class: 'icon-btn', title: 'Supprimer', onclick: () => onDelete?.() }, icon('trash', 13)))),
    body);
}
