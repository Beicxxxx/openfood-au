# FIT5120 Open Food Facts product pipeline

从 [aus-grocery-data](https://github.com/Beicxxxx/aus-grocery-data) 拆出来的新管道：

- **保留**：按条码查商品、统一字段、SQLite、OFF 图片/配料/过敏原/营养
- **去掉**：Coles / Woolworths 抓取、cookie、浏览器兜底、双店比价、跨店 GTIN 合并

这是 FIT5120 能写进提案的开放数据层（ODbL，图片 CC BY-SA，需署名）。

## 和旧仓库的对应关系

| 旧命令 | 新命令 |
|---|---|
| `python -m ausgrocery off --barcode …` | `python -m offpipeline lookup …` |
| `ww-crawl` / `coles-crawl` / `food-all` | 已删除，不再维护 |
| `match` / `merge`（WW+Coles+OFF） | 不再需要；一条 OFF 记录就是商品详情 |

图片：只用 Open Food Facts 正面包装图（多为用户实拍，许可明确）。没有图时 `image_url` 为空，前端用占位卡。不要热链红绿超市 CDN。

## 安装

```powershell
cd F:\Courses\FIT5120\openfood-au
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 用法

```powershell
python -m offpipeline init-db
python -m offpipeline lookup 9310021039080
python -m offpipeline ingest data/sample_barcodes.txt
python -m offpipeline search "Lipton Ice Tea"
python -m offpipeline show 9310021039080
```

Open Food Facts 要求：一次真实扫描对应一次 API。批量入库用 `ingest`，并遵守约 15 次/分钟。全量请用 [OFF 每日 dump](https://world.openfoodfacts.org/data)，不要用 API 爬整库。

## 字段（旧详情页里能合法留下的部分）

| 字段 | 来源 |
|---|---|
| name / brand / size | `product_name`, `brands`, `quantity` |
| image_url | `selected_images.front`（CC BY-SA） |
| ingredients | `ingredients_text` |
| allergens / traces | `allergens_tags`, `traces_tags` |
| dietary | `labels_tags` |
| nutrition | `nutriments` |
| origin / storage | `origins`, `conservation_conditions`（常缺） |
| price / 超市官方棚拍 | **不做** |

过敏原只展示「已声明 / may contain / 未知」，不要把缺失推断成「不含」。
