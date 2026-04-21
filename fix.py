import json

with open('/home/ubuntu/proyecto_sdn/dashboard/config_politicas.json', 'r') as f:
    data = json.load(f)

# Limpiar host_to_port de hosts remotos
if "1" in data["host_to_port"]:
    data["host_to_port"]["1"] = {}
if "5" in data["host_to_port"]:
    data["host_to_port"]["5"] = {}

# Arreglar tabla de rutas para que s1 envie a s3 y s3 envie al túnel
# S3 tunel estara asumiendo el puerto 3.
data["routing_table"]["3"] = {
    "10.0.1.0/24":  1,
    "10.0.2.0/24":  1,
    "10.0.66.0/24": 1,
    "10.0.10.0/24": 3  # <- TUNEL VXLAN
}

# S6 (DC-B) tunel estara en el puerto 4 (porque port 1=S5, 2=srv_db, 3=backup)
data["routing_table"]["6"] = {
    "10.0.1.0/24":  4, # <- TUNEL VXLAN
    "10.0.2.0/24":  4, # <- TUNEL VXLAN
    "10.0.66.0/24": 1
}

# S5 enrutamiento (solo para que no vuelva atras en caso raro, 10.10 va a s6=2)
data["routing_table"]["5"] = {
    "10.0.10.0/24": 2,
    "10.0.66.0/24": 4,
    "10.0.1.0/24":  1,
    "10.0.2.0/24":  1
}

with open('/home/ubuntu/proyecto_sdn/dashboard/config_politicas.json', 'w') as f:
    json.dump(data, f, indent=4)
