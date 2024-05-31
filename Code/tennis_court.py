import pandas as pd
from datetime import datetime
from datetime import timedelta

from email.message import EmailMessage  # email: paquete de manejo de correo electrónico
import smtplib                                              # smtplib: define un objeto de sesión de cliente SMTP que se puede utilizar para enviar correo a cualquier máquina

import os
from dotenv import load_dotenv

import warnings
warnings.filterwarnings("ignore")

# -- Archivos globales --

route = r'Data\registros.csv'
route_users = r'Data\users.csv'

registros = pd.read_csv(route,  parse_dates=['date']) # Obtener los registros históricos con el tipo de dato correcto
users = pd.read_csv(route_users)                                # Usuarios para reservar

load_dotenv()                                                               # Cargar secrets at .env

# registros['date'] = registros['date'].dt.strftime('%Y-%m-%d') # Manejar formato de fecha sin hora

# -- Funciones de consulta --

def consult_reservation_day(date:datetime):
    
    """Dada la fecha consultamos si existen reservas hechas para ese día
    input:
        date : datetime object
    Output: 
        None or pandas dataframe"""
    
    reserves_in_date = registros[registros['date'] == date]
    
    if reserves_in_date.shape[0] != 0:
        return reserves_in_date
    
    else:
        return None

def consult_reservation(date:datetime, hour:int):
    
    """Dada la fecha consultamos si existen reservas hechas para ese día y hora
    input:
        date : datetime object
    Output: 
        None or pandas dataframe"""
    
    reserves_in_date = registros[(registros['date'] == date) & (registros['hour'] == hour)]
    
    if reserves_in_date.shape[0] != 0:
        return True
    
    else:
        return False

def consult_future():
    """Retorna las reservas proximas"""
    return registros[registros['date'] >= datetime.now()]

# -- Funciones de transformación de formato de fecha --

def date_to_Nd_d_Nm(fecha):
    """Dada la fecha la convertimos al formato Nombre día, día, Nombre del mes

    input:
        date : datetime object
        
    Output: 
        date in format: Name_day day de Name_month
        
    example:
    5/05/2024 --> Viernes 5 de Abril"""

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    dia = dias_semana[ fecha.weekday()]
    mes = meses [ fecha.month - 1]

    resultado = f'{dia} {fecha.day} de {mes}'
    return resultado

def strign_to_date(fecha_str:str):
    """dada una fecha en str en formato d / m / A la convertimos a un objeto datetime
    
    Input
        fecha: str
    
    Output
        date: datetime object"""
    return datetime.strptime(fecha_str, '%d-%m-%Y')

def week_day_to_day(this_week:bool, day:str):
    """"Conocido si se quiere reservar para esta semana o la siguiente y el día de reserva, retorna el día en formato datetime
    
    Input
        this_week: bool / valor si se quiere reservar esta (True) o la siguiente semana (Falsee)
        day: str / Inicial del día de la semana en ["L", "M", "W", "J", "V", "S", "D"]
        
    Output
        día_reserva: datetime object
    """

    keys_num = { 'L': 0,  'M': 1, 'W': 2, 'J': 3, 'V': 4, 'S': 5, 'D': 6,}    # Valor de cada día de la semana
    dias_semana = ["L", "M", "W", "J", "V", "S", "D"]

    today = datetime.now()

    key_today = today.weekday()
    left_days = keys_num[day] - key_today  # Cuantos dias faltan para efectuar la reserva, si es (-) significa que ya ese día de esta semana paso

    if this_week and left_days >= 0:
        # Reservas para semana actual, sin que sea Domingo (left_days != 0)

        until_that = keys_num[day] - key_today             # Cantidad de días hasta que eso pase
        day_ro_reserve = today + timedelta(until_that) # día de la reserva

        # Normalize date format
        day_ro_reserve = day_ro_reserve.strftime('%Y-%m-%d')
        day_ro_reserve = datetime.strptime(day_ro_reserve, '%Y-%m-%d')

        return day_ro_reserve

    elif not(this_week) or (this_week and left_days <= 0):
        # Reservas para la siguiente semana, o en caso de que se reserve intente reservar días después

        week_left = 6 - key_today                               # Días para que se acabe la semana 
        until_that = week_left + keys_num[day] + 1   # Cantidad de días para efectuar la reserva

        day_ro_reserve = today + timedelta(until_that) # día de la reserva

        # Normalize date format
        day_ro_reserve = day_ro_reserve.strftime('%Y-%m-%d')
        day_ro_reserve = datetime.strptime(day_ro_reserve, '%Y-%m-%d')

        return day_ro_reserve

