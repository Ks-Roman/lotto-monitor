import requests
import json
import sys
import os
from collections import defaultdict

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

# ===== 7. ОСНОВНАЯ ФУНКЦИЯ (ОДНОКРАТНАЯ) =====
def main():
    print("🚀 Запуск однократной проверки тиражей")
    print("=" * 60)

    # Загружаем последние 10 тиражей
    draws = fetch_draws(page=0, count=10)

    if not draws:
        print("❌ Не удалось получить данные")
        return

    # Проверяем, есть ли наши комбинации
    found_letters = []
    last_checked = None

    # Определяем последний обработанный тираж (если есть)
    if os.path.exists('last_checked.txt'):
        with open('last_checked.txt', 'r') as f:
            last_checked = int(f.read().strip())

    for draw in draws:
        draw_num = draw['number']
        if last_checked and draw_num <= last_checked:
            continue

        nums = tuple(sorted([int(x) for x in draw['winningCombination'][:5]]))
        if nums in COMBO_MAP:
            letter = COMBO_MAP[nums]
            found_letters.append((draw_num, letter))
            sequence.append(letter)
            last_checked = draw_num

    # Если нашли новые буквы
    if found_letters:
        print(f"\n✅ Найдены новые комбинации:")
        for num, letter in found_letters:
            print(f"   Тираж {num}: {letter}")

        # Обновляем последовательность
        with open(sequence_file, 'w') as f:
            f.write(','.join(sequence))

        # Сохраняем последний обработанный тираж
        if last_checked:
            with open('last_checked.txt', 'w') as f:
                f.write(str(last_checked))

        # Делаем прогноз на следующую
        last = sequence[-1]
        best, probs = predict_next(last)
        print(f"\n📊 Текущая буква: {last}")
        print(f"📈 Вероятности следующей:")
        for nxt, prob in probs.items():
            print(f"   → {nxt} : {prob*100:.1f}%")
        print(f"🎯 Самый вероятный следующий: {best}")

        # Проверяем предыдущий прогноз
        if len(sequence) >= 3:
            prev = sequence[-3]
            actual = sequence[-2]
            predicted, _ = predict_next(prev)
            if predicted == actual:
                print(f"✅ Предыдущий прогноз для {prev} → {actual} сбылся!")
            else:
                print(f"❌ Предыдущий прогноз для {prev} был {predicted}, а выпало {actual}")
    else:
        print("❌ Новых комбинаций B, C, D, F не найдено")

    print("\n🏁 Проверка завершена. Скрипт закончил работу.")

if __name__ == "__main__":
    main()
