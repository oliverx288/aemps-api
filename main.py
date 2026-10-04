import requests

url = "https://cima.aemps.es/cima/rest/psuministro"
respuesta = requests.get(url)

datos = respuesta.json()
print(f"Total problemas activos: {datos['totalFilas']}")

for problema in datos['resultados'][:3]:
    print(problema)