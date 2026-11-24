/* Delivra — médiathèque et exports : captures, logos, visuels générés,
   documents produits (PDF, Word, PowerPoint, ZIP). */
import { h, clear, icon, api, toast, confirmBox, fmtBytes, download, modal } from './lib.js';

export function exportsView(ctx) {
  const { getDoc, setDoc, catalog } = ctx;
  const root = h('div', { class: 'page wide', style: { maxWidth: '1180px', margin: '0 auto' } });
  let tab = 'assets';
  let assets = [];
  let exportsList = [];

  const load = async () => {
    try {
      [assets, exportsList] = await Promise.all([api('/api/assets'), api('/api/exports')]);
      draw();
    } catch (e) { toast(e.message, 'err'); }
  };

  const uploadZone = (label = 'Captures d’écran, logos, schémas — glissez vos fichiers ici') => {
    const input = h('input', { type: 'file', accept: 'image/*', multiple: true, style: { display: 'none' }, onchange: (e) => upload([...e.target.files]) });
    const zone = h('div', {
      class: 'dropzone', style: { padding: '28px' },
      onclick: () => input.click(),
      ondragover: (e) => { e.preventDefault(); zone.classList.add('hot'); },
      ondragleave: () => zone.classList.remove('hot'),
      ondrop: (e) => { e.preventDefault(); zone.classList.remove('hot'); upload([...e.dataTransfer.files]); },
    }, icon('upload', 22), h('div', { style: { marginTop: '6px' } }, label),
      h('div', { class: 'hint' }, 'PNG, JPG, SVG, WEBP — 12 Mo maximum par fichier'), input);
    return zone;
  };

  const upload = async (files) => {
    let ok = 0;
    for (const f of files) {
      const fd = new FormData(); fd.append('file', f); fd.append('kind', 'image');
      try { await api('/api/upload', { method: 'POST', body: fd }); ok += 1; }
      catch (e) { toast(`${f.name} : ${e.message}`, 'err'); }
    }
    if (ok) toast(`${ok} fichier${ok > 1 ? 's' : ''} importé${ok > 1 ? 's' : ''}`, 'ok');
    load();
  };

  const insertAsset = (a) => {
    const doc = getDoc();
    if (!doc) { toast('Ouvrez d’abord un livrable.', 'warn'); return; }
    if (!doc.sections.length) { toast('Le document n’a aucune section.', 'warn'); return; }
    doc.sections[doc.sections.length - 1].blocks = doc.sections[doc.sections.length - 1].blocks || [];
    doc.sections[doc.sections.length - 1].blocks.push({
      id: `blk-${Math.random().toString(36).slice(2, 9)}`, type: 'image',
      asset: a.asset, caption: a.name, layout: 'framed',
    });
    setDoc(doc, ctx.getQuality());
    toast('Capture ajoutée à la dernière section', 'ok');
  };

  const assetsTab = () =>
    h('div', { class: 'stack' },
      uploadZone(),
      assets.length ? h('div', { class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(190px,1fr))' } },
        ...assets.map((a) => h('div', { class: 'card', style: { padding: '9px' } },
          h('div', {
            style: {
              height: '120px', borderRadius: '8px', background: '#fff center/contain no-repeat',
              backgroundImage: `url(/api/${a.asset})`, border: '1px solid var(--line)',
            },
          }),
          h('div', { class: 'row', style: { marginTop: '8px' } },
            h('div', { style: { minWidth: 0, flex: 1 } },
              h('div', { class: 'small', style: { fontWeight: 650, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, a.name),
              h('div', { class: 'small muted' }, `${a.dims || ''} ${fmtBytes(a.size)}`)),
            h('button', { class: 'icon-btn', title: 'Insérer dans le document', onclick: () => insertAsset(a) }, icon('plus', 15)),
            h('button', { class: 'icon-btn', title: 'Télécharger', onclick: () => download(`/api/${a.asset}`, a.name) }, icon('download', 14)),
            h('button', {
              class: 'icon-btn', title: 'Supprimer',
              onclick: () => confirmBox('Supprimer le fichier', a.name, async () => {
                await api(`/api/assets/${a.name}`, { method: 'DELETE' }); load();
              }),
            }, icon('trash', 14))))))
        : h('div', { class: 'card', style: { textAlign: 'center', padding: '30px' } },
          h('div', { class: 'muted' }, 'Aucun média importé pour le moment.')));

  const exportsTab = () => {
    const doc = getDoc();
    const doExport = async (fmt) => {
      if (!doc) { toast('Aucun document ouvert.', 'warn'); return; }
      try {
        await api(`/api/projects/${doc.id}`, { method: 'PUT', body: { document: doc } });
        const url = fmt === 'bundle' ? '/api/export/preview-bundle' : `/api/export/${fmt}`;
        const res = await api(url, { method: 'POST', body: { document: doc }, raw: true });
        const blob = await res.blob();
        const obj = URL.createObjectURL(blob);
        const name = (res.headers.get('content-disposition') || '').match(/filename="?([^";]+)/)?.[1] || `livrable.${fmt}`;
        download(obj, name);
        setTimeout(() => URL.revokeObjectURL(obj), 5000);
        toast('Export prêt', 'ok');
        load();
      } catch (e) { toast(e.message, 'err'); }
    };
    return h('div', { class: 'stack' },
      h('div', { class: 'grid grid-4' },
        ...[
          ['pdf', 'PDF', 'Document final, prêt à signer', 'download', 'btn-primary'],
          ['docx', 'Word', 'Réédition complète du contenu', 'file', ''],
          ['pptx', 'PowerPoint', 'Support de restitution', 'layout', ''],
          ['bundle', 'Pack complet', 'ZIP : PDF + Word + PPTX + JSON', 'layers', 'btn-accent'],
        ].map(([fmt, label, sub, ico, cls]) => h('div', { class: 'card' },
          h('div', { style: { color: 'var(--primary)', marginBottom: '8px' } }, icon(ico, 22)),
          h('h3', { class: 'card-title' }, label),
          h('p', { class: 'card-sub' }, sub),
          h('button', { class: `btn btn-sm ${cls}`, style: { width: '100%' }, onclick: () => doExport(fmt) }, 'Exporter')))),
      h('div', { class: 'card' },
        h('div', { class: 'row', style: { marginBottom: '10px' } },
          h('h3', { class: 'card-title', style: { margin: 0 } }, 'Fichiers générés'),
          h('div', { style: { flex: 1 } }),
          h('button', { class: 'btn btn-sm btn-ghost', onclick: load }, icon('refresh', 13), 'Actualiser')),
        exportsList.length ? h('table', { class: 'mini-table' },
          h('thead', {}, h('tr', {}, h('th', {}, 'Fichier'), h('th', {}, 'Taille'), h('th', {}, 'Date'), h('th', {}, ''))),
          h('tbody', {}, ...exportsList.map((f) => h('tr', {},
            h('td', {}, h('span', { class: 'mono' }, f.name)),
            h('td', { class: 'small muted' }, fmtBytes(f.size)),
            h('td', { class: 'small muted' }, f.modified),
            h('td', { style: { textAlign: 'right' } },
              h('button', { class: 'icon-btn', onclick: () => download(`/api/exports/${f.name}`, f.name) }, icon('download', 14)))))))
          : h('div', { class: 'small muted' }, 'Aucun export pour l’instant.')));
  };

  function draw() {
    clear(root);
    root.append(
      h('div', { class: 'row', style: { marginBottom: '14px' } },
        h('div', {},
          h('h2', { style: { margin: 0, fontSize: '20px', letterSpacing: '-.02em' } }, 'Médias & exports'),
          h('div', { class: 'small muted' }, 'Centralisez vos captures d’écran et générez les documents finaux.')),
        h('div', { style: { flex: 1 } })),
      h('div', { class: 'row', style: { gap: '4px', marginBottom: '14px' } },
        ...[['assets', 'Médias', 'image'], ['exports', 'Exports', 'download']].map(([k, l, i]) =>
          h('button', {
            class: 'nav-item' + (tab === k ? ' active' : ''), style: { width: 'auto', padding: '7px 12px' },
            onclick: () => { tab = k; draw(); },
          }, icon(i, 15), h('span', {}, l)))),
      tab === 'assets' ? assetsTab() : exportsTab());
  }

  load();
  return root;
}
