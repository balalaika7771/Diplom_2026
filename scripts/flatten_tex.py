#!/usr/bin/env python3
r"""
Расплющивание LaTeX файла: рекурсивно раскрывает все \input{...} и \inputchapter{...}
"""
import re
import sys
import os

def resolve_path(tex_path, base_dir):
    """Резолвит путь к .tex файлу"""
    # Убираем .tex если уже есть, потом добавляем
    if not tex_path.endswith('.tex'):
        tex_path += '.tex'

    # Пробуем относительно base_dir
    full = os.path.join(base_dir, tex_path)
    if os.path.isfile(full):
        return full

    # Пробуем относительно project root
    full = os.path.join(project_root, tex_path)
    if os.path.isfile(full):
        return full

    # Пробуем в build/
    full = os.path.join(project_root, 'build', tex_path)
    if os.path.isfile(full):
        return full

    return None

def flatten(filepath, base_dir, depth=0, seen=None):
    r"""Рекурсивно раскрывает \input"""
    if seen is None:
        seen = set()

    if depth > 20:
        return f"% [ОШИБКА: слишком глубокая вложенность для {filepath}]\n"

    real_path = os.path.realpath(filepath)
    if real_path in seen:
        return f"% [ПРОПУСК: циклическая ссылка на {filepath}]\n"
    seen.add(real_path)

    if not os.path.isfile(filepath):
        return f"% [ФАЙЛ НЕ НАЙДЕН: {filepath}]\n"

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    file_dir = os.path.dirname(filepath)

    # Раскрываем \inputchapter{name} → \input{src/chapters/name}
    content = re.sub(
        r'\\inputchapter\{([^}]+)\}',
        r'\\input{src/chapters/\1}',
        content
    )

    # Раскрываем \inputappendix{name} → \input{src/appendix/name}
    content = re.sub(
        r'\\inputappendix\{([^}]+)\}',
        r'\\input{src/appendix/\1}',
        content
    )

    # Раскрываем пользовательские пути
    # \input{\titlepath/title} → \input{src/title/title}
    path_map = {
        r'\\titlepath': 'src/title',
        r'\\executorspath': 'src/executors',
        r'\\abstractpath': 'src/abstract',
        r'\\termspath': 'src/terms',
        r'\\abbreviationspath': 'src/abbreviations',
        r'\\chapterspath': 'src/chapters',
        r'\\appendixpath': 'src/appendix',
        r'\\imagespath': 'src/images',
        r'\\bibliographypath': 'src/bibliography',
    }
    for cmd, path in path_map.items():
        content = re.sub(cmd, path, content)

    # Теперь рекурсивно раскрываем \input{...}
    def replace_input(match):
        input_path = match.group(1)
        resolved = resolve_path(input_path, file_dir)
        if resolved is None:
            resolved = resolve_path(input_path, project_root)
        if resolved is None:
            return f"% [ФАЙЛ НЕ НАЙДЕН: {input_path}]\n"
        return flatten(resolved, os.path.dirname(resolved), depth + 1, seen)

    content = re.sub(r'\\input\{([^}]+)\}', replace_input, content)

    return content


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: flatten_tex.py <input.tex> <output.tex> <project_root>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    project_root = sys.argv[3]

    result = flatten(input_file, os.path.dirname(input_file))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"  Расплющено: {input_file} → {output_file}")
    lines = result.count('\n')
    print(f"  Строк: {lines}")
