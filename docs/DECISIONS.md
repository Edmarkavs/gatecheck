# DECISIONES

Registro de las decisiones que definen el producto, con la evidencia que las sostiene.

## D1 — No vender packs de skills (26 oct 2026)

**Evidencia.** El marketplace oficial de Anthropic abrió el 1-may-2026 con ~600 skills y
15% de comisión. Hay 6+ directorios terceros con 3.000-7.200 skills cada uno. GitHub
indexa 6,65 M `SKILL.md` y 1,16 M `AGENTS.md`. Repos gratuitos con 60-110 K estrellas
recaudan $0. Un experimento público: 20 skills a €9,99 → 1 venta, €8,26 netos.

**Decisión.** El archivo de skill es commodity. No es el producto.

## D2 — Vender verificación, no generación

**Evidencia.** Del mismo experimento: de 20 skills, solo 8 se volverían a ejecutar y
todos eran **transformaciones**; los 4 que mataría eran **generadores**. Un generador de
skills es la peor forma de producto: no tiene criterio de aceptación.

**Decisión.** El producto audita material real del cliente y devuelve un artefacto
verificable (score + lista de fallos). Señal propietaria: *el contexto dice la verdad*
(compara los comandos y rutas que promete `AGENTS.md` contra el árbol real).

## D3 — Newsletter y X son canales, no productos

**Evidencia.** Patrocinios a CPM $15-30 en 1-5 K subs: $1.000/mes exige 7.700-15.400
suscriptores y 8-18 meses. X retiró el reparto el 7-sep-2026; el nuevo programa paga
$1-20 por millón de impresiones y exige 5 M impresiones/3 meses.

**Decisión.** El informe semanal de escaneos alimenta la newsletter con dato propio
(no curación de links). X distribuye. Ninguno se espera como fuente de ingreso directa.

## D4 — Precios

| Plan | Precio | Clientes para $1.000 |
|---|---|---|
| Free | $0 | — (lead magnet) |
| Solo | $29/mes | 35 |
| **Team** | **$99/mes** | **10** |
| Agency | $249/mes | 4 |
| Fix pack | $149 una vez | — |

**Razonamiento.** Un CI que bloquea merges lo paga el dueño del repo o el tech lead, no
un individuo. Precio alto = menos clientes = menos soporte = más automatizable. Objetivo
realista: 8 Team + 1 Agency = $1.041 MRR.

## D5 — Infraestructura a coste $0 hasta el primer pago

GitHub Pages + Actions + IssueOps dan escáner público, informes y CI sin servidor, sin
dominio y sin tarjeta. Stripe entra cuando haya algo que cobrar; el dominio cuando haya
tráfico que justifique marca propia.

## D6 — Determinismo sobre "inteligencia"

El escáner no llama a ningún modelo. Mismo repo, mismo score, siempre: eso permite
gatear merges en CI, que es la única forma de que alguien pague mes a mes.

## D7 — Marca

**Gatecheck** (nombre de trabajo). `gatecheck.dev` y `.com` están tomados; alternativas
libres verificadas por DNS: `assaylab.dev`, `normative.dev`, `readysignal.dev`,
`agentassay.dev`. La marca no bloquea nada: hasta que haya ingresos, la URL es
`edmarkavs.github.io/gatecheck`.
