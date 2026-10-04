import requests # importamos la librería para hablar con internet

url = "https://cima.aemps.es/cima/rest/psuministro" # dirección de la API de la AEMPS
respuesta = requests.get(url) # pedimos datos a la API

datos = respuesta.json() # la respusta la convertimos en un diccionario
print(f"Total problemas activos: {datos['totalFilas']}") # imprimimos todo

for problema in datos['resultados'][:3]:
    print(problema) # imprimimos cada problema completo