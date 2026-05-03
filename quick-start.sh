#!/bin/bash

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                                                                            ║
# ║         Solar Monitor - Quick Start Script                               ║
# ║                                                                            ║
# ║ Descargar y ejecutar este script en cualquier lugar para instalar        ║
# ║ Solar Monitor automáticamente.                                           ║
# ║                                                                            ║
# ║ Uso:                                                                      ║
# ║   curl https://raw.githubusercontent.com/pablomartin10/solar-monitor/main/quick-start.sh | bash ║
# ║                                                                            ║
# ╚════════════════════════════════════════════════════════════════════════════╝

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

# Main
clear
print_header "🌞 Solar Monitor - Instalación Rápida"

# Check Git
if ! command -v git &> /dev/null; then
    print_error "Git no está instalado"
    echo ""
    echo "Instala Git primero:"
    echo "  Linux: sudo apt-get install git"
    echo "  macOS: brew install git"
    echo "  Windows: https://git-scm.com/"
    exit 1
fi

print_success "Git detectado"

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    echo ""
    echo "Instala Docker desde: https://www.docker.com/get-docker"
    exit 1
fi

print_success "Docker detectado"

# Check Docker Compose
if ! docker compose version &> /dev/null 2>&1; then
    print_error "Docker Compose no está disponible"
    echo ""
    echo "Docker Compose debe venir con Docker Desktop."
    echo "Asegúrate de que Docker está actualizado."
    exit 1
fi

print_success "Docker Compose disponible"

# Choose install location
print_header "Ubicación de instalación"

read -p "¿Dónde deseas instalar? (por defecto: ./solar-monitor): " install_path
install_path=${install_path:-.}
target_dir="$install_path/solar-monitor"

# Clone repo
print_header "Descargando repositorio"

if [ -d "$target_dir" ]; then
    print_info "El directorio ya existe"
    read -p "¿Deseas actualizar? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        cd "$target_dir"
        git pull
    fi
else
    mkdir -p "$install_path"
    cd "$install_path"
    print_info "Clonando desde GitHub..."
    git clone https://github.com/pablomartin10/solar-monitor.git
    cd "$target_dir"
    print_success "Repositorio clonado"
fi

# Run install.sh
print_header "Ejecutando instalación"
bash install.sh

print_header "✓ ¡Instalación completada!"
echo ""
echo -e "${GREEN}Próximos pasos:${NC}"
echo "  1. Abre http://localhost en tu navegador"
echo "  2. Pulsa '+ Añadir inversor'"
echo "  3. Configura tu data logger Solarman"
echo ""
echo -e "${GREEN}Ubicación del proyecto:${NC}"
echo "  $target_dir"
echo ""
echo -e "${GREEN}Vuelve a ejecutar instalación:${NC}"
echo "  cd $target_dir && bash install.sh"
