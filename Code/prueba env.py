import pandas as pd

route = r'Data\registros.csv'
route_users = r'Data\users.csv'

registros = pd.read_csv(route,  parse_dates=['date']) # Obtener los registros históricos con el tipo de dato correcto



