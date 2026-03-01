<details> <summary>Финальный код для копирования (нажмите, чтобы развернуть)</summary>
import requests
import json
import time
import sys
from collections import defaultdict
import random
import os

# ===== 1. НАСТРОЙКИ =====
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
    'Referer': 'https://www.stoloto.ru/5x36plus/archive/',
    'gosloto-partner': 'bXMjXFRXZ3coWXh6R3s1NTdUX3dnWlBMLUxmdg'
}
URL = "https://www.stoloto.ru/p/api/mobile/api/v35/service/draws/archive"

# ===== 2. НАШИ КОМБИНАЦИИ (только B, C, D, F) =====
COMBO_MAP = {
    (21,30,33,34,35): "B",
    (4,6,11,19,30): "C",
    (2,10,18,19,29): "D",
    (17,23,28,29,36): "F",
}

# ===== 3. ГРАФ ПЕРЕХОДОВ =====
TRANSITIONS = [
    ("B", "C"), ("B", "D"),
    ("C", "D"), ("C", "D"), ("C", "B"),
    ("D", "F"), ("D", "B"),
    ("F", "C"), ("F", "C"),
]

# Строим граф с весами
graph = defaultdict(lambda: defaultdict(int))
for f, t in TRANSITIONS:
    graph[f][t] += 1

# ===== 4. ПОСЛЕДОВАТЕЛЬНОСТЬ =====
sequence_file = 'sequence_backup.txt'
if os.path.exists(sequence_file):
    with open(sequence_file, 'r') as f:
        seq_str = f.read().strip()
        if seq_str:
            sequence = seq_str.split(',')
            print(f"🔄 Загружена сохраненная последовательность длиной {len(sequence)}")
        else:
            sequence = ["B", "C", "D", "F", "C", "B", "D", "F", "B", "C", "D", "F", "C", "D", "B", "F"]
            print("📄 Используется начальная последовательность")
else:
    sequence = ["B", "C", "D", "F", "C", "B", "D", "F", "B", "C", "D", "F", "C", "D", "B", "F"]
    print("📄 Используется начальная последовательность")

# ===== 5. ФУНКЦИЯ ПРОГНОЗА =====
def predict_next(current):
    if current not in graph:
        return None, []
    options = graph[current]
    total = sum(options.values())
    probs = {k: v/total for k, v in options.items()}
    best = max(options.items(), key=lambda x: x[1])[0]
    return best, probs

# ===== 6. ФУНКЦИЯ ПОЛУЧЕНИЯ ТИРАЖЕЙ =====
def fetch_draws(page=0, count=10):
    params = {'game': '5x36plus', 'count': count, 'page': page}
    try:
        response = requests.get(URL, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get('draws', [])
        else:
            print(f"⚠️ Ошибка API: {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️ Ошибка запроса: {e}")
        return []

# ===== 7. ПРИНУДИТЕЛЬНАЯ ПРОВЕРКА ПРИ ЗАПУСКЕ =====
def initial_scan():
    print("🔍 Принудительная проверка последних 50 тиражей...")
    all_draws = []
    for page in range(5):
        draws = fetch_draws(page=page, count=10)
        all_draws.extend(draws)
        if len(draws) < 10:
            break
    found = []
    for draw in all_draws:
        nums = tuple(sorted([int(x) for x in draw['winningCombination'][:5]]))
        if nums in COMBO_MAP:
            letter = COMBO_MAP[nums]
            found.append((draw['number'], letter))
    if found:
        print(f"✅ Найдено {len(found)} вхождений:")
        for num, letter in sorted(found):
            print(f"   Тираж {num}: {letter}")
            sequence.append(letter)
    else:
        print("❌ Ни одной комбинации B, C, D, F не найдено")
    return found

# ===== 8. ОСНОВНОЙ ЦИКЛ =====
def main():
    print("🚀 Запущен мониторинг переходов B, C, D, F")
    print("=" * 60)
    initial_scan()
    last_checked = None
    # Запоминаем последний обработанный тираж при запуске
    if sequence:
        # В качестве начала возьмем последний в последовательности, но для проверки нужен номер тиража
        # Здесь можно доработать сохранение последнего номера, но для простоты пропустим
        pass
    while True:
        try:
            draws = fetch_draws(page=0, count=10)
            new_letters = []
            for draw in draws:
                if last_checked and draw['number'] <= last_checked:
                    continue
                nums = tuple(sorted([int(x) for x in draw['winningCombination'][:5]]))
                if nums in COMBO_MAP:
                    letter = COMBO_MAP[nums]
                    new_letters.append((draw['number'], letter))
            if new_letters:
                print(f"\n📥 Получены новые тиражи: {[f'№{num}={letter}' for num, letter in new_letters]}")
                for num, letter in new_letters:
                    sequence.append(letter)
                    last_checked = num
                last = sequence[-1]
                best, probs = predict_next(last)
                print(f"📊 Текущая буква: {last}")
                print(f"📈 Вероятности следующей:")
                for nxt, prob in probs.items():
                    print(f"   → {nxt} : {prob*100:.1f}%")
                print(f"🎯 Самый вероятный следующий: {best}")
                if len(sequence) >= 3:
                    prev = sequence[-3]
                    actual = sequence[-2]
                    predicted, _ = predict_next(prev)
                    if predicted == actual:
                        print(f"✅ Предыдущий прогноз для {prev} → {actual} сбылся!")
                    else:
                        print(f"❌ Предыдущий прогноз для {prev} был {predicted}, а выпало {actual}")
                with open(sequence_file, 'w') as f:
                    f.write(','.join(sequence))
            print(f"\n⏳ Следующая проверка через 30 минут... ({time.strftime('%H:%M:%S')})")
            sys.stdout.flush()
            time.sleep(1800)
        except KeyboardInterrupt:
            print("\n👋 Завершение работы")
            break
        except Exception as e:
            print(f"⚠️ Ошибка в основном цикле: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
  </details>
