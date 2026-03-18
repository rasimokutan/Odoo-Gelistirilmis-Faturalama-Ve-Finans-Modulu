# Geliştirilmiş Faturalama ve Finans

`enhanced_invoicing_accounting`, Odoo Community Edition üzerinde çalışan ve standart `Invoicing / Accounting` altyapısını daha güçlü bir operasyonel finans katmanına dönüştürmek amacıyla geliştirilmiş özel bir modüldür.

Bu modülün ortaya çıkış nedeni oldukça nettir: Odoo Community Edition kullanan işletmeler temel faturalama süreçlerini yönetebilse de, tam anlamıyla güçlü, günlük operasyonları destekleyen ve karar alma süreçlerine katkı sağlayan bir muhasebe yapısına çoğu zaman doğrudan sahip olamaz. Standart faturalama yapısı; alacak takibi, banka mutabakatı, analitik muhasebe görünürlüğü, bütçe kontrolü, finansal risk analizi ve yönetimsel raporlama gibi alanlarda yetersiz kalabilmektedir.

Bu çalışma, tam da bu eksikliği gidermek için tasarlanmıştır.

Aynı zamanda bu modül; açık kaynak kodlu ERP dünyasında Odoo ekosistemi içinde minimum maliyetle maksimum verim elde etme hedefinin bir parçasıdır. Buradaki amaç yalnızca hazır bir sistemi kullanmak değil, aynı zamanda bu sistemin üzerine yeni modüller geliştirerek sürdürülebilir, esnek ve yerel ihtiyaçlara cevap verebilen bir yapı kurmaktır. Bu bakış açısı, bitirme tezi kapsamında ele alınmış; hem teknik hem işlevsel hem de geliştirilebilir bir temel oluşturulmaya çalışılmıştır.

## Bu Modül Neden Geliştirildi?

Odoo Community Edition, lisans maliyeti açısından son derece avantajlı bir çözümdür. Ancak özellikle finans ve muhasebe operasyonları derinleştikçe, standart yapı birçok işletme için tek başına yeterli olmamaktadır.

Özellikle şu alanlarda ek geliştirme ihtiyacı doğmaktadır:

- müşteri ve tedarikçi finans durumunu tek ekranda izleme
- gecikmiş alacakların sistematik takibi
- yarı otomatik veya manuel banka mutabakatı
- bütçe ile gerçekleşen verinin karşılaştırılması
- analitik muhasebe verisinin daha görünür hale getirilmesi
- yöneticiler için tek noktadan finansal özet ekranı oluşturulması
- Community Edition kullanan yapılarda muhasebe süreçlerinin daha kontrollü yürütülmesi

Bu modül, tam olarak bu ihtiyaçlara cevap vermek üzere geliştirilmiştir.

## Projenin Temel Yaklaşımı

Bu çalışma boyunca Odoo çekirdek dosyaları doğrudan değiştirilmemiştir. Tüm geliştirmeler `inherit`, yeni model tanımları, wizard yapıları, SQL rapor görünümleri, menu/action/view genişletmeleri ve güvenlik katmanları ile hayata geçirilmiştir.

Temel hedefler şunlardır:

- Odoo Community Edition ile uyumlu kalmak
- `account` modülünü bozmadan genişletmek
- temiz, modüler ve sürdürülebilir bir yapı kurmak
- çok şirketli ve çoklu para birimi senaryolarını dikkate almak
- sonradan yeni modüller geliştirilebilecek sağlam bir temel oluşturmak

## Modülün Sağladığı Başlıca Özellikler

### 1. Cari Finans Özeti

Müşteri ve tedarikçi kartlarına finans özeti eklenmiştir.

Bu özet içinde şu bilgiler yer alır:

- toplam alacak
- toplam borç
- gecikmiş bakiye
- gecikmiş fatura sayısı
- yaşlandırma dilimleri
  - 0-30 gün
  - 31-60 gün
  - 61-90 gün
  - 90+ gün
- zamanında ödeme oranı
- risk puanı
- risk seviyesi

