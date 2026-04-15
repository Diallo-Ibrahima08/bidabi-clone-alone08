"""
Script de génération d'un faux dataset réaliste pour le projet bidabi.
Génère des images PNG colorées + CSV pour 3 catégories : sugar, milk, bread.
Structure : data/raw/images/<categorie>/ + data/raw/metadata_<categorie>_<count>.csv
"""

import os
import csv
import random
import struct
import zlib

# -------------------------
# Config
# -------------------------
CATEGORIES = {
    "sugar": {
        "color": (255, 240, 200),   # jaune pâle
        "accent": (220, 180, 60),
        "products": [
            ("Sugar White Granulated", "en:sugars,en:white-sugars,en:sweeteners", "Sucre blanc, sans additifs"),
            ("Brown Sugar Natural", "en:sugars,en:brown-sugars,en:sweeteners", "Sucre roux naturel de canne"),
            ("Icing Sugar Fine", "en:sugars,en:icing-sugars,en:sweeteners", "Sucre glace, amidon de maïs"),
            ("Cane Sugar Organic", "en:sugars,en:cane-sugars,en:organic", "Sucre de canne biologique"),
            ("Coconut Sugar", "en:sugars,en:coconut-sugars,en:natural-sweeteners", "Sucre de fleur de coco"),
            ("Demerara Sugar", "en:sugars,en:demerara-sugars,en:raw-sugars", "Sucre demerara non raffiné"),
            ("Muscovado Sugar", "en:sugars,en:muscovado,en:unrefined", "Sucre muscovado artisanal"),
            ("Vanilla Sugar", "en:sugars,en:flavored-sugars,en:vanilla", "Sucre vanillé naturel"),
            ("Cassonade Sugar", "en:sugars,en:cassonade,en:french-sugars", "Cassonade française pure"),
            ("Raw Cane Sugar", "en:sugars,en:raw-cane-sugars,en:unprocessed", "Sucre de canne brut"),
        ]
    },
    "milk": {
        "color": (240, 248, 255),   # blanc bleuté
        "accent": (180, 210, 240),
        "products": [
            ("Whole Milk Fresh", "en:milks,en:whole-milks,en:dairy", "Lait entier pasteurisé, vitamine D"),
            ("Skimmed Milk", "en:milks,en:skimmed-milks,en:dairy,en:low-fat", "Lait écrémé 0% MG"),
            ("Semi-Skimmed Milk", "en:milks,en:semi-skimmed,en:dairy", "Lait demi-écrémé 1.5% MG"),
            ("Organic Whole Milk", "en:milks,en:organic-milks,en:whole-milks", "Lait entier bio, vache nourrie à l'herbe"),
            ("Oat Milk", "en:milks,en:plant-milks,en:oat-milks,en:vegan", "Lait d'avoine sans gluten"),
            ("Almond Milk", "en:milks,en:plant-milks,en:almond-milks,en:vegan", "Lait d'amande enrichi en calcium"),
            ("Soy Milk", "en:milks,en:plant-milks,en:soy-milks,en:vegan", "Lait de soja sans OGM"),
            ("Coconut Milk", "en:milks,en:plant-milks,en:coconut-milks", "Lait de coco tropical"),
            ("UHT Whole Milk", "en:milks,en:uht-milks,en:whole-milks", "Lait entier UHT longue conservation"),
            ("Lactose-Free Milk", "en:milks,en:lactose-free,en:dairy", "Lait sans lactose Lactel"),
        ]
    },
    "bread": {
        "color": (210, 170, 120),   # brun pain
        "accent": (160, 110, 60),
        "products": [
            ("White Bread Sliced", "en:breads,en:white-breads,en:sliced-breads", "Farine de blé, eau, levure, sel"),
            ("Whole Wheat Bread", "en:breads,en:whole-wheat-breads,en:wholegrain", "Farine complète, graines de lin"),
            ("Sourdough Bread", "en:breads,en:sourdough-breads,en:artisan", "Farine T65, eau, levain naturel, sel"),
            ("Rye Bread", "en:breads,en:rye-breads,en:dark-breads", "Farine de seigle 80%, eau, sel"),
            ("Multigrain Bread", "en:breads,en:multigrain-breads,en:seeds", "Farine complète, graines de tournesol, pavot, sésame"),
            ("Baguette Tradition", "en:breads,en:baguettes,en:french-breads", "Farine T65 Label Rouge, levain, sel"),
            ("Brioche Bread", "en:breads,en:brioche,en:sweet-breads", "Farine, beurre, œufs, sucre, levure"),
            ("Gluten-Free Bread", "en:breads,en:gluten-free,en:special-diet", "Farine de riz, amidon de tapioca"),
            ("Pumpernickel Bread", "en:breads,en:pumpernickel,en:german-breads", "Seigle intégral, eau, sel"),
            ("Ciabatta Bread", "en:breads,en:ciabatta,en:italian-breads", "Farine T45, huile d'olive, levure"),
        ]
    }
}

