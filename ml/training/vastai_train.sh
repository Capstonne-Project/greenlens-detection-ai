#!/bin/bash
# ================================================================
# GreenLens YOLO Training Script — Vast.ai
# Chay: bash vastai_train.sh
# ================================================================
set -e

DATASET_ZIP="dataset.zip"       # Ten file zip ban upload len
EPOCHS=100
BATCH=16
IMGSZ=640
MODEL_BASE="yolov8n.pt"         # Hoac duong dan best.pt cu neu muon fine-tune
RUN_NAME="greenlens_v2"

echo "=== [1/5] Cai dat thu vien ==="
pip install ultralytics --quiet

echo "=== [2/5] Giai nen dataset ==="
unzip -q "$DATASET_ZIP" -d dataset/
ls dataset/

echo "=== [3/5] Tao data.yaml ==="
DATASET_ABS=$(realpath dataset)
cat > data.yaml <<EOF
path: ${DATASET_ABS}
train: images/train
val: images/val
names:
  0: TRASH
  1: WATER
  2: SMOKE
  3: CHEMICAL
EOF
echo "data.yaml:"
cat data.yaml

echo "=== [4/5] Download base weights ==="
# Neu muon fine-tune tu best.pt cu, upload file do len va sua MODEL_BASE
# Neu train tu dau dung yolov8n.pt (tu dong download)
echo "Using base model: $MODEL_BASE"

echo "=== [5/5] Bat dau train ==="
yolo detect train \
  data=data.yaml \
  model=$MODEL_BASE \
  epochs=$EPOCHS \
  batch=$BATCH \
  imgsz=$IMGSZ \
  name=$RUN_NAME \
  project=runs \
  patience=20 \
  save=True \
  workers=4 \
  amp=True

echo ""
echo "================================================"
echo "DONE! best.pt tai:"
echo "  runs/${RUN_NAME}/weights/best.pt"
echo ""
echo "Download ve may local:"
echo "  (dung Vast.ai file browser hoac scp)"
echo "================================================"