Risk seviyesi hesaplanırken şu veriler dikkate alınır:

- geciken fatura sayısı
- toplam gecikmiş tutar
- geçmiş ödeme performansı

### 2. Alacak Takibi ve Follow-up Sistemi

Vadesi geçmiş müşteri faturalarını sistematik biçimde takip edebilmek için özel bir follow-up yapısı geliştirilmiştir.

Özellikler:

- cron ile otomatik gecikmiş fatura taraması
- 1. hatırlatma
- 2. hatırlatma
- son uyarı
- her takip için log kaydı
- manuel takip sihirbazı
- cari bazında takip geçmişi

Bu yapı şu an log temelli çalışır. Gerçek e-posta gönderimi zorunlu değildir; ancak ileride mail entegrasyonuna uygun altyapı hazırlanmıştır.

### 3. Basit ve İşlevsel Banka Mutabakatı

Community Edition tarafında operasyonel banka mutabakatı ihtiyacını karşılamak için özel bir mutabakat modeli geliştirilmiştir.

Özellikler:

- banka hareketleri için özel mutabakat kaydı
- satır bazlı banka hareket yönetimi
- CSV içe aktarma sihirbazı
- otomatik öneri mantığı
  - referans eşleşmesi
  - cari eşleşmesi
  - tutar eşleşmesi
- manuel eşleştirme
- eşleştirmeyi kaldırma
- durum yönetimi
  - taslak
  - önerilen
  - eşleşti
  - istisna

### 4. Analitik Muhasebe Görünürlüğü

Standart yapıdaki analitik dağılım bilgisinin daha anlaşılır ve daha kullanışlı görünmesi hedeflenmiştir.

Özellikler:

- fatura satırlarında analitik dağılım görünürlüğü
- birincil analitik hesap özeti
- analitik özet raporu
- pivot ve grafik görünümleri
- cari, ürün, hesap ve günlük bazında analiz

### 5. Bütçe Yönetimi

Basit fakat geliştirilebilir bir bütçe yönetim yapısı tasarlanmıştır.

Özellikler:

- bütçe ana kaydı
- bütçe satırları
- analitik hesap bazlı planlama
- hesap bazlı planlama
- planlanan ve gerçekleşen tutarın karşılaştırılması
- gerçekleşme oranı
- bütçe aşımı uyarısı
- durum yönetimi
  - taslak
  - onaylı
  - kapalı

### 6. Finans Panosu

Yönetsel görünürlük sağlamak için tek ekranlı bir finans panosu hazırlanmıştır.

Bu panoda özet olarak izlenebilen bilgiler:

- toplam alacak
- toplam borç
- gecikmiş alacak
- gecikmiş borç
- taslak faturalar
- açık müşteri faturası sayısı
- açık tedarikçi faturası sayısı
- eşleşen banka satırları
- eşleşmeyen banka satırları

### 7. Gelişmiş Finansal Raporlar

Community Edition altyapısını desteklemek üzere birden fazla SQL view tabanlı özel rapor hazırlanmıştır.

Raporlar:

- Cari Yaşlandırma Raporu
- Gecikmiş Fatura Raporu
- Bütçe Performans Raporu
- Banka Mutabakat Durum Raporu
- Analitik Özet Raporu

Hazır görünümler:

- liste
- arama
- pivot
- grafik

### 8. Finansal Kontroller

Belge ve operasyon seviyesinde ilave kontroller eklenmiştir.

Örnekler:

- fatura post edilirken vade tarihi kontrolü
- yüksek riskli cari için uyarı
- negatif toplam tutar kontrolü
- tedarikçi belge referans tekrar kontrolü
- yüksek gecikmiş bakiye uyarısı
- bütçe aşımı uyarısı
- yüksek tutarlı eşleşmemiş banka hareketleri için istisna işareti

## Teknik Yapı

Modül aşağıdaki temel bileşenlerden oluşur:

- `models/`
  - partner finans özeti
  - fatura kontrolleri
  - banka mutabakatı
  - bütçe
  - takip logları
  - finans panosu
  - SQL rapor modelleri
