import re
import telnetlib
import threading

PATRON_PROMPT = re.compile(rb'[>#]\s*$')


usuario = "admin"
password_login = "cisco"


routers = [
    {"nombre": "R1", "ip": "10.1.1.10"},
    {"nombre": "R2", "ip": "10.1.1.20"},
    {"nombre": "R3", "ip": "10.1.1.30"},
]

# Comandos que se ejecutan en cada router
comandos = [
    "show running-config",
    "show ip interface brief",
    "show ip route",
    "show version",
]

archivo_reporte = "audit_report.txt"


def registrar(mensaje, lineas_reporte):
    # Con varios routers auditandose al mismo tiempo (threading), si cada hilo imprimiera linea por linea, los mensajes de distintos routers
    # se mezclarian en la terminal. 
    lineas_reporte.append(mensaje)


def conectar_y_obtener_salidas(ip):

    tn = telnetlib.Telnet(host=ip, timeout=10)

    # Login: usuario y contraseña
    tn.read_until(b'Username: ', timeout=10)
    tn.write(usuario.encode() + b'\n')

    tn.read_until(b'Password: ', timeout=10)
    tn.write(password_login.encode() + b'\n')

    # Despues de loguearse aparece el prompt EXEC, que puede ser "R1>" (modo
    # usuario) o "R1#"
    tn.expect([PATRON_PROMPT], timeout=10)

    # Desactivamos la paginacion para que la salida de "show running-config"
    tn.write(b'terminal length 0\n')
    tn.expect([PATRON_PROMPT], timeout=10)

    salidas = {}

    for comando in comandos:
        tn.write(comando.encode() + b'\n')
        # Leemos hasta que vuelva a aparecer el prompt "algo>" o "algo#"
        _, _, salida = tn.expect([PATRON_PROMPT], timeout=15)
        salida = salida.decode('utf-8', errors='ignore')
        salidas[comando] = salida

    tn.write(b'exit\n')
    tn.close()

    return salidas


def verificar_hostname(salida_running_config):
    for linea in salida_running_config.splitlines():
        linea = linea.strip()
        if linea.startswith("hostname "):
            nombre_configurado = linea.split()[1]
            return "OK", f"Hostname configurado: {nombre_configurado}"

    return "WARNING", "No se encontro la linea 'hostname' en la configuracion"


def verificar_interfaces(salida_ip_int_brief):
    lineas = salida_ip_int_brief.splitlines()
    detalle = []
    hay_interfaz_con_problema = False

    for linea in lineas:
        linea = linea.strip()

        if not linea or linea.startswith("Interface"):
            continue

        columnas = linea.split()

    
        if len(columnas) < 6:
            continue

        nombre_interfaz = columnas[0]
        protocolo = columnas[-1]

        # El estado "administratively down" ocupa dos palabras, hay que detectar ese caso especial antes de tomar la penultima columna
        if columnas[-3] == "administratively" and columnas[-2] == "down":
            estado = "administratively down"
        else:
            estado = columnas[-2]

        detalle.append(f"{nombre_interfaz}: {estado}/{protocolo}")

        # Una interfaz apagada a proposito (administratively down) es una decision del administrador, no la consideramos un problema aqui
        if estado != "administratively down" and (estado != "up" or protocolo != "up"):
            hay_interfaz_con_problema = True

    if detalle:
        mensaje = "; ".join(detalle)
    else:
        mensaje = "No se encontraron interfaces en la salida"

    if hay_interfaz_con_problema:
        return "WARNING", mensaje
    else:
        return "OK", mensaje


def verificar_ruta_default(salida_ip_route):
    if "Gateway of last resort is not set" in salida_ip_route:
        return "WARNING", "No hay ruta por defecto configurada"

    if "0.0.0.0/0" in salida_ip_route or "Gateway of last resort is" in salida_ip_route:
        return "OK", "Existe ruta por defecto"

    return "WARNING", "No se pudo determinar si existe ruta por defecto"


def verificar_version_ios(salida_version):
    for linea in salida_version.splitlines():
        if "IOS" in linea and "Version" in linea:
            try:
                version = linea.split("Version ")[1].split(",")[0]
                return "OK", f"Version de IOS: {version}"
            except IndexError:
                return "WARNING", "No se pudo extraer la version de IOS de la linea"

    return "WARNING", "No se encontro informacion de version de IOS"


def verificar_telnet_habilitado(salida_running_config):
    lineas = salida_running_config.splitlines()
    dentro_de_vty = False

    for linea in lineas:
        linea_sin_espacios = linea.strip()

        if linea_sin_espacios.startswith("line vty"):
            dentro_de_vty = True
            continue

        if dentro_de_vty and linea_sin_espacios.startswith("line ") and not linea_sin_espacios.startswith("line vty"):
            dentro_de_vty = False

        if dentro_de_vty and linea_sin_espacios.startswith("transport input"):
            if "telnet" in linea_sin_espacios or "all" in linea_sin_espacios:
                return "OK", "Telnet habilitado en las lineas VTY"
            else:
                return "WARNING", f"Telnet podria estar deshabilitado en VTY: '{linea_sin_espacios}'"

    return "OK", "Telnet habilitado (no se encontro restriccion en 'transport input')"


