# casino/roulette_utils.py
"""
Вспомогательные функции для игры в рулетку.
Содержит функционал для определения результатов спина рулетки.
"""
import random

def get_roulette_result():
    """
    Генерирует случайный результат спина рулетки с учетом вероятности.
    
    Вероятности:
    - черное (black): 17.5/36 (48.61%)
    - красное (red): 17.5/36 (48.61%)
    - зеро (zero): 1/36 (2.78%)
    
    Returns:
        str: Результат спина - 'black', 'red' или 'zero'
    """
    outcomes = ['black', 'red', 'zero']
    probabilities = [17.5 / 36, 17.5 / 36, 1 / 36]  # 1/36 на zero, оставшееся равномерно между black и red
    
    result = random.choices(outcomes, probabilities)[0]
    return result
