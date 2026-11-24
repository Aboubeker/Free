/* Génère mods/*.mjs à partir de delivra/static/js (imports ES natifs). */
import fs from 'fs';
import path from 'path';

const SRC = path.resolve('../../delivra/static/js');
const OUT = path.resolve('mods');
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

for (const f of fs.readdirSync(SRC).filter((x) => x.endsWith('.js'))) {
  const code = fs.readFileSync(path.join(SRC, f), 'utf8')
    .replace(/from '\.\/([^']+)\.js'/g, "from './$1.mjs'")
    .replace(/import\('\.\/([^']+)\.js'\)/g, "import('./$1.mjs')");
  fs.writeFileSync(path.join(OUT, f.replace(/\.js$/, '.mjs')), code);
}
console.log('mods/ régénéré :', fs.readdirSync(OUT).join(', '));