def auditar_router(nombre, ip, lineas_reporte):
    registrar("", lineas_reporte)
    registrar("#" * 50, lineas_reporte)
    registrar(f"Auditando {nombre} ({ip})", lineas_reporte)
    registrar("#" * 50, lineas_reporte)

    try:
        salidas = conectar_y_obtener_salidas(ip)
    except Exception as error:
        registrar(f"ERROR - No se pudo conectar con {nombre} ({ip}): {error}", lineas_reporte)
        return "ERROR"

    resultado_hostname, mensaje_hostname = verificar_hostname(salidas["show running-config"])
    resultado_interfaces, mensaje_interfaces = verificar_interfaces(salidas["show ip interface brief"])
    resultado_ruta, mensaje_ruta = verificar_ruta_default(salidas["show ip route"])
    resultado_version, mensaje_version = verificar_version_ios(salidas["show version"])
    resultado_telnet, mensaje_telnet = verificar_telnet_habilitado(salidas["show running-config"])

    resultados = [
        ("Hostname", resultado_hostname, mensaje_hostname),
        ("Interfaces", resultado_interfaces, mensaje_interfaces),
        ("Ruta por defecto", resultado_ruta, mensaje_ruta),
        ("Version IOS", resultado_version, mensaje_version),
        ("Telnet", resultado_telnet, mensaje_telnet),
    ]

    hay_warning = False
    hay_error = False

    for nombre_check, resultado, mensaje in resultados:
        registrar(f"[{resultado}] {nombre_check}: {mensaje}", lineas_reporte)
        if resultado == "WARNING":
            hay_warning = True
        if resultado == "ERROR":
            hay_error = True

    if hay_error:
        return "ERROR"
    elif hay_warning:
        return "WARNING"
    else:
        return "OK"


def hilo_auditoria(router, resultados_por_router, candado_resultados, candado_impresion):
 

    nombre = router["nombre"]
    ip = router["ip"]

    # Cada hilo escribe en su propia lista, asi no hay mezcla de datos.
    lineas_router = []

    estado_final = auditar_router(nombre, ip, lineas_router)

    with candado_impresion:
        for linea in lineas_router:
            print(linea)

    # Tambien protegemos con un candado el guardado del resultado, aunque
    # cada hilo usa una clave distinta del diccionario (su propio nombre).
    with candado_resultados:
        resultados_por_router[nombre] = {"estado": estado_final, "lineas": lineas_router}


if __name__ == "__main__":

    resultados_por_router = {}
    candado_resultados = threading.Lock()
    candado_impresion = threading.Lock()

    hilos = []

    # Creamos y arrancamos un hilo por cada router, para que las 3
    for router in routers:
        hilo = threading.Thread(
            target=hilo_auditoria,
            args=(router, resultados_por_router, candado_resultados, candado_impresion),
        )
        hilos.append(hilo)
        hilo.start()

    for hilo in hilos:
        hilo.join()

    lineas_reporte = []
    resumen = []

    for router in routers:
        nombre = router["nombre"]
        resultado_router = resultados_por_router[nombre]

        lineas_reporte.extend(resultado_router["lineas"])
        resumen.append((nombre, resultado_router["estado"]))

    # Guardamos en que linea empieza el resumen, para poder imprimirlo
    inicio_resumen = len(lineas_reporte)

    registrar("", lineas_reporte)
    registrar("=" * 40, lineas_reporte)
    registrar("AUDIT SUMMARY", lineas_reporte)
    registrar("=" * 40, lineas_reporte)

    total_ok = 0
    total_warning = 0
    total_error = 0

    for nombre, estado in resumen:
        registrar(f"{nombre} - {estado}", lineas_reporte)

        if estado == "OK":
            total_ok += 1
        elif estado == "WARNING":
            total_warning += 1
        elif estado == "ERROR":
            total_error += 1

    registrar("", lineas_reporte)
    registrar(f"Total: {len(resumen)}", lineas_reporte)
    registrar(f"OK: {total_ok}", lineas_reporte)
    registrar(f"WARNING: {total_warning}", lineas_reporte)
    registrar(f"ERROR: {total_error}", lineas_reporte)
    registrar("=" * 40, lineas_reporte)

    for linea in lineas_reporte[inicio_resumen:]:
        print(linea)

    with open(archivo_reporte, "w") as archivo:
        for linea in lineas_reporte:
            archivo.write(linea + "\n")

    print("")
    print(f"Reporte guardado en: {archivo_reporte}")
