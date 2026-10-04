import requests

def buscar_problemas(nombre_medicamento):
    url = "https://cima.aemps.es/cima/rest/psuministro"
    respuesta = requests.get(url, params={"nombre": nombre_medicamento})  # filtramos por nombre
    
    datos = respuesta.json()
    print(f"Problemas encontrados para '{nombre_medicamento}': {datos['totalFilas']}")
    print("---")
    
    for problema in datos['resultados']:
        print(f"Medicamento: {problema['nombre']}")
        print(f"Observación: {problema['observ']}")
        print("---")

# probamos con ibuprofeno
buscar_problemas("ibuprofeno")