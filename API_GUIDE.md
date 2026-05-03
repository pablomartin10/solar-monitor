# 📖 Guía de Uso de la API Solar Monitor

## 🚀 Inicio Rápido

### 1. Instalación
```bash
bash install.sh
```

### 2. Acceder a Dashboard
Abre http://localhost en tu navegador

### 3. Documentación Interactiva
http://localhost/api/docs (Swagger UI)

---

## 📋 Ejemplos de API

### 1. Listar todos los inversores
```bash
curl http://localhost/api/inverters | jq .
```

**Respuesta:**
```json
[
  {
    "id": "abc123",
    "name": "Casa Principal",
    "host": "192.168.1.100",
    "port": 8899,
    "serial": "2712345678",
    "type": "hybrid",
    "slave": 1,
    "status": "online",
    "last_update": "2026-05-03T10:30:45.123456Z",
    "created_at": "2026-05-01T08:00:00Z",
    "poll_count": 1250,
    "poll_errors": 0,
    "data": { ... }
  }
]
```

---

### 2. Añadir un nuevo inversor

```bash
curl -X POST http://localhost/api/inverters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Casa Principal",
    "host": "192.168.1.100",
    "port": 8899,
    "serial": "2712345678",
    "type": "hybrid",
    "slave": 1
  }'
```

**Validaciones automáticas:**
- ❌ IP inválida → `ValueError: Invalid IP or hostname`
- ❌ Puerto fuera de rango → `ValueError: Port must be between 1 and 65535`
- ❌ Tipo no soportado → `ValueError: Unsupported inverter type`
- ❌ Duplicado → `409 Conflict: Inverter with same host/port/serial already exists`

---

### 3. Obtener detalles de un inversor

```bash
curl http://localhost/api/inverters/abc123 | jq .
```

---

### 4. Editar un inversor

```bash
curl -X PUT http://localhost/api/inverters/abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Casa de Verano",
    "port": 8899
  }'
```

> **Nota:** Al cambiar configuración, el estado se resetea a "unknown" y se reinicia el poller

---

### 5. Eliminar un inversor

```bash
curl -X DELETE http://localhost/api/inverters/abc123
```

---

### 6. Forzar lectura inmediata

```bash
curl -X POST http://localhost/api/inverters/abc123/refresh
```

**Respuesta:**
```json
{
  "status": "queued"
}
```

---

### 7. Ver estado del sistema

```bash
curl http://localhost/api/health | jq .
```

**Respuesta:**
```json
{
  "status": "ok",
  "timestamp": "2026-05-03T10:30:45.123456Z",
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
    "last_poll": "2026-05-03T10:30:30.123456Z"
  },
  "influxdb": {
    "connected": true
  },
  "supported_types": ["hybrid", "4mppt"]
}
```

---

### 8. Obtener histórico de una métrica

```bash
# Últimas 24 horas
curl "http://localhost/api/inverters/abc123/history?metric=Daily%20Production&hours=24" | jq .

# Última semana
curl "http://localhost/api/inverters/abc123/history?metric=Daily%20Production&hours=168" | jq .

# Últimos 30 días (máximo)
curl "http://localhost/api/inverters/abc123/history?metric=Daily%20Production&hours=720" | jq .
```

**Respuesta:**
```json
[
  {
    "time": "2026-05-03T09:00:00Z",
    "value": 42.5
  },
  {
    "time": "2026-05-03T09:30:00Z",
    "value": 43.1
  },
  ...
]
```

---

### 9. Obtener métricas disponibles

```bash
curl http://localhost/api/inverters/abc123/metrics | jq .
```

**Respuesta:**
```json
[
  "Daily Production",
  "Total Production",
  "PV1 Power",
  "PV2 Power",
  "Battery Power",
  "Grid Frequency",
  ...
]
```

---

## 🔍 Validación de Entrada

### IP y Hostname válidos
```bash
✓ "192.168.1.100"
✓ "inverter.local"
✓ "192.168.100.1"
✗ "999.999.999.999"
✗ "invalid..host"
```

### Puertos válidos
```bash
✓ "8899"
✓ "80"
✓ "65535"
✗ "70000"
✗ "0"
```

### Slave IDs válidos
```bash
✓ "0"
✓ "1"
✓ "255"
✗ "256"
✗ "-1"
```

### Tipos de inversor válidos
```bash
✓ "hybrid"
✓ "4mppt"
✗ "8mppt"
✗ "hybrid-new"
```

---

## 📊 Monitoreo

### Ver estadísticas en tiempo real
```bash
watch -n 5 'curl -s http://localhost/api/health | jq .'
```

### Ver logs de la API
```bash
docker compose logs -f api
```

### Ver solo errores
```bash
docker compose logs -f api | grep -i "error\|failed"
```

### Ver solo poleos exitosos
```bash
docker compose logs -f api | grep "Poll OK"
```

---

## 🚨 Troubleshooting

### Inversor muestra "offline"
```bash
# Verificar que el data logger es accesible
ping 192.168.1.100

# Ver logs para más detalles
docker compose logs -f api | grep -A 2 "nombre-inversor"

# Forzar lectura
curl -X POST http://localhost/api/inverters/id/refresh
```

### API no responde
```bash
# Verificar que el contenedor está corriendo
docker compose ps

# Reiniciar API
docker compose restart api

# Ver logs de error
docker compose logs api
```

### InfluxDB no accesible
```bash
# Verificar que el contenedor está corriendo
docker compose ps influxdb

# Reiniciar InfluxDB
docker compose restart influxdb

# Ver logs
docker compose logs influxdb
```

---

## 🔧 Configuración Avanzada

### Cambiar intervalo de polling
Edita `.env` y modifica `POLL_INTERVAL`:
```env
POLL_INTERVAL=30  # Leer cada 30 segundos (mínimo: 10s)
```

Luego reinicia:
```bash
docker compose restart api
```

### Cambiar puerto del dashboard
Edita `.env`:
```env
DASHBOARD_PORT=8080
```

Reinicia:
```bash
docker compose down && docker compose up -d
```

---

## 📈 Casos de Uso

### 1. Integración con Home Assistant
```python
import requests

api_url = "http://localhost/api"

# Obtener potencia actual
response = requests.get(f"{api_url}/inverters/abc123/history?metric=PV1%20Power&hours=1")
latest = response.json()[-1] if response.json() else None
```

### 2. Exportar datos para análisis
```bash
curl http://localhost/api/inverters | jq . > inverters_backup.json
```

### 3. Crear alertas
```bash
#!/bin/bash
while true; do
  status=$(curl -s http://localhost/api/health | jq -r '.inverters.offline')
  if [ "$status" -gt 0 ]; then
    echo "⚠️ ALERTA: $status inversores offline"
    # Aquí enviar email, webhook, etc.
  fi
  sleep 300  # Cada 5 minutos
done
```

---

## 📚 Referencias

- **OpenAPI Docs**: http://localhost/api/docs
- **README**: Ver README.md
- **Mejoras**: Ver IMPROVEMENTS.md
- **InfluxDB**: http://localhost:8086
