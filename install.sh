#!/bin/bash
set -e

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                    Solar Monitor Installation Script                       ║
# ║                                                                            ║
# ║ Complete setup: clones repo, verifies files, configures, and starts       ║
# ║                                                                            ║
# ║ Usage:                                                                     ║
# ║   bash install.sh                 (run from within project)               ║
# ║   bash install.sh /path/to/clone   (clone to specific path)               ║
# ╚════════════════════════════════════════════════════════════════════════════╝

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_NAME="solar-monitor"
GITHUB_REPO="https://github.com/pablomartin10/solar-monitor.git"
ENV_FILE="$SCRIPT_DIR/.env"
DATA_DIR="$SCRIPT_DIR/data"
CLONE_PATH="${1:-.}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${1}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Repository setup
# ─────────────────────────────────────────────────────────────────────────────

is_solar_monitor_repo() {
    # Check if we're in a solar-monitor repo directory
    [ -f "$1/docker-compose.yml" ] && [ -d "$1/api" ] && [ -d "$1/dashboard" ] && [ -d "$1/config" ]
}

clone_repo() {
    local target_dir="$1"
    local temp_clone="/tmp/${PROJECT_NAME}_$$"
    
    print_header "Clonando repositorio"
    
    if [ -d "$target_dir/$PROJECT_NAME" ] && is_solar_monitor_repo "$target_dir/$PROJECT_NAME"; then
        print_info "El repositorio ya existe en $target_dir/$PROJECT_NAME"
        SCRIPT_DIR="$target_dir/$PROJECT_NAME"
        return
    fi
    
    print_info "Descargando desde $GITHUB_REPO..."
    
    if ! command -v git &> /dev/null; then
        print_error "Git no está instalado"
        echo ""
        echo "Instala Git:"
        echo "  Ubuntu/Debian: sudo apt-get install git"
        echo "  macOS: brew install git"
        echo "  O descarga desde: https://git-scm.com/"
        exit 1
    fi
    
    if git clone "$GITHUB_REPO" "$temp_clone" 2>/dev/null; then
        mkdir -p "$target_dir"
        mv "$temp_clone" "$target_dir/$PROJECT_NAME"
        SCRIPT_DIR="$target_dir/$PROJECT_NAME"
        print_success "Repositorio clonado en $SCRIPT_DIR"
    else
        print_error "No se pudo clonar el repositorio"
        exit 1
    fi
}

