# Configuración masiva de VLANs con Netmiko y VTP

## Descripción

Este laboratorio consiste en desarrollar un programa en Python, utilizando la librería Netmiko, que se conecta a varios switches Cisco y configura automáticamente un conjunto de VLANs. La información de las VLANs se almacena en una estructura de datos de Python, y el programa genera de forma dinámica los comandos de configuración necesarios para cada switch.

## Topología

![Topología del laboratorio](imagenes/topologia.png)

## Planteamiento del laboratorio

Para este laboratorio, primero configuré manualmente todo lo relacionado con VTP: el nombre del dominio, el modo de cada switch (VTP Server y VTP Client) y la versión 2 de VTP.

Mi idea era conectarme primero al switch que actúa como VTP Server, crear allí las VLANs y comprobar que estas se propagaran al resto de switches a través de los enlaces trunk. De esta forma, los switches configurados como VTP Client incrementan su número de VLANs automáticamente cuando el VTP Server aumenta su número de revisión.

En el script, configuro primero los enlaces trunk y, a continuación, creo las VLANs en el VTP Server.

También decidí hacer un programa síncrono, ya que en este caso solo trabajo con tres switches. Si tuviera que aplicar esta misma tarea a un número mayor de switches, dividiría el trabajo en dos programas independientes: uno para configurar los trunks mediante multithreading, y otro, separado, para crear las VLANs únicamente en el VTP Server.

## Configuración previa de los switches

Antes de ejecutar el script, preparé manualmente cada switch con el hostname, el acceso SSH y la interfaz de gestión.

```cmd
inserthostname-here(config)#hostname SW1
SW1(config)#ip domain name vlans.com
SW1(config)#crypto key generate rsa
!
SW1(config)#line vty 0 4
SW1(config-line)#login local
SW1(config-line)#transport input ssh
```

```cmd
SW1(config)#int vlan 1
SW1(config-if)#ip add 192.168.1.20 255.255.255.0
SW1(config-if)#no shut
!
SW2(config)#int vlan 1
SW2(config-if)#ip add 192.168.1.30 255.255.255.0
SW2(config-if)#no shut
!
SW3(config)#int vlan 1
SW3(config-if)#ip add 192.168.1.40 255.255.255.0
SW3(config-if)#no shut
```

También dejé preconfigurado el VTP en cada switch, con SW1 como servidor y SW2 y SW3 como clientes:

```cmd
SW1(config)#vtp mode server
SW1(config)#vtp domain VLANS
SW1(config)#vtp version 2
!
SW2(config)#vtp mode client
SW2(config)#vtp domain VLANS
SW2(config)#vtp version 2
!
SW3(config)#vtp domain VLANS
SW3(config)#vtp mode client
SW3(config)#vtp version 2
```

## Script de Python

El script se encuentra en [configurar_vtp_vlans_switches.py](configurar_vtp_vlans_switches.py). A continuación explico su funcionamiento:

1. Pido la contraseña por consola mediante `getpass`. El usuario de conexión SSH queda fijo como `admin`.
2. Me conecto por SSH a los tres switches definidos en el diccionario `SWITCHES`, a través de la función `conectar_switch`, y guardo únicamente las conexiones que se establecen correctamente.
3. En cada switch conectado, configuro como trunk dot1q los puertos definidos en `TRUNK_PORTS`, permitiendo el paso de la VLAN 1 y de todas las VLANs definidas en `VLANS`, mediante la función `configurar_trunks`.
4. Identifico cuál de los switches es el VTP Server comparando su dirección IP con `VTP_SERVER_HOST`. Únicamente en ese switch creo de forma dinámica todas las VLANs del diccionario `VLANS`, con la función `crear_vlans_en_vtp_server`. Los switches clientes reciben estas VLANs por VTP, que ya está preconfigurado y no modifico desde el script.
5. Espero 10 segundos para dar tiempo a que VTP propague las VLANs a los switches clientes.
6. Muestro la salida de `show interfaces trunk`, con la función `verificar_trunks`.

## Resultados

![Resultado de la ejecución del script](imagenes/resultados-script.png)

## Verificación en los switches

Finalmente, compruebo directamente en los switches que las VLANs se han creado y propagado correctamente:

![Verificación de VLANs en los switches, parte 1](imagenes/verificacion-switches-1.png)

![Verificación de VLANs en los switches, parte 2](imagenes/verificacion-switches-2.png)
