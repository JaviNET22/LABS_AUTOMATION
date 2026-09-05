from napalm import get_network_driver
from concurrent.futures import ThreadPoolExecutor


lista_routers = [
    {'nombre': 'R1', 'ip': '10.1.1.10', 'usuario': 'admin', 'password': 'cisco'},
    {'nombre': 'R2', 'ip': '10.1.1.20', 'usuario': 'admin', 'password': 'cisco'},
    {'nombre': 'R3', 'ip': '10.1.1.30', 'usuario': 'admin', 'password': 'cisco'},
]


def auditar_interfaces(router):

    nombre = router['nombre']
    ip = router['ip']
    usuario = router['usuario']
    password = router['password']

    
    resultado = "\n" + "=" * 40 + "\n"
    resultado += f"             ROUTER {nombre}\n"
    resultado += "=" * 40 + "\n"

    driver = get_network_driver('ios')
    optional_args = {'secret': 'cisco'}
    dispositivo = driver(ip, usuario, password, optional_args=optional_args)

    try:
        dispositivo.open()

        interfaces = dispositivo.get_interfaces()

        contador_activas = 0
        contador_inactivas = 0
        contador_deshabilitadas = 0

        resultado += "\nInterfaces:\n"

        # Ordenamos los nombres de interfaz para que el listado salga siempre
        for nombre_interfaz in sorted(interfaces.keys()):
            datos_interfaz = interfaces[nombre_interfaz]

            if datos_interfaz['is_enabled'] is False:
                resultado += f"{nombre_interfaz}  → ADMIN DOWN (deshabilitada)\n"
                contador_deshabilitadas += 1
            elif datos_interfaz['is_up'] is True:
                resultado += f"{nombre_interfaz}  → UP\n"
                contador_activas += 1
            else:
                resultado += f"{nombre_interfaz}  → DOWN\n"
                contador_inactivas += 1

        resultado += "\nResumen:\n"
        resultado += f"{contador_activas} interfaces activas\n"
        resultado += f"{contador_inactivas} interfaces inactivas\n"
        resultado += f" {contador_deshabilitadas} interfaces deshabilitadas administrativamente\n"

    except Exception as error:
        resultado += f"\nERROR al conectar u obtener datos de {nombre} ({ip}): {error}\n"

    finally:
        # Cerramos la conexion pase lo que pase, incluso si hubo un error arriba.
        try:
            dispositivo.close()
        except Exception:
            pass

    resultado += "=" * 40 + "\n"
    return resultado


if __name__ == "__main__":

    print("Iniciando auditoria simultanea de interfaces en los routers...\n")
    with ThreadPoolExecutor(max_workers=3) as executor:
        resultados = executor.map(auditar_interfaces, lista_routers)

        for texto_resultado in resultados:
            print(texto_resultado)

    print("Auditoria finalizada para todos los routers.")
