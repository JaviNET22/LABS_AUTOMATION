from napalm import get_network_driver
from concurrent.futures import ThreadPoolExecutor
import difflib
import itertools

lista_routers = [
    {'nombre': 'R1', 'ip': '10.1.1.10', 'usuario': 'admin', 'password': 'cisco'},
    {'nombre': 'R2', 'ip': '10.1.1.20', 'usuario': 'admin', 'password': 'cisco'},
    {'nombre': 'R3', 'ip': '10.1.1.30', 'usuario': 'admin', 'password': 'cisco'},
]


def obtener_configuracion(router):

    # Armar un diccionario con el resultado y lo devuelve.

    nombre = router['nombre']
    ip = router['ip']
    usuario = router['usuario']
    password = router['password']

    resultado = {
        'nombre': nombre,
        'ip': ip,
        'config': None,
        'estado': 'ERROR',
        'mensaje_error': None,
    }

    driver = get_network_driver('ios')
    optional_args = {'secret': 'cisco'}
    dispositivo = driver(ip, usuario, password, optional_args=optional_args)

    try:

        dispositivo.open()

        # Para comparar routers usamos la configuracion que esta corriendo actualmente.
        configuraciones = dispositivo.get_config()
        configuracion_running = configuraciones['running']

        resultado['config'] = configuracion_running
        resultado['estado'] = 'OK'

    except Exception as error:
        resultado['mensaje_error'] = str(error)

    finally:
        try:
            dispositivo.close()
        except Exception:
            pass

    return resultado


def clasificar_linea(linea):

    # Recibe una linea de configuracion y decide a que categoria pertenece.

    linea_limpia = linea.strip().lower()

    if linea_limpia.startswith('hostname'):
        return 'Hostname'
    elif linea_limpia.startswith('interface'):
        return 'Interfaces'
    elif linea_limpia.startswith('ip address'):
        return 'Direcciones IP'
    elif linea_limpia.startswith('router '):
        return 'Routing'
    elif linea_limpia.startswith('ip route'):
        return 'Routing'
    elif linea_limpia.startswith('network '):
        return 'Routing'
    else:
        return 'Otras lineas de configuracion'


def comparar_configuraciones(config_1, config_2):

    # Compara y devuelve un texto ya formateado con las diferencias encontradas, agrupadas por categoria.

    lineas_config_1 = config_1.splitlines()
    lineas_config_2 = config_2.splitlines()

    diferencias_crudas = difflib.unified_diff(
        lineas_config_1,
        lineas_config_2,
        n=0,
        lineterm=''
    )

    # Diccionario donde vamos a ir agrupando las diferencias por categoria.
    diferencias_por_categoria = {
        'Hostname': [],
        'Interfaces': [],
        'Direcciones IP': [],
        'Routing': [],
        'Otras lineas de configuracion': [],
    }

    for linea in diferencias_crudas:
        if linea.startswith('+++') or linea.startswith('---') or linea.startswith('@@'):
            continue

        if linea.startswith('+') or linea.startswith('-'):
            categoria = clasificar_linea(linea[1:])
            diferencias_por_categoria[categoria].append(linea)

    # Armamos el texto final, categoria por categoria, solo con las que tienen contenido.
    texto_final = ""
    se_encontraron_diferencias = False

    for categoria in diferencias_por_categoria:
        lineas_categoria = diferencias_por_categoria[categoria]

        if len(lineas_categoria) > 0:
            se_encontraron_diferencias = True
            texto_final += f"\n[{categoria}]\n"
            for linea in lineas_categoria:
                texto_final += f"  {linea}\n"

    if se_encontraron_diferencias is False:
        texto_final = "No se encontraron diferencias relevantes.\n"

    return texto_final


if __name__ == "__main__":

    print("=" * 70)
    print(" LABORATORIO NAPALM + MULTITHREADING - COMPARADOR DE CONFIGURACIONES")
    print("=" * 70)
    print("\nConectando simultaneamente a los routers y obteniendo configuraciones...")

    # ThreadPoolExecutor.map lanza obtener_configuracion() para cada router en paralelo, pero nos devuelve los resultados en el mismo orden en que estan en lista_routers.
    with ThreadPoolExecutor(max_workers=3) as executor:
        resultados_routers = list(executor.map(obtener_configuracion, lista_routers))

    # Mostrar el estado de cada router, uno despues del otro (sin imprimir la configuracion completa).
    for resultado in resultados_routers:
        print("\n" + "=" * 70)
        print(f"Hostname: {resultado['nombre']}  ({resultado['ip']})")
        print("=" * 70)

        if resultado['estado'] == 'OK':
            print("\nEstado: OK")
        else:
            print(f"\nEstado: ERROR - {resultado['mensaje_error']}")

    # Comparar las configuraciones de los routers que respondieron
    print("\n\n" + "=" * 70)
    print(" COMPARACION DE CONFIGURACIONES")
    print("=" * 70)

    # Filtramos solo los routers que si entregaron una configuracion valida.
    routers_ok = []
    for resultado in resultados_routers:
        if resultado['estado'] == 'OK':
            routers_ok.append(resultado)

    if len(routers_ok) < 2:
        print("\nNo hay suficientes routers con configuracion valida para comparar.")
    else:
        # itertools.combinations(routers_ok, 2) arma todas las parejas posibles
        # entre los routers, sin repetir (R1-R2, R1-R3, R2-R3), sin comparar
        # un router contra si mismo ni repetir la misma pareja al reves.
        for router_1, router_2 in itertools.combinations(routers_ok, 2):

            print(f"\n{router_1['nombre']} ↔ {router_2['nombre']}")
            print("-" * 70)

            print("Diferencias encontradas:")
            texto_diferencias = comparar_configuraciones(router_1['config'], router_2['config'])
            print(texto_diferencias)

    print("Comparacion finalizada.")
