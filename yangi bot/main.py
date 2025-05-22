import requests
import time
import json
import re

TOKEN = '7770984939:AAFcvF1sC_fzCp-RZE6XHHUazGFy89SvVhc'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_CHAT_ID = 8037792078  # O'zingizning Telegram ID'ingizni bu yerga yozing

foydalanuvchilar = {}
testlar = []  # Bir nechta testlarni saqlash uchun ro'yxat
oxirgi_test = None  # Foydalanuvchiga beriladigan test

def get_updates(offset=None):
    res = requests.get(URL + 'getUpdates', params={'timeout': 100, 'offset': offset})
    return res.json()

def send_message(chat_id, text, parse_mode=None):
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    requests.post(URL + 'sendMessage', json=payload)

def format_test(test):
    text = "🧪 <b>Testni yeching</b>\nJavoblaringizni <code>1.a 2.b 3.c</code> ko'rinishida yuboring:\n\n"
    for item in test['savollar']:
        text += item['savol'] + '\n' + '\n'.join(item['variantlar']) + '\n\n'
    return text

def check_answers_flexible(user_input, test):
    correct_answers = [q['togri'].lower() for q in test['savollar']]
    try:
        pattern = re.compile(r'(\d+)[\.\:\-\s]?([a-zA-Z])')
        matches = pattern.findall(user_input.lower())
        user_answers = {}
        for num, ans in matches:
            user_answers[int(num)] = ans
        score = 0
        total = len(correct_answers)
        for i in range(1, total + 1):
            if i in user_answers and user_answers[i] == correct_answers[i - 1]:
                score += 1
        return score, total
    except Exception:
        return -1, len(correct_answers)

def parse_test_from_text(text):
    try:
        lines = text.split('\n')
        savollar = []
        javoblar = []

        reading_savollar = False
        reading_javoblar = False
        current_savol = {}
        variants = []

        for line in lines:
            line = line.strip()
            if line.lower() == 'savollar:':
                reading_savollar = True
                reading_javoblar = False
                continue
            elif line.lower() == 'javoblar:':
                reading_javoblar = True
                reading_savollar = False
                if current_savol:
                    current_savol['variantlar'] = variants
                    savollar.append(current_savol)
                continue

            if reading_savollar:
                if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    if current_savol:
                        current_savol['variantlar'] = variants
                        savollar.append(current_savol)
                        variants = []
                    current_savol = {'savol': line}
                elif line and current_savol:
                    variants.append(line)
            elif reading_javoblar:
                if '.' in line:
                    _, answer = line.split('.')
                    javoblar.append(answer.strip())

        if current_savol:
            current_savol['variantlar'] = variants
            savollar.append(current_savol)

        for i in range(len(javoblar)):
            savollar[i]['togri'] = javoblar[i]

        return {"savollar": savollar}
    except Exception as e:
        return None

def handle_message(msg):
    global oxirgi_test
    chat_id = msg['chat']['id']
    text = msg.get('text', '').strip()

    if chat_id == ADMIN_CHAT_ID and 'savollar:' in text.lower() and 'javoblar:' in text.lower():
        test = parse_test_from_text(text)
        if test:
            testlar.append(test)
            oxirgi_test = test
            send_message(chat_id, "✅ Test muvaffaqiyatli qo‘shildi.")
        else:
            send_message(chat_id, "❌ Xatolik! Testni to‘g‘ri formatda yuboring.")
        return

    if text == '/start':
        if not oxirgi_test:
            send_message(chat_id, "❗ Hozircha test mavjud emas. Admin test yuklashi kerak.")
            return
        send_message(chat_id, "Assalomu alaykum! Testni boshlaymiz!", parse_mode="HTML")
        send_message(chat_id, format_test(oxirgi_test), parse_mode="HTML")
        foydalanuvchilar[str(chat_id)] = {"expecting_answers": True}
    elif str(chat_id) in foydalanuvchilar and foydalanuvchilar[str(chat_id)].get("expecting_answers"):
        score, total = check_answers_flexible(text, oxirgi_test)
        if score == -1:
            send_message(chat_id, "❗ Javoblar formati noto‘g‘ri. To‘g‘ri format: 1.a 2.b 3.c")
        else:
            msg = f"✅ Test tugadi!\nSizning natijangiz: {score}/{total}"
            if score == total:
                msg += "\n🎉 Ajoyib! Barcha javoblar to‘g‘ri!"
            elif score >= total * 0.7:
                msg += "\n👍 Yaxshi ish!"
            elif score >= total * 0.4:
                msg += "\n🙂 Yaxshi boshlanish."
            else:
                msg += "\n📚 Yana mashq qiling."
            send_message(chat_id, msg)
            foydalanuvchilar[str(chat_id)]["expecting_answers"] = False
    else:
        send_message(chat_id, "Yangi test uchun /start ni bosing.")

def handle_update(update):
    if 'message' in update:
        handle_message(update['message'])

def main():
    offset = None
    print("Bot ishga tushdi...")
    while True:
        updates = get_updates(offset)
        for update in updates.get('result', []):
            offset = update['update_id'] + 1
            handle_update(update)
        time.sleep(1)

if __name__ == '__main__':
    main()
