"""
Набор вспомогательных функций
"""

import os
import re

def make_safe_path(path: str, create_path: bool=True) -> str:
    """Преобразование пути в абсолютный и безопасный.
    
    Args:
        path: Исходный путь
        create: Создавать директорию, если отсутствует
        
    Returns:
        str: Строка безопасного пути
    """
    safe_path = os.path.abspath(path)
    drive, path_part = os.path.splitdrive(safe_path)
    safe_path = os.path.join(
        os.sep,
        f"{drive}{os.sep}",
        *map(
            make_safe_filename,
            os.path.normpath(path_part).split(os.sep)
        )
    )
    if create_path:
        os.makedirs(safe_path, exist_ok=True)
    return safe_path

# Таблицы преобразования для make_safe_filename
_ILLEGAL_CHARS = set('/\\?%*:|"<>')
_ILLEGAL_UNPRINTABLE = {chr(c) for c in [*range(31), 127]}
_RESERVED_WORDS = {
    'CON', 'CONIN$', 'CONOUT$', 'PRN', 'AUX', 'CLOCK$', 'NUL',
    'COM0', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT0', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
    'LST', 'KEYBD$', 'SCREEN$', '$IDLE$', 'CONFIG$'
}

def make_safe_filename(filename: str) -> str:
    """
    # Преобразование имени файла в безопасное
    # https://stackoverflow.com/questions/7406102/create-sane-safe-filename-from-any-unsafe-string
    """
    if not filename: return "file"
    if os.path.splitext(filename)[0].upper() in _RESERVED_WORDS: return f"__{filename}"
    if filename[0]==filename[-1]=='.' and set(filename)=={'.'}: return '\uff0e' * len(filename)
    return "".join(
        chr(ord(c)+65248) if c in _ILLEGAL_CHARS else c
        for c in filename
        if c not in _ILLEGAL_UNPRINTABLE
    ).rstrip('. ') or "file"

# Предварительно скомпилированные регулярные выражения
_MULTISPACE_PATTERN = re.compile(r' {2,}')
_MULTINEWLINE_PATTERN = re.compile(r'\n{3,}')
_CLEAN_NEWLINES = re.compile(r'\r\n|\r')

def clear_text_multiplespaces(text: str) -> str:
    """Очистка от множественных пробелов и переносов строки"""
    text = _CLEAN_NEWLINES.sub('\n', text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = _MULTISPACE_PATTERN.sub(' ', text)
    text = _MULTINEWLINE_PATTERN.sub('\n\n', text)
    return text.strip()

def check_corrects_file(filepath: str|os.PathLike) -> bool:
    """Проверка файла на существование и корректность"""
    try:
        return os.path.getsize(filepath) > 1024
    except OSError:
        return False
