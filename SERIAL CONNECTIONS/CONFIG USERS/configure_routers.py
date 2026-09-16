import serial
import threading
import time
import re



routers = [
    {"port": "/home/javinet/ttyS0", "hostname": "R1"},
    {"port": "/home/javinet/ttyS1", "hostname": "R2"},
    {"port": "/home/javinet/ttyS2", "hostname": "R3"},
]

BAUDRATE = 9600
BYTESIZE = 8
PARIDAD = 'N'
STOPBITS = 1

USUARIO = 'javier'
PRIVILEGIO = '15'
CLAVE = 'javier123'
TEXTO_BANNER = 'ACCESO SOLO AUTORIZADO'

bloqueo = threading.Lock()

resultados = {}


def imprimir(texto):
    with bloqueo:
        print(texto)


def abrir_conexion(puerto):
    consola = serial.Serial(
        port=puerto,
        baudrate=BAUDRATE,
        bytesize=BYTESIZE,
        parity=PARIDAD,
        stopbits=STOPBITS,
        timeout=2
    )
    return consola


def procesar_negociacion_telnet(datos):
    texto_limpio = b''
    respuesta = b''

    i = 0
    while i < len(datos):
        if datos[i] == 0xff and i + 2 < len(datos):
            comando = datos[i + 1]
            opcion = datos[i + 2]

            if comando == 0xfd:      # el servidor propone "DO"   -> respondemos "WONT"
                respuesta += bytes([0xff, 0xfc, opcion])
            elif comando == 0xfb:    # el servidor propone "WILL" -> respondemos "DONT"
                respuesta += bytes([0xff, 0xfe, opcion])

            i += 3  # nos saltamos los 3 bytes de la negociacion (IAC + comando + opcion)
        else:
            texto_limpio += bytes([datos[i]])
            i += 1

    return texto_limpio, respuesta


def leer_respuesta(consola):
    datos = consola.read_all()
    texto_limpio, respuesta_telnet = procesar_negociacion_telnet(datos)

    if respuesta_telnet:
        consola.write(respuesta_telnet)

    return texto_limpio.decode(errors='ignore')


def enviar_comando(consola, comando, espera=1, mostrar=False):
    # mostrar=True se usa solo para los comandos que queremos ver en pantalla
    if mostrar:
        imprimir('    >> ' + comando)

    consola.write(comando.encode() + b'\r\n')
    time.sleep(espera)


def esperar_prompt(consola, hostname, intentos=5, espera=2):
    texto_acumulado = ''

    for numero_de_intento in range(intentos):
        enviar_comando(consola, '', espera=espera)
        texto_acumulado += leer_respuesta(consola)

        if re.search(re.escape(hostname) + r'#\s*$', texto_acumulado):
            return True

    return False


def configure_router(port, hostname):

    try:
        imprimir('[+] Conectando ' + hostname + '...')
        consola = abrir_conexion(port)
        consola.reset_input_buffer()

        # El router no tiene modo enable: en cuanto aparece el prompt "R1#"
        # entramos directo a configuracion
        esperar_prompt(consola, hostname)

        enviar_comando(consola, 'configure terminal', espera=1)
        leer_respuesta(consola)

        imprimir('[+] Configurando hostname...')
        enviar_comando(consola, 'hostname ' + hostname, espera=1)
        leer_respuesta(consola)

        imprimir('[+] Creando usuario...')
        comando_usuario = 'username ' + USUARIO + ' privilege ' + PRIVILEGIO + ' secret ' + CLAVE
        enviar_comando(consola, comando_usuario, espera=1, mostrar=True)
        leer_respuesta(consola)

        imprimir('[+] Configurando banner...')
        comando_banner = 'banner motd #' + TEXTO_BANNER + '#'
        enviar_comando(consola, comando_banner, espera=1, mostrar=True)
        leer_respuesta(consola)

        imprimir('[+] Configurando consola...')
        enviar_comando(consola, 'line console 0', espera=1)
        leer_respuesta(consola)

        enviar_comando(consola, 'login local', espera=1)
        leer_respuesta(consola)

        enviar_comando(consola, 'exit', espera=1)
        leer_respuesta(consola)

        # Salimos del modo de configuracion global
        enviar_comando(consola, 'end', espera=1)
        leer_respuesta(consola)

        # Comando de verificacion final
        enviar_comando(consola, 'show run | include hostname', espera=2)
        leer_respuesta(consola)

        consola.close()

        imprimir('[OK] ' + hostname + ' configurado correctamente')

        with bloqueo:
            resultados[hostname] = True

    except Exception as error:
        imprimir('[ERROR] Fallo configurando ' + hostname + ': ' + str(error))

        with bloqueo:
            resultados[hostname] = False


def main():

    hilos = []
    for router in routers:
        hilo = threading.Thread(target=configure_router, args=(router['port'], router['hostname']))
        hilos.append(hilo)
        hilo.start()

    # Ahora si esperamos a que todos los hilos terminen antes de seguir
    for hilo in hilos:
        hilo.join()

    imprimir('')
    imprimir('=' * 50)
    imprimir(' ' * 14 + 'LAB COMPLETADO')
    imprimir('=' * 50)

    for router in routers:
        hostname = router['hostname']
        if resultados.get(hostname):
            imprimir('[OK] ' + hostname)
        else:
            imprimir('[ERROR] ' + hostname)


if __name__ == "__main__":
    main()
