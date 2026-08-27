import warnings
import time
import logging
import threading
import paramiko
# Silenciar TODAS las advertencias antes de importar paramiko
warnings.filterwarnings("ignore")
# Desactivar logs de paramiko
logging.getLogger("paramiko").setLevel(logging.CRITICAL)

# Algunos equipos Cisco con IOS antiguo solo soportan algoritmos de intercambio de llaves (kex) viejos
paramiko.Transport._preferred_kex = (
    'diffie-hellman-group14-sha1',
    'diffie-hellman-group-exchange-sha1',
    'diffie-hellman-group1-sha1',
) + paramiko.Transport._preferred_kex


# VLANs que se deben crear y nombrar en TODOS los switches
vlans_a_crear = [
    {'numero': 10, 'nombre': 'Ventas'},
    {'numero': 20, 'nombre': 'Admin'},
    {'numero': 30, 'nombre': 'Dev'},
]

# VLANs que se deben permitir en todos los puertos trunk
vlans_permitidas_trunk = '1,10,20,30'

# Lista de switches a configurar, con sus puertos trunk correspondientes
lista_switches = [
    {
        'hostname': '192.168.1.15',
        'usuario': 'admin',
        'password': 'cisco',
        'puertos_trunk': ['Ethernet0/1'],
    },
    {
        'hostname': '192.168.1.16',
        'usuario': 'admin',
        'password': 'cisco',
        'puertos_trunk': ['Ethernet0/1', 'Ethernet0/2'],
    },
    {
        'hostname': '192.168.1.17',
        'usuario': 'admin',
        'password': 'cisco',
        'puertos_trunk': ['Ethernet0/1'],
    },
]

# Listas donde vamos guardando qué switches se configuraron bien y cuáles fallaron
switches_exitosos = []
switches_fallidos = []


# Función que revisa la salida de "show vlan brief" y confirma que cada VLAN
def verificar_vlans(salida_show_vlan, vlans_esperadas):
    resultado_final = True
    lineas_salida = salida_show_vlan.splitlines()

    for vlan in vlans_esperadas:
        vlan_encontrada = False

        for linea in lineas_salida:
            columnas = linea.split()
            if len(columnas) >= 2 and columnas[0] == str(vlan['numero']):
                if columnas[1] == vlan['nombre']:
                    vlan_encontrada = True
                break

        if vlan_encontrada == False:
            print(f"  VLAN {vlan['numero']} ({vlan['nombre']}) no se encontró o el nombre no coincide")
            resultado_final = False

    return resultado_final


# Función que revisa la salida de "show interfaces <puerto> switchport" y confirma que el puerto esté en modo trunk y tenga permitidas las VLANs esperadas
def verificar_puerto_trunk(salida_show_switchport, vlans_permitidas_esperadas):
    modo_trunk_activo = False
    vlans_correctas = False

    lineas_salida = salida_show_switchport.splitlines()
    for linea in lineas_salida:
        linea_limpia = linea.strip()

        if linea_limpia.startswith("Administrative Mode:") and "trunk" in linea_limpia:
            modo_trunk_activo = True

        if linea_limpia.startswith("Trunking VLANs Enabled:"):
            vlans_en_puerto = linea_limpia.split(":")[1].strip()
            if vlans_en_puerto == vlans_permitidas_esperadas:
                vlans_correctas = True

    return modo_trunk_activo and vlans_correctas