#  -- Función para crear el cuerpo del correo, rellenando los datos de usuario y fecha --

def texto_reserva(fecha:datetime,  hora:int, user_index=0):
    """A partir de la plantilla de las reservas, dados los datos de usuario, fecha y hora, 
    creamos el cuerpo del correo para la reserva de la cancha
    
    input
        fecha: datetime object / (fecha en la que se quiere reservar el espacio)
        hora: int / (hora a la que se quiere reservar el espacio)
        user_index: int (usuario quien pide la reserva, por default usuario principal (user_index = 0))
        
    Output
        mail_body: string"""
    
    with open('Data\plantilla.txt', 'r', encoding="utf-8") as plantilla:
        reserva = plantilla.read()  # Guaradar copia de la plantilla para rellenar campos
    
    # Campos del usuario
    nombre = users.loc[user_index, 'nombre']
    documento = users.loc[user_index, 'documento']
    telefono = users.loc[user_index, 'telefono']

    # Campos temporales
    fecha = date_to_Nd_d_Nm(fecha)
    hora = f'{hora}:00 - {hora+1}:00'

    body = reserva.format(nombre, documento, fecha, hora, telefono)

    return body

# -- Función de envio del correo --

def enviar_correo(fecha, hora, user_index):
     
    """A partir de los datos de usuario, fecha y hora, enviamos el correo electronico para solicitar la reserva de la cancha
    
    input
        fecha: datetime object / (fecha en la que se quiere reservar el espacio)
        hora: int / (hora a la que se quiere reservar el espacio)
        user_index: int (usuario quien pide la reserva, por default usuario principal (user_index = 0))
        
    Output
       Message:  'Mail has been sent'"""
     
    remitente = users.loc[user_index, 'correo']
    destinatario = os.getenv("CORREO_RESERVAS_U")

    mensaje = texto_reserva(fecha, hora, user_index)

    # Creación del objeto EmailMessage
    email = EmailMessage()

    # -- Estructura del correo ---

    email["From"] = remitente                                       # De:
    email["To"] = destinatario                                        # Para: 
    email["Subject"] = "Reserva cancha de Tenis"         # Asunto
    email.set_content(mensaje)                                     # Cuerpo del correo


    # -- Enviar correo utilizando el protocolo SMTP --

    smtp = smtplib.SMTP_SSL("smtp.gmail.com")                            # Crea una conexión SSL con el servidor SMTP  de Gmail
    smtp.login(remitente, users.loc[0, 'contraseña'] )                        # Inicio de sesión en el servidor
    smtp.sendmail(remitente, destinatario, email.as_string())           # Envio del correo

    smtp.quit()                                                                                   # Cerrar conexión con el servidor

    print('El correo se ha enviado')

# -- Función  para agregar registro de reserva pendiente --

def agregar_registro(fecha, hora):

    global registros
    nueva_fila = {'date':fecha, 'hour':hora, 'email_sent':True,'User':0}
    
    registros = registros.append(nueva_fila,ignore_index=True)
    registros.to_csv(route,  index=False) # Guardar registro

# -- Enviar correo y agregar registros, evaluando cuándo se puede hacer o no --

