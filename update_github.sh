#!/bin/bash

# Configure git credentials
git config --global user.email "plaka.tanima@example.com"
git config --global user.name "Plaka Tanima Sistemi"

# Configure GitHub token-based authentication
git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"

echo "GitHub'a değişiklikler gönderiliyor..."

# Add all changes
git add .

# Create commit with current date
git commit -m "Manuel güncelleme: $(date)"

# Push changes to GitHub
if git push origin main; then
    echo "Değişiklikler başarıyla GitHub'a gönderildi"
else
    echo "HATA: Değişiklikler gönderilemedi"
fi
