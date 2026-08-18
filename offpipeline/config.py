from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB = DATA_DIR / "products.db"

OFF_API_V3 = "https://world.openfoodfacts.org/api/v3/product/{barcode}"
OFF_SEARCH = "https://world.openfoodfacts.org/api/v2/search"
OFF_FIELDS = (
    "code,product_name,generic_name,brands,quantity,serving_size,"
    "image_front_url,image_url,selected_images,images,ingredients_text,"
    "allergens,allergens_tags,traces_tags,labels_tags,categories_tags,"
    "conservation_conditions,origins,countries_tags,nutriments"
)
OFF_USER_AGENT = "FIT5120-off-pipeline/0.1 (Monash FIT5120 course project)"
REQUEST_TIMEOUT = 30.0
# Stay under OFF's 15 reads/minute guidance.
MIN_REQUEST_INTERVAL = 4.1
