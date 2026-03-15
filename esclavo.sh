# Desde MAESTRA, configurar ESCLAVA
ssh ubuntu@192.168.32.132 "

# Instalar Python y crear entorno virtual
sudo apt install python3 python3-pip python3-venv -y
python3 -m venv ~/mpi_env_esclava