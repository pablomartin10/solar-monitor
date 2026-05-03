# 🚀 Guía de Instalación - Solar Monitor

## Instalación Automática (RECOMENDADO)

El script `install.sh` automatiza TODO el proceso. Puedes usarlo de dos formas:

### Opción 1: Clonar + Instalar en un paso

Si **no tienes el repositorio descargado**:

```bash
# Crea un directorio para el proyecto
mkdir solar-projects
cd solar-projects

# Ejecuta el script de instalación
bash <(curl -s https://raw.githubusercontent.com/pablomartin10/solar-monitor/main/install.sh)
```

O simplemente:

```bash
bash install.sh
```

El script te preguntará:
- ¿Deseas clonar el repositorio? → **SÍ**
- ¿Dónde deseas clonar? → (Enter para directorio actual)

### Opción 2: Instalar en un repo existente

Si **ya tienes el repositorio**:

```bash
cd solar-monitor
bash install.sh
```

---

## 🎯 Qué hace el script

### ✅ Verifica la estructura

```
✓ Busca archivos necesarios:
  • docker-compose.yml
  • api/main.py
  • api/requirements.txt
  • api/Dockerfile
  • api/poller.py
  • api/influx.py
  • api/parser.py
  • dashboard/index.html
  • dashboard/nginx.conf
  • config/deye_hybrid.yaml
  • config/deye_4mppt.yaml
```

Si falta alguno, muestra un error claro y ofrece soluciones.

### ✅ Clona el repo (si no existe)

```bash
git clone https://github.com/pablomartin10/solar-monitor.git
```

### ✅ Verifica requisitos

```
✓ Docker instalado
✓ Docker Compose instalado
✓ Git instalado (si necesita clonar)
```

### ✅ Genera `.env` seguro

```
✓ Contraseña InfluxDB aleatoria (25 caracteres)
✓ Token de acceso aleatorio
✓ Configuración bien documentada
```

### ✅ Crea directorios

```
✓ data/
✓ Otros necesarios
```

### ✅ Inicia servicios

```
✓ Descarga imágenes Docker
✓ Inicia contenedores
✓ Verifica salud de servicios
✓ Espera a que estén listos
```

### ✅ Verifica instalación

```
✓ API disponible en /api/health
✓ InfluxDB disponible
✓ Dashboard disponible
```

### ✅ Muestra resultado

```
Dashboard:       http://localhost:80
API Docs:        http://localhost:80/api/docs
InfluxDB:        http://localhost:8086

Credenciales generadas:
Usuario:         influx_admin
Contraseña:      xxxxxxxxxxxxxxxxxxxxx
```

---

## 🔄 Casos de Uso

### Caso 1: Usuario nuevo en Linux/Mac

```bash
# Paso 1: Clona el repo
git clone https://github.com/pablomartin10/solar-monitor.git
cd solar-monitor

# Paso 2: Ejecuta instalación
bash install.sh

# ¡Listo! Abre http://localhost en tu navegador
```

### Caso 2: Usuario nuevo en Windows (WSL2/Git Bash)

```bash
# Instala Git si no lo tienes
# Descarga desde: https://git-scm.com/

# Clona y instala
git clone https://github.com/pablomartin10/solar-monitor.git
cd solar-monitor
bash install.sh
```

### Caso 3: Ya tienes Docker y quieres una instalación manual

```bash
# Descarga sin clonar (ej, desde web)
cd /tu/carpeta/solar-monitor

# Crea .env
cat > .env << 'EOF'
INFLUXDB_USER=influx_admin
INFLUXDB_PASSWORD=mi-contraseña-segura
INFLUXDB_TOKEN=mi-token-seguro
INFLUXDB_ORG=solar
INFLUXDB_BUCKET=inverters
POLL_INTERVAL=60
DASHBOARD_PORT=80
EOF

# Inicia servicios
docker compose up -d
```

### Caso 4: Actualizar después de cambios

```bash
cd solar-monitor

# Pull últimos cambios
git pull

# Reconstruir y reiniciar
docker compose build api
docker compose up -d

# Verificar
curl http://localhost/api/health | jq .
```

---

## 🆘 Solucionar Problemas

### Error: "No se detectó repositorio"

```bash
# Solución 1: Clona manualmente
git clone https://github.com/pablomartin10/solar-monitor.git
cd solar-monitor

# Solución 2: Si ya tienes archivos, colócalos en la carpeta correcta
# Asegúrate que la estructura sea:
# solar-monitor/
# ├── docker-compose.yml
# ├── api/
# ├── dashboard/
# ├── config/
# └── install.sh
```

### Error: "Docker no está instalado"

```bash
# Instala Docker Desktop (incluye Docker Compose)
# Linux: https://docs.docker.com/engine/install/
# Mac: https://www.docker.com/products/docker-desktop
# Windows: WSL2 + Docker Desktop

# Para Linux, después de instalar:
sudo usermod -aG docker $USER
Docker Compose viene incluido en Docker 20.10+
```

### Error: "Falta: api/main.py"

```bash
# Verifica que estés en la carpeta correcta
ls -la

# Debe mostrar:
# docker-compose.yml
# api/
# dashboard/
# config/
# install.sh

# Si no, descarga el repo:
git clone https://github.com/pablomartin10/solar-monitor.git
```

### Error: "Git no está instalado"

```bash
# Instala Git
# Linux: sudo apt-get install git
# Mac: brew install git
# Windows: https://git-scm.com/

# O descarga el ZIP manualmente desde:
# https://github.com/pablomartin10/solar-monitor/archive/main.zip
```

---

## 📋 Variables de Entorno

El script crea automáticamente `.env` con:

```env
# InfluxDB
INFLUXDB_USER=influx_admin
INFLUXDB_PASSWORD=contraseña_aleatoria_25_chars
INFLUXDB_TOKEN=token_aleatorio_25_chars
INFLUXDB_ORG=solar
INFLUXDB_BUCKET=inverters

# Polling (segundos, rango 10-3600)
POLL_INTERVAL=60

# Dashboard
DASHBOARD_PORT=80
```

Para cambiar valores:

```bash
# Edita el archivo
nano .env

# Guarda y reinicia
docker compose restart api
```

---

## 🔒 Seguridad

✅ Script valida estructura del proyecto
✅ Genera credenciales aleatorias
✅ Verifica requisitos antes de instalar
✅ Detecta instalaciones duplicadas
✅ Proporciona mensajes de error claros

---

## 📖 Documentación

Después de instalar, consulta:

- **[README.md](README.md)** - Guía general
- **[API_GUIDE.md](API_GUIDE.md)** - Ejemplos de API REST
- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - Detalles técnicos
- **[.env](.env)** - Todas las variables documentadas

---

## 🆘 Ayuda

Si tienes problemas:

1. **Verifica los logs:**
   ```bash
   docker compose logs -f
   ```

2. **Reinicia servicios:**
   ```bash
   docker compose restart
   ```

3. **Limpia e instala de nuevo:**
   ```bash
   docker compose down -v
   bash install.sh
   ```

4. **Issues en GitHub:**
   https://github.com/pablomartin10/solar-monitor/issues

---

## ✅ Verificación

Después de instalar, verifica que todo funciona:

```bash
# Health check
curl http://localhost/api/health | jq .

# Dashboard
# Abre http://localhost en navegador

# InfluxDB UI
# Abre http://localhost:8086

# API Docs
# Abre http://localhost/api/docs
```

¡Todo listo! 🎉
