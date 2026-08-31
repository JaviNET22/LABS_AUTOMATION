from netmiko import ConnectHandler
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException
import time
import getpass

SWITCHES = {
    "SW1": {"host": "192.168.1.20", "role": "vtp_server"},
    "SW2": {"host": "192.168.1.30", "role": "vtp_client"},
    "SW3": {"host": "192.168.1.40", "role": "vtp_client"},
}

VLANS = {
    10: "USERS",
    20: "SERVERS",
    30: "MANAGEMENT",
    40: "VOICE",
}

TRUNK_PORTS = {
    "SW1": ["e0/1"],
    "SW2": ["e0/1", "e0/2"],
    "SW3": ["e0/1"],
}

# ip de gestion del switch que ya esta configurado como VTP Server
VTP_SERVER_HOST = "192.168.1.20"

USUARIO_SSH = "admin"
PASSWORD_SSH = getpass.getpass("Pon aquí tu contraseña: ")


def conectar_switch(nombre_switch, datos_switch):

    device = {
        'device_type': 'cisco_ios',   
        'host': datos_switch["host"], 
        'username': USUARIO_SSH,      
        'password': PASSWORD_SSH,     
        'secret': PASSWORD_SSH,       
        'port': 22,                   
        'verbose': False,             
    }

    try:
        connection = ConnectHandler(**device)
        connection.enable()  # entra en modo privilegiado (enable) para poder configurar el switch
        print(f'[OK] Conexion establecida con {nombre_switch} ({datos_switch["host"]})')
        return connection

    except NetmikoAuthenticationException:
        print(f'[ERROR] Usuario o contraseña incorrectos en {nombre_switch} ({datos_switch["host"]})')
        return None

    except NetmikoTimeoutException:
        print(f'[ERROR] Tiempo de espera agotado conectando a {nombre_switch} ({datos_switch["host"]})')
        return None

    except Exception as error:
        print(f'[ERROR] No se pudo conectar a {nombre_switch}: {error}')
        return None


def configurar_trunks(connection, nombre_switch):
    
    puertos = TRUNK_PORTS.get(nombre_switch, [])
    if not puertos:
        print(f'[AVISO] No hay puertos de trunk definidos para {nombre_switch}')
        return

    # se arma la lista de vlans permitidas: la 1 (nativa/gestion) + las del diccionario VLANS
    lista_vlans_permitidas = [1] + list(VLANS.keys())
    vlans_permitidas_texto = ",".join(str(vlan_id) for vlan_id in lista_vlans_permitidas)

    for puerto in puertos:
        comandos = [
            f'interface {puerto}',
            'switchport trunk encapsulation dot1q',
            'switchport mode trunk',
            f'switchport trunk allowed vlan {vlans_permitidas_texto}',
        ]
        try:
            connection.send_config_set(comandos)
            print(f'[OK] Puerto {puerto} de {nombre_switch} configurado como trunk')
        except Exception as error:
            print(f'[ERROR] No se pudo configurar el trunk en {puerto} de {nombre_switch}: {error}')


def crear_vlans_en_vtp_server(connection, nombre_switch):
    # Crea dinamicamente todas las VLANs definidas en el diccionario VLANS, esta funcion solo debe llamarse sobre la conexion del VTP Server
    for vlan_id, nombre_vlan in VLANS.items():
        comandos = [
            f'vlan {vlan_id}',
            f'name {nombre_vlan}',
        ]
        try:
            connection.send_config_set(comandos)
            print(f'[OK] VLAN {vlan_id} ({nombre_vlan}) creada en {nombre_switch}')
        except Exception as error:
            print(f'[ERROR] No se pudo crear la VLAN {vlan_id} en {nombre_switch}: {error}')


def verificar_vlans(connection, nombre_switch):
    # Revisa la salida de 'show vlan brief' y comprueba que todas las VLANs del diccionario VLANS existan en ese switch (server o cliente).
    print(f'--- Verificando VLANs en {nombre_switch} ---')
    salida = connection.send_command('show vlan brief')

    for vlan_id, nombre_vlan in VLANS.items():
        if str(vlan_id) in salida:
            print(f'[OK] VLAN {vlan_id} ({nombre_vlan}) presente en {nombre_switch}')
        else:
            print(f'[ERROR] VLAN {vlan_id} ({nombre_vlan}) NO aparece en {nombre_switch}')


def verificar_trunks(connection, nombre_switch):
    # Muestra la salida de 'show interfaces trunk' para revisar a simple vista el estado de los trunks
    print(f'--- Verificando trunks en {nombre_switch} ---')
    salida = connection.send_command('show interfaces trunk')
    print(salida)

if PASSWORD_SSH == "":
        print('[ERROR] Debes introducir una contraseña para continuar')
        exit()

# aqui se guardan las conexiones abiertas correctamente, para poder usarlas mas adelante y cerrarlas todas al final
conexiones = {}


nombre_vtp_server = None
for nombre_switch, datos_switch in SWITCHES.items():
    if datos_switch["host"] == VTP_SERVER_HOST:
        nombre_vtp_server = nombre_switch

print('#' * 50)
print('PASO 1: Conectando a los switches y configurando trunks')
print('#' * 50)

for nombre_switch, datos_switch in SWITCHES.items():
    connection = conectar_switch(nombre_switch, datos_switch)
    if connection is not None:
        conexiones[nombre_switch] = connection
        configurar_trunks(connection, nombre_switch)

print('#' * 50)
print('PASO 2: Creando las VLANs en el VTP Server')
print('#' * 50)

if nombre_vtp_server in conexiones:
    crear_vlans_en_vtp_server(conexiones[nombre_vtp_server], nombre_vtp_server)
else:
    print(f'[ERROR] No hay conexion con el VTP Server ({nombre_vtp_server}), no se pueden crear las VLANs')

print('Esperando unos segundos a que VTP propague las VLANs a los clientes...')
time.sleep(10)

print('#' * 50)
print('Verificando VLANs en todos los switches')
print('#' * 50)

for nombre_switch, connection in conexiones.items():
    verificar_vlans(connection, nombre_switch)

print('#' * 50)
print('Verificando trunks en todos los switches')
print('#' * 50)

for nombre_switch, connection in conexiones.items():
    verificar_trunks(connection, nombre_switch)

print('#' * 50)
print('Cerrando todas las conexiones')
print('#' * 50)

for nombre_switch, connection in conexiones.items():
    connection.disconnect()
    print(f'[OK] Conexion cerrada con {nombre_switch}')
