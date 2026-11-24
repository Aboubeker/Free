/* Delivra — paramètres : moteur IA, valeurs par défaut, stockage local. */
import { h, clear, icon, api, toast } from './lib.js';

export function settingsView(ctx) {
  const { catalog } = ctx;
  const root = h('div', { class: 'page', style: { maxWidth: '860px' } });
  const status = h('div', { class: 'stack', style: { gap: '8px' } });

  const providers = [
    ['local', 'Moteur local (recommandé)', 'Aucune connexion, aucune donnée envoyée.'],
    ['openai', 'OpenAI', 'Modèles GPT — clé API requise.'],
    ['mistral', 'Mistral AI', 'Modèles européens, hébergement UE.'],
    ['ollama', 'Ollama (local)', 'Serveur local compatible OpenAI, aucune clé.'],
    ['anthropic', 'Anthropic', 'Modèles Claude — clé API requise.'],
    ['custom', 'Endpoint personnalisé', 'Tout service compatible OpenAI.'],
  ];

  const draw = async () => {
    let s = {};
    try { s = await api('/api/settings'); } catch { /* valeurs par défaut */ }
    const status2 = await api('/api/ai/status').catch(() => ({ provider: 'local', available: false }));
    clear(root);
    const providerSel = h('select', { class: 'select' },
      ...providers.map(([v, l]) => h('option', { value: v, selected: (s.provider || 'local') === v }, l)));
    providerSel.value = s.provider || 'local';
    const keyInput = h('input', { class: 'input', type: 'password', placeholder: s.api_key_set ? s.api_key : 'sk-…', value: '' });
    const modelInput = h('input', { class: 'input', value: s.model || '', placeholder: 'gpt-4o-mini / mistral-large-latest / llama3.1' });
    const urlInput = h('input', { class: 'input', value: s.base_url || '', placeholder: 'http://localhost:11434/v1' });

    const save = async () => {
      try {
        const r = await api('/api/settings', { method: 'POST', body: {
          provider: providerSel.value, model: modelInput.value, base_url: urlInput.value, api_key: keyInput.value,
        } });
        toast(r.ai.available ? `Fournisseur ${r.ai.provider} actif` : 'Moteur local actif', 'ok');
        clear(status);
        status.append(h('div', { class: 'chip ' + (r.ai.available ? 'ok' : '') },
          r.ai.available ? `IA connectée : ${r.ai.provider}` : 'Moteur local (hors ligne)'));
        keyInput.value = '';
      } catch (e) { toast(e.message, 'err'); }
    };

    root.append(
      h('div', { class: 'stack' },
        h('div', { class: 'row' },
          h('div', {},
            h('h2', { style: { margin: 0, fontSize: '20px', letterSpacing: '-.02em' } }, 'Paramètres'),
            h('div', { class: 'small muted' }, 'Delivra fonctionne hors ligne. Connecter un modèle est facultatif.'))),
        h('div', { class: 'card' },
          h('div', { class: 'row', style: { marginBottom: '12px' } },
            h('h3', { class: 'card-title', style: { margin: 0 } }, 'Moteur de génération'),
            h('div', { style: { flex: 1 } }),
            h('span', { class: 'badge-ai' }, icon('sparkle', 13), status2.available ? status2.provider : 'local')),
          h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Fournisseur'), providerSel),
          h('p', { class: 'hint', style: { marginTop: '-6px', marginBottom: '12px' } },
            providers.find((p) => p[0] === providerSel.value)?.[2] || ''),
          h('div', { class: 'row-2' },
            h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Clé API'), keyInput),
            h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'Modèle'), modelInput)),
          h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'URL de base (Ollama / personnalisé)'), urlInput),
          h('div', { class: 'row', style: { marginTop: '6px' } },
            h('button', { class: 'btn btn-primary', onclick: save }, icon('save', 15), 'Enregistrer'),
            h('button', {
              class: 'btn', onclick: async (e) => {
                const btn = e.currentTarget; btn.disabled = true;
                try {
                  await save();
                  const r = await api('/api/settings/test', { method: 'POST', body: {} });
                  toast(r.message, r.ok ? 'ok' : 'warn');
                } catch (err) { toast(err.message, 'err'); } finally { btn.disabled = false; }
              },
            }, icon('bolt', 15), 'Tester la connexion'),
            h('div', { style: { flex: 1 } }),
            status),
          h('div', { class: 'hint', style: { marginTop: '10px' } },
            'Les clés sont stockées localement dans le dossier de données de l’application (settings.json). ',
            'Elles ne sont jamais transmises ailleurs qu’au fournisseur choisi.')),
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'Stockage & confidentialité'),
          h('div', { class: 'check-list', style: { marginTop: '8px' } },
            ...[
              'Documents enregistrés en JSON lisible dans votre dossier personnel.',
              'Aucun envoi de fichier vers un serveur : les exports sont générés localement.',
              'Supprimer un livrable retire définitivement son fichier du disque.',
            ].map((t) => h('div', { class: 'check-item' }, h('span', { class: 'dot ok' }, '✓'), h('div', {}, t)))),
          s.path_fallback ? null : null),
        h('div', { class: 'card' },
          h('h3', { class: 'card-title' }, 'À propos'),
          h('div', { class: 'grid grid-2', style: { marginTop: '10px' } },
            h('div', {}, h('div', { class: 'small muted' }, 'Version'), h('strong', {}, ctx.version || '1.0.0')),
            h('div', {}, h('div', { class: 'small muted' }, 'Polices embarquées'),
              h('strong', {}, 'Manrope, Sora, Source Serif, JetBrains Mono')),
            h('div', {}, h('div', { class: 'small muted' }, 'Formats d’export'),
              h('strong', {}, 'PDF · DOCX · PPTX · Markdown · ZIP')),
            h('div', {}, h('div', { class: 'small muted' }, 'Licence des polices'), h('strong', {}, 'SIL Open Font License 1.1'))))));
  };
  draw();
  return root;
}
