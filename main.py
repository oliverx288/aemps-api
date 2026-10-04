import requests # librería para hablar con internet

def buscar_problemas(nombre_medicamento):
    url = "https://cima.aemps.es/cima/rest/psuministro"
    respuesta = requests.get(url, params={"nombre": nombre_medicamento}) # llamamos a api
    
    datos = respuesta.json() # convertimos la respuesta en diccionario
    print(f"Problemas encontrados para '{nombre_medicamento}': {datos['totalFilas']}")
    print("---")
    
    for problema in datos['resultados']:
        print(f"Medicamento: {problema['nombre']}")
        print(f"Observación: {problema['observ']}")
        print("---")

# pedimos al usuario que escriba el nombre
nombre = input("¿Qué medicamento quieres buscar? ")
buscar_problemas(nombre)