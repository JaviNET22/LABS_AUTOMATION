from netmiko import ConnectHandler
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException
import threading
import os

# Lista de routers a los que nos vamos a conectar.
routers = [
    {
        'etiqueta': 'ROUTER 1',
        'host': '10.1.1.10',
        'username': 'admin',
        'password': 'cisco',
    },
    {
        'etiqueta': 'ROUTER 2',
        'host': '10.1.1.20',
        'username': 'admin',
        'password': 'cisco',
    },
    {
        'etiqueta': 'ROUTER 3',
        'host': '10.1.1.30',
        'username': 'admin',
        'password': 'cisco',
    },
]

# Carpeta donde se van a guardar todos los backups
carpeta_backups = 'backups'


# Se conecta a un router, obtiene su running-config y la guarda en un archivo dentro de carpeta_backups.
def respaldar_router(router):

    # Diccionario de conexion que usa Netmiko.

    dispositivo = {
        'device_type': 'cisco_ios',
        'host': router['host'],
        'username': router['username'],
        'password': router['password'],
    }

    try:
        # ConnectHandler abre la conexion SSH hacia el router
        conexion = ConnectHandler(**dispositivo)

        conexion.enable()

        prompt = conexion.find_prompt()
        hostname = prompt[0:-1]

        salida = conexion.send_command('show running-config')

        # Armamos la ruta completa del archivo: backups/HOSTNAME_config.txt
        nombre_archivo = f'{hostname}_config.txt'
        ruta_archivo = os.path.join(carpeta_backups, nombre_archivo)

        with open(ruta_archivo, 'w') as archivo_backup:
            archivo_backup.write(salida)

        print(f'Backup de {router["etiqueta"]} ({hostname}) guardado en {ruta_archivo}')

        print(f'Cerrando conexion con {router["etiqueta"]}')
        conexion.disconnect()

    except NetmikoTimeoutException:
        print(f'ERROR: Tiempo de espera agotado al conectar con {router["etiqueta"]} ({router["host"]})')

    except NetmikoAuthenticationException:
        print(f'ERROR: Usuario o password incorrectos para {router["etiqueta"]} ({router["host"]})')

    except Exception as error:
        print(f'ERROR inesperado con {router["etiqueta"]} ({router["host"]}): {error}')


os.makedirs(carpeta_backups, exist_ok=True)

hilos = list()
for router in routers:
    hilo = threading.Thread(target=respaldar_router, args=(router,))
    hilos.append(hilo)

for hilo in hilos:
    hilo.start()

for hilo in hilos:
    hilo.join()

print('Proceso de backup finalizado para todos los routers.')
