FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# LA CLAVE MÁGICA: Forzamos a pbr a saber que es la versión 4.34
ENV PBR_VERSION=4.34

WORKDIR /app

RUN pip install --upgrade pip

# 1. Preparamos el terreno con el setuptools que te funcionó a ti + pbr
RUN pip install "setuptools==67.6.1" wheel pbr

# 2. Instalamos Ryu (ahora sí, sin aislar y sabiendo su versión)
RUN pip install --no-cache-dir --no-build-isolation ryu==4.34

# 3. Tu parche de eventlet para que ryu-manager no explote
RUN pip install --no-cache-dir "eventlet<0.30"

# 4. Instalamos tu requirements.txt tranquilamente
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 6633 6653 8080

CMD ["ryu-manager", "firewall.py"]
