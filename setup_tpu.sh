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
sudo apt-get install -y curl unzip

# Python paketlerini yükle
echo "Python paketleri yükleniyor..."
pip3 install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime
pip3 install easyocr
pip3 install requests
pip3 install python-dotenv
pip3 install numpy

# Model dizinini oluştur
echo "Model dizini oluşturuluyor..."
mkdir -p model

# TPU modelini indir
echo "TPU modeli indiriliyor..."
MODEL_URL="https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
curl -L ${MODEL_URL} -o model/plate_detect_edgetpu.tflite

# İndirilen modelin varlığını kontrol et
if [ -f "model/plate_detect_edgetpu.tflite" ]; then
    echo "Model başarıyla indirildi!"
else
    echo "Model indirilemedi! Lütfen bağlantınızı kontrol edin."
    exit 1
fi

echo "Kurulum tamamlandı!"
echo "TPU modeli: model/plate_detect_edgetpu.tflite"