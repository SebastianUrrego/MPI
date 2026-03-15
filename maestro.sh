# Instalar Python y pip
sudo apt install python3 python3-pip python3-venv -y

# Crear entorno virtual
cd /home/ubuntu
python3 -m venv mpi_env

# Activar entorno
source mpi_env/bin/activate

# Configurar variables para MPI
export MPI_HOME=/home/ubuntu/mpich-install
export LD_LIBRARY_PATH=/home/ubuntu/mpich-install/lib:$LD_LIBRARY_PATH

# Instalar mpi4py 
pip install --no-cache-dir --no-binary=mpi4py mpi4py