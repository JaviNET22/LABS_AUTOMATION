from netmiko import ConnectHandler
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException


usuario = 'u1'
password = 'cisco'

# Lista de IPs de los routers a los que nos vamos a conectar
routers = ['10.1.1.10', '10.1.1.20', '10.1.1.30']

def conectar_y_mostrar_info(ip, usuario, password):

    print('================================')
    print(f'Conectando a {ip}')
    print('================================')

    # Diccionario de conexion que usa Netmiko.
    router = {
        'device_type': 'cisco_ios',
        'host': ip,
        'username': usuario,
        'password': password,
    }

    try:
        # ConnectHandler abre la conexion SSH hacia el router
        conexion = ConnectHandler(**router)

        salida_interfaces = conexion.send_command('show ip interface brief')
        print(salida_interfaces)

        salida_version = conexion.send_command('show version')

        print('--- Informacion relevante de show version ---')
        for linea in salida_version.splitlines():
            if 'Version' in linea or 'uptime' in linea or 'System image' in linea or 'bytes of' in linea:
                print(linea)

        print(f'Cerrando conexion con {ip}')
        conexion.disconnect()

    # NetmikoTimeoutException: el router no respondio a tiempo
    except NetmikoTimeoutException:
        print(f'ERROR: Tiempo de espera agotado al conectar con {ip}')

    # NetmikoAuthenticationException: usuario o password incorrectos
    except NetmikoAuthenticationException:
        print(f'ERROR: Usuario o password incorrectos para {ip}')

    # Cualquier otro error no contemplado arriba
    except Exception as error:
        print(f'ERROR inesperado con {ip}: {error}')

    print()

for ip in routers:
    conectar_y_mostrar_info(ip, usuario, password)

print('Todos los routers fueron procesados.')
