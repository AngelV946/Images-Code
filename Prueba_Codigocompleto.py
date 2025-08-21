import os
import csv
import requests
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- Configuración ----------------
# Carpeta(s) de entrada: puedes agregar N carpetas aquí
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
    422: "422"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)
session = requests.Session()

# ---------------- Funciones ----------------
def get_image_quality(image_path):
    """Obtiene la calidad de la imagen desde el servidor"""
    try:
        with open(image_path, 'rb') as img_file:
            response = session.post(ENDPOINT, data=img_file, timeout=30)
            if response.status_code == 200:
                data = response.json()
                simple_quality = data.get("simple", 422)
                return QUALITY_MAP.get(simple_quality, "422")
            return "422"
    except Exception:
        return "422"

def get_image_dimensions(image_path):
    """Obtiene ancho y alto de la imagen"""
    try:
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception:
        return 0, 0

def process_image(image_path):
    """Procesa una sola imagen y devuelve la fila para CSV"""
    name = os.path.basename(image_path)
    rel_path = image_path.replace("\\", "/")
    width, height = get_image_dimensions(image_path)
    quality = get_image_quality(image_path)
    return [name, rel_path, width, height, quality]

def gather_images(folders):
    """Reúne todas las imágenes de N carpetas"""
    image_files = []
    for folder in folders:
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(IMAGE_EXTENSIONS):
                    image_files.append(os.path.join(root, file))
    return image_files

# ---------------- Gráfica ----------------
def plot_quality_distribution(csv_path):
    try:
        df = pd.read_csv(csv_path)
        df['Calidad'] = df['Calidad'].astype(str).apply(
            lambda x: QUALITY_MAP.get(int(x) if x.isdigit() else x, x)
        )

        all_categories = pd.DataFrame({
            'Calidad': list(QUALITY_MAP.values()),
            'Orden': list(QUALITY_MAP.keys())
        })

        quality_counts = df['Calidad'].value_counts().reset_index()
        quality_counts.columns = ['Calidad', 'Cantidad']
        quality_counts = all_categories.merge(
            quality_counts,
            on='Calidad',
            how='left'
        ).fillna(0)
        quality_counts = quality_counts.sort_values('Orden')

        plt.figure(figsize=(12, 6))
        bars = plt.bar(
            quality_counts['Calidad'],
            quality_counts['Cantidad'],
            color='skyblue',
            edgecolor='black'
        )

        for bar in bars:
            height = bar.get_height()
            if height > 0:
                plt.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{int(height)}',
                    ha='center',
                    va='bottom',
                    fontweight='bold'
                )

        plt.title('Distribución de Calidades de Imágenes', pad=20, fontsize=14)
        plt.xlabel('Banda de Calidad', labelpad=10)
        plt.ylabel('Cantidad de Imágenes', labelpad=10)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()

        print("\nResumen de calidades:")
        print(quality_counts[['Calidad', 'Cantidad']].to_string(index=False))

    except Exception as e:
        print(f"Error al graficar: {e}")

# ---------------- Main ----------------
def main():
    image_files = gather_images(FOLDERS)
    total_images = len(image_files)
    print(f"Total de imágenes encontradas: {total_images}")

    csv_path = os.path.join(OUTPUT_DIR, "image_quality.csv")

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Imagen", "Ruta", "Ancho", "Alto", "Calidad"])

        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            futures = {executor.submit(process_image, img): img for img in image_files}
            for i, future in enumerate(as_completed(futures), 1):
                row = future.result()
                writer.writerow(row)
                print(f"Procesadas {i}/{total_images} ({(i/total_images)*100:.2f}%)")

    print(f"CSV generado correctamente en: {csv_path}")
    session.close()
    print("Proceso completado. Conexiones liberadas.")

    # ---------------- Graficar automáticamente ----------------
    plot_quality_distribution(csv_path)

if __name__ == "__main__":
    main()
