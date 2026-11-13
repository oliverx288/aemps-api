import requests
import json  # para guardar datos en formato JSON
from datetime import datetime

def convertir_fecha(timestamp):
    if timestamp:
        return datetime.fromtimestamp(timestamp / 1000).strftime("%d/%m/%Y")
    return None  # devolvemos None en vez de texto para que el JSON sea más limpio

def buscar_problemas(nombre_medicamento):
    url = "https://cima.aemps.es/cima/rest/psuministro"
    respuesta = requests.get(url, params={"nombre": nombre_medicamento})
    
    datos = respuesta.json()
    print(f"Problemas encontrados para '{nombre_medicamento}': {datos['totalFilas']}")
    
    resultados = []  # lista vacía donde guardaremos los resultados
    
    for problema in datos['resultados']:
        resultados.append({  # añadimos cada medicamento a la lista
            "nombre": problema['nombre'],
            "inicio": convertir_fecha(problema.get('fini')),
            "fin": convertir_fecha(problema.get('ffin')),
            "observacion": problema['observ']
        })
    
    # guardamos en un archivo JSON
    nombre_archivo = f"{nombre_medicamento}.json"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"Guardado en {nombre_archivo}")

nombre = input("¿Qué medicamento quieres buscar? ")
buscar_problemas(nombre)