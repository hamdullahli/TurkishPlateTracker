# Plaka Tanıma Sistemi

Bu proje, güvenlik ve erişim yönetimi için gelişmiş plaka tanıma sistemi sağlar.

## Özellikler

- Gerçek zamanlı plaka tanıma
- Web tabanlı yönetim arayüzü
- Rol tabanlı erişim kontrolü
- Yetkili plaka yönetimi
- Plaka geçmiş kaydı
- Kamera ayarları ve yönetimi
- GitHub ile otomatik senkronizasyon

## Kurulum

1. PostgreSQL veritabanını kurun ve yapılandırın
2. Gerekli Python paketlerini yükleyin
3. `.env` dosyasını oluşturun ve yapılandırın
4. Uygulamayı başlatın

## Kullanım

1. Tarayıcıdan web arayüzüne erişin
2. Admin hesabıyla giriş yapın
3. Yetkili plakaları ve kamera ayarlarını yapılandırın
4. Sistemi izlemeye başlayın

## Test

Sistemin doğru çalıştığından emin olmak için:
1. Test video ile plaka tanıma sistemini test edin
2. Yetkili ve yetkisiz plakalarla erişim kontrolünü test edin
3. Kamera bağlantılarını test edin

## Güncelleme

Projeyi GitHub'da güncellemek için:
1. `.env` dosyasına GitHub token ekleyin
2. Değişiklikleri yapın
3. `./update_github.sh` scriptini çalıştırın

## Sistem Gereksinimleri

- Python 3.9+
- PostgreSQL
- OpenCV
- EasyOCR
- Flask