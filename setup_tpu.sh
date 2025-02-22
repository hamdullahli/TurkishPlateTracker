#!/bin/bash

# TPU kurulum betiği
echo "Google Coral TPU kurulumu başlatılıyor..."

# Gerekli paketleri yükle
echo "Sistem paketleri yükleniyor..."
sudo apt-get update
sudo apt-get install -y python3-pip
sudo apt-get install -y python3-opencv
sudo apt-get install -y libedgetpu1-std
sudo apt-get install -y python3-pycoral

# Python paketlerini yükle
echo "Python paketleri yükleniyor..."
pip3 install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime
pip3 install easyocr
pip3 install requests
pip3 install python-dotenv

# Model dizinini oluştur
echo "Model dizini oluşturuluyor..."
mkdir -p model

# TPU modelini indir
echo "TPU modeli indiriliyor..."
# Not: Burada gerçek model URL'sini ekleyin
# wget -O model/plate_detect_edgetpu.tflite YOUR_MODEL_URL

echo "Kurulum tamamlandı!"
echo "Lütfen plate_detect_edgetpu.tflite modelini model/ dizinine yerleştirin."
