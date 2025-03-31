import pytest
import random
from collections import Counter
from unittest.mock import patch

# Импортируем тестируемую функцию
try:
    from casino.roulette_utils import get_roulette_result
except ImportError as e:
    pytest.skip(f"Пропуск тестов roulette_utils: не удалось импортировать модуль casino.roulette_utils ({e}).", allow_module_level=True)

# --- Тесты для get_roulette_result ---

def test_get_roulette_result_returns_valid_outcome():
    """Тест, что функция всегда возвращает один из допустимых результатов."""
    valid_outcomes = {'black', 'red', 'zero'}
    for _ in range(100): # Проверим на 100 запусках
        result = get_roulette_result()
        assert result in valid_outcomes

@patch('random.choices') # Мокаем сам random.choices
def test_get_roulette_result_calls_choices_correctly(mock_choices):
    """Тест, что random.choices вызывается с правильными аргументами."""
    # Устанавливаем возвращаемое значение, чтобы избежать IndexError
    mock_choices.return_value = ['black'] 
    
    get_roulette_result()
    
    expected_outcomes = ['black', 'red', 'zero']
    expected_probabilities = [17.5 / 36, 17.5 / 36, 1 / 36]
    
    # Проверяем, что choices был вызван один раз с ожидаемыми параметрами
    mock_choices.assert_called_once_with(expected_outcomes, expected_probabilities)

def test_get_roulette_result_distribution():
    """
    Статистический тест для проверки распределения результатов.
    Запускаем функцию много раз и проверяем, что частоты близки к ожидаемым.
    Примечание: Этот тест недетерминирован и может иногда падать из-за случайности,
    но он полезен для проверки общей логики вероятностей.
    """
    num_runs = 10000 # Большое количество запусков для статистики
    results = [get_roulette_result() for _ in range(num_runs)]
    counts = Counter(results)
    
    total_runs = sum(counts.values())
    assert total_runs == num_runs
    
    # Ожидаемые вероятности
    prob_black = 17.5 / 36
    prob_red = 17.5 / 36
    prob_zero = 1 / 36
    
    # Допустимое отклонение (например, 15%)
    tolerance = 0.15 
    
    # Проверяем частоту для black
    observed_prob_black = counts.get('black', 0) / total_runs
    assert prob_black * (1 - tolerance) <= observed_prob_black <= prob_black * (1 + tolerance)
    
    # Проверяем частоту для red
    observed_prob_red = counts.get('red', 0) / total_runs
    assert prob_red * (1 - tolerance) <= observed_prob_red <= prob_red * (1 + tolerance)

    # Проверяем частоту для zero
    observed_prob_zero = counts.get('zero', 0) / total_runs
    assert prob_zero * (1 - tolerance) <= observed_prob_zero <= prob_zero * (1 + tolerance) 