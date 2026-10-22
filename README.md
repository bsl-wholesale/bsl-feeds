# BSL pazaryeri feed'leri

bsl-wholesale.com (Shopify) kataloğundan pazaryerlerine XML feed üretir.
İlk kullanıcı **Yakemall**; aynı altyapı ileride Modadays gibi kanallara da feed verebilir.

- `yakemall_feed.py`: Shopify Admin API'den aktif ürünleri çeker (bulk operation), XML'i yazar. Ek paket gerekmez.
- `.github/workflows/yakemall-feed.yml`: Script'i 30 dakikada bir çalıştırır. Feed değiştiyse `docs/yakemall.xml` dosyasını günceller.
- `docs/`: GitHub Pages'in yayınladığı klasör. Feed adresi şöyle olur: `https://<github-kullanıcısı>.github.io/<repo>/yakemall.xml`
- `tests/test_feed.py`: 5 gerçek modelle API'ye bağlanmadan çalışan test. `tests/ornek_yakemall.xml` dosyası bu testin çıktısıdır.

---

## Feed yapısı (Yakemall / Toserof için)

Hiyerarşi şöyle: **model → renk → beden**. Satılabilir birim bir rengin bir **serisidir**. BSL seri bölmez.

```xml
<catalog brand="BSL" currency="USD" products="..." colors="...">
  <product id="21620">
    <shopify_id>…</shopify_id>
    <updated_at>2026-10-22T08:26:50Z</updated_at>
    <title><![CDATA[Shawl-Collar Double-Breasted Blazer]]></title>
    <title_tr><![CDATA[…]]></title_tr>
    <product_type><![CDATA[Jackets & Coats]]></product_type>
    <product_type_tr><![CDATA[…]]></product_type_tr>
    <category><![CDATA[Apparel & Accessories > … > Blazers]]></category>
    <gender>Woman</gender>
    <season/> <material/> <fit/> <fabric_type/> <length/> <waist/> <measurements/> <description/>
    <pack size="6" content="XS/1-S/2-M/2-L/1">
      <item size="XS" qty="1"/> …
    </pack>
    <colors>
      <color id="21620-40" code="40" name="Anthracite">
        <unit_price>33.00</unit_price>
        <pack_price>198.00</pack_price>
        <packs_in_stock>14</packs_in_stock>
        <images><image position="1">https://cdn.shopify.com/…</image> …</images>
        <variants>
          <variant sku="21620-40-XS" barcode="8682502895715" size="XS" pack_qty="1" stock="14" price="33.00"/> …
        </variants>
      </color>
    </colors>
  </product>
</catalog>
```

| Alan | Anlamı |
|---|---|
| `product@id` | Model kodu (Nebim stok kodu). Sabit anahtar. |
| `title_tr`, `product_type_tr` | Shopify'daki Türkçe çeviri. Çevirisi olmayan modellerde boş gelir. |
| `category` | Shopify standart kategori yolu. Atanmamış modellerde boş ya da `Uncategorized` gelir. |
| `pack` | Seri içeriği: hangi bedenden kaç adet. `size` serideki toplam adettir. |
| `color@id` | `{model}-{renk kodu}`. Pazaryerinde ürünün sabit anahtarı olarak kullanılmalı. |
| `unit_price` | Adet fiyatı, USD. |
| `pack_price` | Seri fiyatı (adet fiyatı × serideki adet), USD. |
| `packs_in_stock` | **Satılabilir seri sayısı.** Beden stoklarından tamamlanabilen tam seri kadardır. `0` tükendi demektir. |
| `images` | Yalnızca bu renge ait görseller, sıralı (en fazla 10). |
| `variant@stock` | Beden bazlı ham stok, bilgi amaçlı. Satış `packs_in_stock` üzerinden yapılmalı. |
| `variant@barcode` | Bedenin barkodu (Nebim). |

**Pazaryerinde uyulması gereken kurallar**
1. Sipariş birimi seridir. Tek beden satılmaz; adet seri katı olmalıdır.
2. Stok `packs_in_stock` alanından okunur.
3. Fiyat USD gelir; TL'ye çevrim pazaryeri tarafında yapılır.
4. Feed'de artık bulunmayan bir `color@id` satıştan kaldırılmalıdır. Model pasife alındıysa ya da rengin görseli yoksa o renk feed'e girmez.

---

## Kurulum

### 1. Shopify'da API erişimi (Dev Dashboard uygulaması)
Shopify admin'den yeni "custom app" artık oluşturulamıyor. Yeni uygulamalar Dev Dashboard'dan açılıyor.

