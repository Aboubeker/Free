/* Delivra — gestion des livrables : liste, recherche, duplication, exports. */
import { h, clear, icon, api, toast, confirmBox, download, fmtBytes, modal } from './lib.js';

export function projectsView(ctx) {
  const { go, openProject, setDoc, catalog } = ctx;
  const root = h('div', { class: 'page' });
  let items = [];
  let query = '';
  const grid = h('div', { class: 'grid', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(268px,1fr))', marginTop: '16px' } });
  const count = h('span', { class: 'small muted' }, '');

  const load = async () => {
    try {
      items = await api('/api/projects');
      draw();
    } catch (e) { toast(e.message, 'err'); }
  };

  const exportOf = async (id, fmt) => {
    try {
      const res = await api(`/api/export/${fmt}`, { method: 'POST', body: { id }, raw: true });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      download(url, `${id}.${fmt}`);
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast('Export lancé', 'ok');
    } catch (e) { toast(e.message, 'err'); }
  };

  const card = (p) => {
    const pal = (catalog.palettes || []).find((x) => x.key === p.palette) || { primary: '#0B5FFF', accent: '#00C2A8', dark: '#0A1930' };
    return h('div', { class: 'card', style: { padding: '12px' } },
      h('div', {
        class: 'project-thumb', style: { background: `linear-gradient(135deg, ${pal.dark}, ${pal.primary})` },
        onclick: () => openProject(p.id),
      }, h('div', { class: 't-title' }, p.title)),
      h('div', { class: 'row', style: { marginBottom: '6px' } },
        h('strong', { style: { fontSize: '13.5px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, p.client || 'Client non renseigné'),
        h('div', { style: { flex: 1 } }),
        h('span', { class: 'chip small' }, `${p.sections} sect.`)),
      h('div', { class: 'small muted', style: { marginBottom: '10px' } },
        [p.project, p.date].filter(Boolean).join(' · ') || '—'),
      h('div', { class: 'row wrap', style: { gap: '4px' } },
        h('button', { class: 'btn btn-sm', onclick: () => openProject(p.id) }, icon('doc', 13), 'Ouvrir'),
        h('button', { class: 'btn btn-sm btn-ghost', title: 'Export PDF', onclick: () => exportOf(p.id, 'pdf') }, icon('download', 13)),
        h('button', {
          class: 'btn btn-sm btn-ghost', title: 'Dupliquer',
          onclick: async () => { await api(`/api/projects/${p.id}/duplicate`, { method: 'POST' }); toast('Copie créée', 'ok'); load(); },
        }, icon('copy', 13)),
        h('button', {
          class: 'btn btn-sm btn-ghost', title: 'Supprimer',
          onclick: () => confirmBox('Supprimer le livrable', `« ${p.title} » sera définitivement supprimé.`, async () => {
            await api(`/api/projects/${p.id}`, { method: 'DELETE' }); toast('Supprimé', 'ok'); load();
          }),
        }, icon('trash', 13))));
  };

  function draw() {
    clear(root);
    const filtered = items.filter((p) => !query || [p.title, p.client, p.project].join(' ').toLowerCase().includes(query.toLowerCase()));
    const search = h('input', { class: 'input', placeholder: 'Rechercher un livrable, un client…', value: query,
      style: { maxWidth: '320px' },
      oninput: (e) => { query = e.target.value; draw(); } });
    root.append(h('div', { class: 'row', style: { marginBottom: '4px' } },
      h('div', {},
        h('h2', { style: { margin: 0, fontSize: '20px', letterSpacing: '-.02em' } }, 'Mes livrables'),
        h('div', { class: 'small muted' }, `${items.length} document${items.length > 1 ? 's' : ''} enregistré${items.length > 1 ? 's' : ''} en local`)),
      h('div', { style: { flex: 1 } }),
      search,
      h('button', { class: 'btn btn-primary', onclick: () => go('brief') }, icon('sparkle', 15), 'Nouveau livrable')),
      grid, clear(count));
    clear(grid);
    if (!filtered.length) {
      grid.style.gridTemplateColumns = '1fr';
      grid.append(h('div', { class: 'card', style: { textAlign: 'center', padding: '48px 20px' } },
        h('div', { style: { display: 'grid', placeItems: 'center', marginBottom: '12px', color: 'var(--ink-3)' } }, icon('folder', 40)),
        h('h3', { class: 'card-title' }, query ? 'Aucun résultat' : 'Aucun livrable pour le moment'),
        h('p', { class: 'card-sub' }, query ? 'Essayez un autre mot-clé.' : 'Générez votre premier dossier en quelques secondes avec l’assistant.'),
        !query ? h('button', { class: 'btn btn-primary', onclick: () => go('brief') }, icon('sparkle', 15), 'Créer un livrable') : null));
    } else {
      grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(268px,1fr))';
      filtered.forEach((p) => grid.append(card(p)));
    }
  }

  load();
  return root;
}
