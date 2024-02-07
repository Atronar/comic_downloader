"""
Набор вспомогательных функций
"""

import os

def make_safe_path(path: str, create_path: bool=True) -> str:
    """Преобразование пути в абсолютный и безопасный
    """
    safe_path = os.path.abspath(path)
    drive, dir_ = os.path.splitdrive(safe_path)
    safe_path = os.path.join(
        os.sep,
        f"{drive}{os.sep}",
        *map(
            make_safe_filename,
            dir_.split(os.sep)
        )
    )
    if create_path and not os.path.exists(safe_path):
        os.makedirs(safe_path)
    return safe_path

def make_safe_filename(filename: str) -> str:
    """
    # Преобразование имени файла в безопасное
    # https://stackoverflow.com/questions/7406102/create-sane-safe-filename-from-any-unsafe-string
    """
    illegal_chars = "/\\?%*:|\"<>"
    illegal_unprintable = {chr(c) for c in (*range(31), 127)}
    reserved_words = {
        'CON', 'CONIN$', 'CONOUT$', 'PRN', 'AUX', 'CLOCK$', 'NUL',
        'COM0', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT0', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
        'LST', 'KEYBD$', 'SCREEN$', '$IDLE$', 'CONFIG$'
    }
    if os.path.splitext(filename)[0].upper() in reserved_words: return f"__{filename}"
    if set(filename)=={'.'}: return filename.replace('.', '\uff0e')
    return "".join(
        chr(ord(c)+65248) if c in illegal_chars else c
        for c in filename
        if c not in illegal_unprintable
    ).rstrip().rstrip('.')

def clear_text_multiplespaces(text: str) -> str:
    """Очистка от множественных пробелов и переносов строки"""
    text = "\n".join(line.strip() for line in text.splitlines())
    while "  " in text:
        text = text.replace("  ", " ")
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()

def check_corrects_file(filepath: str|os.PathLike) -> bool:
    """Проверка файла на существование и корректность"""
    return os.path.exists(filepath) and os.path.getsize(filepath) > 1024