1. https://dev.shopify.com adresinde yeni bir uygulama oluşturun (ör. "BSL Feed").
2. Uygulamanın sürümünde şu erişim kapsamlarını seçip sürümü yayınlayın: `read_products`, `read_inventory`, `read_translations`.
3. Uygulamayı bsl-wholesale mağazasına kurun.
4. Uygulama ayarlarından **Client ID** ve **Client secret** değerlerini alın.

Script bu ikisiyle her çalışmada 24 saatlik bir token alır (client credentials grant). Bu yöntem, uygulama ile mağaza Dev Dashboard'da **aynı organizasyon** altındaysa çalışır. `shop_not_permitted` hatası alırsanız ikisi farklı organizasyondadır.

Elinizde eski tip bir admin custom app token'ı (`shpat_…`) varsa, Client ID ve secret yerine onu `SHOPIFY_ACCESS_TOKEN` olarak da verebilirsiniz.

### 2. GitHub
1. **Public** bir repo açın (ör. `bsl-feeds`). Ücretsiz GitHub Pages için repo public olmalı. Repoda hiçbir gizli bilgi yok; anahtarlar Secrets'ta durur.
2. Bu klasördeki dosyaları repoya yükleyin.
   - `.github/workflows/yakemall-feed.yml` gizli klasörde olduğu için web arayüzünden sürükle-bırak bazen almaz.
   - O durumda "Add file → Create new file" ile bu yolu yazıp içeriği yapıştırın.
3. **Settings → Secrets and variables → Actions**:
   - Secrets: `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`
   - Variables (isteğe bağlı): `SHOPIFY_SHOP` = `0kym5e-we.myshopify.com` (bu zaten varsayılan)
4. **Actions → Yakemall feed → Run workflow** ile ilk çalıştırmayı yapın. Çalışmanın özet sayfasında feed raporu görünür.
5. **Settings → Pages** altında "Deploy from a branch" seçin, ardından `main` ve `/docs` klasörünü seçin.
6. Birkaç dakika sonra feed `https://<kullanıcı>.github.io/bsl-feeds/yakemall.xml` adresinde yayında olur. Bu adresi Yakemall'a iletin.

---

## Ayarlar (Actions → Variables veya ortam değişkeni)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SHOPIFY_SHOP` | `0kym5e-we.myshopify.com` | Mağazanın myshopify adresi |
| `SHOPIFY_API_VERSION` | `2026-10` | Admin API sürümü. Yılda bir güncellenmeli. |
| `PRODUCT_QUERY` | `status:active` | Feed'e girecek ürünlerin Shopify arama filtresi |
| `INCLUDE_ZERO_STOCK` | `1` | Stoğu biten renkler `packs_in_stock=0` ile feed'de kalsın mı? Kalırsa pazaryeri onları tükendi olarak gösterir. |
| `INCLUDE_TR` | `1` | Türkçe başlık ve ürün tipi eklensin mi? `read_translations` kapsamı gerekir. |
| `MAX_IMAGES` | `10` | Renk başına en fazla görsel |
| `SHRINK_GUARD` | `0.5` | Model sayısı önceki feed'in %50'sinin altına düşerse feed **yazılmaz**, iş hata verir. |

## Güvenlik ve izleme
- **Düşüş koruması:** API hatası ya da yanlış bir filtre yüzünden feed boşalırsa pazaryerindeki bütün ürünler kapanabilir. Bu yüzden ani düşüşte eski feed yerinde kalır. Bilinçli bir düşüşte script'i elle `--force` ile çalıştırın.
- **Uyarılar:** Başarısız çalışmalarda GitHub e-posta gönderir.
- **Rapor:** Her çalışmanın özet sayfasında şunlar listelenir:
  - stokta olduğu halde görseli olmayan renkler (bunlar feed'e girmez),
  - seri tanımı eksik modeller,
  - Türkçe başlığı olmayan modeller.
- **60 gün kuralı:** GitHub, 60 gün hiç etkinlik olmayan public repolarda zamanlanmış işleri durdurur. Feed stok değiştikçe commit attığı için normalde sorun olmaz. Durursa Actions sekmesinden tek tıkla yeniden açılır.
- **Feed herkese açık:** Feed adresi USD fiyat ve stok içerir ve herkese açıktır. Shopify'ın `/products/<handle>.js` adresleri fiyatı zaten herkese döndürdüğü için bu yeni bir açık yaratmaz.

## Yerel deneme
```bash
python tests/test_feed.py tests/ornek_yakemall.xml        # API'siz test
SHOPIFY_CLIENT_ID=… SHOPIFY_CLIENT_SECRET=… python yakemall_feed.py --out yakemall.xml --save-jsonl ham.jsonl
python yakemall_feed.py --from-jsonl ham.jsonl --out yakemall.xml   # kayıtlı veriden tekrar üret
```
