#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API'ye bağlanmadan feed mantığını test eder.

Fikstür, 22.10.2026'da bsl-wholesale.com'dan okunan 5 gerçek modelin verisidir
(21620, 21637, 21635, 19415, 18553). Bulk operation'ın JSONL çıktısı formatına
çevrilip script'in gerçek ayrıştırma yolundan geçirilir.
Not: 19415 dışındaki medya ID'leri ve 19415'in bazı varyant ID'leri yer tutucudur
(feed'e yazılmazlar); 18553'ün varyant görselleri okunmadığı için boş bırakıldı.

Çalıştırma:  python tests/test_feed.py [örnek_xml_yolu]
"""

import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import yakemall_feed as feed  # noqa: E402

CDN = "https://cdn.shopify.com/s/files/1/0704/7643/1430/files/"
PACK6 = "XS/1-S/2-M/2-L/1"


def mfv(value):
    return {"value": value} if value is not None else None


def product(pid, title, ptype, handle, updated, category, tr, item_group, season, material, fit,
            fabric, length, measurements, pack, pack_size):
    return {
        "id": f"gid://shopify/Product/{pid}", "handle": handle, "title": title, "productType": ptype,
        "vendor": "BSL", "updatedAt": updated, "descriptionHtml": "", "category": {"fullName": category},
        "tr": tr, "itemGroup": mfv(item_group), "season": mfv(season), "material": mfv(material),
        "fit": mfv(fit), "fabricType": mfv(fabric), "length": mfv(length), "waist": None,
        "measurements": mfv(measurements), "packContent": mfv(pack), "packSize": mfv(pack_size),
    }


def variant(vid, sku, barcode, price, qty, color, size, image=None):
    return {"id": f"gid://shopify/ProductVariant/{vid}", "sku": sku, "barcode": barcode, "price": price,
            "inventoryQuantity": qty,
            "selectedOptions": [{"name": "Color", "value": color}, {"name": "Size", "value": size}],
            "image": {"url": CDN + image} if image else None}


def media(mid, filename):
    return {"id": f"gid://shopify/MediaImage/{mid}", "image": {"url": CDN + filename}}


FIXTURE = []

# --- 21620: 4 renk; 2'si hiç üretilmemiş (stok ve görsel yok), görseller barkod adlı -------------
p = product(10243631743046, "Shawl-Collar Double-Breasted Blazer", "Jackets & Coats",
            "shawl-collar-double-breasted-blazer-21620", "2026-10-22T08:26:50Z",
            "Apparel & Accessories > Clothing > Outerwear > Coats & Jackets > Blazers", [], "21620",
            "Winter 2027", "Viscose %35, Pes %65, Inner Material: Pes %100", "Regular Fit", "Weaving",
            "Standard Size", "Chest: 56 cm - Waist: 31.5 cm - Sleeve Length: 61 cm - Length: 65 cm", PACK6, "6")
blk, ant = "8682502895630_1.jpg?v=1792655756", "8682502895715_1.jpg?v=1792655818"
v = [
    variant(50592873218118, "21620-02-L", "8682502895609", "33.00", 1, "Black", "L", blk),
    variant(50592873250886, "21620-02-M", "8682502895616", "33.00", 2, "Black", "M", blk),
    variant(50592873283654, "21620-02-S", "8682502895623", "33.00", 2, "Black", "S", blk),
    variant(50592873316422, "21620-02-XS", "8682502895630", "33.00", 1, "Black", "XS", blk),
    variant(50592873349190, "21620-221-L", "8682502895647", "33.00", 0, "Anthracite-1", "L"),
    variant(50592873381958, "21620-221-M", "8682502895654", "33.00", 0, "Anthracite-1", "M"),
    variant(50592873414726, "21620-221-S", "8682502895661", "33.00", 0, "Anthracite-1", "S"),
    variant(50592873447494, "21620-221-XS", "8682502895678", "33.00", 0, "Anthracite-1", "XS"),
    variant(50592873480262, "21620-40-L", "8682502895685", "33.00", 14, "Anthracite", "L", ant),
    variant(50592873513030, "21620-40-M", "8682502895692", "33.00", 28, "Anthracite", "M", ant),
    variant(50592873545798, "21620-40-S", "8682502895708", "33.00", 28, "Anthracite", "S", ant),
    variant(50592873578566, "21620-40-XS", "8682502895715", "33.00", 14, "Anthracite", "XS", ant),
    variant(50592873611334, "21620-576-L", "8682502895722", "33.00", 0, "Antrasit 2", "L"),
    variant(50592873644102, "21620-576-M", "8682502895739", "33.00", 0, "Antrasit 2", "M"),
    variant(50592873676870, "21620-576-S", "8682502895746", "33.00", 0, "Antrasit 2", "S"),
    variant(50592873709638, "21620-576-XS", "8682502895753", "33.00", 0, "Antrasit 2", "XS"),
]
m = [media(f"f1{i}", f) for i, f in enumerate([
    "8682502895630_1.jpg?v=1792655756", "8682502895630_2.jpg?v=1792655756", "8682502895630_4.jpg?v=1792655756",
    "8682502895630_3.jpg?v=1792655756", "8682502895630_5.jpg?v=1792655756", "8682502895715_1.jpg?v=1792655818",
    "8682502895715_2.jpg?v=1792655872", "8682502895715_3.jpg?v=1792655872", "8682502895715_4.jpg?v=1792655872",
    "8682502895715_5.jpg?v=1792655872"])]
FIXTURE.append((p, v, m))

# --- 21637: tek renk -------------------------------------------------------------------------------
p = product(10251588370502, "Sheer Lace Top", "Tops & Bodysuits", "sheer-lace-top-21637", "2026-10-22T08:05:35Z",
            "Apparel & Accessories > Clothing > Clothing Tops > Blouses", [], "21637", "Winter 2027",
            "Elastane %5, Recycle polyamid %95", "Slim Fit", "Knitting", "Standard Size",
            "Chest: 40.5 cm - Waist: 34 cm - Sleeve Length: 65 cm - Length: 55 cm", PACK6, "6")
img = "8682502898129_1.jpg?v=1792656300"
v = [
    variant(50614710239302, "21637-02-L", "8682502898099", "8.00", 7, "Black", "L", img),
    variant(50614710272070, "21637-02-M", "8682502898105", "8.00", 14, "Black", "M", img),
    variant(50614710304838, "21637-02-S", "8682502898112", "8.00", 14, "Black", "S", img),
    variant(50614710337606, "21637-02-XS", "8682502898129", "8.00", 7, "Black", "XS", img),
]
m = [media(f"f2{i}", f"8682502898129_{i}.jpg?v=1792656300") for i in range(1, 6)]
FIXTURE.append((p, v, m))

# --- 21635: renk adında Türkçe ı ("Mılk coffee") ------------------------------------------------------
p = product(10243633250374, "Boat Neck Draped Top", "Tops & Bodysuits", "boat-neck-draped-top-21635",
            "2026-10-22T08:23:49Z", "Apparel & Accessories > Clothing > Clothing Tops > Blouses", [], "21635",
            "Winter 2027", "Elastane %5, Pes %95", "Slim Fit", "Knitting", "Standard Size",
            "Chest: 35 cm - Waist: 27 cm - Sleeve Length: 61 cm - Boy's Size: 72 cm", PACK6, "6")
img = "8682502897788_1.jpg?v=1792656209"
v = [
    variant(50592882720838, "21635-25-L", "8682502897757", "8.00", 10, "Mılk coffee", "L", img),
    variant(50592882753606, "21635-25-M", "8682502897764", "8.00", 20, "Mılk coffee", "M", img),
    variant(50592882786374, "21635-25-S", "8682502897771", "8.00", 20, "Mılk coffee", "S", img),
    variant(50592882819142, "21635-25-XS", "8682502897788", "8.00", 10, "Mılk coffee", "XS", img),
]
m = [media(f"f3{i}", f"8682502897788_{i}.jpg?v=1792656209") for i in range(1, 6)]
FIXTURE.append((p, v, m))

# --- 19415: 7'li seri (XS/2), slug adlı görseller, Black stokta ama görselsiz ---------------------------
p = product(8530183782470, "Carmen Neck Strap Detailled Midi Knit Dress", "Dresses",
            "carmen-neck-strap-detailled-midi-knit-dress-19415", "2026-10-22T02:55:28Z",
            "Apparel & Accessories > Clothing > Dresses",
            [{"key": "title", "value": "Carmen Boyun Askılı Detaylı Midi Triko Elbise"},
             {"key": "product_type", "value": "Elbiseler"}],
            "19415", "Winter 2024", "Pes %100", "Slim Fit", "Knitting", None,
            "Chest:26cm Waist:26cm Sleeve Length:54cm Length:108cm", "XS/2-S/2-M/2-L/1", "7")
slug = "carmen-yaka-aski-detayli-midi-triko-elbise_19415_"
red, brown, mink = (slug + "kirmizi-kirmizi_1_buyuk.jpg?v=1788954353", slug + "kahve-kahverengi_1_buyuk.jpg?v=1788954353",
                    slug + "vizon-vizon_1_buyuk.jpg?v=1788954354")
v = [
    variant(46492437610566, "19415-02-L", "8682502653308", "12.00", 51, "Black", "L"),
    variant(46492437643334, "19415-02-M", "8682502653315", "12.00", 102, "Black", "M"),
    variant("fx-19415-02-S", "19415-02-S", "8682502653322", "12.00", 102, "Black", "S"),
    variant("fx-19415-02-XS", "19415-02-XS", "8682502653339", "12.00", 102, "Black", "XS"),
    variant("fx-19415-03-L", "19415-03-L", "8682502653346", "12.00", 24, "Red", "L", red),
    variant("fx-19415-03-M", "19415-03-M", "8682502653353", "12.00", 48, "Red", "M", red),
    variant("fx-19415-03-S", "19415-03-S", "8682502653360", "12.00", 48, "Red", "S", red),
    variant("fx-19415-03-XS", "19415-03-XS", "8682502653377", "12.00", 48, "Red", "XS", red),
    variant("fx-19415-07-L", "19415-07-L", "8682502653384", "12.00", 28, "Brown", "L", brown),
    variant("fx-19415-07-M", "19415-07-M", "8682502653391", "12.00", 56, "Brown", "M", brown),
    variant("fx-19415-07-S", "19415-07-S", "8682502653407", "12.00", 56, "Brown", "S", brown),
    variant("fx-19415-07-XS", "19415-07-XS", "8682502653414", "12.00", 56, "Brown", "XS", brown),
    variant("fx-19415-45-L", "19415-45-L", "8682502653421", "12.00", 42, "Mink", "L", mink),
    variant("fx-19415-45-M", "19415-45-M", "8682502653438", "12.00", 84, "Mink", "M", mink),
    variant("fx-19415-45-S", "19415-45-S", "8682502653445", "12.00", 84, "Mink", "S", mink),
    variant("fx-19415-45-XS", "19415-45-XS", "8682502653452", "12.00", 84, "Mink", "XS", mink),
]
media_19415 = [
    (30236534177862, "vizon-vizon_1", 1788954354), (30236534210630, "vizon-vizon_2", 1788954353),
    (30236534276166, "vizon-vizon_4", 1788954353), (30236534243398, "vizon-vizon_3", 1788954353),
    (30236534308934, "vizon-vizon_5", 1788954353), (30236534341702, "vizon-vizon_6", 1788954353),
    (30236534374470, "vizon-vizon_7", 1788954353), (30236533719110, "kirmizi-kirmizi_1", 1788954353),
    (30236533751878, "kirmizi-kirmizi_2", 1788954353), (30236533784646, "kirmizi-kirmizi_3", 1788954353),
    (30236533817414, "kirmizi-kirmizi_4", 1788954353), (30236533850182, "kirmizi-kirmizi_5", 1788954353),
    (30236533882950, "kirmizi-kirmizi_6", 1788954353), (30236533915718, "kirmizi-kirmizi_7", 1788954354),
    (30236533948486, "kahve-kahverengi_1", 1788954353), (30236533981254, "kahve-kahverengi_2", 1788954354),
    (30236534014022, "kahve-kahverengi_3", 1788954353), (30236534046790, "kahve-kahverengi_4", 1788954353),
    (30236534079558, "kahve-kahverengi_5", 1788954353), (30236534112326, "kahve-kahverengi_6", 1788954354),
    (30236534145094, "kahve-kahverengi_7", 1788954353), (30236534407238, "vizon-vizon_8", 1788954353),
]
m = [media(mid, f"{slug}{name}_buyuk.jpg?v={ver}") for mid, name, ver in media_19415]
FIXTURE.append((p, v, m))

# --- 18553: tek renk, aynı görselin tekrar yüklenmiş kopyası (uuid ekli) ------------------------------
p = product(8530153439302, "Drapped mini dress", "Dresses", "drapped-mini-dress-18553", "2026-10-22T01:07:26Z",
            "Uncategorized", [{"key": "title", "value": "Drapeli mini elbise"},
                              {"key": "product_type", "value": "Elbiseler"}],
            "18553", "Winter 2023", "Inner Material: Pes %100, Outer Material: Pes %100", "Short", "Weaving",
            None, "Chest 44cm, Waist 32,5cm, Sleeve Length 63cm, Length 77cm", PACK6, "6")
v = [
    variant("fx-18553-L", "18553-278-L", "8682502555510", "12.00", 133, "Multı colour", "L"),
    variant("fx-18553-M", "18553-278-M", "8682502555527", "12.00", 266, "Multı colour", "M"),
    variant("fx-18553-S", "18553-278-S", "8682502555534", "12.00", 266, "Multı colour", "S"),
    variant("fx-18553-XS", "18553-278-XS", "8682502555541", "12.00", 133, "Multı colour", "XS"),
]
m = [media(f"f5{i}", f) for i, f in enumerate([
    "8682502555541_2.jpg?v=1788855618", "8682502555541_2_23cd5ebd-d9dc-4151-8def-e3c9bc92dbbb.jpg?v=1788855669",
    "8682502555541_3.jpg?v=1788855669", "8682502555541_4.jpg?v=1788855669", "8682502555541_5.jpg?v=1788855669",
    "8682502555541_6.jpg?v=1788855669", "8682502555541_7.jpg?v=1788855669"])]
FIXTURE.append((p, v, m))


def to_bulk_jsonl(fixture):
    lines = []
    for prod, variants, medias in fixture:
        lines.append(json.dumps(prod, ensure_ascii=False))
        for item in variants + medias:
            lines.append(json.dumps({**item, "__parentId": prod["id"]}, ensure_ascii=False))
    return lines


def main():
    feed.SAFETY_STOCK = 0          # temel hesap kontrolleri güvenlik payı olmadan
    lines = to_bulk_jsonl(FIXTURE)
    report = feed.Report()
    catalog = feed.build_catalog(feed.products_from_jsonl(lines), report)
    xml_text = feed.render_xml(catalog)
    root = ET.fromstring(xml_text.encode("utf-8"))

    by_id = {c.get("id"): c for c in root.iter("color")}

    # Seri hesabı: tamamlanabilen seri sayısı
    assert by_id["21620-02"].findtext("packs_in_stock") == "1"
    assert by_id["21620-40"].findtext("packs_in_stock") == "14"
    assert by_id["19415-45"].findtext("packs_in_stock") == "42"          # 7'li seri, XS/2
    assert by_id["18553-278"].findtext("packs_in_stock") == "133"

    # Fiyat: birim × seri
    assert by_id["21620-40"].findtext("pack_price") == "198.00"
    assert by_id["19415-03"].findtext("pack_price") == "84.00"           # 12 × 7

    # Görseli olmayan renkler feed'e girmez, stoklu olan rapora düşer
    assert "21620-221" not in by_id and "21620-576" not in by_id
    assert "19415-02" not in by_id
    assert ("19415", "Black", 51) in report.skipped_colors

    # Görseller renge göre ayrışır, sıralanır, ?v= atılır, tekrar yüklenen kopya elenir
    imgs = lambda cid: [i.text for i in by_id[cid].iter("image")]  # noqa: E731
    assert all("8682502895715_" in u for u in imgs("21620-40")) and len(imgs("21620-40")) == 5
    assert imgs("21620-02")[2].endswith("8682502895630_3.jpg")
    assert len(imgs("19415-45")) == 8 and all("vizon" in u for u in imgs("19415-45"))
    assert len(imgs("18553-278")) == 6 and not any("?" in u for u in imgs("18553-278"))

    # Varyantlar seri sırasıyla, barkodlu
    sizes = [v.get("size") for v in by_id["21637-02"].iter("variant")]
    assert sizes == ["XS", "S", "M", "L"], sizes
    assert by_id["19415-45"].find("variants/variant").get("pack_qty") == "2"

    # Türkçe başlık
    p19415 = root.find("product[@id='19415']")
    assert p19415.findtext("title_tr") == "Carmen Boyun Askılı Detaylı Midi Triko Elbise"
    assert root.get("products") == "5" and root.get("colors") == str(len(by_id))

    # Seri tanımı ayrıştırma (birleşik bedenler dahil)
    assert feed.parse_pack("XS/1-S/2-M/2-L/1") == [("XS", 1), ("S", 2), ("M", 2), ("L", 1)]
    assert feed.parse_pack("XS-S/3-M-L/3") == [("XS-S", 3), ("M-L", 3)]
    assert feed.parse_pack("XS/2-S/2-M/2-L/1") == [("XS", 2), ("S", 2), ("M", 2), ("L", 1)]
    assert feed.parse_pack("bozuk") == [] and feed.parse_pack("") == []

    # 16894: birleşik bedenli şort (XS-S / M-L), seri 3+3
    p = product(1, "Rib-Knit Cuffed Mini Shorts", "Shorts", "x-16894", "", "", [], "16894", "", "", "", "", None,
                "", "XS-S/3-M-L/3", "6")
    v = [variant("c1", "16894-10-M-L", "1", "5.00", 54, "Cream", "M-L", "c_1.jpg"),
         variant("c2", "16894-10-XS-S", "2", "5.00", 54, "Cream", "XS-S", "c_1.jpg")]
    m = [media("cm1", "c_1.jpg"), media("cm2", "c_2.jpg")]
    shorts = feed.build_catalog(feed.products_from_jsonl(to_bulk_jsonl([(p, v, m)])), feed.Report())
    assert shorts[0]["colors"][0]["packs"] == 18
    assert [x["size"] for x in shorts[0]["colors"][0]["variants"]] == ["XS-S", "M-L"]

    # 20695: görselsiz renk (White) sahipsiz başka renk fotoğraflarıyla eşleştirilmemeli
    p = product(2, "Polo Collar Maxi Pique Dress", "Dresses", "x-20695", "", "", [], "20695", "", "", "", "", None,
                "", PACK6, "6")
    v = [variant(f"w{s}", f"20695-01-{s}", f"w{s}", "9.00", 0, "White", s) for s in ("XS", "S", "M", "L")] + \
        [variant(f"n{s}", f"20695-05-{s}", f"n{s}", "9.00", 2, "Navy", s, "8682502788420_1.jpg") for s in ("XS", "S", "M", "L")]
    m = [media("l1", "polo-yakali-maksi-pike-elbise_20695_lacivert-lacivert_1_buyuk.jpg"),
         media("n1", "8682502788420_1.jpg"), media("n2", "8682502788420_2.jpg")]
    rep = feed.Report()
    polo = feed.build_catalog(feed.products_from_jsonl(to_bulk_jsonl([(p, v, m)])), rep)
    assert [c["name"] for c in polo[0]["colors"]] == ["Navy"]
    assert ("20695", "White", 0) in rep.skipped_colors

    # Güvenlik payı: her renkten 1 seri düşülür, 0'ın altına inmez; görselsiz renk raporu gerçek stoğu gösterir
    feed.SAFETY_STOCK = 1
    rep = feed.Report()
    buffered = feed.build_catalog(feed.products_from_jsonl(lines), rep)
    packs = {c["id"]: c["packs"] for p in buffered for c in p["colors"]}
    assert packs["21620-40"] == 13 and packs["21620-02"] == 0 and packs["18553-278"] == 132
    assert ("19415", "Black", 51) in rep.skipped_colors

    print(f"Tüm kontroller geçti: {root.get('products')} model, {root.get('colors')} renk.\n")
    print(report.render())

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as handle:
            handle.write(feed.render_xml(buffered))   # canlı ayarla (1 seri güvenlik payı)
        print(f"\nÖrnek XML yazıldı: {sys.argv[1]}")


if __name__ == "__main__":
    main()
