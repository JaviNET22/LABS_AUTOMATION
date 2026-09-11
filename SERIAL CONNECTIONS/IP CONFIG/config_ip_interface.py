import serial
import time

PUERTO = '/home/javinet/ttyS0'
BAUDRATE = 9600

INTERFAZ = 'f0/0'
DIRECCION_IP = '10.1.1.10'
MASCARA = '255.255.255.0'


def enviar_comando(console, comando, espera=1, mostrar=True):
    if mostrar:
        print('Enviando comando: ' + comando)

    console.write(comando.encode() + b'\r\n')
    time.sleep(espera)


def leer_respuesta(console):
    salida = console.read_all()
    return salida.decode(errors='ignore')


def main():

    try:
        console = serial.Serial(
            port=PUERTO,
            baudrate=BAUDRATE,
            parity='N',
            stopbits=1,
            bytesize=8,
            timeout=2
        )

    except Exception as error:
        print('Error al abrir el puerto serie: ' + str(error))
        return

    print('Consola abierta correctamente en ' + PUERTO)

    console.reset_input_buffer()

    enviar_comando(console, '', mostrar=False)
    leer_respuesta(console)

    enviar_comando(console, 'enable', mostrar=False)
    leer_respuesta(console)

    enviar_comando(console, 'terminal length 0', mostrar=False)
    leer_respuesta(console)

    enviar_comando(console, 'configure terminal', mostrar=False)
    leer_respuesta(console)

    enviar_comando(console, 'interface ' + INTERFAZ)
    print(leer_respuesta(console))

    enviar_comando(console, 'ip address ' + DIRECCION_IP + ' ' + MASCARA)
    print(leer_respuesta(console))

    enviar_comando(console, 'no shutdown', espera=2, mostrar=False)
    leer_respuesta(console)

    enviar_comando(console, 'exit', mostrar=False)
    enviar_comando(console, 'exit', mostrar=False)
    leer_respuesta(console)

    time.sleep(5)

    enviar_comando(console, 'show ip interface brief', espera=3)

    print('Resultado de la verificacion:')
    print(leer_respuesta(console))

    console.close()
    print('Conexion serial cerrada.')


if __name__ == "__main__":
    main()