verify_project_structure() {
    print_header "Verificando estructura del proyecto"
    
    local required_files=(
        "docker-compose.yml"
        "api/main.py"
        "api/requirements.txt"
        "api/Dockerfile"
        "api/poller.py"
        "api/influx.py"
        "api/parser.py"
        "dashboard/index.html"
        "dashboard/nginx.conf"
        "config/deye_hybrid.yaml"
        "config/deye_4mppt.yaml"
    )
    
    local missing=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$SCRIPT_DIR/$file" ]; then
            missing+=("$file")
            print_error "Falta: $file"
        else
            print_success "Encontrado: $file"
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        print_header "⚠ Error: Faltan archivos del proyecto"
        echo ""
        echo "Archivos faltantes:"
        for f in "${missing[@]}"; do
            echo "  • $f"
        done
        echo ""
        echo "Soluciones:"
        echo "  1. Clona el repo: git clone $GITHUB_REPO"
        echo "  2. Descarga de: https://github.com/pablomartin10/solar-monitor"
        exit 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Check prerequisites
# ─────────────────────────────────────────────────────────────────────────────

check_requirements() {
    print_header "Verificando requisitos previos"
    
    local missing=()
    
    if ! command -v docker &> /dev/null; then
        missing+=("Docker")
        print_error "Docker no instalado"
    else
        print_success "Docker instalado"
    fi
    
    if ! docker compose version &> /dev/null 2>&1; then
        missing+=("Docker Compose")
        print_error "Docker Compose no instalado"
    else
        print_success "Docker Compose instalado"
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        print_header "Instalación de dependencias"
        echo -e "${YELLOW}Por favor instala:${NC}"
        for item in "${missing[@]}"; do
            echo "  • $item"
        done
        echo ""
        echo "Ubuntu/Debian:"
        echo "  curl -fsSL https://get.docker.com | sh"
        echo "  sudo usermod -aG docker \$USER"
        echo ""
        echo "O visita: https://docs.docker.com/get-docker/"
        exit 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Generate secure passwords
# ─────────────────────────────────────────────────────────────────────────────

generate_password() {
    # Generate a secure random password
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# ─────────────────────────────────────────────────────────────────────────────
# Create .env file
# ─────────────────────────────────────────────────────────────────────────────

setup_env() {
    print_header "Configuración de variables de entorno"
    
    if [ -f "$ENV_FILE" ]; then
        print_warning "El archivo .env ya existe"
        read -p "¿Quieres regenerarlo? (s/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            print_info "Usando .env existente"
            return
        fi
    fi
    
    print_info "Generando variables de entorno..."
    
    local influx_user="influx_admin"
    local influx_pass=$(generate_password)
    local influx_token=$(generate_password)
    local influx_org="solar"
    local influx_bucket="inverters"
    local poll_interval="60"
    local dashboard_port="80"
    
    cat > "$ENV_FILE" << EOF
# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                    Solar Monitor Configuration                             ║
# ║                                                                            ║
# ║ Generated by install.sh - $(date)                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# ─────── InfluxDB ──────────────────────────────────────────────────────────
INFLUXDB_USER=${influx_user}
INFLUXDB_PASSWORD=${influx_pass}
INFLUXDB_TOKEN=${influx_token}
INFLUXDB_ORG=${influx_org}
INFLUXDB_BUCKET=${influx_bucket}

# ─────── Polling ───────────────────────────────────────────────────────────
# Interval en segundos entre lecturas de inversores (rango: 10-3600)
POLL_INTERVAL=${poll_interval}

# ─────── Dashboard ─────────────────────────────────────────────────────────
DASHBOARD_PORT=${dashboard_port}

# ─────── Notas ─────────────────────────────────────────────────────────────
# • Modifica POLL_INTERVAL según necesidad (más bajo = más actualizaciones)
# • DASHBOARD_PORT es el puerto HTTP del dashboard (por defecto 80)
# • InfluxDB UI estará disponible en: http://localhost:8086
# • API docs estará disponible en: http://localhost/api/docs
EOF

    print_success ".env creado con configuración segura"
    print_info "Contraseña de InfluxDB: ${YELLOW}${influx_pass}${NC}"
    print_info "Token de InfluxDB: ${YELLOW}${influx_token:0:20}...${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Create data directory
# ─────────────────────────────────────────────────────────────────────────────

setup_data_dir() {
    print_header "Preparación de directorios"
    
    if [ ! -d "$DATA_DIR" ]; then
        mkdir -p "$DATA_DIR"
        print_success "Directorio de datos creado: $DATA_DIR"
    else
        print_info "Directorio de datos ya existe"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Start services
# ─────────────────────────────────────────────────────────────────────────────

start_services() {
    print_header "Iniciando servicios"
    
    cd "$SCRIPT_DIR"
    
    print_info "Descargando imágenes Docker (esto puede tardar 1-2 minutos)..."
    docker compose pull
    
    print_info "Iniciando contenedores..."
    docker compose up -d
    
    # Wait for services to be ready
    print_info "Esperando a que los servicios estén listos..."
    sleep 10
    
    if docker compose ps | grep -q "Up"; then
        print_success "Servicios iniciados"
    else
        print_error "Algunos servicios no se iniciaron correctamente"
        print_info "Verifica los logs con: docker compose logs"
        exit 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Verify installation
# ─────────────────────────────────────────────────────────────────────────────

verify_installation() {
    print_header "Verificación de instalación"
    
    local dashboard_port=$(grep "DASHBOARD_PORT" "$ENV_FILE" | cut -d= -f2)
    local failed=0
    
    # Check API
    if curl -s http://localhost:$(( dashboard_port )).api/health > /dev/null 2>&1 || \
       curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "API disponible"
    else
        print_warning "API no disponible aún (puede tardar un momento más)"
    fi
    
    # Check InfluxDB
    if curl -s http://localhost:8086/health > /dev/null 2>&1; then
        print_success "InfluxDB disponible"
    else
        print_warning "InfluxDB no disponible aún"
    fi
    
    # Check dashboard
    if curl -s http://localhost:${dashboard_port:-80}/ > /dev/null 2>&1; then
        print_success "Dashboard disponible"
    else
        print_warning "Dashboard no disponible aún (puede tardar)"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Show next steps
# ─────────────────────────────────────────────────────────────────────────────

show_next_steps() {
    local dashboard_port=$(grep "DASHBOARD_PORT" "$ENV_FILE" | cut -d= -f2 || echo "80")
    
    print_header "✓ Instalación completada"
    
    echo ""
    echo -e "${GREEN}Servicios disponibles:${NC}"
    echo -e "  • ${BLUE}Dashboard${NC}:       http://localhost:${dashboard_port:-80}"
    echo -e "  • ${BLUE}API docs${NC}:        http://localhost:${dashboard_port:-80}/api/docs"
    echo -e "  • ${BLUE}InfluxDB UI${NC}:     http://localhost:8086"
    echo ""
    
    echo -e "${GREEN}Credenciales de InfluxDB:${NC}"
    local influx_user=$(grep "INFLUXDB_USER" "$ENV_FILE" | cut -d= -f2)
    local influx_pass=$(grep "INFLUXDB_PASSWORD" "$ENV_FILE" | cut -d= -f2)
    echo -e "  • Usuario: ${YELLOW}${influx_user}${NC}"
    echo -e "  • Contraseña: ${YELLOW}${influx_pass}${NC}"
    echo ""
    
    echo -e "${GREEN}Primeros pasos:${NC}"
    echo "  1. Abre el dashboard: http://localhost:${dashboard_port:-80}"
    echo "  2. Pulsa '+ Añadir inversor'"
    echo "  3. Completa con datos de tu data logger Solarman"
    echo "  4. ¡Listo! Los datos se actualizarán cada 60 segundos"
    echo ""
    
    echo -e "${GREEN}Comandos útiles:${NC}"
    echo "  Ver logs:              docker compose logs -f"
    echo "  Ver logs de API:       docker compose logs -f api"
    echo "  Ver health status:     curl http://localhost/api/health | jq ."
    echo "  Parar servicios:       docker compose down"
    echo "  Reiniciar:             docker compose restart"
    echo "  Reconstruir API:       docker compose build api && docker compose up -d"
    echo ""
    
    echo -e "${GREEN}Documentación:${NC}"
    echo "  • README.md         - Instalación y configuración"
    echo "  • API_GUIDE.md      - Ejemplos de API REST"
    echo "  • IMPROVEMENTS.md   - Detalles técnicos de mejoras"
    echo ""
    
    echo -e "${YELLOW}⚠ Nota importante:${NC}"
    echo "  • El archivo .env contiene credenciales. Guárdalo en lugar seguro."
    echo "  • Para clonar desde GitHub sin este script:"
    echo "    git clone $GITHUB_REPO"
    echo "    cd solar-monitor && bash install.sh"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main execution
# ─────────────────────────────────────────────────────────────────────────────

main() {
    clear
    print_header "🌞 Solar Monitor - Instalación Automatizada"
    
    # Check if we're in the right place
    if ! is_solar_monitor_repo "$SCRIPT_DIR"; then
        print_info "No se detectó repositorio de Solar Monitor en el directorio actual"
        echo ""
        read -p "¿Deseas clonar el repositorio? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            read -p "¿Dónde deseas clonar? (por defecto: directorio actual): " clone_target
            clone_target=${clone_target:-.}
            clone_repo "$clone_target"
            
            # Update paths after clone
            ENV_FILE="$SCRIPT_DIR/.env"
            DATA_DIR="$SCRIPT_DIR/data"
        else
            print_error "Abortado por el usuario"
            exit 0
        fi
    fi
    
    # Verify all required files exist
    verify_project_structure
    
    check_requirements
    setup_env
    setup_data_dir
    start_services
    verify_installation
    show_next_steps
    
    echo -e "${GREEN}Instalación finalizada exitosamente ✓${NC}"
}

# Run main function
main
