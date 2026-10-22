#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BSL Wholesale (Shopify) -> pazaryeri XML feed'i (ilk kullanıcı: Yakemall)

Shopify Admin API'den aktif ürünleri bulk operation ile çeker ve
model > renk > beden hiyerarşisinde tek bir XML dosyası üretir.

    <catalog>
      <product id="21620">            model (custom.item_group_id)
        ...model alanları...
        <pack size="6">...</pack>     seri içeriği (custom.pack_content)
        <colors>
          <color id="21620-40">       satılabilir birim = bu rengin bir serisi
            <images>...</images>      yalnızca bu rengin görselleri
            <variants>                beden bazlı stok + barkod
          </color>
        </colors>
      </product>
    </catalog>

Kullanım:
    python yakemall_feed.py --out docs/yakemall.xml
    python yakemall_feed.py --from-jsonl export.jsonl --out test.xml   (API'siz deneme)

Ayarlar ortam değişkenleriyle verilir; liste için README.md'ye bakın.
Yalnızca Python standart kütüphanesi kullanılır (ek paket gerekmez).
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict
from decimal import Decimal, InvalidOperation


# --------------------------------------------------------------------------
# Ayarlar
# --------------------------------------------------------------------------

def env(name, default=""):
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


def env_bool(name, default):
    value = env(name, "")
    if not value:
        return default
    return value.lower() in ("1", "true", "yes", "evet", "on")


SHOP = env("SHOPIFY_SHOP", "0kym5e-we.myshopify.com")
API_VERSION = env("SHOPIFY_API_VERSION", "2026-10")
PRODUCT_QUERY = env("PRODUCT_QUERY", "status:active")
INCLUDE_TR = env_bool("INCLUDE_TR", True)            # Türkçe başlık/ürün tipi (read_translations gerekir)
INCLUDE_ZERO_STOCK = env_bool("INCLUDE_ZERO_STOCK", True)  # stoğu biten renkler packs_in_stock=0 ile kalsın
MAX_IMAGES = int(env("MAX_IMAGES", "10"))
GENDER = env("GENDER", "Woman")
BRAND = env("BRAND", "BSL")
SHRINK_GUARD = float(env("SHRINK_GUARD", "0.5"))     # ürün sayısı önceki feed'in bu oranının altına düşerse yazma
BULK_TIMEOUT_SEC = int(env("BULK_TIMEOUT_SEC", "900"))

COLOR_OPTION_NAMES = {"color", "colour", "renk"}
SIZE_OPTION_NAMES = {"size", "beden"}
SIZE_ORDER = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "STD"]


