# casino/roulette_utils.py
import random

def get_roulette_result():
    outcomes = ['black', 'red', 'zero']
    probabilities = [17.5 / 36, 17.5 / 36, 1 / 36]  # 1/36 на zero, оставшееся равномерно между black и red
    
    result = random.choices(outcomes, probabilities)[0]
    return result