TARGET_COUNT = 20  # 20 produits par catégorie (rapide)

# -------------------------
# Générer une image PNG simple sans librairie externe
# -------------------------
def create_png(filepath, color_bg, color_accent, label, size=64):
    """Génère un PNG minimal avec couleur de fond et texte simulé."""
    width, height = size, size
    
    # Créer les pixels (RGB)
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            # Bordure accent
            if x < 4 or x >= width-4 or y < 4 or y >= height-4:
                row.extend(color_accent)
            # Bande centrale simulant du texte
            elif 20 <= y <= 24 and 10 <= x <= width-10:
                row.extend(color_accent)
            elif 28 <= y <= 30 and 15 <= x <= width-15:
                row.extend([c // 2 for c in color_accent])
            else:
                # Légère variation pour simuler une texture
                noise = (x * 3 + y * 7) % 15
                row.extend([min(255, c + noise) for c in color_bg])
        pixels.append(bytes(row))

    def make_png(pixels, width, height):
        def chunk(name, data):
            c = name + data
            return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        
        sig = b'\x89PNG\r\n\x1a\n'
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        ihdr = chunk(b'IHDR', ihdr_data)
        
        raw = b''
        for row in pixels:
            raw += b'\x00' + row  # filter type 0
        
        idat = chunk(b'IDAT', zlib.compress(raw))
        iend = chunk(b'IEND', b'')
        
        return sig + ihdr + idat + iend
    
    png_data = make_png(pixels, width, height)
    with open(filepath, 'wb') as f:
        f.write(png_data)


# -------------------------
# Génération du dataset
# -------------------------
def generate_dataset():
    base = "data/raw"
    os.makedirs(base, exist_ok=True)

    for category, config in CATEGORIES.items():
        print(f"\n→ Génération de la catégorie : {category}")
        
        img_dir = f"{base}/images/{category}"
        os.makedirs(img_dir, exist_ok=True)

        rows = []
        products = config["products"]
        color_bg = config["color"]
        color_accent = config["accent"]

        for i in range(TARGET_COUNT):
            # Cycler sur les produits et varier les IDs
            base_product = products[i % len(products)]
            suffix = i // len(products)
            
            food_id = f"{category}-{1000 + i:04d}"
            label = base_product[0] + (f" #{suffix+1}" if suffix > 0 else "")
            cat_tags = base_product[1]
            ingredients = base_product[2]
            image_filename = f"{food_id}.png"
            image_path = os.path.join(img_dir, image_filename)
            
            # Générer l'image
            create_png(image_path, color_bg, color_accent, label)
            
            # URL simulée (format OpenFoodFacts)
            image_url = f"https://images.openfoodfacts.org/images/products/{food_id}/front_fr.jpg"
            
            rows.append([food_id, label, cat_tags, ingredients, image_url])
            print(f"  [{i+1:02d}/{TARGET_COUNT}] {label} → {image_filename}")

        # Écrire le CSV
        csv_path = f"{base}/metadata_{category}_{TARGET_COUNT}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["foodId", "label", "category", "foodContentsLabel", "image"])
            writer.writerows(rows)
        
        print(f"  ✔ CSV créé : {csv_path} ({len(rows)} produits)")

    print("\n✅ Dataset généré avec succès !")
    print(f"   Catégories : {', '.join(CATEGORIES.keys())}")
    print(f"   Produits par catégorie : {TARGET_COUNT}")
    print(f"   Total images : {TARGET_COUNT * len(CATEGORIES)}")


if __name__ == "__main__":
    generate_dataset()
