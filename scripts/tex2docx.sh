#!/bin/bash
# Скрипт конвертации LaTeX → DOCX через pandoc
# Создаёт расплющенный .tex, обрабатывает tikz/pgfplots, конвертирует
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
OUTPUT_DOCX="$BUILD_DIR/main.docx"
FLAT_TEX="$BUILD_DIR/flat_main.tex"

echo "=== LaTeX → DOCX конвертация ==="
echo "Проект: $PROJECT_DIR"

# Убедимся что build существует
mkdir -p "$BUILD_DIR"

# Шаг 1: Расплющивание всех \input в один файл
echo "[1/4] Расплющивание \input..."
python3 "$SCRIPTS_DIR/flatten_tex.py" "$PROJECT_DIR/main.tex" "$FLAT_TEX" "$PROJECT_DIR"

# Шаг 2: Предобработка — убрать tikz, pgfplots, несовместимые команды
echo "[2/4] Предобработка для pandoc..."
python3 "$SCRIPTS_DIR/preprocess_for_pandoc.py" "$FLAT_TEX" "$BUILD_DIR/pandoc_ready.tex"

# Шаг 3: Конвертация pandoc
echo "[3/4] Конвертация pandoc..."
cd "$PROJECT_DIR"
pandoc "$BUILD_DIR/pandoc_ready.tex" \
    -f latex \
    -t docx \
    --resource-path="$BUILD_DIR:$PROJECT_DIR" \
    -o "$OUTPUT_DOCX" \
    2>&1 || true

# Шаг 4: Проверка
if [ -f "$OUTPUT_DOCX" ]; then
    SIZE=$(ls -lh "$OUTPUT_DOCX" | awk '{print $5}')
    echo ""
    echo "✓ Готово! DOCX: $OUTPUT_DOCX"
    echo "  Размер: $SIZE"
else
    echo "✗ Ошибка: DOCX не создан"
    exit 1
fi
