import re

def procesar_archivo(ruta):
    with open(ruta, 'r', encoding='utf-8') as f:
        texto = f.read()

    # Evita modificar notas en fechas
    def excluir_fecha(pos):
        contexto = texto[max(0, pos - 100):pos].lower()
        palabras = re.findall(r'\b\w+\b', contexto)[-3:]
        return any(p in ['año', 'años', 'entre', 'del'] for p in palabras)

    # palabra + número
    def reemplazar(match):
        palabra, numero, puntuacion = match.groups()
        if excluir_fecha(match.start()):
            return match.group(0)
        return f'{palabra}<sup>{numero}</sup>{puntuacion}'

    texto = re.sub(r'([A-Za-zÁÉÍÓÚÜüáéíóúñÑ]+)(\d{1,3})([.,;:]?)', reemplazar, texto)
    texto = re.sub(r'([»”’\)\]])(\d{1,3})([.,;:]?)', r'\1<sup>\2</sup>\3', texto)

    # Espaciado y comillas
    texto = re.sub(r'([.,;:])(?=[^\s\n</])', r'\1 ', texto)
    texto = re.sub(r'(?<![.,;:]) {2,}', ' ', texto)
    texto = re.sub(r' +\n', '\n', texto)
    texto = texto.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")

    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(texto)

    print("✅ Sobrenúmeros aplicados sin enlaces ni notas.")

if __name__ == "__main__":
    ruta = input("Ruta del archivo Markdown: ").strip()
    procesar_archivo(ruta)
