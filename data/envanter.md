# ODTÜ Mevzuat Doküman Envanteri (Faz 0 / Gün 4)

Bu veri seti, RAG boru hattının doküman parçalama (chunking), gömme (embedding), hibrit arama ve yetki-farkında (ACL) erişim testlerinde kullanılmak üzere ODTÜ resmi mevzuat havuzundan derlenmiştir.

| Doküman Adı | Format | Sayfa | Kapsam / Rol | Açıklama |
| :--- | :--- | :--- | :--- | :--- |
| `lisans_yonetmeligi.pdf` | PDF | 20 | Öğrenci (Lisans), Akademik | Kayıt, ders yükü, sınavlar, başarı koşulları, intibak |
| `lisansustu_yonetmeligi.pdf` | PDF | 40 | Öğrenci (Lisansüstü), Tez Danışmanı | Yüksek lisans, doktora, tez jürileri, azami süreler |
| `yurtlar_yonetmeligi.pdf` | PDF | 9 | Yurt Sakini, İdari Personel | Yurt başvuruları, disiplin kuralları, barınma şartları |
| `cap_yonergesi.pdf` | PDF | 14 | Öğrenci (Lisans), ÇAP Koordinatörlüğü | Çift Anadal başvuru şartları, kontenjanlar, mezuniyet |

## Notlar
- **Hiyerarşik Yapı:** Belgelerin tamamı Madde, Fıkra ve Bent formatındadır; başlık ve madde bazlı yapısal parçalama için uygundur.
- **Yetkilendirme (ACL) Uygunluğu:** Lisans ve Lisansüstü rolleri arasındaki bilgi sınırlarının test edilmesine olanak tanır.
- **Gizlilik:** Kamuya açık resmi mevzuat olduğundan veri gizliliği riski taşımamaktadır.