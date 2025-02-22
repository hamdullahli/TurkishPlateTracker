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
sudo apt-get install -y curl unzip wget

# Python paketlerini yükle
echo "Python paketleri yükleniyor..."
pip3 install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime
pip3 install easyocr
pip3 install requests
pip3 install python-dotenv
pip3 install numpy
pip3 install pillow

# Model dizinini oluştur
echo "Model dizini oluşturuluyor..."
mkdir -p model

# TPU modellerini indir
echo "TPU modelleri indiriliyor..."

# Object Detection modeli (araçları tespit etmek için)
wget -O model/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite \
  https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite

# Model dosyalarının varlığını kontrol et
if [ ! -f "model/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite" ]; then
    echo "Model indirilemedi! Lütfen bağlantınızı kontrol edin."
    exit 1
fi

echo "Kurulum tamamlandı!"
echo "Model dosyaları:"
ls -l model/