# Función que se conecta a un switch, crea las VLANs, configura los puertos trunk, guarda la configuración y comprueba que todo haya quedado bien.
def configurar_switch(switch):
    hostname = switch['hostname']
    print(f"\nConectando a {hostname}...")

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=hostname,
            port=22,
            username=switch['usuario'],
            password=switch['password'],
            look_for_keys=False,
            allow_agent=False
        )

        shell = ssh_client.invoke_shell()

        shell.send('terminal length 0\n')
        time.sleep(1)
        shell.recv(50000)  # limpiamos el buffer con el banner/prompt inicial

        # Entramos a modo de configuración global
        shell.send('configure terminal\n')
        time.sleep(1)

        # Creamos y nombramos las VLANs en este switch
        for vlan in vlans_a_crear:
            shell.send(f'vlan {vlan["numero"]}\n')
            time.sleep(1)

            shell.send(f'name {vlan["nombre"]}\n')
            time.sleep(1)

            shell.send('exit\n')
            time.sleep(1)

        # Configuramos cada puerto trunk de este switch, permitiendo las VLANs indicadas
        for puerto in switch['puertos_trunk']:
            shell.send(f'interface {puerto}\n')
            time.sleep(1)

            # Fijamos la encapsulación a dot1q antes de activar el modo trunk.
            shell.send('switchport trunk encapsulation dot1q\n')
            time.sleep(1)

            shell.send('switchport mode trunk\n')
            time.sleep(1)

            shell.send(f'switchport trunk allowed vlan {vlans_permitidas_trunk}\n')
            time.sleep(1)

            shell.send('exit\n')
            time.sleep(1)

        shell.send('end\n')
        time.sleep(1)

        # Guardamos la configuración en la memoria del switch
        shell.send('write memory\n')
        time.sleep(3)

        shell.recv(50000)  # limpiamos el buffer de todo lo enviado hasta aquí

        # Verificación de las VLANs 
        shell.send('show vlan brief\n')
        time.sleep(2)
        salida_show_vlan = shell.recv(50000).decode('utf-8')

        vlans_correctas = verificar_vlans(salida_show_vlan, vlans_a_crear)

        # Verificación de cada puerto trunk, uno por uno
        puertos_correctos = True
        for puerto in switch['puertos_trunk']:
            shell.send(f'show interfaces {puerto} switchport\n')
            time.sleep(2)
            salida_show_switchport = shell.recv(50000).decode('utf-8')

            puerto_ok = verificar_puerto_trunk(salida_show_switchport, vlans_permitidas_trunk)

            if puerto_ok == True:
                print(f"Switch {hostname}: puerto {puerto} configurado correctamente como trunk con VLANs {vlans_permitidas_trunk}")
            else:
                print(f"Switch {hostname}: el puerto {puerto} no quedó como se esperaba, revisar manualmente")
                puertos_correctos = False

        # Cerramos la conexión SSH con el dispositivo
        if ssh_client.get_transport().is_active() == True:
            print(f"Cerrando conexión con {hostname}")
            ssh_client.close()

        # Comprobamos con Python que tanto las VLANs como los puertos trunk quedaron bien
        if vlans_correctas == True and puertos_correctos == True:
            print(f"Switch {hostname}: configuración completa y verificada correctamente")
            switches_exitosos.append(hostname)
        else:
            print(f"Switch {hostname}: hubo problemas en la verificación, revisar manualmente")
            switches_fallidos.append(hostname)

    except Exception as error:
        print(f"Error al conectar o configurar el switch {hostname}: {error}")
        switches_fallidos.append(hostname)


# Creamos un hilo por cada switch para que todos se configuren en paralelo.
if __name__ == "__main__":
    hilos = list()

    for switch in lista_switches:
        hilo = threading.Thread(target=configurar_switch, args=(switch,))
        hilos.append(hilo)

    for hilo in hilos:
        hilo.start()

    for hilo in hilos:
        hilo.join()

    # Resumen final del proceso de configuración
    print("\n----- RESUMEN DE CONFIGURACIÓN DE VLANs Y TRUNKS -----")

    print(f"Switches configurados correctamente ({len(switches_exitosos)}):")
    for hostname in switches_exitosos:
        print(f"  - {hostname}")

    print(f"Switches con errores ({len(switches_fallidos)}):")
    for hostname in switches_fallidos:
        print(f"  - {hostname}")
