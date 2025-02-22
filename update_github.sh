#!/bin/bash

# Hata durumunda betiği durdur
set -e

# Git yapılandırmasını ayarla
git config --global user.email "plaka.tanima@example.com"
git config --global user.name "Plaka Tanima Sistemi"

echo "GitHub'a değişiklikler gönderiliyor..."

# Değişiklikleri zorla ekle
git add -A

# Değişiklik var mı kontrol et
if git diff --cached --quiet; then
    echo "⚠️ Hiç değişiklik yok. Önce bazı değişiklikler yapın."
    exit 0
fi

# Tarih ile commit oluştur
git commit -m "Manuel güncelleme: $(date)"

# GitHub token kullanarak değişiklikleri gönder
if git push https://${GITHUB_TOKEN}@github.com/$(git config --get remote.origin.url | sed 's/https:\/\/github.com\///g'); then
    echo "✅ Değişiklikler başarıyla GitHub'a gönderildi"
else
    echo "❌ HATA: Değişiklikler gönderilemedi"
    echo "Lütfen aşağıdakileri kontrol edin:"
    echo "1. GITHUB_TOKEN doğru ayarlandı mı?"
    echo "2. Repository'e yazma izniniz var mı?"
    echo "3. Internet bağlantınız aktif mi?"
    exit 1
fi