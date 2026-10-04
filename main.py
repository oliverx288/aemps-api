import requests
from datetime import datetime  # para convertir fechas

def convertir_fecha(timestamp):
    if timestamp:  # si existe la fecha
        # timestamp viene en milisegundos, dividimos entre 1000 para convertir a segundos
        return datetime.fromtimestamp(timestamp / 1000).strftime("%d/%m/%Y")  # formato día/mes/año
    return "Sin fecha"  # si no hay fecha devolvemos esto

def buscar_problemas(nombre_medicamento):
    url = "https://cima.aemps.es/cima/rest/psuministro"  # endpoint de problemas de suministro
    respuesta = requests.get(url, params={"nombre": nombre_medicamento})  # llamada a la API filtrando por nombre
    
    datos = respuesta.json()  # convertimos la respuesta en diccionario
    print(f"Problemas encontrados para '{nombre_medicamento}': {datos['totalFilas']}")
    print("---")
    
    for problema in datos['resultados']:  # recorremos cada medicamento
        print(f"Medicamento: {problema['nombre']}")
        print(f"Inicio del problema: {convertir_fecha(problema.get('fini'))}")  # .get() evita error si no existe la clave
        print(f"Fin previsto: {convertir_fecha(problema.get('ffin'))}")  # .get() evita error si no existe la clave
        print(f"Observación: {problema['observ']}")
        print("---")

nombre = input("¿Qué medicamento quieres buscar? ")  # el usuario escribe el nombre
buscar_problemas(nombre)  # llamamos a la función con el nombre introducido