import warnings
import time
import logging
import threading
from datetime import datetime
import paramiko
# Silenciar advertencias y logs de paramiko
warnings.filterwarnings("ignore")
logging.getLogger("paramiko").setLevel(logging.CRITICAL)

# Soporte para kex antiguos en equipos con IOS viejo
paramiko.Transport._preferred_kex = (
    'diffie-hellman-group14-sha1',
    'diffie-hellman-group-exchange-sha1',
    'diffie-hellman-group1-sha1',
) + paramiko.Transport._preferred_kex


# Lista de dispositivos de los que se va a levantar el inventario
lista_dispositivos = [
    {'hostname': '10.1.1.10', 'usuario': 'u1', 'password': 'cisco'},
    {'hostname': '10.1.1.20', 'usuario': 'u1', 'password': 'cisco'},  
    {'hostname': '10.1.1.30', 'usuario': 'u1', 'password': 'cisco'},  
]

# Listas compartidas: cada hilo agrega aqui el resultado de SU dispositivo
inventario_dispositivos = []
dispositivos_exitosos = []
dispositivos_fallidos = []


# Funcion que busca la linea "hostname X" en la salida de "show run | include hostname" y devuelve el nombre real del dispositivo
def obtener_nombre_dispositivo(salida_show_run):
    lineas_salida = salida_show_run.splitlines()
    for linea in lineas_salida:
        linea = linea.strip()
        if linea.startswith("hostname "):
            columnas = linea.split()
            return columnas[1]
    return "Desconocido"

# Funcion que busca la linea con "IOS Software" en la salida de "show version" y devuelve un texto corto con el tipo de sistema operativo
def obtener_version_sistema(salida_show_version):
    lineas_salida = salida_show_version.splitlines()
    for linea in lineas_salida:
        if "IOS Software" in linea:
            if "IOS XE" in linea:
                return "Cisco IOS XE"
            return "Cisco IOS"
    return "Desconocido"


# Funcion que recorre la salida de "show ip interface brief" y arma una lista con cada interfaz, su IP y su estado 
def parsear_interfaces(salida_show_ip_int_br):
    lista_interfaces = []
    lineas_salida = salida_show_ip_int_br.splitlines()
    for linea in lineas_salida:
        columnas = linea.split()
        if len(columnas) >= 6 and columnas[0] != "Interface":
            nombre_interfaz = columnas[0]
            ip_interfaz = columnas[1]
            estado_interfaz = columnas[-2]
            estado_protocolo = columnas[-1]
            lista_interfaces.append({
                'nombre': nombre_interfaz,
                'ip': ip_interfaz,
                'estado_interfaz': estado_interfaz,
                'estado_protocolo': estado_protocolo
            })
    return lista_interfaces


# 9. Funcion que cuenta cuantas interfaces estan en up/up
def contar_interfaces_activas(lista_interfaces):
    total_activas = 0
    for interfaz in lista_interfaces:
        if interfaz['estado_interfaz'].lower() == "up" and interfaz['estado_protocolo'].lower() == "up":
            total_activas += 1
    return total_activas


# 10. Funcion que se conecta a UN dispositivo, recopila su inventario y guarda el resultado en las listas compartidas. 
def recopilar_inventario_dispositivo(dispositivo):
    ip_gestion = dispositivo['hostname']
    print(f"\nConectando a {ip_gestion}...")

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=ip_gestion,
            port=22,
            username=dispositivo['usuario'],
            password=dispositivo['password'],
            look_for_keys=False,
            allow_agent=False
        )

        shell = ssh_client.invoke_shell()

        shell.send('terminal length 0\n')
        time.sleep(1)
        shell.recv(50000)  

        shell.send('show run | include hostname\n')
        time.sleep(1)
        salida_hostname = shell.recv(50000).decode('utf-8')
        nombre_dispositivo = obtener_nombre_dispositivo(salida_hostname)

        shell.send('show version\n')
        time.sleep(2)
        salida_version = shell.recv(50000).decode('utf-8')
        version_sistema = obtener_version_sistema(salida_version)

        shell.send('show ip interface brief\n')
        time.sleep(2)
        salida_interfaces = shell.recv(50000).decode('utf-8')
        lista_interfaces = parsear_interfaces(salida_interfaces)
        total_interfaces_activas = contar_interfaces_activas(lista_interfaces)

        if ssh_client.get_transport().is_active() == True:
            print(f"Cerrando conexion con {ip_gestion}")
            ssh_client.close()

        inventario_dispositivos.append({
            'ip_gestion': ip_gestion,
            'nombre': nombre_dispositivo,
            'version': version_sistema,
            'interfaces_activas': total_interfaces_activas,
            'error': None
        })
        dispositivos_exitosos.append(ip_gestion)
        print(f"Dispositivo {ip_gestion} ({nombre_dispositivo}): inventario recopilado correctamente")

    except Exception as error:
        print(f"Error al conectar o recopilar inventario de {ip_gestion}: {error}")
        inventario_dispositivos.append({
            'ip_gestion': ip_gestion,
            'nombre': 'Desconocido',
            'version': 'Desconocido',
            'interfaces_activas': 0,
            'error': str(error)
        })
        dispositivos_fallidos.append(ip_gestion)


# Funcion que escribe el archivo de texto con el inventario final
def guardar_inventario(lista_inventario, nombre_archivo):
    with open(nombre_archivo, 'w', encoding='utf-8') as archivo_inventario:
        archivo_inventario.write("========== INVENTARIO DE RED ==========\n\n")

        for info_dispositivo in lista_inventario:
            archivo_inventario.write(f"Dispositivo: {info_dispositivo['nombre']}\n")
            archivo_inventario.write(f"IP de gestion: {info_dispositivo['ip_gestion']}\n")

            if info_dispositivo['error'] is None:
                archivo_inventario.write(f"Sistema operativo: {info_dispositivo['version']}\n")
                archivo_inventario.write(f"Interfaces activas: {info_dispositivo['interfaces_activas']}\n")
            else:
                archivo_inventario.write(f"Error: no se pudo recopilar el inventario ({info_dispositivo['error']})\n")

            archivo_inventario.write("\n-------------------------------------\n\n")


# Creamos un hilo por cada dispositivo para recopilar todo.
hilos = list()

for dispositivo in lista_dispositivos:
    hilo = threading.Thread(target=recopilar_inventario_dispositivo, args=(dispositivo,))
    hilos.append(hilo)

for hilo in hilos:
    hilo.start()

for hilo in hilos:
    hilo.join()

# Ya con todos los hilos terminados, guardamos el inventario en el archivo
ahora = datetime.now()
nombre_archivo_inventario = f"inventario_red_{ahora.year}-{ahora.month:02d}-{ahora.day:02d}.txt"
guardar_inventario(inventario_dispositivos, nombre_archivo_inventario)

# Resumen final en consola
print("\n----- RESUMEN DEL INVENTARIO DE RED -----")

print(f"Dispositivos recopilados correctamente ({len(dispositivos_exitosos)}):")
for ip in dispositivos_exitosos:
    print(f"  - {ip}")

print(f"Dispositivos con errores ({len(dispositivos_fallidos)}):")
for ip in dispositivos_fallidos:
    print(f"  - {ip}")

print(f"\nInventario guardado en: {nombre_archivo_inventario}")
