from napalm import get_network_driver
from concurrent.futures import ThreadPoolExecutor


lista_routers = [
    {'nombre': 'R1', 'ip': '10.1.1.10', 'usuario': 'admin', 'password': 'cisco'},
    {'nombre': 'R2', 'ip': '10.1.1.20', 'usuario': 'admin', 'password': 'cisco'},
    {'nombre': 'R3', 'ip': '10.1.1.30', 'usuario': 'admin', 'password': 'cisco'},
]


def obtener_vecinos(router):

    nombre = router['nombre']
    ip = router['ip']
    usuario = router['usuario']
    password = router['password']

    resultado = "\n" + "=" * 60 + "\n"
    resultado += f"Router: {nombre}  ({ip})\n"
    resultado += "=" * 60 + "\n"
    resultado += f"Conectando a {nombre} ({ip})...\n"

    driver = get_network_driver('ios')
    optional_args = {'secret': 'cisco'} 
    dispositivo = driver(ip, usuario, password, optional_args=optional_args)

    try:
        # Abrimos la conexion hacia el router
        dispositivo.open()
        resultado += f"Conexion establecida con {nombre}.\n"
        resultado += f"Obteniendo vecinos OSPF de {nombre}...\n"
        resultado += "-" * 60 + "\n"

        comando = 'show ip ospf neighbor'
        salida_cli = dispositivo.cli([comando])
        salida_texto = salida_cli[comando]

        if len(salida_texto.strip()) == 0:
            resultado += "No se encontraron vecinos OSPF en este router.\n"
        else:
            resultado += salida_texto + "\n"

    except Exception as error:
        resultado += f"ERROR al conectar u obtener datos de {nombre} ({ip}): {error}\n"

    finally:
        try:
            dispositivo.close()
            resultado += f"Conexion con {nombre} cerrada correctamente.\n"
        except Exception:
            pass

    resultado += "=" * 60 + "\n"
    return resultado


if __name__ == "__main__":

    print("Iniciando consulta simultanea de vecinos en los routers...\n")

    with ThreadPoolExecutor(max_workers=3) as executor:
        resultados = executor.map(obtener_vecinos, lista_routers)

        for texto_resultado in resultados:
            print(texto_resultado)

    print("Consulta finalizada para todos los routers.")
