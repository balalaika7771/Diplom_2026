# Makefile для компиляции LaTeX документа с отдельной папкой build
# Оптимизированная версия с умным копированием и проверкой ошибок

# Основные переменные
MAIN = main
LATEX = pdflatex
BIBTEX = biber
VIEWER = open
BUILD_DIR = build

# Флаги для LaTeX (подавление лишнего вывода, но показываем ошибки)
LATEX_FLAGS = -shell-escape -interaction=nonstopmode -file-line-error -halt-on-error

# Цели по умолчанию
.PHONY: all pdf clean view help quick copy-sources docx

# Зависимости для копирования
SRC_DIRS = src config

# Файлы с главами и приложениями (сканирование папок src)
CHAPTER_TEX := $(wildcard src/chapters/*.tex)
APPENDIX_TEX := $(wildcard src/appendix/*.tex)

# Полная сборка: PDF + DOCX
all: pdf docx

# Компиляция только PDF
pdf: $(BUILD_DIR)/$(MAIN).pdf

# Копирование источников (только если изменились)
copy-sources:
	@mkdir -p $(BUILD_DIR)
	@for dir in $(SRC_DIRS); do \
		if [ -d $$dir ]; then \
			echo "Копирование $$dir/..."; \
			cp -r $$dir $(BUILD_DIR)/ 2>/dev/null || true; \
		fi \
	done

# Генерация списков глав и приложений в build/ после копирования
generate-lists: copy-sources
	@echo "Генерация списков глав и приложений..."
	@mkdir -p $(BUILD_DIR)/src/chapters $(BUILD_DIR)/src/appendix
	@if [ -f src/chapters/chapters_list.tex ]; then \
		echo "Используется существующий файл chapters_list.tex"; \
		cp src/chapters/chapters_list.tex $(BUILD_DIR)/src/chapters/chapters_list.tex; \
	else \
		echo "Генерация chapters_list.tex автоматически..."; \
		echo "% Файл сгенерирован автоматически. Не редактируйте вручную." > $(BUILD_DIR)/src/chapters/chapters_list.tex; \
		for f in $(CHAPTER_TEX); do \
			base=$$(basename $$f .tex); \
			echo "\\inputchapter{$$base}" >> $(BUILD_DIR)/src/chapters/chapters_list.tex; \
		done; \
	fi
	@if [ -f src/appendix/appendix_list.tex ]; then \
		echo "Используется существующий файл appendix_list.tex"; \
		cp src/appendix/appendix_list.tex $(BUILD_DIR)/src/appendix/appendix_list.tex; \
	else \
		echo "Генерация appendix_list.tex автоматически..."; \
		echo "% Файл сгенерирован автоматически. Не редактируйте вручную." > $(BUILD_DIR)/src/appendix/appendix_list.tex; \
		for f in $(APPENDIX_TEX); do \
			base=$$(basename $$f .tex); \
			echo "\\inputappendix{$$base}" >> $(BUILD_DIR)/src/appendix/appendix_list.tex; \
		done; \
	fi

# Первая компиляция LaTeX
$(BUILD_DIR)/$(MAIN).aux: $(MAIN).tex | generate-lists
	@echo "Компиляция документа..."
	@cp $(MAIN).tex $(BUILD_DIR)/
	@cd $(BUILD_DIR) && $(LATEX) $(LATEX_FLAGS) $(MAIN).tex > /dev/null 2>&1 || \
		($(LATEX) $(LATEX_FLAGS) $(MAIN).tex && false)
	@if [ ! -f $(BUILD_DIR)/$(MAIN).aux ]; then \
		echo "Ошибка: не удалось создать $(MAIN).aux"; \
		exit 1; \
	fi

# Обработка библиографии
$(BUILD_DIR)/$(MAIN).bbl: $(BUILD_DIR)/$(MAIN).aux
	@echo "Обработка библиографии..."
	@cd $(BUILD_DIR) && $(BIBTEX) $(MAIN) > /dev/null 2>&1 || \
		($(BIBTEX) $(MAIN) && false)
	@if [ ! -f $(BUILD_DIR)/$(MAIN).bbl ]; then \
		echo "Предупреждение: библиография не обработана, создаю пустой файл"; \
		touch $(BUILD_DIR)/$(MAIN).bbl; \
	fi

# Вторая компиляция для обновления ссылок
$(BUILD_DIR)/$(MAIN).toc: $(BUILD_DIR)/$(MAIN).bbl
	@echo "Обновление ссылок..."
	@cd $(BUILD_DIR) && $(LATEX) $(LATEX_FLAGS) $(MAIN).tex > /dev/null 2>&1 || \
		($(LATEX) $(LATEX_FLAGS) $(MAIN).tex && false)

# Финальная компиляция и создание PDF
$(BUILD_DIR)/$(MAIN).pdf: $(BUILD_DIR)/$(MAIN).toc
	@echo "Финальная компиляция..."
	@cd $(BUILD_DIR) && $(LATEX) $(LATEX_FLAGS) $(MAIN).tex > /dev/null 2>&1 || \
		($(LATEX) $(LATEX_FLAGS) $(MAIN).tex && false)
	@if [ -f $(BUILD_DIR)/$(MAIN).pdf ]; then \
		echo ""; \
		echo "✓ Готово! PDF: $(BUILD_DIR)/$(MAIN).pdf"; \
		ls -lh $(BUILD_DIR)/$(MAIN).pdf | awk '{print "  Размер: " $$5}'; \
	else \
		echo "Ошибка: PDF не создан"; \
		exit 1; \
	fi

# Быстрая компиляция (без библиографии, один проход)
quick: generate-lists
	@echo "Быстрая компиляция (без библиографии)..."
	@cp $(MAIN).tex $(BUILD_DIR)/
	@cd $(BUILD_DIR) && $(LATEX) $(LATEX_FLAGS) $(MAIN).tex > /dev/null 2>&1 || \
		($(LATEX) $(LATEX_FLAGS) $(MAIN).tex && false)
	@if [ -f $(BUILD_DIR)/$(MAIN).pdf ]; then \
		echo "✓ Готово! PDF: $(BUILD_DIR)/$(MAIN).pdf"; \
	else \
		echo "Ошибка: PDF не создан"; \
		exit 1; \
	fi

# Конвертация в DOCX (требует pandoc и python3)
docx: generate-lists
	@echo "Конвертация LaTeX → DOCX..."
	@bash scripts/tex2docx.sh

# Просмотр PDF
view: $(BUILD_DIR)/$(MAIN).pdf
	@$(VIEWER) $(BUILD_DIR)/$(MAIN).pdf

# Очистка временных файлов (удаляем всю папку build)
clean:
	@echo "Очистка временных файлов..."
	@rm -rf $(BUILD_DIR)
	@echo "✓ Готово"

# Полная очистка (включая PDF)
distclean: clean
	@rm -f $(MAIN).pdf
	@echo "✓ Полная очистка завершена"

# Показать ошибки из последней сборки
errors:
	@if [ -f $(BUILD_DIR)/$(MAIN).log ]; then \
		echo "Ошибки из последней сборки:"; \
		grep -E "^!" $(BUILD_DIR)/$(MAIN).log | head -20; \
	else \
		echo "Лог не найден. Запустите сборку сначала."; \
	fi

# Показать предупреждения из последней сборки
warnings:
	@if [ -f $(BUILD_DIR)/$(MAIN).log ]; then \
		echo "Предупреждения из последней сборки:"; \
		grep -E "Warning|warning" $(BUILD_DIR)/$(MAIN).log | head -30; \
	else \
		echo "Лог не найден. Запустите сборку сначала."; \
	fi

# Справка
help:
	@echo "Доступные команды:"
	@echo "  make          - Полная сборка: PDF + DOCX"
	@echo "  make pdf      - Только PDF (3 прохода + библиография)"
	@echo "  make docx     - Только DOCX (LaTeX → pandoc → Word)"
	@echo "  make quick    - Быстрая компиляция PDF (1 проход, без библиографии)"
	@echo "  make view     - Открыть PDF файл"
	@echo "  make clean    - Удалить папку build/ со всеми временными файлами"
	@echo "  make distclean - Удалить все сгенерированные файлы"
	@echo "  make errors   - Показать ошибки из последней сборки"
	@echo "  make warnings - Показать предупреждения из последней сборки"
	@echo "  make help     - Показать эту справку"
	@echo ""
	@echo "Результаты:"
	@echo "  PDF:  $(BUILD_DIR)/$(MAIN).pdf"
	@echo "  DOCX: $(BUILD_DIR)/$(MAIN).docx"
