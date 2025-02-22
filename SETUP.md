# Veritabanı Kurulum Kılavuzu

## PostgreSQL Kurulumu (Raspberry Pi)

1. Sistem paketlerini güncelleyin:
```bash
sudo apt update
sudo apt upgrade -y
```

2. PostgreSQL'i kurun:
```bash
sudo apt install postgresql postgresql-contrib -y
```

3. PostgreSQL servisini başlatın:
```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

4. Veritabanı kullanıcısı ve veritabanını oluşturun:
```bash
# PostgreSQL komut satırına geçiş yapın
sudo -u postgres psql

# Veritabanı kullanıcısı oluşturun (şifreyi değiştirin)
CREATE USER postgres WITH PASSWORD 'your_secure_password';

# Veritabanını oluşturun
CREATE DATABASE plaka_tanima_db;

# Kullanıcıya veritabanı yetkilerini verin
GRANT ALL PRIVILEGES ON DATABASE plaka_tanima_db TO postgres;

# PostgreSQL komut satırından çıkın
\q
```

5. PostgreSQL yapılandırmasını düzenleyin:
```bash
sudo nano /etc/postgresql/[version]/main/postgresql.conf
```
Aşağıdaki satırı bulun ve düzenleyin:
```
listen_addresses = '*'
```

6. İstemci kimlik doğrulama yapılandırmasını düzenleyin:
```bash
sudo nano /etc/postgresql/[version]/main/pg_hba.conf
```
Dosyanın sonuna ekleyin:
```
host    all             all             0.0.0.0/0               md5
```

7. PostgreSQL servisini yeniden başlatın:
```bash
sudo systemctl restart postgresql
```

## Uygulama Yapılandırması

1. `.env` dosyasını oluşturun:
```bash
cp .env.example .env
```

2. `.env` dosyasını düzenleyin ve gerekli değerleri girin:
```bash
nano .env
```

3. Python bağımlılıklarını yükleyin:
```bash
pip install -r requirements.txt
```

4. Uygulamayı başlatın:
```bash
python app.py
```

## Bağlantı Testi

Veritabanı bağlantısını test etmek için:
```bash
psql -h localhost -U postgres -d plaka_tanima_db
```

## Güvenlik Notları

1. Güçlü şifreler kullanın
2. Firewall yapılandırmasını kontrol edin
3. Düzenli yedekleme alın
4. Güncellemeleri takip edin

## Hata Ayıklama

1. PostgreSQL loglarını kontrol edin:
```bash
sudo tail -f /var/log/postgresql/postgresql-[version]-main.log
```

2. Servis durumunu kontrol edin:
```bash
sudo systemctl status postgresql
```
