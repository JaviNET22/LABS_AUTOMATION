import telnetlib
import time
import os
from datetime import date

routers = [
    {
        "hostname": "R1",
        "ip": "10.1.1.10"
    },
    {
        "hostname": "R2",
        "ip": "10.1.1.20"
    },
    {
        "hostname": "R3",
        "ip": "10.1.1.30"
    }
]


usuario = "admin"
password_login = "cisco"

carpeta_backups = "backups"


def obtener_configuracion(ip):

    tn = telnetlib.Telnet(host=ip)

    # Login: usuario y contraseña
    tn.read_until(b'Username: ')
    tn.write(usuario.encode() + b'\n')

    tn.read_until(b'Password: ')
    tn.write(password_login.encode() + b'\n')

    tn.write(b'terminal length 0\n')

    # Pedir la configuracion actual del router
    tn.write(b'show running-config\n')

    tn.write(b'exit\n')

    # Esperamos un poco para dar tiempo a que el router envie toda la salida
    time.sleep(2)

    salida = tn.read_all()
    salida = salida.decode()

    return salida


def guardar_backup(hostname, ip, configuracion):
    
    if not os.path.exists(carpeta_backups):
        os.makedirs(carpeta_backups)

    fecha_hoy = date.today().isoformat()
    nombre_archivo = f'{carpeta_backups}/{hostname}_{fecha_hoy}.txt'

    # Encabezado identificativo del backup
    encabezado = '=' * 50 + '\n'
    encabezado += 'CISCO ROUTER BACKUP\n'
    encabezado += '=' * 50 + '\n'
    encabezado += f'Hostname: {hostname}\n'
    encabezado += f'IP: {ip}\n'
    encabezado += f'Date: {fecha_hoy}\n'
    encabezado += '=' * 50 + '\n\n'

    with open(nombre_archivo, 'w') as archivo:
        archivo.write(encabezado)
        archivo.write(configuracion)

    print(f'Backup guardado en: {nombre_archivo}')


if __name__ == "__main__":

    for router in routers:
        hostname = router['hostname']
        ip = router['ip']

        print(f'Conectando a {hostname} ({ip})...')

        try:
            configuracion = obtener_configuracion(ip)
            guardar_backup(hostname, ip, configuracion)

        except Exception as error:
            print(f'Error al conectar con {hostname} ({ip}): {error}')

        print('#' * 50)
