import requests
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
from datetime import datetime

# ===== 1. НАСТРОЙКИ =====
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
    'Referer': 'https://www.stoloto.ru/5x36plus/archive/',
    'gosloto-partner': 'bXMjXFRXZ3coWXh6R3s1NTdUX3dnWlBMLUxmdg'
}
URL = "https://www.stoloto.ru/p/api/mobile/api/v35/service/draws/archive"

# ===== 2. НАШИ КОМБИНАЦИИ =====
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
            print(f"🔄 Загружена последовательность: {len(sequence)} букв")
        else:
            sequence = ["B", "C", "D", "F", "C", "B", "D", "F", "B", "C", "D", "F", "C", "D", "B", "F"]
else:
    sequence = ["B", "C", "D", "F", "C", "B", "D", "F", "B", "C", "D", "F", "C", "D", "B", "F"]

# ===== 5. ФУНКЦИЯ ПРОГНОЗА =====
def predict_next(current):
    if current not in graph:
        return None, {}
    options = graph[current]
    total = sum(options.values())
    probs = {k: v/total for k, v in options.items()}
    best = max(options.items(), key=lambda x: x[1])[0]
    return best, probs

# ===== 6. ФУНКЦИЯ ОТПРАВКИ EMAIL (Яндекс) =====
def send_notification(letter, draw_number, sequence):
    sender_email = os.environ.get('YANDEX_USER')
    sender_password = os.environ.get('YANDEX_PASSWORD')
    receiver_email = sender_email

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"🎯 Выпала комбинация {letter} в тираже {draw_number}"

    last = sequence[-1]
    best, probs = predict_next(last)

    body = f"""
    <h2>🎯 Обнаружена комбинация {letter}</h2>
    <p><b>Тираж:</b> {draw_number}</p>
    <p><b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <p><b>Последовательность:</b> {', '.join(sequence[-10:])}</p>
    <h3>📊 Прогноз:</h3>
    <p>Сейчас: <b>{last}</b></p>
    <p>Вероятности:</p><ul>
    """
    for nxt, prob in probs.items():
        body += f"<li>{nxt} : {prob*100:.1f}%</li>"
    body += f"</ul><p>🎯 Самый вероятный: <b>{best}</b></p>"

    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("✅ Email отправлен")
        return True
    except Exception as e:
        print(f"❌ Ошибка email: {e}")
        return False

# ===== 7. ПОЛУЧЕНИЕ ТИРАЖЕЙ =====
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

# ===== 8. ОСНОВНАЯ ФУНКЦИЯ =====
def main():
    print("🚀 Проверка тиражей")
    print("=" * 40)

    draws = fetch_draws(page=0, count=10)
    if not draws:
        print("❌ Нет данных")
        return

    found = []
    last_checked = None
    if os.path.exists('last_checked.txt'):
        with open('last_checked.txt', 'r') as f:
            last_checked = int(f.read().strip())

    for draw in draws:
        num = draw['number']
        if last_checked and num <= last_checked:
            continue
        nums = tuple(sorted([int(x) for x in draw['winningCombination'][:5]]))
        if nums in COMBO_MAP:
            letter = COMBO_MAP[nums]
            found.append((num, letter))
            sequence.append(letter)
            last_checked = num

    if found:
        print(f"✅ Найдено: {found}")
        with open(sequence_file, 'w') as f:
            f.write(','.join(sequence))
        with open('last_checked.txt', 'w') as f:
            f.write(str(last_checked))

        for num, letter in found:
            send_notification(letter, num, sequence)

        last = sequence[-1]
        best, probs = predict_next(last)
        print(f"📊 Сейчас: {last}, вероятный следующий: {best}")

        if len(sequence) >= 3:
            prev = sequence[-3]
            actual = sequence[-2]
            predicted, _ = predict_next(prev)
            status = "✅" if predicted == actual else "❌"
            print(f"{status} Предыдущий прогноз: {prev} → {actual} (ожидался {predicted})")
    else:
        print("❌ Новых комбинаций нет")

    print("🏁 Завершено")

if __name__ == "__main__":
    main()
