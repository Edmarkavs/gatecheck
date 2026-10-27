# CUENTAS Y CREDENCIALES

Documento de control: qué existe, quién lo controla, dónde vive el secreto y qué falta.

## Ya operativo (creado y verificado en esta sesión)

| Recurso | Valor | Control | Secreto |
|---|---|---|---|
| Repo público | `github.com/Edmarkavs/gatecheck` | tu cuenta GitHub `Edmarkavs` (sesión ya autenticada en esta máquina) | no aplica |
| Web | `https://edmarkavs.github.io/gatecheck/` | GitHub Pages desde `docs/` | no aplica |
| Escáner gratis | GitHub Actions `scan.yml` | `GITHUB_TOKEN` del repo (lo inyecta GitHub, nadie lo copia) | ninguno en disco |
| CI / tests | `.github/workflows/ci.yml` | idem | ninguno |
| Stripe | cuenta existente tuya | tú | **falta la API key** (ver abajo) |

## Lo que NO puedo crear yo, y por qué

No tecleo contraseñas, tarjetas ni códigos 2FA: es una restricción dura de mi entorno,
no una preferencia. Por eso las cuentas que dependen de eso quedan a un clic de ti.
Nada de esto bloquea el trabajo: el producto ya funciona sin ellas.

| Cuenta | Para qué | Estado | Quién la crea |
|---|---|---|---|
| Stripe API + webhook | cobrar suscripciones | pendiente | tú (o me pasas la clave restringida) |
| Dominio (`gatecheck.*`) | marca propia en vez de `github.io` | opcional | tú, 10 min |
| X (Twitter) | distribución | pendiente | tú, inicio de sesión en el navegador |
| beehiiv / Buttondown | newsletter | opcional | puede esperar al primer informe |
| Polar (alternativa a Stripe) | MoR sin entidad en EE. UU. | no necesario si usas Stripe | — |

## Cómo pasarme las claves (seguro)

1. **Stripe → Developers → API keys → Create restricted key** con permisos:
   `Checkout Sessions: write`, `Products: write`, `Prices: write`, `Webhooks: write`,
   `Customers: read`. Nada más. Prefijo `rk_live_…` o `rk_test_…`.
2. Guárdala en `C:\Users\edava\AppData\Local\hermes\.env` como
   `STRIPE_SECRET_KEY=...` (nunca en el repo, nunca en el chat).
3. Para el webhook: `stripe listen` o el dashboard; el secreto va como
   `STRIPE_WEBHOOK_SECRET=...`.

Con eso puedo crear productos, precios, enlaces de pago y probar un checkout real.

## Qué NO hacer

- No pegar claves en el chat ni en un commit: si se filtran, hay que rotarlas.
- No usar la clave `sk_live` completa con permisos totales si basta una restringida.
- No subir `.env` al repo (ya está en `.gitignore`).
