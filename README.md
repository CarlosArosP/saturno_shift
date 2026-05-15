# Saturno – Levantamiento de Inconsistencias de Turno

App web para registrar y consultar inconsistencias de turno en tiendas Walmart Chile.  
Stack: **FastAPI + HTMX + Tailwind + Turso (SQLite cloud) + Render (hosting)**

---

## 🌐 URL pública (una vez deployado)
```
https://saturno-shift.onrender.com
```

## 🗄️ Base de datos
- Proveedor: **Turso** (SQLite en la nube, free tier)
- DB: `saturno-shift` — cuenta `carlosarosp`
- Los datos **nunca se pierden** al actualizar el código

---

## 🚀 Deploy en Render (paso a paso)

### 1. Push a GitHub
```bash
cd C:\Users\caros\Documents\puppy_workspace\saturno_shift
git push -u origin master
```
> Si pide contraseña, usa un Personal Access Token de GitHub (no tu password).

### 2. Configurar Render
1. Ve a https://dashboard.render.com/new/web
2. Conecta tu cuenta GitHub → selecciona repo `saturno-shift`
3. Render detecta `render.yaml` automáticamente
4. En **Environment Variables** agrega:

| Variable | Valor |
|---|---|
| `TURSO_URL` | `https://saturno-shift-carlosarosp.aws-us-west-2.turso.io` |
| `TURSO_AUTH_TOKEN` | `eyJhbGci...` (tu token completo) |

5. Clic **"Create Web Service"** → espera ~2 min → listo 🎉

---

## 🔧 Desarrollo local

```bash
# 1. Copia credenciales
copy .env.example .env
# (ya configurado si ejecutaste la app antes)

# 2. Instala dependencias
uv pip install -r requirements.txt

# 3. Corre el servidor
uvicorn main:app --reload --port 8502

# 4. Abre http://localhost:8502
```

> ⚠️ Desde la red Walmart, Turso no es accesible localmente (firewall).  
> El servidor sí funciona — solo que no puede conectar a la DB desde aquí.  
> Para probar local, usa una red externa (celular hotspot).

---

## 📦 Migrar datos históricos a Turso

Si tienes datos en la DB local de Windows:
```bash
python migrate_to_turso.py
```

---

## 🏗️ Estructura del proyecto

```
saturno_shift/
├── main.py              # FastAPI app (rutas, lógica)
├── database.py          # Cliente Turso HTTP API
├── migrate_to_turso.py  # Script migracion datos locales → Turso
├── requirements.txt
├── render.yaml          # Config deploy Render
├── .env                 # Credenciales (NO commitear)
├── .env.example         # Template para nuevos devs
├── .gitignore
└── templates/
    ├── index.html
    └── partials/
        └── tabla.html
```

---

## 👤 Autor
**Carlos Aros** · Gerencia de Operaciones · Walmart Chile  
Creado con Code Puppy 🐶