- `wizard/`
  - banka CSV içe aktarma
  - manuel takip
  - rapor filtreleme
- `views/`
  - form, liste, arama, pivot ve grafik görünümleri
- `security/`
  - grup tanımları
  - erişim hakları
  - kayıt kuralları
- `data/`
  - cron
  - sequence
  - mail template
- `report/`
  - PDF rapor çıktısı
- `demo/`
  - temel deneme verileri

## Odoo Community İçin Katkısı

Bu modülün en önemli katkısı, Odoo Community Edition kullanan bir yapının yalnızca “fatura kesen” bir uygulama olmaktan çıkmasına yardımcı olmasıdır.

Bu sayede kullanıcı:

- lisans maliyetini artırmadan finans operasyonlarını güçlendirebilir
- kendi ihtiyaçlarına uygun yeni modüller geliştirebilir
- ERP sistemini kendi süreçlerine göre genişletebilir
- Community Edition ile daha profesyonel bir finans iş akışına yaklaşabilir

Bu açıdan modül yalnızca teknik bir geliştirme değil; aynı zamanda maliyet/verim dengesi odaklı bir yaklaşımın ürünüdür.

## Bitirme Tezi Kapsamı

Bu modül, bitirme tezi kapsamında ele alınmış bir geliştirme çalışmasının sonucudur.

Tez perspektifinde temel amaç şu şekilde özetlenebilir:

- açık kaynak kodlu ERP çözümlerinin gerçek hayatta ne kadar geliştirilebilir olduğunu göstermek
- Odoo Community Edition gibi düşük maliyetli bir platformu daha verimli hale getirmek
- hazır sistemleri sadece kullanmak yerine, onların üzerinde yeni modüller geliştirerek özgün bir ekosistem kurmak
- yerel ihtiyaçlara uygun, sürdürülebilir ve genişleyebilir bir finans altyapısı ortaya koymak

Bu nedenle proje yalnızca bir yazılım eklentisi değil; aynı zamanda açık kaynak ERP mimarisinin geliştirilebilirliğini gösteren uygulamalı bir akademik çalışmadır.

## Kurulum

1. Modül klasörünü `custom_addons` altına yerleştirin.
2. Odoo `addons_path` içinde bu dizinin tanımlı olduğundan emin olun.
3. Uygulama listesini güncelleyin.
4. `Geliştirilmiş Faturalama ve Finans` modülünü yükleyin veya mevcutsa yükseltin.

## Önerilen Kontroller

Kurulumdan sonra şu adımlarla doğrulama yapabilirsiniz:

1. Üst menüde `Geliştirilmiş Finans` veya `Gelişmiş Finans` menüsünün görünüp görünmediğini kontrol edin.
2. Bir cari kartında `Finans Özeti` sekmesinin açıldığını doğrulayın.
3. Bir müşteri faturasında `Gelişmiş Finans` sekmesinin geldiğini kontrol edin.
4. `Takipler` menüsü altında manuel takip oluşturmayı deneyin.
5. `Banka Mutabakatı` altında CSV içe aktarma akışını test edin.
6. `Bütçeler` ekranında bütçe oluşturup satır ekleyin.
7. Finansal raporlarda pivot ve grafik görünümlerini kontrol edin.

## Geliştirme Notu

Bu modül, sonradan genişletilmeye uygun bir temel olacak şekilde kurgulanmıştır. Aşağıdaki alanlar ileride daha da geliştirilebilir:

- gerçek e-posta gönderim entegrasyonu
- daha gelişmiş banka eşleştirme algoritmaları
- tahsilat workflow’ları
- otomatik risk politikası kuralları
- daha kapsamlı dashboard görselleştirmeleri
- yerel muhasebe mevzuatına göre ilave kontroller

## Lisans

Bu modül, Odoo ekosistemi ile uyumlu şekilde `LGPL-3` lisansı ile dağıtılacak biçimde tasarlanmıştır.
