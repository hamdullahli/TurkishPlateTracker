#!/bin/bash

# Configure git credentials
git config --global user.email "plaka.tanima@example.com"
git config --global user.name "Plaka Tanima Sistemi"

# Configure GitHub token-based authentication
git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"

while true; do
    # Check for changes
    git add .
    git status | grep "Changes to be committed" > /dev/null

    if [ $? -eq 0 ]; then
        echo "Değişiklikler tespit edildi, commit ve push yapılıyor..."
        git commit -m "Otomatik güncelleme: $(date)"

        # Try to push changes
        if git push origin main; then
            echo "Değişiklikler başarıyla gönderildi"
        else
            echo "HATA: Değişiklikler gönderilemedi"
        fi
    else
        echo "Değişiklik tespit edilmedi"
    fi

    # Wait for 5 minutes before next check
    sleep 300
done