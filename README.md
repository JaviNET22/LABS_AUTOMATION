# Network Automation Labs

Laboratorios de automatización de redes con Python. Cada carpeta agrupa los scripts de una librería o método de conexión a dispositivos de red, desde los accesos más básicos (Telnet, consola serie) hasta librerías de más alto nivel como Netmiko y Napalm.

> **Estado:** en crecimiento. Próximamente añadiré los laboratorios de **Ansible**.

---

## Sobre mí

Soy ingeniero de redes en formación, con interés en infraestructura de data center y automatización. Este repositorio recoge mi evolución práctica en Network Automation: empecé con Paramiko, pasé a Napalm como librería principal y he ido incorporando Netmiko y asyncio para trabajar con varios dispositivos a la vez.

---

## Contenido

| Carpeta | Qué se practica |
|---|---|
| [`TELNET/`](./TELNET) | Conexión y configuración de dispositivos mediante Telnet |
| [`SERIAL CONNECTIONS/`](<./SERIAL%20CONNECTIONS>) | Acceso a equipos por puerto de consola (serie) |
| [`PARAMIKO/`](./PARAMIKO) | Conexiones SSH de bajo nivel y ejecución de comandos |
| [`NETMIKO/`](./NETMIKO) | Automatización de equipos de red sobre SSH con Netmiko |
| [`NAPALM/`](./NAPALM) | Obtención de datos y configuración multivendor con Napalm |

<!-- Ajusta la columna "Qué se practica" a lo que haga realmente cada carpeta -->

---

## Tecnologías

- **Lenguaje:** Python 3
- **Librerías:** Napalm, Netmiko, Paramiko, asyncio
- **Protocolos de acceso:** SSH, Telnet, consola serie
- **Entorno de laboratorio:** `[GNS3 / EVE-NG / Packet Tracer / equipos reales: indica cuál usas]`
- **Próximamente:** Ansible

---

## Requisitos

```bash
python3 -m venv venv
source venv/bin/activate
pip install napalm netmiko paramiko
```

Para los laboratorios por consola serie hará falta además `pyserial`:

```bash
pip install pyserial
```

---

## Cómo usar los laboratorios

1. Clona el repositorio:
   ```bash
   git clone https://github.com/JaviNET22/LABS_AUTOMATION.git
   ```
2. Entra en la carpeta de la librería que quieras revisar.
3. Ajusta en cada script la IP, el usuario y la contraseña de tu entorno de laboratorio.
4. Ejecuta el script con `python3 nombre_del_script.py`.

> Los scripts están pensados para entornos de laboratorio. No incluyas credenciales reales en el código.

---

## Hoja de ruta

- [x] Telnet
- [x] Conexiones por consola serie
- [x] Paramiko
- [x] Netmiko
- [x] Napalm
- [ ] Ansible

<!-- Deja solo los puntos que realmente quieras abordar -->

---

## Contacto

- GitHub: [@JaviNET22](https://github.com/JaviNET22)
- LinkedIn: `https://www.linkedin.com/in/javiermarinhenao/?isSelfProfile=true`

---

*Proyecto personal con fines de aprendizaje.*
