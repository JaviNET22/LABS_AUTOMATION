from netmiko import ConnectHandler
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException
import threading

# Lista de routers a configurar.
routers = [
    {
        'etiqueta': 'ROUTER 1',
        'host': '10.1.1.10',
        'username': 'admin',
        'password': 'cisco',
        'loopback_numero': 0,
        'loopback_ip': '10.10.10.10',
        'loopback_mascara': '255.255.255.255',
    },
    {
        'etiqueta': 'ROUTER 2',
        'host': '10.1.1.20',
        'username': 'admin',
        'password': 'cisco',
        'loopback_numero': 0,
        'loopback_ip': '20.20.20.20',
        'loopback_mascara': '255.255.255.255',
    },
    {
        'etiqueta': 'ROUTER 3',
        'host': '10.1.1.30',
        'username': 'admin',
        'password': 'cisco',
        'loopback_numero': 0,
        'loopback_ip': '30.30.30.30',
        'loopback_mascara': '255.255.255.255',
    },
]


resultados = list()


# configura la Loopback y guarda el resultado de "show ip interface" en la lista compartida.
def configurar_router(router):

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

        # Comandos para crear la interfaz Loopback y asignarle la IP indicada
        comandos_loopback = [
            f'interface loopback {router["loopback_numero"]}',
            f'ip address {router["loopback_ip"]} {router["loopback_mascara"]}',
            'exit',
        ]

        conexion.send_config_set(comandos_loopback)

        # Comprobamos el resultado de la configuracion con show ip interface
        salida = conexion.send_command('show ip interface br')

        # Armamos el bloque de texto ya formateado para este router, para imprimirlo mas tarde junto con el de los demas routers
        bloque = '=' * 40 + '\n'
        bloque += f'SHOW IP INTERFACE - {router["etiqueta"]}\n'
        bloque += '=' * 40 + '\n'
        bloque += salida + '\n'

        resultados.append(bloque)

        conexion.disconnect()

    except NetmikoTimeoutException:
        resultados.append(f'ERROR: Tiempo de espera agotado al conectar con {router["etiqueta"]} ({router["host"]})')

    except NetmikoAuthenticationException:
        resultados.append(f'ERROR: Usuario o password incorrectos para {router["etiqueta"]} ({router["host"]})')

    except Exception as error:
        resultados.append(f'ERROR inesperado con {router["etiqueta"]} ({router["host"]}): {error}')


if __name__ == "__main__":

    # Creamos un hilo por cada router, apuntando a la funcion configurar_router
    hilos = list()
    for router in routers:
        hilo = threading.Thread(target=configurar_router, args=(router,))
        hilos.append(hilo)

    for hilo in hilos:
        hilo.start()

    for hilo in hilos:
        hilo.join()

    # Imprimimos el resultado de cada router. El orden depende de que hilo termino primero.
    for bloque in resultados:
        print(bloque)
