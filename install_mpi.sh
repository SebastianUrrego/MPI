#!/bin/bash

# ============================================================
#  Instalacion de MPICH y mpi4py en Ubuntu
#  Basado en: https://mpitutorial.com/tutorials/installing-mpich2/
# ============================================================

set -e  # Detener el script si ocurre un error

MPICH_VERSION="3.3.2"
MPICH_TAR="mpich-${MPICH_VERSION}.tar.gz"
MPICH_URL="https://www.mpich.org/static/downloads/${MPICH_VERSION}/${MPICH_TAR}"
INSTALL_DIR="/usr/local"

echo "============================================================"
echo "  Instalacion de MPICH ${MPICH_VERSION}"
echo "============================================================"

# ------------------------------------------------------------
# 1. Actualizar repositorios e instalar dependencias
# ------------------------------------------------------------
echo ""
echo "[1/6] Actualizando repositorios..."
sudo apt-get update -y

echo "[2/6] Instalando dependencias (gcc, g++, gfortran, make, wget)..."
sudo apt-get install -y gcc g++ gfortran make wget python3 python3-pip

# ------------------------------------------------------------
# 2. Descargar MPICH
# ------------------------------------------------------------
echo ""
echo "[3/6] Descargando MPICH ${MPICH_VERSION}..."
cd /tmp
wget -q --show-progress "${MPICH_URL}" -O "${MPICH_TAR}"
tar -xzf "${MPICH_TAR}"
cd "mpich-${MPICH_VERSION}"

# ------------------------------------------------------------
# 3. Configurar, compilar e instalar
# ------------------------------------------------------------
echo ""
echo "[4/6] Configurando MPICH (esto puede tomar varios minutos)..."
./configure --prefix="${INSTALL_DIR}" --disable-fortran 2>&1 | tail -5

echo ""
echo "[5/6] Compilando e instalando MPICH..."
make -j$(nproc)
sudo make install

# ------------------------------------------------------------
# 4. Verificar instalacion
# ------------------------------------------------------------
echo ""
echo "[6/6] Verificando instalacion..."
mpiexec --version

# ------------------------------------------------------------
# 5. Instalar mpi4py para Python
# ------------------------------------------------------------
echo ""
echo "Instalando mpi4py para Python..."
pip3 install mpi4py --break-system-packages 2>/dev/null || pip3 install mpi4py

echo ""
echo "Verificando mpi4py..."
python3 -c "from mpi4py import MPI; print('mpi4py OK - version:', MPI.Get_version())"

# ------------------------------------------------------------
# 6. Limpieza
# ------------------------------------------------------------
echo ""
echo "Limpiando archivos temporales..."
cd /tmp
rm -rf "mpich-${MPICH_VERSION}" "${MPICH_TAR}"

echo ""
echo "============================================================"
echo "  Instalacion completada exitosamente."
echo ""
echo "  Prueba rapida:"
echo "    mpirun -n 2 python3 factorizacion_primos.py"
echo "============================================================"
