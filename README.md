# Solar Monitor 🌞

Dashboard para monitorización de inversores Deye/Solarman con InfluxDB.

## Estructura

```
solar-monitor/
├── docker-compose.yml
├── .env                    ← credenciales y configuración
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py             ← FastAPI app
│   ├── poller.py           ← lectura via PySolarmanV5
│   ├── parser.py           ← decodificación de registros Modbus
│   └── influx.py           ← escritura/lectura InfluxDB
├── config/
│   ├── deye_hybrid.yaml    ← definición de registros Hybrid
│   └── deye_4mppt.yaml     ← definición de registros 4 MPPT
├── dashboard/
│   ├── index.html          ← dashboard web
│   └── nginx.conf          ← proxy /api/ → FastAPI
└── data/
    └── inverters.json      ← configuración de inversores (auto-generado)
```

## Instalación Rápida ⚡

### Opción 1: Automática (Recomendado)
```bash
bash install.sh
```

El script realiza automáticamente:
1. ✅ Verifica que Docker esté instalado
2. ✅ Genera `.env` con credenciales seguras
3. ✅ Crea directorios necesarios
4. ✅ Inicia todos los servicios
5. ✅ Verifica que todo funciona
6. ✅ Muestra URLs de acceso

### Opción 2: Manual

#### Requisitos
- Docker + Docker Compose v2
- El host debe tener acceso de red a los data loggers Solarman

#### Configuración
Crea o edita `.env` con tus valores:
```env
INFLUXDB_USER=influx_admin
INFLUXDB_PASSWORD=tu-password-seguro
INFLUXDB_TOKEN=tu-token-secreto-largo
INFLUXDB_ORG=solar
INFLUXDB_BUCKET=inverters
POLL_INTERVAL=60          # segundos entre lecturas (10-3600)
DASHBOARD_PORT=80         # puerto del dashboard
```

#### Arrancar
```bash
docker compose up -d
```

El primer inicio descarga las imágenes y configura InfluxDB automáticamente (~1-2 min).

#### Acceder
- **Dashboard**: http://localhost (o el puerto configurado)
- **API Swagger UI**: http://localhost/api/docs
- **InfluxDB UI**: http://localhost:8086
- **Health Check**: http://localhost/api/health

### Añadir Inversores
Desde el dashboard, pulsa **"+ Añadir inversor"**:
- **Nombre**: identificador libre (p.ej., "Casa principal")
- **IP/Host**: IP del data logger Solarman (no del inversor)
- **Puerto**: 8899 (por defecto Solarman)
- **SN Logger**: número de serie del data logger (ver etiqueta del dispositivo)
- **Tipo**: `Hybrid 2MPPT` o `4 MPPT`
- **Slave ID**: 1 (en la mayoría de casos)

> **Nota**: La validación rechaza:
> - IPs inválidas
> - Puertos fuera de rango (1-65535)
> - Tipos de inversor no soportados
> - Duplicados (mismo host/puerto/serial)

## API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET    | `/api/inverters` | Lista inversores con últimos datos |
| POST   | `/api/inverters` | Añadir inversor (con validación) |
| GET    | `/api/inverters/{id}` | Obtener detalles de inversor |
| PUT    | `/api/inverters/{id}` | Editar inversor |
| DELETE | `/api/inverters/{id}` | Eliminar inversor |
| POST   | `/api/inverters/{id}/refresh` | Forzar lectura inmediata |
| GET    | `/api/inverters/{id}/history` | Histórico de métrica (max 30 días) |
| GET    | `/api/inverters/{id}/metrics` | Métricas disponibles del inversor |
| GET    | `/api/health` | Estado y estadísticas del sistema |

### Ejemplo: Ver estadísticas del sistema
```bash
curl http://localhost/api/health | jq .
```

Respuesta:
```json
{
  "status": "ok",
  "timestamp": "2026-05-03T10:30:45Z",
  "inverters": {
    "total": 3,
    "online": 2,
    "offline": 1,
    "unknown": 0
  },
  "polling": {
    "interval_seconds": 60,
    "total_polls": 1250,
    "successful": 1200,
    "failed": 50,
    "last_poll": "2026-05-03T10:30:30Z"
  },
  "supported_types": ["hybrid", "4mppt"]
}
```

### Validación de Entrada

La API valida automáticamente:
- ✅ Formato de IP/hostname válido
- ✅ Puertos entre 1-65535
- ✅ Slave ID Modbus entre 0-255
- ✅ Tipo de inversor soportado
- ✅ Detección de duplicados
- ✅ Nombres entre 1-100 caracteres
- ✅ Rango de histórico: máximo 720 horas (30 días)

## Gestión

```bash
# Ver logs de todos los servicios
docker compose logs -f

# Ver logs de la API solamente
docker compose logs -f api

# Ver logs de InfluxDB
docker compose logs -f influxdb

# Reiniciar solo la API
docker compose restart api

# Parar todos los servicios
docker compose down

# Parar y borrar todos los datos
docker compose down -v

# Reconstruir la imagen de la API
docker compose build api && docker compose up -d api
```

## 🎯 Mejoras Recientes

### API
- ✅ **Validación robusta** de parámetros (IP, puerto, slave ID, tipo)
- ✅ **Detección de duplicados** automática
- ✅ **Estadísticas de polling** (total de poleos, éxitos, fallos)
- ✅ **Tracking de inversores** (fecha creación, errores)
- ✅ **Documentación OpenAPI** en `/api/docs`
- ✅ **Mejor manejo de errores** con mensajes descriptivos
- ✅ **Límites de parámetros** bien definidos (ej: histórico máximo 30 días)

### Instalación
- ✅ **Script de instalación automático** (`install.sh`)
- ✅ **Generación segura de contraseñas** aleatorias
- ✅ **Verificación de requisitos** (Docker, Docker Compose)
- ✅ **Salud de servicios** verificada
- ✅ **Interfaz amigable** con colores y progreso

Ver documento [IMPROVEMENTS.md](IMPROVEMENTS.md) para detalles completos.

## Añadir más tipos de inversor

1. Añade el archivo YAML de registros en `config/`
2. Edita `YAML_MAP` en `api/poller.py` con la nueva clave y nombre de archivo
3. Añade el renderizado correspondiente en `dashboard/index.html`
4. Reconstruye: `docker compose build api && docker compose up -d api`

## Notas

- Los datos se guardan en InfluxDB indefinidamente. Para configurar retención:
  Accede a InfluxDB UI → Data → Buckets → inverters → Edit retention
- La configuración de inversores se persiste en `data/inverters.json`
- El dashboard hace auto-refresh cada 60 segundos
- Haz clic en cualquier métrica (excepto tensiones fijas) para ver su histórico
