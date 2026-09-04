from napalm import get_network_driver
import os
from datetime import datetime


lista_routers = [
    {'nombre': 'R1', 'ip': '10.1.1.10', 'usuario': 'admin', 'password': 'cisco', 'secret': 'cisco'},
    {'nombre': 'R2', 'ip': '10.1.1.20', 'usuario': 'admin', 'password': 'cisco', 'secret': 'cisco'},
    {'nombre': 'R3', 'ip': '10.1.1.30', 'usuario': 'admin', 'password': 'cisco', 'secret': 'cisco'},
]

# Carpetas donde se guardan los informes y los backups de configuracion
carpeta_informes = 'informes'
carpeta_backups = 'backups'

# Archivo con los comandos a aplicar cuando se quiera modificar
archivo_cambios = 'cambios.txt'


def conectar_router(datos_router):
    # Se conecta a un router IOS usando NAPALM.
    print(f"\nConectando a {datos_router['nombre']} ({datos_router['ip']})...")

    driver = get_network_driver('ios')
    optional_args = {'secret': datos_router['secret']}

    router = driver(
        datos_router['ip'],
        datos_router['usuario'],
        datos_router['password'],
        optional_args=optional_args
    )

    try:
        router.open()
        print(f"Conexion establecida con {datos_router['nombre']}")
        return router
    except Exception as error:
        print(f"ERROR: no se pudo conectar a {datos_router['nombre']} ({datos_router['ip']}): {error}")
        return None


def obtener_estado_interfaces(router):
    # Devuelve una lista de lineas de texto indicando que interfaces
    # estan UP y cuales estan DOWN.
    lineas = []
    interfaces = router.get_interfaces()

    for nombre_interfaz, datos_interfaz in interfaces.items():
        if datos_interfaz['is_up']:
            estado = 'UP'
        else:
            estado = 'DOWN'
        lineas.append(f"  {nombre_interfaz}: {estado} (habilitada: {datos_interfaz['is_enabled']})")

    return lineas


def obtener_ips_interfaces(router):
    # Devuelve una lista de lineas de texto con las IPs configuradas en cada interfaz del router.
    lineas = []
    interfaces_ip = router.get_interfaces_ip()

    for nombre_interfaz, datos_ip in interfaces_ip.items():
        if 'ipv4' in datos_ip:
            for direccion, detalle in datos_ip['ipv4'].items():
                lineas.append(f"  {nombre_interfaz}: {direccion}/{detalle['prefix_length']}")

    return lineas


def obtener_vecinos_ospf(router):
    salida = router.cli(['show ip ospf neighbor'])
    return salida['show ip ospf neighbor']


def obtener_tabla_rutas(router):
    # Igual que con OSPF, se consulta la tabla de rutas con el
    # comando directo de IOS.
    salida = router.cli(['show ip route'])
    return salida['show ip route']


def generar_informe(datos_router, router):
    # Arma un informe de texto con interfaces up/down, IPs
    nombre_router = datos_router['nombre']
    fecha_hora = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    informe = []
    informe.append(f"INFORME DE AUDITORIA - {nombre_router} ({datos_router['ip']})")
    informe.append(f"Fecha: {fecha_hora}")
    informe.append("")

    informe.append("ESTADO DE INTERFACES:")
    informe.extend(obtener_estado_interfaces(router))
    informe.append("")

    informe.append("DIRECCIONES IP:")
    informe.extend(obtener_ips_interfaces(router))
    informe.append("")

    informe.append("VECINOS OSPF:")
    informe.append(obtener_vecinos_ospf(router))
    informe.append("")

    informe.append("TABLA DE RUTAS:")
    informe.append(obtener_tabla_rutas(router))

    texto_informe = "\n".join(informe)

    print("\n" + texto_informe)

    # Si la carpeta de informes no existe todavia, se crea
    if not os.path.exists(carpeta_informes):
        os.makedirs(carpeta_informes)

    nombre_archivo = os.path.join(carpeta_informes, f"informe_{nombre_router}_{fecha_hora}.txt")
    with open(nombre_archivo, 'w') as archivo:
        archivo.write(texto_informe)

    print(f"Informe guardado en {nombre_archivo}")


def hacer_backup_configuracion(datos_router, router):
    # Descarga la configuracion running y startup del router y las guarda en dos archivos de texto separados, con fecha y hora
    nombre_router = datos_router['nombre']
    fecha_hora = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    if not os.path.exists(carpeta_backups):
        os.makedirs(carpeta_backups)

    configuracion = router.get_config()

    archivo_running = os.path.join(carpeta_backups, f"{nombre_router}_running_{fecha_hora}.txt")
    with open(archivo_running, 'w') as archivo:
        archivo.write(configuracion['running'])

    archivo_startup = os.path.join(carpeta_backups, f"{nombre_router}_startup_{fecha_hora}.txt")
    with open(archivo_startup, 'w') as archivo:
        archivo.write(configuracion['startup'])

    print(f"Backup de configuracion guardado: {archivo_running} y {archivo_startup}")


def modificar_configuracion(datos_router, router):
    nombre_router = datos_router['nombre']

    respuesta = input(f"\n¿Queres cargar cambios de configuracion en {nombre_router}? <si|no>: ")

    if respuesta.lower() != 'si':
        print("No se realizaron cambios de configuracion.")
        return

    if not os.path.exists(archivo_cambios):
        print(f"ERROR: no se encontro el archivo {archivo_cambios} con los comandos a aplicar.")
        return

    try:
        router.load_merge_candidate(filename=archivo_cambios)
        diferencia = router.compare_config()

        if len(diferencia) == 0:
            print("No hay cambios para aplicar.")
            router.discard_config()
            return

        print("\nCambios detectados:")
        print(diferencia)

        respuesta_commit = input(f"¿Aplicar estos cambios en {nombre_router}? <si|no>: ")

        if respuesta_commit.lower() == 'si':
            router.commit_config()
            print("Cambios aplicados correctamente.")
        else:
            router.discard_config()
            print("Cambios descartados.")

    except Exception as error:
        print(f"ERROR al modificar la configuracion de {nombre_router}: {error}")
        router.discard_config()


def auditar_router(datos_router):
    router = conectar_router(datos_router)

    if router is None:
        return

    try:
        generar_informe(datos_router, router)
        hacer_backup_configuracion(datos_router, router)
        modificar_configuracion(datos_router, router)
    except Exception as error:
        print(f"ERROR durante la auditoria de {datos_router['nombre']}: {error}")
    finally:
        router.close()
        print(f"Conexion cerrada con {datos_router['nombre']}")



if __name__ == "__main__":
    print("=== LABORATORIO NAPALM - AUDITORIA DE RED ===")

    for datos_router in lista_routers:
        auditar_router(datos_router)

    print("\nAuditoria finalizada para todos los routers.")