def die(message, code=1):
    print(f"HATA: {message}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------
# Shopify Admin API
# --------------------------------------------------------------------------

def http_json(url, data=None, headers=None, method=None, timeout=60, retries=4):
    last_error = None
    for attempt in range(retries):
        request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")[:500]
            last_error = f"HTTP {error.code} {url}: {body}"
            if error.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise RuntimeError(last_error) from None
        except urllib.error.URLError as error:
            last_error = f"{url}: {error.reason}"
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise RuntimeError(last_error) from None
    raise RuntimeError(last_error or "bilinmeyen HTTP hatası")


def http_text(url, timeout=120):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def get_access_token():
    """Dev Dashboard uygulaması için client credentials grant (token 24 saat geçerli).
    Eski tip admin custom app token'ı varsa SHOPIFY_ACCESS_TOKEN ile doğrudan verilebilir."""
    token = env("SHOPIFY_ACCESS_TOKEN")
    if token:
        return token
    client_id = env("SHOPIFY_CLIENT_ID")
    client_secret = env("SHOPIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        die("SHOPIFY_CLIENT_ID ve SHOPIFY_CLIENT_SECRET (ya da SHOPIFY_ACCESS_TOKEN) tanımlı değil.")
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    result = http_json(
        f"https://{SHOP}/admin/oauth/access_token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    token = result.get("access_token")
    if not token:
        die(f"Access token alınamadı: {result}")
    return token


def graphql(token, query, variables=None, retries=5):
    url = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": token}
    for attempt in range(retries):
        result = http_json(url, data=payload, headers=headers, method="POST")
        errors = result.get("errors")
        if not errors:
            return result["data"]
        throttled = any((e.get("extensions") or {}).get("code") == "THROTTLED" for e in errors)
        if throttled and attempt < retries - 1:
            time.sleep(2 ** attempt * 2)
            continue
        die(f"GraphQL hatası: {json.dumps(errors, ensure_ascii=False)[:800]}")
    die("GraphQL isteği tekrar denemelere rağmen başarısız.")


def build_bulk_query():
    translations = 'tr: translations(locale: "tr") { key value }' if INCLUDE_TR else ""
    return f"""
{{
  products(query: {json.dumps(PRODUCT_QUERY)}) {{
    edges {{
      node {{
        id handle title productType vendor updatedAt descriptionHtml
        category {{ fullName }}
        {translations}
        itemGroup: metafield(namespace: "custom", key: "item_group_id") {{ value }}
        season: metafield(namespace: "custom", key: "season") {{ value }}
        material: metafield(namespace: "custom", key: "material") {{ value }}
        fit: metafield(namespace: "custom", key: "fit") {{ value }}
        fabricType: metafield(namespace: "custom", key: "fabric_type") {{ value }}
        length: metafield(namespace: "custom", key: "length") {{ value }}
        waist: metafield(namespace: "custom", key: "waist") {{ value }}
        measurements: metafield(namespace: "custom", key: "product_measurements") {{ value }}
        packContent: metafield(namespace: "custom", key: "pack_content") {{ value }}
        packSize: metafield(namespace: "custom", key: "pack_size") {{ value }}
        variants {{
          edges {{
            node {{
              id sku barcode price inventoryQuantity
              selectedOptions {{ name value }}
              image {{ url }}
            }}
          }}
        }}
        media {{
          edges {{
            node {{
              id
              ... on MediaImage {{ image {{ url }} }}
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""


RUN_BULK = """
mutation RunBulk($query: String!) {
  bulkOperationRunQuery(query: $query, groupObjects: false) {
    bulkOperation { id status }
    userErrors { field message }
  }
}
"""

POLL_BULK = """
query PollBulk($id: ID!) {
  bulkOperation(id: $id) { id status errorCode objectCount url partialDataUrl }
}
"""


def fetch_bulk_jsonl(token):
    data = graphql(token, RUN_BULK, {"query": build_bulk_query()})
    run = data["bulkOperationRunQuery"]
    if run["userErrors"]:
        die(f"Bulk operation başlatılamadı: {run['userErrors']}")
    op_id = run["bulkOperation"]["id"]
    print(f"Bulk operation başladı: {op_id}")

    deadline = time.time() + BULK_TIMEOUT_SEC
    while True:
        time.sleep(5)
        op = graphql(token, POLL_BULK, {"id": op_id})["bulkOperation"]
        status = op["status"]
        if status == "COMPLETED":
            break
        if status in ("FAILED", "CANCELED", "CANCELING", "EXPIRED"):
            die(f"Bulk operation {status} (errorCode={op.get('errorCode')})")
        if time.time() > deadline:
            die(f"Bulk operation {BULK_TIMEOUT_SEC} sn içinde bitmedi (son durum: {status}).")

    print(f"Bulk operation tamamlandı, {op.get('objectCount')} nesne.")
    if not op.get("url"):
        return []
    return http_text(op["url"]).splitlines()


# --------------------------------------------------------------------------
# Ham veriyi ortak yapıya çevirme
# --------------------------------------------------------------------------

def mf(node, alias):
    value = node.get(alias)
    if isinstance(value, dict):
        return (value.get("value") or "").strip()
    return ""


def normalize_variant(v):
    color, size = "", ""
    for option in v.get("selectedOptions") or []:
        name = (option.get("name") or "").strip().lower()
        if name in COLOR_OPTION_NAMES:
            color = (option.get("value") or "").strip()
        elif name in SIZE_OPTION_NAMES:
            size = (option.get("value") or "").strip()
    image = v.get("image") or {}
    return {
        "sku": (v.get("sku") or "").strip(),
        "barcode": (v.get("barcode") or "").strip(),
        "price": v.get("price") or "0",
        "stock": max(int(v.get("inventoryQuantity") or 0), 0),
        "color": color,
        "size": size,
        "image": image.get("url") or "",
    }


def normalize_product(node, variants, media_urls):
    translations = {t.get("key"): (t.get("value") or "").strip() for t in (node.get("tr") or [])}
    return {
        "shopify_id": (node.get("id") or "").rsplit("/", 1)[-1],
        "handle": node.get("handle") or "",
        "title": (node.get("title") or "").strip(),
        "title_tr": translations.get("title", ""),
        "product_type": (node.get("productType") or "").strip(),
        "product_type_tr": translations.get("product_type", ""),
        "category": ((node.get("category") or {}).get("fullName") or "").strip(),
        "updated_at": node.get("updatedAt") or "",
        "description": (node.get("descriptionHtml") or "").strip(),
        "item_group": mf(node, "itemGroup"),
        "season": mf(node, "season"),
        "material": mf(node, "material"),
        "fit": mf(node, "fit"),
        "fabric_type": mf(node, "fabricType"),
        "length": mf(node, "length"),
        "waist": mf(node, "waist"),
        "measurements": mf(node, "measurements"),
        "pack_content": mf(node, "packContent"),
        "pack_size": mf(node, "packSize"),
        "variants": [normalize_variant(v) for v in variants],
        "media": media_urls,
    }


def products_from_jsonl(lines):
    """Bulk operation JSONL çıktısı: ürün satırları + __parentId ile bağlı varyant/medya satırları."""
    products = OrderedDict()
    children = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if obj.get("__parentId"):
            children.append(obj)
        else:
            products[obj["id"]] = {"node": obj, "variants": [], "media": []}
    for child in children:
        parent = products.get(child["__parentId"])
        if parent is None:
            continue
        child_id = child.get("id") or ""
        if "/ProductVariant/" in child_id:
            parent["variants"].append(child)
        elif (child.get("image") or {}).get("url"):
            parent["media"].append(child["image"]["url"])
    return [normalize_product(p["node"], p["variants"], p["media"]) for p in products.values()]


def products_from_graphql(nodes):
    """Normal (sayfalı) GraphQL yanıtından gelen iç içe yapı — test ve hata ayıklama için."""
    result = []
    for node in nodes:
        variants = [e["node"] for e in (node.get("variants") or {}).get("edges", [])]
        media = []
        for edge in (node.get("media") or {}).get("edges", []):
            url = ((edge.get("node") or {}).get("image") or {}).get("url")
            if url:
                media.append(url)
        result.append(normalize_product(node, variants, media))
    return result


# --------------------------------------------------------------------------
# İş kuralları
# --------------------------------------------------------------------------

PACK_PART = re.compile(r"\s*([^/]+?)\s*/\s*(\d+)\s*(?:-|$)")


def parse_pack(text):
    """'XS/1-S/2-M/2-L/1' -> [('XS', 1), ('S', 2), ('M', 2), ('L', 1)]
    Birleşik bedenler de desteklenir: 'XS-S/3-M-L/3' -> [('XS-S', 3), ('M-L', 3)]"""
    text = (text or "").strip()
    if not text:
        return []
    pairs, position = [], 0
    while position < len(text):
        match = PACK_PART.match(text, position)
        if not match or match.end() == position:
            return []
        qty = int(match.group(2))
        if qty > 0:
            pairs.append((match.group(1).upper(), qty))
        position = match.end()
    return pairs


UUID_SUFFIX = re.compile(r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
INDEX_SUFFIX = re.compile(r"^(.+?)_(\d+)(?:_[a-z]+)?$", re.I)


def clean_url(url):
    return url.split("?", 1)[0]


def image_key(url):
    """Görseli renk grubuna ayırmak için dosya adından anahtar çıkarır.
    8682502895630_1.jpg                                  -> ('8682502895630', 1)
    8682502555541_2_23cd5ebd-....jpg                     -> ('8682502555541', 2)
    omuz-pencere-..._18730_gri-gri_1_buyuk.jpg           -> ('omuz-pencere-..._18730_gri-gri', 1)"""
    name = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0]
    stem = UUID_SUFFIX.sub("", stem)
    match = INDEX_SUFFIX.match(stem)
    if match:
        return match.group(1).lower(), int(match.group(2))
    return stem.lower(), 0


def assign_images(product, colors, report):
    """Her renge kendi görsellerini bulur.
    1) Varyant görseli (renk çapası) ile aynı dosya grubundaki görseller
    2) Dosya adı rengin varyant barkodlarından biriyle başlayan görseller
    3) Tek renkli ürünse tüm görseller
    Eşleşmeyen renk feed'e girmez ve rapora düşer; yanlış renkte fotoğraf göstermektense
    rengi hiç göndermemek tercih edilir."""
    groups = OrderedDict()
    seen = set()
    for url in product["media"]:
        key, index = image_key(url)
        if (key, index) in seen:          # aynı görselin tekrar yüklenmiş kopyası
            continue
        seen.add((key, index))
        groups.setdefault(key, []).append((index, clean_url(url)))

    assigned = {}
    used_keys = set()
    for color, variants in colors.items():
        keys = []
        for v in variants:
            if v["image"]:
                key = image_key(v["image"])[0]
                if key in groups and key not in keys:
                    keys.append(key)
        if not keys:
            barcodes = {v["barcode"] for v in variants if v["barcode"]}
            keys = [k for k in groups if k in barcodes]
        if keys:
            assigned[color] = keys
            used_keys.update(keys)

    if len(colors) == 1 and not assigned and groups:
        only = next(iter(colors))
        assigned[only] = list(groups)
        used_keys.update(groups)

    result = {}
    for color, keys in assigned.items():
        images = []
        for key in keys:
            images.extend(url for _, url in sorted(groups[key], key=lambda x: x[0]))
        result[color] = images[:MAX_IMAGES]
    return result


SKU_COLOR = re.compile(r"^[^-]+-([^-]+)-")


def color_code(color, variants):
    for v in variants:
        match = SKU_COLOR.match(v["sku"])
        if match:
            return match.group(1)
    return slugify(color)


TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.translate(TR_MAP).lower()).strip("-") or "renk"


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def size_sort_key(size, pack_order):
    if size in pack_order:
        return (0, pack_order.index(size))
    if size in SIZE_ORDER:
        return (1, SIZE_ORDER.index(size))
    return (2, size)


class Report:
    def __init__(self):
        self.warnings = []
        self.skipped_products = []
        self.skipped_colors = []
        self.missing_tr = []
        self.stats = Counter()

    def warn(self, text):
        self.warnings.append(text)

    def render(self):
        s = self.stats
        lines = [
            "## Yakemall feed raporu",
            "",
            f"- Shopify'dan gelen ürün: **{s['products_in']}**",
            f"- Feed'deki model: **{s['products_out']}**, renk: **{s['colors_out']}** "
            f"(stoğu 0 olan renk: {s['colors_zero']})",
            f"- Atlanan model: {len(self.skipped_products)}, görseli olmadığı için atlanan renk: "
            f"{len(self.skipped_colors)}",
            f"- Türkçe başlığı olmayan model: {len(self.missing_tr)}" if INCLUDE_TR else "",
            "",
        ]
        stocked = [c for c in self.skipped_colors if c[2] > 0]
        if stocked:
            lines.append("### Stokta olduğu halde görseli olmayan renkler (feed'e girmedi)")
            for item in sorted(stocked, key=lambda x: -x[2])[:60]:
                lines.append(f"- {item[0]} / {item[1]} — {item[2]} seri")
            lines.append("")
        if len(stocked) < len(self.skipped_colors):
            lines.append(f"_Ayrıca stoğu ve görseli olmayan {len(self.skipped_colors) - len(stocked)} "
                         f"renk varyantı atlandı (üretilmemiş renk seçenekleri)._")
            lines.append("")
        if self.skipped_products:
            lines.append("### Atlanan modeller")
            for item in self.skipped_products[:60]:
                lines.append(f"- {item}")
            lines.append("")
        if self.warnings:
            lines.append("### Uyarılar")
            for item in self.warnings[:60]:
                lines.append(f"- {item}")
            lines.append("")
        if INCLUDE_TR and self.missing_tr:
            lines.append("### Türkçe başlığı eksik modeller (ilk 40)")
            lines.append(", ".join(self.missing_tr[:40]))
            lines.append("")
        return "\n".join(line for line in lines if line is not None)


def build_catalog(products, report):
    catalog = []
    report.stats["products_in"] = len(products)
    for p in sorted(products, key=lambda x: (x["item_group"] or "~", x["title"])):
        label = p["item_group"] or p["handle"] or p["shopify_id"]
        if not p["item_group"]:
            report.skipped_products.append(f"{label}: custom.item_group_id boş")
            continue
        pack = parse_pack(p["pack_content"])
        if not pack:
            report.skipped_products.append(f"{label}: custom.pack_content boş/okunamadı ({p['pack_content']!r})")
            continue
        pack_total = sum(q for _, q in pack)
        if p["pack_size"] and p["pack_size"] != str(pack_total):
            report.warn(f"{label}: pack_size={p['pack_size']} ama pack_content toplamı {pack_total}; "
                        f"{pack_total} kullanıldı.")
        pack_sizes = [s for s, _ in pack]

        colors = OrderedDict()
        for v in p["variants"]:
            colors.setdefault(v["color"], []).append(v)
        images = assign_images(p, colors, report)

        color_entries = []
        used_ids = set()
        for color, variants in colors.items():
            stock_by_size = Counter()
            for v in variants:
                stock_by_size[v["size"].upper()] += v["stock"]
            packs = min(stock_by_size.get(size, 0) // qty for size, qty in pack)

            if not images.get(color):
                report.skipped_colors.append((label, color or "(renk yok)", packs))
                continue
            if packs == 0 and not INCLUDE_ZERO_STOCK:
                continue

            missing_sizes = [s for s in pack_sizes if s not in stock_by_size]
            if missing_sizes:
                report.warn(f"{label} / {color}: seri bedeni varyant olarak yok: {', '.join(missing_sizes)}")

            price_by_size = {v["size"].upper(): money(v["price"]) for v in variants}
            prices = Counter(price_by_size.values())
            unit_price = prices.most_common(1)[0][0] if prices else Decimal("0.00")
            pack_price = sum((price_by_size.get(size, unit_price) * qty for size, qty in pack), Decimal("0.00"))

            code = color_code(color, variants)
            color_id = f"{p['item_group']}-{code}"
            if color_id in used_ids:
                color_id = f"{color_id}-{slugify(color)}"
                report.warn(f"{label} / {color}: renk kodu tekrarlıyor, id {color_id} yapıldı.")
            used_ids.add(color_id)

            qty_by_size = dict(pack)
            ordered = sorted(variants, key=lambda v: size_sort_key(v["size"].upper(), pack_sizes))
            color_entries.append({
                "id": color_id,
                "code": code,
                "name": color,
                "unit_price": unit_price,
                "pack_price": pack_price,
                "packs": packs,
                "images": images[color],
                "variants": [{
                    "sku": v["sku"],
                    "barcode": v["barcode"],
                    "size": v["size"],
                    "pack_qty": qty_by_size.get(v["size"].upper(), 0),
                    "stock": v["stock"],
                    "price": money(v["price"]),
                } for v in ordered],
            })
            report.stats["colors_out"] += 1
            if packs == 0:
                report.stats["colors_zero"] += 1

        if not color_entries:
            report.skipped_products.append(f"{label}: görseli olan renk yok")
            continue
        if INCLUDE_TR and not p["title_tr"]:
            report.missing_tr.append(label)
        catalog.append({**p, "pack": pack, "pack_total": pack_total, "colors": color_entries})
        report.stats["products_out"] += 1
    return catalog


# --------------------------------------------------------------------------
# XML
# --------------------------------------------------------------------------

INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean(text):
    return INVALID_XML.sub("", str(text or ""))


def attr(text):
    text = clean(text).replace("\r", " ").replace("\n", " ")
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;"))


def cdata(text):
    return "<![CDATA[" + clean(text).replace("]]>", "]]]]><![CDATA[>") + "]]>"


def render_xml(catalog):
    color_count = sum(len(p["colors"]) for p in catalog)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<catalog brand="{attr(BRAND)}" currency="USD" products="{len(catalog)}" colors="{color_count}">']
    for p in catalog:
        out.append(f'  <product id="{attr(p["item_group"])}">')
        out.append(f'    <shopify_id>{attr(p["shopify_id"])}</shopify_id>')
        out.append(f'    <updated_at>{attr(p["updated_at"])}</updated_at>')
        out.append(f'    <title>{cdata(p["title"])}</title>')
        if INCLUDE_TR:
            out.append(f'    <title_tr>{cdata(p["title_tr"])}</title_tr>')
        out.append(f'    <product_type>{cdata(p["product_type"])}</product_type>')
        if INCLUDE_TR:
            out.append(f'    <product_type_tr>{cdata(p["product_type_tr"])}</product_type_tr>')
        out.append(f'    <category>{cdata(p["category"])}</category>')
        out.append(f'    <gender>{attr(GENDER)}</gender>')
        for tag in ("season", "material", "fit", "fabric_type", "length", "waist", "measurements", "description"):
            out.append(f'    <{tag}>{cdata(p[tag])}</{tag}>')
        out.append(f'    <pack size="{p["pack_total"]}" content="{attr(p["pack_content"])}">')
        for size, qty in p["pack"]:
            out.append(f'      <item size="{attr(size)}" qty="{qty}"/>')
        out.append('    </pack>')
        out.append('    <colors>')
        for c in p["colors"]:
            out.append(f'      <color id="{attr(c["id"])}" code="{attr(c["code"])}" name="{attr(c["name"])}">')
            out.append(f'        <unit_price>{c["unit_price"]}</unit_price>')
            out.append(f'        <pack_price>{c["pack_price"]}</pack_price>')
            out.append(f'        <packs_in_stock>{c["packs"]}</packs_in_stock>')
            out.append('        <images>')
            for position, url in enumerate(c["images"], start=1):
                out.append(f'          <image position="{position}">{attr(url)}</image>')
            out.append('        </images>')
            out.append('        <variants>')
            for v in c["variants"]:
                out.append(
                    f'          <variant sku="{attr(v["sku"])}" barcode="{attr(v["barcode"])}" '
                    f'size="{attr(v["size"])}" pack_qty="{v["pack_qty"]}" stock="{v["stock"]}" '
                    f'price="{v["price"]}"/>')
            out.append('        </variants>')
            out.append('      </color>')
        out.append('    </colors>')
        out.append('  </product>')
    out.append('</catalog>')
    return "\n".join(out) + "\n"


def previous_product_count(path):
    try:
        with open(path, encoding="utf-8") as handle:
            head = handle.read(600)
    except FileNotFoundError:
        return None
    match = re.search(r'<catalog[^>]*\sproducts="(\d+)"', head)
    return int(match.group(1)) if match else None


def write_summary(text):
    print(text)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")


# --------------------------------------------------------------------------
# Giriş noktası
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BSL Wholesale -> pazaryeri XML feed")
    parser.add_argument("--out", default="docs/yakemall.xml", help="Yazılacak XML dosyası")
    parser.add_argument("--from-jsonl", help="API yerine kayıtlı bulk JSONL dosyasından üret")
    parser.add_argument("--save-jsonl", help="Ham bulk çıktısını bu dosyaya da kaydet (hata ayıklama)")
    parser.add_argument("--force", action="store_true", help="Ürün sayısı düşüş korumasını atla")
    args = parser.parse_args()

    if args.from_jsonl:
        with open(args.from_jsonl, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    else:
        token = get_access_token()
        lines = fetch_bulk_jsonl(token)
        if args.save_jsonl:
            with open(args.save_jsonl, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")

    report = Report()
    catalog = build_catalog(products_from_jsonl(lines), report)
    xml_text = render_xml(catalog)

    try:
        ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError as error:
        die(f"Üretilen XML geçersiz, dosya yazılmadı: {error}")

    previous = previous_product_count(args.out)
    if previous and not args.force and len(catalog) < previous * SHRINK_GUARD:
        write_summary(report.render())
        die(f"Model sayısı {previous} -> {len(catalog)} düştü (eşik %{int(SHRINK_GUARD * 100)}). "
            f"Pazaryerinde ürünlerin toplu kapanmaması için feed güncellenmedi. "
            f"Bilinçli bir düşüşse --force ile çalıştırın.", code=2)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    temp_path = args.out + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        handle.write(xml_text)
    os.replace(temp_path, args.out)

    write_summary(report.render())
    print(f"Yazıldı: {args.out} ({len(catalog)} model)")


if __name__ == "__main__":
    main()
