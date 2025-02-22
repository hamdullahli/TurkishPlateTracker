#!/bin/bash

# Hata durumunda betiği durdur
set -e

# Git yapılandırmasını ayarla
git config --global user.email "plaka.tanima@example.com"
git config --global user.name "Plaka Tanima Sistemi"

echo "GitHub'a değişiklikler gönderiliyor..."

# Tüm değişiklikleri ekle
git add .

# Tarih ile commit oluştur
git commit -m "Manuel güncelleme: $(date)"

# GitHub token kullanarak değişiklikleri gönder
git push https://${GITHUB_TOKEN}@github.com/$(git config --get remote.origin.url | sed 's/https:\/\/github.com\///g')

if [ $? -eq 0 ]; then
    echo "✅ Değişiklikler başarıyla GitHub'a gönderildi"
else
    echo "❌ HATA: Değişiklikler gönderilemedi"
    exit 1
fi