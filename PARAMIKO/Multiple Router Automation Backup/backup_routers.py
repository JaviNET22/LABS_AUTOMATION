import warnings
import time
import logging
import os
import paramiko
# 1. Silenciar TODAS las advertencias antes de importar paramiko
warnings.filterwarnings("ignore")
# 2. Desactivar logs de paramiko
logging.getLogger("paramiko").setLevel(logging.CRITICAL)

# 2.1 Algunos equipos Cisco con IOS antiguo solo soportan algoritmos de intercambio de llaves (kex) viejos, que las versiones recientes de paramiko
# ya no traen habilitados por defecto. 
paramiko.Transport._preferred_kex = (
    'diffie-hellman-group14-sha1',
    'diffie-hellman-group-exchange-sha1',
    'diffie-hellman-group1-sha1',
) + paramiko.Transport._preferred_kex


# 3. Lista de dispositivos a los que vamos a hacer backup
lista_ips = ['10.1.1.11', '10.1.1.12', '10.1.1.13']

# 5. Listas donde vamos guardando qué backups salieron bien y cuáles fallaron
backups_exitosos = []
backups_fallidos = []

# 6. Recorremos cada IP de la lista y hacemos el backup de su configuración
for ip in lista_ips:
    print(f"\nConectando a {ip}...")

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=ip,
            port=22,
            username="admin",
            password="cisco",
            look_for_keys=False,
            allow_agent=False
        )

        shell = ssh_client.invoke_shell()

        shell.send('terminal length 0\n')
        time.sleep(1)

        shell.send('show running-config\n')
        time.sleep(2)  # esperamos a que el router termine de enviar toda la configuración

        output = shell.recv(50000)
        output = output.decode('utf-8')

        # Cerramos la conexión SSH con el dispositivo
        if ssh_client.get_transport().is_active() == True:
            print(f"Cerrando conexión con {ip}")
            ssh_client.close()

        # Guardamos la configuración en un archivo de texto, nombrado con la IP del dispositivo
        nombre_archivo = f"{ip}_backup.txt"
        with open(nombre_archivo, 'w') as archivo_backup:
            archivo_backup.write(output)

        # Comprobamos que el archivo se haya creado correctamente y que no esté vacío
        if os.path.exists(nombre_archivo) and os.path.getsize(nombre_archivo) > 0:
            print(f"Backup de {ip} guardado correctamente en {nombre_archivo}")
            backups_exitosos.append(ip)
        else:
            print(f"El archivo de backup de {ip} no se creó correctamente")
            backups_fallidos.append(ip)

    except Exception as error:
        print(f"Error al conectar o respaldar el dispositivo {ip}: {error}")
        backups_fallidos.append(ip)

# 7. Resumen final del proceso de backup
print("\n----- RESUMEN DEL BACKUP -----")

print(f"Backups exitosos ({len(backups_exitosos)}):")
for ip in backups_exitosos:
    print(f"  - {ip}")

print(f"Backups fallidos ({len(backups_fallidos)}):")
for ip in backups_fallidos:
    print(f"  - {ip}")
