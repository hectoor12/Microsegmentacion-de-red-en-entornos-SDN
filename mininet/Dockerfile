# proyecto_sdn/mininet/Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    mininet \
    openvswitch-switch \
    python3-pip \
    iproute2 \
    iputils-ping \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias (Asegúrate que Flask esté en requirements.txt)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 5000
EXPOSE 6633
EXPOSE 6653

# Copiamos todos los scripts
COPY . .

# Al arrancar, ejecutamos el script de la topología que llama a la API
CMD /etc/init.d/openvswitch-switch start && sleep 5 && exec python3 estructura.py
