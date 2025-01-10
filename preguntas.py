import csv
import random

# Archivos CSV
ARCHIVO_PREGUNTAS = 'preguntas.csv'

# Cargar preguntas desde el archivo CSV
def cargar_preguntas():
    preguntas = []
    with open(ARCHIVO_PREGUNTAS, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            preguntas.append({
                "pregunta": row["pregunta"],
                "opciones": row["opciones"].split('|'),
                "respuesta": row["respuesta"]
            })
    return preguntas

# Selección de preguntas
def seleccionar_preguntas(preguntas, num_preguntas=5):
    return random.sample(preguntas, num_preguntas)