def reservar(fecha, hora):

    # -- Casos para evitar reserva --

    if fecha <= datetime.today(): # Reserva pasada
        print(chr(27)+'[0;31mWarning: No se reserva para ayer :c')
        return None
    
    if fecha.weekday() == 6: # Reserva domingo
        print(chr(27)+'[0;31mWarning: No se reservan domingos :c')
        return None
    
    if not( hora in range(8, 19)): # Advertencia por si se intenta reservar en un horario no adecuado
        print(chr(27)+'[0;31mWarning: hora en rango de reservas no adecuado )')

        seguir = input('Quieres continuar? (Y/N): ')    

        if seguir == 'N' or seguir == 'n':                  # No continuar
            print(chr(27)+'[0;37m Reserva cancelada')
            return None
        
        elif seguir == 'Y' or seguir == 'y': pass       # Continuar

        else: return None                                        # No continuar


    print(chr(27)+f'[0;37mEstablecer reserva para el : {date_to_Nd_d_Nm(fecha)} a las {hora}:00')
    
    if consult_reservation(fecha, hora):                # Consulta si ya existe reserva para ese momento
        print(chr(27)+'[0;31mWarning: Ya se ha realizado reserva para esa fecha y hora')
        return None
        
    seguir = input('Quieres continuar? (Y/N): ')    

    # Escoger usuario 
    user_index = 0

    if seguir == 'N' or seguir == 'n':                  # No reservar
        print(chr(27)+'[0;37m Reserva cancelada')
        return None
        
    elif seguir == 'Y' or seguir == 'y':                # Reservar
        # Efectuar la reserva
        
        enviar_correo(fecha, hora, user_index)
        agregar_registro(fecha, hora)
        print(chr(27)+'[0;32mPetición de Reserva realizada con éxito')

        # except:
        #     print(chr(27)+'[0;37m Ha ocurrido un error, comuniquese con soporte')
        #     return None

    else: return None                                        # No reservar

# -- Interfaz de usuario --

if __name__ == "__main__":

    while True:

        print(chr(27)+'[1;36m\n\nWelcome to Sinner\n')
        print(chr(27) + '[0;37mMenú de opciones\n1) Consultar reservas\n2) Reservar Cancha\nx) Salir')

        opcion = input('Seleccion una opción: ')
        
        if opcion == '1': # Consultar reservas
            print(chr(27) + '[0;37m\nConsulta de:\n1)Reservas futuras\n2)Reserva específica\n')
            opcion_reservas = input('Seleccion una opción: ')


            if opcion_reservas == '1': # Reservas futuras
                print(consult_future())
                break

            elif opcion_reservas == '2': # Reserva día especifico
                day = input('Digite el día en formato (%D / %M / %A): ')

                try: 
                    day = strign_to_date(day)
                    print(consult_reservation_day(day))
                    break

                except:
                    print(chr(27) + '[0;31mNo se ha ingresado la fecha en el formato adecuado')

        elif opcion == '2': # Reservar
            print(chr(27) + '[0;37m\nReserva para\n1) Esta semana\n2) Proxima semana\n3) Seleccionar día')

            opcion_reserva = input('Seleccion una opción: ')

            if opcion_reserva == '1': # Reserva esta semana
                day = input('Selecciona el día de la semana ( [L]   [M]   [W]   [J]   [V]   [S]   [D]): ')

                if day in ["L", "M", "W", "J", "V", "S", "D"]:
                    fecha = week_day_to_day(True, day)
                    hora = int(input('¿A qué hora vamos a jugar (24h format): ?'))

                    reservar(fecha, hora)
                    break

                else:
                    print(chr(27) + '[0;31mError')
                    

            elif opcion_reserva == '2': # Reserva la siguiente semana 

                day = input('Selecciona el día de la semana ( [L]   [M]   [W]   [J]   [V]   [S]   [D]): ')

                if day in ["L", "M", "W", "J", "V", "S", "D"]:
                    fecha = week_day_to_day(False, day)
                    hora = int(input('A qué hora vamos a jugar (24h format): '))

                    reservar(fecha, hora)
                    break
                    
                else:
                    print(chr(27) + '[0;31mError')
                    
                
            elif opcion_reserva == '3': # Reserva para un día especifico 
                day = input('¿Qué día quieres reservar? format( %d - %m - %A): ')

                try: 

                    fecha = strign_to_date(day)
                    hora = int(input('A qué hora vamos a jugar (24h format): '))

                    reservar(fecha, hora)
                    print(chr(27) + '[0;37m')
                
                except:
                    print(chr(27) + '[0;31mError')


        elif opcion == 'ex' or opcion == 'x':
            break

