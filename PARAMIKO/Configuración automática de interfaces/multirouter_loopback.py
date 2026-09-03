import warnings
import time
import logging
import threading
import paramiko
# 1. Silenciar TODAS las advertencias antes de importar paramiko
warnings.filterwarnings("ignore")
# 2. Desactivar logs de paramiko
logging.getLogger("paramiko").setLevel(logging.CRITICAL)

# 2.1 Algunos equipos Cisco con IOS antiguo solo soportan algoritmos de intercambio de llaves (kex) viejos
paramiko.Transport._preferred_kex = (
    'diffie-hellman-group14-sha1',
    'diffie-hellman-group-exchange-sha1',
    'diffie-hellman-group1-sha1',
) + paramiko.Transport._preferred_kex


# 3. Lista de routers a configurar
lista_routers = [
    {
        'hostname': '10.1.1.10',
        'usuario': 'admin',
        'password': 'cisco',
        'numero_loopback': 1,
        'ip_loopback': '1.1.1.1',
        'mascara_loopback': '255.255.255.255' 
    },
    {
        'hostname': '10.1.1.20',
        'usuario': 'admin',
        'password': 'cisco',
        'numero_loopback': 2,
        'ip_loopback': '1.1.1.1',
        'mascara_loopback': '255.255.255.255'
    },
    {
        'hostname': '10.1.1.30',
        'usuario': 'admin',
        'password': 'cisco',
        'numero_loopback': 3,
        'ip_loopback': '3.3.3.3',
        'mascara_loopback': '255.255.255.255'
    },
]

# 4. Listas donde vamos guardando qué routers se configuraron bien y cuáles fallaron
routers_exitosos = []
routers_fallidos = []


# 5. Función que revisa la salida de "show ip interface brief" y confirma que la interfaz Loopback exista, tenga la IP correcta y esté activa (up/up)
def verificar_loopback(salida_show, numero_loopback, ip_esperada):
    nombre_interfaz = f"Loopback{numero_loopback}"

    lineas_salida = salida_show.splitlines()
    for linea in lineas_salida:
        columnas = linea.split()
        if len(columnas) >= 6 and columnas[0] == nombre_interfaz:
            ip_encontrada = columnas[1]
            estado_interfaz = columnas[-2]
            estado_protocolo = columnas[-1]
            if ip_encontrada == ip_esperada and estado_interfaz.lower() == "up" and estado_protocolo.lower() == "up":
                return True
            else:
                return False

    # Si no encontramos ninguna línea con esa interfaz, es que no existe
    return False


# 6. Función que se conecta a un router, configura la Loopback, guarda la configuración y comprueba que todo haya quedado bien.
def configurar_router(router):
    hostname = router['hostname']
    print(f"\nConectando a {hostname}...")

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=hostname,
            port=22,
            username=router['usuario'],
            password=router['password'],
            look_for_keys=False,
            allow_agent=False
        )

        shell = ssh_client.invoke_shell()

        shell.send('terminal length 0\n')
        time.sleep(1)

        # Entramos a modo config mode y creamos (o modificamos) la interfaz loopback con la IP indicada en el diccionario del router
        shell.send('configure terminal\n')
        time.sleep(1)

        shell.send(f'interface loopback {router["numero_loopback"]}\n')
        time.sleep(1)

        shell.send(f'ip address {router["ip_loopback"]} {router["mascara_loopback"]}\n')
        time.sleep(1)

        shell.send('no shutdown\n')
        time.sleep(1)

        shell.send('end\n')
        time.sleep(1)

        # Guardamos la configuración en la memoria del router
        shell.send('write memory\n')
        time.sleep(3)


        shell.recv(50000)

        shell.send('show ip interface brief\n')
        time.sleep(2)

        salida_show = shell.recv(50000)
        salida_show = salida_show.decode('utf-8')

        # Cerramos la conexión SSH con el dispositivo
        if ssh_client.get_transport().is_active() == True:
            print(f"Cerrando conexión con {hostname}")
            ssh_client.close()

        # Comprobamos con Python que la interfaz Loopback existe, tiene la IP correcta y está activa
        loopback_correcta = verificar_loopback(salida_show, router['numero_loopback'], router['ip_loopback'])

        if loopback_correcta == True:
            print(f"Router {hostname}: Loopback{router['numero_loopback']} configurada correctamente con IP {router['ip_loopback']}")
            routers_exitosos.append(hostname)
        else:
            print(f"Router {hostname}: la Loopback{router['numero_loopback']} no quedó como se esperaba, revisar manualmente")
            routers_fallidos.append(hostname)

    except Exception as error:
        print(f"Error al conectar o configurar el router {hostname}: {error}")
        routers_fallidos.append(hostname)


# 7. Creamos un hilo por cada router para que todos se configuren en paralelo.
hilos = list()

for router in lista_routers:
    hilo = threading.Thread(target=configurar_router, args=(router,))
    hilos.append(hilo)

for hilo in hilos:
    hilo.start()

for hilo in hilos:
    hilo.join()

# 8. Resumen final del proceso de configuración
print("\n----- RESUMEN DE CONFIGURACIÓN DE LOOPBACKS -----")

print(f"Routers configurados correctamente ({len(routers_exitosos)}):")
for hostname in routers_exitosos:
    print(f"  - {hostname}")

print(f"Routers con errores ({len(routers_fallidos)}):")
for hostname in routers_fallidos:
    print(f"  - {hostname}")
