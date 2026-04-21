# 🛡️ Microsegmentación de Red en Entornos SDN (Software-Defined Networking)

> **Trabajo de Fin de Grado (TFG)**   
> **Autor:** Héctor Muñoz Rubio  
> **Universidad/Centro:** Universidad Autónoma de Madrid  
> **Titulación:** Grado en Ingeniería Informática  
> **Fecha:** Mayo 2026

![SDN Concept](https://img.shields.io/badge/SDN-Network_Architecture-blue.svg)
![Security](https://img.shields.io/badge/Security-Microsegmentation-red.svg)
![Status](https://img.shields.io/badge/Status-Completado-brightgreen.svg)

---

## 📖 Descripción del Proyecto

Este repositorio contiene el código, las configuraciones y la documentación desarrollada para el Trabajo de Fin de Grado titulado **"Microsegmentación de red en entornos SDN"**. 

El objetivo principal de este proyecto es demostrar cómo el paradigma de las Redes Definidas por Software (SDN) facilita la implementación de políticas de seguridad granulares mediante la microsegmentación. A diferencia de las redes tradicionales basadas en perímetros, este enfoque permite aislar el tráfico a nivel de host o carga de trabajo, mitigando los movimientos laterales de posibles amenazas dentro del centro de datos o la red corporativa.

### 🎯 Objetivos

* **Objetivo General:** Diseñar, desplegar y evaluar una arquitectura de red SDN capaz de aplicar políticas de microsegmentación para aislar diferentes flujos de tráfico.
* **Objetivos Específicos:**
  * Desplegar una topología de red virtualizada.
  * Configurar e integrar un controlador SDN con Ryu.
  * Desarrollar y aplicar reglas de flujo usando OpenFlow para segmentar el tráfico entre distintos grupos lógicos.
  * Verificar la efectividad de la microsegmentación ante intentos de comunicación no autorizados.

---

## 🏗️ Arquitectura y Tecnologías

El proyecto se basa en un entorno de laboratorio virtualizado, utilizando las siguientes herramientas y tecnologías:

| Tecnología | Rol en el Proyecto |
| :--- | :--- |
| **Mininet** | Emulador de red para crear la topología virtual (switches, hosts y enlaces). |
| **Ryu** | Controlador SDN que actúa como el "cerebro" de la red y gestiona las reglas. |
| **Open vSwitch (OVS)** | Conmutadores virtuales compatibles con OpenFlow. |
| **OpenFlow [v1.3]** | Protocolo de comunicación entre el plano de control (Controlador) y el plano de datos (Switches). |
| **Python [3.x]** | Lenguaje utilizado para el scripting de la topología y la lógica del controlador. |

---

## 📂 Estructura del Repositorio

```text
Microsegmentacion-de-red-en-entornos-SDN/
├── controlador/          # Scripts y lógica del controlador SDN (políticas de seguridad)
├── topologia/            # Scripts de Mininet para la generación de la red
├── pruebas/              # Scripts automatizados para verificar conectividad y aislamiento
├── documentacion/        # Memorias, diagramas de red y capturas de pantalla (TFG)
├── requirements.txt      # Dependencias necesarias de Python
└── README.md             # Este archivo
