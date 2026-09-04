from netmiko import ConnectHandler
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException
import threading
import getpass

# Diccionario con los 3 routers de la topologia: nombre logico -> ip de gestion
ROUTERS = {
    "Router 1": {"host": "10.1.1.10"},
    "Router 2": {"host": "10.1.1.20"},
    "Router 3": {"host": "10.1.1.30"},
}

# Los 3 routers estan en la misma subred de gestion (10.1.1.0/24)
RED_OSPF = "10.1.1.0"
WILDCARD_OSPF = "0.0.0.255"
AREA_OSPF = "0"

USUARIO_SSH = "admin"
PASSWORD_SSH = getpass.getpass("Introduce la contraseña SSH: ")


lock_impresion = threading.Lock()


def conectar_router(nombre_router, datos_router):
    
    device = {
        'device_type': 'cisco_ios',
        'host': datos_router["host"], 
        'username': USUARIO_SSH,      
        'password': PASSWORD_SSH,     
        'secret': PASSWORD_SSH,       
        'port': 22,
        'verbose': False,
        'global_delay_factor': 2,
        'fast_cli': False,
    }

    try:
        connection = ConnectHandler(**device)
        connection.enable()  # entra en modo privilegiado (enable), necesario para poder configurar
        return connection

   
    except NetmikoAuthenticationException:
        with lock_impresion:
            print(f'[ERROR] Usuario o contraseña incorrectos en {nombre_router} ({datos_router["host"]})')
        return None

    except NetmikoTimeoutException:
        with lock_impresion:
            print(f'[ERROR] Tiempo de espera agotado conectando a {nombre_router} ({datos_router["host"]})')
        return None

    except Exception as error:
        with lock_impresion:
            print(f'[ERROR] No se pudo conectar a {nombre_router}: {error}')
        return None


def configurar_ospf(connection, router_id):
    comandos_ospf = [
        'router ospf 1',
        f'router-id {router_id}',
        f'network {RED_OSPF} {WILDCARD_OSPF} area {AREA_OSPF}',
    ]

    try:
        connection.send_config_set(comandos_ospf, read_timeout=60)
        connection.send_command('write memory', read_timeout=60)
        return True
    except Exception as error:
        with lock_impresion:
            print(f'[ERROR] No se pudo configurar OSPF: {error}')
        return False


def verificar_ospf(connection, nombre_router, host):
    salida_vecinos = connection.send_command('show ip ospf neighbor', read_timeout=60)
    salida_rutas = connection.send_command('show ip route ospf', read_timeout=60)

    titulo = f'{nombre_router.upper()} - {host}'
    bloque = ''
    bloque += '=' * 60 + '\n'
    bloque += titulo.center(60) + '\n'
    bloque += '=' * 60 + '\n\n'
    bloque += '--- show ip ospf neighbor ---\n\n'
    bloque += salida_vecinos + '\n\n'
    bloque += '--- show ip route ospf ---\n\n'
    bloque += salida_rutas + '\n'

    return bloque


def procesar_router(nombre_router, datos_router):
    # Esta es la funcion que ejecuta cada hilo (uno por router), de principio a fin
    connection = conectar_router(nombre_router, datos_router)
    if connection is None:
        return  

    router_id = datos_router["host"]
    configuracion_ok = configurar_ospf(connection, router_id)

    if configuracion_ok:
        bloque_verificacion = verificar_ospf(connection, nombre_router, datos_router["host"])
        with lock_impresion:
            print(bloque_verificacion)

    connection.disconnect()


# lista donde se guardan los hilos, uno por cada router
hilos = list()

for nombre_router, datos_router in ROUTERS.items():
    hilo = threading.Thread(target=procesar_router, args=(nombre_router, datos_router))
    hilos.append(hilo)

for hilo in hilos:
    hilo.start()

for hilo in hilos:
    hilo.join()
