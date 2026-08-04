"""
Ejecuta los scripts de análisis clave seguidos y junta sus resultados.
Al final destaca las líneas con R neto positivo para revisión manual.
Corre esto desde dentro de research/ (o ajusta las rutas si lo mueves).
"""
import subprocess
import sys
import re
import os

# Scripts a ejecutar, en orden. Ajusta la lista si añades más.
SCRIPTS = [
    'gap_and_go/analisis_st.py',
    'gap_and_go/catalizador_gapgo_afinado.py',
    'gap_and_go/validar_float.py',
    'first_red_day/frd_realista.py',
    'first_red_day/barrido_frd.py',
    'overextended_gap_down/overext_gapdown.py',
    'overextended_gap_down/overext_volumen_test.py',
    'contexto/institucional_filtro.py',
    'validacion_final/validacion_fuera_de_muestra_70_30.py',
    'validacion_final/validacion_fuera_de_muestra_60_40.py',
]

PYTHON = sys.executable  # usa el mismo Python con el que corres esto

lineas_positivas = []  # para el resumen final

print("=" * 70)
print("  EJECUTANDO LOS ANÁLISIS CLAVE")
print("=" * 70)

for script in SCRIPTS:
    if not os.path.exists(script):
        print(f"\n⚠ No encontrado: {script} (se salta)")
        continue

    print(f"\n\n{'#' * 70}")
    print(f"#  {script}")
    print(f"{'#' * 70}")

    try:
        resultado = subprocess.run(
            [PYTHON, script],
            capture_output=True, text=True, timeout=1800,  # 30 min máx por script
            encoding='utf-8', errors='replace'
        )
        salida = resultado.stdout
        print(salida)
        if resultado.stderr:
            print("--- errores ---")
            print(resultado.stderr)

        for linea in salida.split('\n'):
            m = re.findall(r'\+0\.\d+R', linea)
            if m:
                lineas_positivas.append((script, linea.strip()))

    except subprocess.TimeoutExpired:
        print(f"⏱ {script} tardó demasiado y se detuvo.")
    except Exception as e:
        print(f"✗ Error corriendo {script}: {e}")

print("\n\n")
print("=" * 70)
print("  RESUMEN: LÍNEAS CON R NETO POSITIVO (revísalas tú con criterio)")
print("=" * 70)
print("\n⚠ Recuerda: R positivo NO significa edge bueno. Mira también:")
print("   - Nº de trades (>200 fiable, <50 dudoso)")
print("   - Que tenga lógica de mercado")
print("   - Que esté validado fuera de muestra, no solo en una pasada\n")

if lineas_positivas:
    script_actual = None
    for script, linea in lineas_positivas:
        if script != script_actual:
            print(f"\n--- {script} ---")
            script_actual = script
        print(f"  {linea}")
else:
    print("No se detectaron líneas con R neto positivo.")

print("\n\n✓ Todos los análisis completados.")
