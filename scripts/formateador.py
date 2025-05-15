import re
import sys
from pathlib import Path
import shutil
from datetime import datetime
from collections import Counter

ARCHIVO_ULTIMA_RUTA = '.ultima_ruta.txt'
superscript_counter = Counter()
frase_counter = Counter()

SIMPLE_WORDS = ["infra", "supra", "ibid", "passim", "circa"]
PHRASE_PATTERNS = {
    "op. cit.": r"op\. cit\.",
    "et al.": r"et al\.",
    "s.v.": r"s\.v\.",
    "loc. cit.": r"loc\. cit\.",
    "i.e.": r"i\.e\.",
    "e.g.": r"e\.g\."
}

simple_pattern = re.compile(rf"(?<!_)\b({'|'.join(SIMPLE_WORDS)})\b([.,;:]?)(?!_)")
phrase_wrappers = {p: re.compile(rf"(?<!_)\b{ptn}\b(?!_)") for p, ptn in PHRASE_PATTERNS.items()}
phrase_spacings = {p: re.compile(rf"_\s*{ptn}\s*_") for p, ptn in PHRASE_PATTERNS.items()}
inline_number_pattern = re.compile(r'([A-Za-zÁÉÍÓÚÜüáéíóúñÑ]+)(\d{1,4})([.,;:]?)')
after_punctuation_pattern = re.compile(r'([»”’\)\]])(\d{1,4})([.,;:]?)')

def guardar_ultima_ruta(ruta):
    with open(ARCHIVO_ULTIMA_RUTA, 'w', encoding='utf-8') as f:
        f.write(ruta)

def cargar_ultima_ruta():
    if Path(ARCHIVO_ULTIMA_RUTA).exists():
        return Path(ARCHIVO_ULTIMA_RUTA).read_text(encoding='utf-8').strip()
    return ''

def excluir_fecha(texto, pos):
    contexto = texto[max(0, pos - 100):pos].lower()
    # Solo filtra si hay expresiones como "año 476" o "años 1234"
    return bool(re.search(r'\b(año|años)\s*(\d{1,4})?\b', contexto))

def procesar_texto(texto):
    # Frases simples
    def reemplazar_simple(match):
        palabra, punct = match.groups()
        frase_counter[palabra] += 1
        return f'_{palabra}_{punct}'

    texto = simple_pattern.sub(reemplazar_simple, texto)

    # Frases mal espaciadas
    for frase, fixer in phrase_spacings.items():
        if fixer.search(texto):
            frase_counter[frase] += 1
        texto = fixer.sub(f'_{frase}_', texto)

    # Frases correctas sin formateo
    for frase, detector in phrase_wrappers.items():
        if detector.search(texto):
            frase_counter[frase] += 1
        texto = detector.sub(f'_{frase}_', texto)

    # Superíndices palabra + número
    def reemplazar_palabra_numero(match):
        palabra, numero, puntuacion = match.groups()
        pos = match.start()
        if excluir_fecha(texto, pos):
            return match.group(0)
        clave = f"{palabra}{numero}"
        superscript_counter[clave] += 1
        return f"{palabra}<sup>{numero}</sup>{puntuacion or ''}"

    texto = inline_number_pattern.sub(reemplazar_palabra_numero, texto)

    # Superíndices tras puntuación
    def reemplazar_signo_numero(match):
        simbolo, numero, puntuacion = match.groups()
        clave = f"{simbolo}{numero}"
        superscript_counter[clave] += 1
        return f"{simbolo}<sup>{numero}</sup>{puntuacion or ''}"

    texto = after_punctuation_pattern.sub(reemplazar_signo_numero, texto)

    # Limpieza de espacios y comillas
    texto = re.sub(r'([.,;:])(?=[^\s\n</])', r'\1 ', texto)
    texto = re.sub(r'(?<![.,;:]) {2,}', ' ', texto)
    texto = re.sub(r' +\n', '\n', texto)
    texto = texto.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")

    return texto

def generar_resumen_total():
    total_frases = sum(frase_counter.values())
    total_super = sum(superscript_counter.values())
    total = total_frases + total_super
    return "\n".join([
        "=== Total de modificaciones ===",
        f"- Frases latinas corregidas: {total_frases}",
        f"- Palabras con superíndice: {total_super}",
        f"- Total general: {total}"
    ])

def generar_resumen_markdown(nombre_archivo):
    ahora = datetime.now()
    resumen = [f"# Resumen de correcciones",
               f"- Fecha: {ahora.strftime('%Y-%m-%d %H:%M:%S')}",
               f"- Archivo procesado: `{nombre_archivo}`\n"]

    if frase_counter:
        resumen.append("## Frases latinas corregidas")
        for frase, cuenta in frase_counter.most_common():
            resumen.append(f"- _{frase}_: {cuenta} vez/veces")

    if superscript_counter:
        resumen.append("\n## Palabras convertidas a superíndice")
        for clave, cuenta in superscript_counter.most_common():
            resumen.append(f"- {clave}: {cuenta} vez/veces")

    resumen.append("\n## Total de modificaciones")
    resumen.extend(generar_resumen_total().splitlines()[1:])
    return "\n".join(resumen)

def process_file(file_path):
    file = Path(file_path)
    if not file.exists():
        print(f"❌ Archivo no encontrado: {file_path}")
        return False

    original_text = file.read_text(encoding='utf-8')
    updated_text = procesar_texto(original_text)

    if updated_text == original_text:
        print("ℹ️ No se realizaron cambios.")
        return True

    backup_path = file.with_suffix(file.suffix + ".bak")
    shutil.copyfile(file, backup_path)
    print(f"✅ Copia de respaldo creada: {backup_path.name}")

    file.write_text(updated_text, encoding='utf-8')
    print(f"✅ Archivo actualizado: {file.name}")

    date_str = datetime.now().strftime("%Y-%m-%d")
    log_path = file.parent / f"format_changes_{date_str}.log"
    with open(log_path, "a", encoding='utf-8') as log:
        log.write(f"=== {datetime.now().isoformat()} ===\n")
        log.write(f"Archivo: {file.name}\n\n")
        log.write(generar_resumen_total() + "\n\n")
        if superscript_counter:
            log.write("\n=== Conversiones a superíndice ===\n")
            for entrada, cuenta in superscript_counter.most_common():
                log.write(f"- {entrada}: {cuenta} vez/veces\n")
        log.write("\n" + generar_resumen_total() + "\n\n")
    print(f"📝 Log actualizado: {log_path.name}")

    resumen_md = generar_resumen_markdown(file.name)
    resumen_path = file.parent / "frases_corregidas.md"
    resumen_path.write_text(resumen_md, encoding='utf-8')
    print(f"📘 Resumen escrito en: {resumen_path.name}")

    return True

if __name__ == "__main__":
    print("📄 Formateador de términos latinos y superíndices")
    ultima = cargar_ultima_ruta()
    if ultima:
        print(f"(Enter para usar la última ruta: {ultima})")
    ruta = input("Ruta del archivo .md a procesar: ").strip()
    if not ruta:
        ruta = ultima
    if not ruta or not Path(ruta).exists():
        print("❌ Ruta no válida.")
        sys.exit(1)

    guardar_ultima_ruta(ruta)
    process_file(ruta)
