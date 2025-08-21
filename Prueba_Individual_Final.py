import os
import csv
import requests
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import matplotlib.pyplot as plt
import re

# ---------------- Configuración ----------------
# Puedes poner N carpetas aquí (una o varias rutas base)
FOLDERS = [
    r"C:\Users\angel\OneDrive\Documentos\GS\Mike\Insumos 1\Insumos",
]

OUTPUT_DIR = r"C:\Users\angel\OneDrive\Documentos\GS\Mike\Insumos 1\Insumos\Pruebas final csv y grafica"
ENDPOINT = "http://localhost:4445/L9h/v3/assess"
CONCURRENT_WORKERS = 6
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp")

QUALITY_MAP = {
    0: "Enrolamiento",
    1: "Autenticacion",
    2: "Busqueda",
    3: "Minima",
    4: "No_Calidad",
    422: "422",
}

os.makedirs(OUTPUT_DIR, exist_ok=True)
session = requests.Session()

# ---------------- Utilidades ----------------
def safe_filename(name: str) -> str:
    """Convierte un nombre de carpeta en un nombre válido para archivo."""
    name = name.strip().replace(" ", "_")
    return re.sub(r'[^A-Za-z0-9_\-\.]', "_", name)

def categories_in_order():
    """Lista de categorías en el orden numérico de QUALITY_MAP."""
    # preserva el orden por clave numérica (0,1,2,3,4,422)
    ordered_keys = sorted(QUALITY_MAP.keys(), key=lambda x: (x == 422, x))
    return [QUALITY_MAP[k] for k in ordered_keys]

def derive_label_for_image(abs_img_path: str, base_dirs_abs: list[str]) -> str:
    """
    Etiqueta 'Carpeta' = subcarpeta tope bajo la base correspondiente.
    Si la imagen está directamente en la base, usa el nombre de la base.
    Si no coincide con ninguna base, usa la carpeta inmediata del archivo.
    """
    # Encuentra la base más larga que sea prefijo del path
    matched_base = None
    for b in base_dirs_abs:
        if abs_img_path == b or abs_img_path.startswith(b + os.sep):
            if matched_base is None or len(b) > len(matched_base):
                matched_base = b

    if matched_base:
        rel = os.path.relpath(abs_img_path, matched_base)
        if rel == ".":
            return os.path.basename(matched_base)
        top = rel.split(os.sep)[0]
        return top if top not in (".", "") else os.path.basename(matched_base)

    # Fallback
    return os.path.basename(os.path.dirname(abs_img_path))

# ---------------- Funciones de procesamiento ----------------
def get_image_quality(image_path):
    """Obtiene la calidad de la imagen desde el servidor; devuelve etiqueta mapeada."""
    try:
        with open(image_path, 'rb') as img_file:
            # El servicio acepta binario en el body (octet-stream)
            response = session.post(ENDPOINT, data=img_file, timeout=30)
            if response.status_code == 200:
                data = response.json()
                simple_quality = data.get("simple", 422)
                return QUALITY_MAP.get(simple_quality, "422")
            return "422"
    except Exception:
        return "422"

def get_image_dimensions(image_path):
    """Obtiene ancho y alto de la imagen."""
    try:
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception:
        return 0, 0

def process_image(image_path, carpeta_label):
    """Procesa una sola imagen y devuelve la fila para CSV."""
    name = os.path.basename(image_path)
    rel_path = image_path.replace("\\", "/")
    width, height = get_image_dimensions(image_path)
    quality = get_image_quality(image_path)
    return [carpeta_label, name, rel_path, width, height, quality]

def gather_images(folders):
    """Reúne todas las imágenes de N carpetas, con etiqueta 'Carpeta'."""
    image_items = []
    base_dirs_abs = [os.path.abspath(os.path.normpath(f)) for f in folders]

    for base in base_dirs_abs:
        for root, _, files in os.walk(base):
            for file in files:
                if file.lower().endswith(IMAGE_EXTENSIONS):
                    abs_path = os.path.abspath(os.path.join(root, file))
                    label = derive_label_for_image(abs_path, base_dirs_abs)
                    image_items.append((abs_path, label))
    return image_items

# ---------------- Gráficas ----------------
def plot_global_and_per_folder(csv_path, output_dir):
    df = pd.read_csv(csv_path)

    # Si por alguna razón la columna 'Calidad' trae números como texto, mapearlos
    df['Calidad'] = df['Calidad'].astype(str).apply(
        lambda x: QUALITY_MAP.get(int(x) if x.isdigit() else x, x)
    )

    cats = categories_in_order()

    # -------- Gráfica global --------
    global_counts = df['Calidad'].value_counts()
    global_series = [int(global_counts.get(cat, 0)) for cat in cats]

    plt.figure(figsize=(12, 6))
    bars = plt.bar(cats, global_series, edgecolor='black')
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            plt.text(bar.get_x() + bar.get_width()/2., h, f'{int(h)}',
                     ha='center', va='bottom', fontweight='bold')
    plt.title('Distribución global de calidades')
    plt.xlabel('Banda de Calidad')
    plt.ylabel('Cantidad de Imágenes')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    global_png = os.path.join(output_dir, "grafica_GLOBAL.png")
    plt.savefig(global_png, dpi=120)
    plt.show()
    plt.close()
    print(f"Gráfica global guardada en: {global_png}")

    # -------- Gráfica por carpeta --------
    for carpeta, df_c in df.groupby('Carpeta'):
        counts = df_c['Calidad'].value_counts()
        serie = [int(counts.get(cat, 0)) for cat in cats]

        plt.figure(figsize=(12, 6))
        bars = plt.bar(cats, serie, edgecolor='black')
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                plt.text(bar.get_x() + bar.get_width()/2., h, f'{int(h)}',
                         ha='center', va='bottom', fontweight='bold')
        plt.title(f'Distribución de calidades - {carpeta}')
        plt.xlabel('Banda de Calidad')
        plt.ylabel('Cantidad de Imágenes')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        fname = f"grafica_{safe_filename(carpeta)}.png"
        out_png = os.path.join(output_dir, fname)
        plt.savefig(out_png, dpi=120)
        plt.show()
        plt.close()
        print(f"Gráfica guardada: {out_png}")

# ---------------- Main ----------------
def main():
    images = gather_images(FOLDERS)
    total_images = len(images)
    print(f"Total de imágenes encontradas: {total_images}")

    csv_path = os.path.join(OUTPUT_DIR, "image_quality.csv")

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Carpeta", "Imagen", "Ruta", "Ancho", "Alto", "Calidad"])

        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            futures = {executor.submit(process_image, path, label): (path, label) for path, label in images}
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    row = future.result()
                    writer.writerow(row)
                except Exception as e:
                    # En caso de error con una imagen, la marcamos como 422
                    path, label = futures[future]
                    name = os.path.basename(path)
                    rel_path = path.replace("\\", "/")
                    writer.writerow([label, name, rel_path, 0, 0, "422"])
                print(f"Procesadas {i}/{total_images} ({(i/total_images)*100:.2f}%)")

    print(f"CSV generado correctamente en: {csv_path}")
    session.close()
    print("Proceso completado. Conexiones liberadas.")

    # ---- Gráficas global + por carpeta ----
    plot_global_and_per_folder(csv_path, OUTPUT_DIR)

if __name__ == "__main__":
    main()
