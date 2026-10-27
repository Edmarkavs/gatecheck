# RUNBOOK — operación de Gatecheck

Todo lo que hay que hacer para operar el producto, sin adivinar nada.

## 1. Escanear un repo (local, gratis, offline)

```bash
cd C:/Users/edava/projects/agentreadiness
python scanner/scan.py --local=C:/ruta/al/repo
python scanner/scan.py --local=. --json-out=/tmp/gc.json --markdown
```

Salida: `out/<owner>__<repo>.html` + `.json`. Sin red, sin LLM, ~10 s.

## 2. Escanear un repo público remoto

```bash
python scanner/scan.py owner/repo --out=./out
python scanner/scan.py --file=repos.txt --csv=corpus.csv --stats=stats.json --workers=8
```

Requiere `gh auth login` (ya está autenticado como `Edmarkavs`).
Las respuestas de la API se cachean 6-24 h en `.cache/` (gitignoreado).

## 3. Escaneo gratis para un usuario (IssueOps, coste $0)

1. El usuario abre un issue titulado `scan: owner/repo`.
2. `.github/workflows/scan.yml` lo detecta, corre el escáner, comenta la tabla y
   publica el HTML en `docs/reports/`.
3. Nada que mantener: usa el `GITHUB_TOKEN` del repo, sin servidores.

## 4. Republicar la web

`docs/` es la raíz de GitHub Pages (rama `main`). Cualquier push a `docs/` publica.
URL: https://edmarkavs.github.io/gatecheck/

## 5. Regenerar la portada y los datos

```bash
python scanner/scan.py --file=repos.txt --out=./out --csv=corpus.csv --stats=stats.json --workers=8
cp out/SawyerHood__dev-browser.html         docs/reports/demo-A.html
cp out/coreyhaines31__marketingskills.html  docs/reports/demo-B.html
cp out/VoltAgent__awesome-agent-skills.html docs/reports/demo-F.html
cp corpus.csv stats.json docs/reports/
```

Después, actualizar los números de `docs/index.html` a mano para que coincidan con
`docs/reports/stats.json`. **Regla: nunca publicar una cifra que no esté en stats.json.**

## 6. Cadencia semanal (lunes)

1. `python scanner/scan.py --file=repos.txt ...` → stats nuevos.
2. Escribir el informe con los deltas (repos que empeoraron, nuevos F).
3. Publicar en el issue fijado + X.
4. Re-escanear los repos de clientes de pago y avisar si baja el score.

## 7. Qué no hacer

- No añadir llamadas a modelos al escáner: la determinación es el producto.
- No ejecutar código del repo escaneado, nunca, ni "solo los tests".
- No editar a mano `docs/reports/*.html`: son artefactos generados.
