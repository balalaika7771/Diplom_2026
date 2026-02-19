#!/usr/bin/env python3
r"""
Предобработка расплющённого LaTeX для pandoc:
- Удаляет/заменяет пакеты и команды, несовместимые с pandoc
- Заменяет tikzpicture/pgfplots/circuitikz на текстовые плейсхолдеры
- Сохраняет формулы, таблицы, текст
"""
import re
import sys

def preprocess(content):
    # ===== 1. Удаляем преамбулу до \begin{document} и конец =====
    # Но сохраняем тело документа
    doc_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', content, re.DOTALL)
    if doc_match:
        body = doc_match.group(1)
    else:
        # Если нет \begin{document}, берём всё
        body = content

    # ===== 2. Убираем команды, которые pandoc не понимает =====

    # Удаляем \thispagestyle{...}
    body = re.sub(r'\\thispagestyle\{[^}]*\}', '', body)

    # Удаляем \setcounter{...}{...}
    body = re.sub(r'\\setcounter\{[^}]*\}\{[^}]*\}', '', body)

    # Удаляем \let\oldchapter... и \let\chapter...
    body = re.sub(r'\\let\\oldchapter\\chapter', '', body)
    body = re.sub(r'\\let\\chapter\\oldchapter', '', body)

    # Удаляем \renewcommand{\chapter}[1]{\section{#1}}
    body = re.sub(r'\\renewcommand\{\\chapter\}\[1\]\{\\section\{#1\}\}', '', body)

    # Удаляем \tableofcontents и \newpage
    body = re.sub(r'\\tableofcontents', '', body)

    # Удаляем \addcontentsline
    body = re.sub(r'\\addcontentsline\{[^}]*\}\{[^}]*\}\{[^}]*\}', '', body)

    # Удаляем \printbibliography[...]
    body = re.sub(r'\\printbibliography\[[^\]]*\]', '', body)
    body = re.sub(r'\\printbibliography', '', body)

    # Удаляем \appendix
    body = re.sub(r'\\appendix\b', '', body)

    # Удаляем \medskip, \bigskip, \smallskip
    body = re.sub(r'\\(?:medskip|bigskip|smallskip)\b', '', body)

    # Удаляем \newpage
    body = re.sub(r'\\newpage\b', '', body)

    # ===== 3. Заменяем tikzpicture, pgfplots, circuitikz на плейсхолдеры =====

    figure_counter = [0]

    def replace_figure_env(match):
        """Заменяет figure environments содержащие tikz на плейсхолдер."""
        figure_content = match.group(0)

        # Ищем caption
        caption_match = re.search(r'\\caption\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', figure_content)
        caption = caption_match.group(1) if caption_match else "Рисунок"

        # Ищем label
        label_match = re.search(r'\\label\{([^}]+)\}', figure_content)
        label = label_match.group(1) if label_match else ""

        # Проверяем есть ли tikz/pgf/circuitikz внутри
        has_tikz = bool(re.search(r'\\begin\{(?:tikzpicture|circuitikz)\}', figure_content))
        has_pgf = bool(re.search(r'\\begin\{axis\}', figure_content))

        if has_tikz or has_pgf:
            figure_counter[0] += 1
            label_str = f"\\label{{{label}}}" if label else ""
            # Возвращаем текстовый плейсхолдер в рамке
            return (
                f"\\begin{{center}}\n"
                f"\\fbox{{[Рисунок — см. PDF версию]}}\n\n"
                f"Рисунок {figure_counter[0]} — {caption} {label_str}\n"
                f"\\end{{center}}\n"
            )
        else:
            # Оставляем figure as-is (может содержать \includegraphics)
            return figure_content

    # Заменяем figure environments с tikz
    body = re.sub(
        r'\\begin\{figure\}\[H?\].*?\\end\{figure\}',
        replace_figure_env,
        body,
        flags=re.DOTALL
    )

    # Оставшиеся standalone tikzpicture (без figure)
    def replace_standalone_tikz(match):
        figure_counter[0] += 1
        return f"\n\\begin{{center}}\n\\fbox{{[Схема — см. PDF версию]}}\n\\end{{center}}\n"

    body = re.sub(
        r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',
        replace_standalone_tikz,
        body,
        flags=re.DOTALL
    )

    body = re.sub(
        r'\\begin\{circuitikz\}.*?\\end\{circuitikz\}',
        replace_standalone_tikz,
        body,
        flags=re.DOTALL
    )

    # ===== 4. Обработка \\cite =====
    # Pandoc не знает biblatex — заменяем \cite{key} на [N]
    cite_counter = [0]
    cite_map = {}

    def replace_cite(match):
        keys = match.group(1).split(',')
        nums = []
        for key in keys:
            key = key.strip()
            if key not in cite_map:
                cite_counter[0] += 1
                cite_map[key] = cite_counter[0]
            nums.append(str(cite_map[key]))
        return f"[{', '.join(nums)}]"

    body = re.sub(r'\\cite\{([^}]+)\}', replace_cite, body)

    # ===== 5. Обработка алгоритмов =====
    # \begin{algorithm}...\end{algorithm} — оставляем, pandoc может обрабатывать
    # Но algorithmic внутри может ломаться — заменяем на lstlisting-подобный вид

    def replace_algorithm(match):
        algo_content = match.group(0)
        caption_match = re.search(r'\\caption\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', algo_content)
        caption = caption_match.group(1) if caption_match else "Алгоритм"
        # Извлекаем тело algorithmic
        algo_body_match = re.search(r'\\begin\{algorithmic\}(.*?)\\end\{algorithmic\}', algo_content, re.DOTALL)
        if algo_body_match:
            algo_body = algo_body_match.group(1)
            # Упрощаем команды
            algo_body = re.sub(r'\\STATE\s*', '  ', algo_body)
            algo_body = re.sub(r'\\IF\{([^}]+)\}', r'  IF \1 THEN', algo_body)
            algo_body = re.sub(r'\\ELSE', '  ELSE', algo_body)
            algo_body = re.sub(r'\\ENDIF', '  ENDIF', algo_body)
            algo_body = re.sub(r'\\FOR\{([^}]+)\}', r'  FOR \1 DO', algo_body)
            algo_body = re.sub(r'\\ENDFOR', '  ENDFOR', algo_body)
            algo_body = re.sub(r'\\WHILE\{([^}]+)\}', r'  WHILE \1 DO', algo_body)
            algo_body = re.sub(r'\\ENDWHILE', '  ENDWHILE', algo_body)
            algo_body = re.sub(r'\\RETURN\s*', '  RETURN ', algo_body)
            algo_body = re.sub(r'\\REQUIRE\s*', 'Вход: ', algo_body)
            algo_body = re.sub(r'\\ENSURE\s*', 'Выход: ', algo_body)
            return (
                f"\n\\textbf{{{caption}}}\n\n"
                f"\\begin{{verbatim}}\n{algo_body}\n\\end{{verbatim}}\n"
            )
        return algo_content

    body = re.sub(
        r'\\begin\{algorithm\}.*?\\end\{algorithm\}',
        replace_algorithm,
        body,
        flags=re.DOTALL
    )

    # ===== 6. Обработка listings / CodeBlock =====
    # CodeBlock — кастомное окружение, pandoc не знает
    # Заменяем на lstlisting
    body = re.sub(r'\\begin\{CodeBlock\}\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}',
                  r'\\begin{verbatim}', body)
    body = re.sub(r'\\end\{CodeBlock\}', r'\\end{verbatim}', body)

    # ===== 7. Убираем \small, \normalsize и прочие размерные =====
    body = re.sub(r'\\(?:small|footnotesize|scriptsize|tiny|normalsize|large|Large|LARGE|huge|Huge)\b', '', body)

    # ===== 8. Убираем \centering =====
    body = re.sub(r'\\centering\b', '', body)

    # ===== 9. Удаляем \fbox если pandoc не понимает =====
    # Оставляем — pandoc может обработать

    # ===== 10. Заменяем \textbf{Этап...} на жирный текст =====
    # pandoc обрабатывает \textbf, оставляем

    # ===== 11. Убираем \label{...} и \notag из math environments =====
    # pandoc не понимает \label внутри equation/align — удаляем их

    def clean_math_env(match):
        full = match.group(0)
        begin_tag = match.group(1)
        env_body = match.group(2)
        end_tag = match.group(3)
        # Убираем \label{...}
        env_body = re.sub(r'\\label\{[^}]+\}\s*', '', env_body)
        # Убираем \notag
        env_body = re.sub(r'\\notag\b', '', env_body)
        return begin_tag + env_body + end_tag

    # Обрабатываем все math environments
    math_envs = '|'.join(['equation', r'equation\*', 'align', r'align\*',
                          'gather', r'gather\*', 'multline', r'multline\*',
                          'flalign', r'flalign\*', 'alignat', r'alignat\*'])
    body = re.sub(
        r'(\\begin\{(?:' + math_envs + r')\})'
        r'(.*?)'
        r'(\\end\{(?:' + math_envs + r')\})',
        clean_math_env,
        body,
        flags=re.DOTALL
    )

    # ===== 12. Заменяем --- на em-dash =====
    body = body.replace('---', '—')
    body = body.replace('--', '–')

    # ===== 14. Заменяем \ref{...} на текстовые заглушки =====
    # В DOCX кросс-ссылки не работают — заменяем на "N"
    body = re.sub(r'\\ref\{[^}]+\}', 'N', body)
    body = re.sub(r'\\eqref\{[^}]+\}', '(N)', body)
    body = re.sub(r'\\cref\{[^}]+\}', 'N', body)

    # ===== 15. Заменяем \, на пробел (тонкий пробел в формулах не нужно менять — pandoc поймёт) =====
    # Но в тексте \, → маленький пробел
    # \  → обычный пробел (уже работает)

    # ===== 16. Заменяем << >> на кавычки =====
    body = body.replace('<<', '«')
    body = body.replace('>>', '»')

    # ===== 17. Собираем итоговый документ =====
    # Минимальная преамбула для pandoc
    preamble = r"""\documentclass[14pt,a4paper]{extreport}
\usepackage[utf8]{inputenc}
\usepackage[T2A]{fontenc}
\usepackage[english,russian]{babel}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{mathtools}
\usepackage{graphicx}
\usepackage{float}
\usepackage{array}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{verbatim}
\begin{document}
"""
    postamble = "\n\\end{document}\n"

    return preamble + body + postamble


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: preprocess_for_pandoc.py <input.tex> <output.tex>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()

    result = preprocess(content)

    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(result)

    lines = result.count('\n')
    print(f"  Предобработано: {sys.argv[1]} → {sys.argv[2]} ({lines} строк)")
