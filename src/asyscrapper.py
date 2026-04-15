import asyncio
import aiohttp
import csv
import os
from aiohttp import ClientSession, ClientTimeout

API_URL = "https://world.openfoodfacts.org/api/v2/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

OUTPUT_DIR = "data/raw"

CATEGORY = "bread" #"bread", "milk", "champagnes", "butter" 
TARGET_COUNT = 180
PAGE_SIZE = 100
MAX_PAGES = 50

MAX_CONCURRENT_REQUESTS = 3
MAX_CONCURRENT_IMAGES = 3


# -------------------------
# Helpers
# -------------------------
def get_best_image(product):
    return (
        product.get("image_url")
        or product.get("image_front_url")
        or product.get("image_small_url")
        or product.get("image_thumb_url")
    )


def is_valid_product(product):
    required = ["code", "product_name"]
    if not all(product.get(f) for f in required):
        return False
    return bool(get_best_image(product))


def extract_product_info(product):
    return [
        product.get("code"),  # <-- changé
        product.get("product_name"),
        ", ".join(product.get("categories_tags", [])),
        product.get("ingredients_text", ""),
        get_best_image(product)
    ]


# -------------------------
# Async API fetch
# -------------------------
async def fetch_page(session, category, page, page_size, sem):
    params = {
        "categories_tags_en": category,
        "page": page,
        "page_size": page_size,
        "fields": "code,product_name,categories_tags,ingredients_text,image_url"
    }

    async with sem:
        try:
            async with session.get(API_URL, params=params) as resp:
                if resp.status != 200:
                    print(f"⚠ Erreur API page {page} | status={resp.status}")
                    return []

                data = await resp.json()
                return data.get("products", [])

        except Exception as e:
            print(f"⚠ Erreur API page {page} :", e)
            return []


# -------------------------
# Async image download
# -------------------------
async def download_image(session, url, image_id, sem, category, folder=None):
    await asyncio.sleep(0.5)
    if folder is None: folder = f"data/raw/images/{category}"
    if not url:
        return

    os.makedirs(folder, exist_ok=True)

    ext = url.split(".")[-1].split("?")[0]
    filename = os.path.join(folder, f"{image_id}.{ext}")

    if os.path.exists(filename):
        return

    async with sem:
        try:
            async with session.get(url) as resp:
                content = await resp.read()
                with open(filename, "wb") as f:
                    f.write(content)
        except Exception as e:
            print(f"⚠ Impossible de télécharger {url} :", e)


# -------------------------
# Main scraping logic
# -------------------------
async def scrape(category, target_count, page_size, max_pages):
    timeout = ClientTimeout(total=60)
    sem_api = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    sem_img = asyncio.Semaphore(5)

    async with ClientSession(headers=HEADERS, timeout=timeout) as session:
        await asyncio.sleep(2)
        valid_products = []
        image_tasks = []
        page = 1

        while len(valid_products) < target_count and page <= max_pages:
            print(f"→ Téléchargement page {page}…")

            products = await fetch_page(session, category, page, page_size, sem_api)
            if not products:
                print("Aucun produit trouvé sur cette page.")
                break

            for product in products:
                if is_valid_product(product):
                    info = extract_product_info(product)
                    valid_products.append(info)

                    image_url = info[-1]
                    image_id = info[0]

                    task = asyncio.create_task(
                        download_image(session, image_url, image_id, sem_img, CATEGORY)
                    )
                    image_tasks.append(task)

                    if len(valid_products) >= target_count:
                        break

            page += 1

        await asyncio.gather(*image_tasks)
        return valid_products


# -------------------------
# CSV export
# -------------------------
def save_to_csv(filename, rows):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["foodId", "label", "category", "foodContentsLabel", "image"])
        writer.writerows(rows)


# -------------------------
# Entry point
# -------------------------
def main():
    products = asyncio.run(scrape(CATEGORY, TARGET_COUNT, PAGE_SIZE, MAX_PAGES))
    output_file = f"data/raw/metadata_{CATEGORY}_{TARGET_COUNT}.csv"
    save_to_csv(output_file, products)
    print(f"✔ Fichier {output_file} créé. Produits valides collectés : {len(products)}")


if __name__ == "__main__":
    main()





