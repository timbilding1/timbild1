# 🔥 Персистентная история для Rex35

Этот патч добавляет **сохранение истории диалогов** с помощью SQLite, чтобы при перезагрузке страницы ты мог продолжить с места остановки.

---

## 📦 Что делает патч

### До патча:
- История чата жила только в браузере (JS переменная)
- После перезагрузки страницы — всё пропадало
- Контекст терялся при каждом обновлении

### После патча:
- Все сообщения сохраняются в SQLite (`chats.db`)
- Можно вернуться к любому старому диалогу
- При открытии чата — история загружается с бэка
- Автоматическое именование чатов по первому сообщению

---

## 🚀 Установка (3 простых шага)

### 1. Скопируй файлы из workspace в свой репозиторий

```bash
cd /path/to/rex35

# Скопируй патч-скрипт
cp workspace/apply_patch.py .

# Скопируй обновлённый бэкенд
cp workspace/main_updated.py .
```

### 2. Примени патч к index.html

```bash
python3 apply_patch.py index.html
```

Скрипт:
- Создаст бэкап `index.html.backup`
- Пропатчит `index.html` для работы с новыми эндпоинтами
- Покажет что именно изменилось

### 3. Замени main.py на обновлённую версию

```bash
# Бэкап старого бэкенда
mv main.py main_old.py

# Активируй новый
mv main_updated.py main.py
```

---

## 🔄 Перезапуск сервера

```bash
python main.py
```

Или если у тебя Docker/Railway — просто сделай:

```bash
git add .
git commit -m "feat: add persistent chat history with SQLite"
git push
```

Railway подхватит изменения автоматически.

---

## 🧪 Проверка что всё работает

1. Открой веб-интерфейс
2. Напиши что-нибудь в чат
3. **Обнови страницу (F5)**
4. История должна остаться

Если видишь старые сообщения после перезагрузки — всё работает ✅

---

## 📊 Новые эндпоинты API

Патч добавляет:

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/chats` | POST | Создать новый чат |
| `/api/chats` | GET | Список всех чатов |
| `/api/chats/{id}/messages` | GET | История конкретного чата |
| `/api/chats/{id}/message` | POST | Сохранить сообщение |
| `/api/chats/{id}` | DELETE | Удалить чат |

---

## 🗂️ Структура базы данных

SQLite создаёт автоматически:

```sql
-- Таблица чатов
CREATE TABLE chats (
    id INTEGER PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Таблица сообщений
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER,
    role TEXT,          -- 'user' или 'assistant'
    content TEXT,
    timestamp TIMESTAMP,
    FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
);
```

База хранится в файле `chats.db` рядом с `main.py`.

---

## 🔧 Откат изменений

Если что-то пошло не так:

```bash
# Восстанови старые файлы
mv main_old.py main.py
mv index.html.backup index.html

# Удали базу если нужно начать заново
rm chats.db
```

---

## 🎯 Что дальше?

Теперь у тебя полноценная история диалогов. Можешь:

- Открывать старые чаты из панели слева
- Продолжать прерванные разговоры
- Удалять ненужные через кнопку ✕
- Экспортировать `chats.db` для бэкапа

---

## 🐛 Troubleshooting

### "No module named 'sqlite3'"

SQLite входит в стандартную библиотеку Python, но если вдруг:

```bash
# Debian/Ubuntu
apt-get install libsqlite3-dev python3-sqlite3

# Alpine (в Docker)
apk add sqlite-dev
```

### Чаты не появляются после перезагрузки

Проверь консоль браузера (F12 → Console) на ошибки. Частые причины:

1. **CORS-ошибка** — убедись что `allow_origins=["*"]` в main.py
2. **Путь к базе** — проверь что `chats.db` создаётся в правильной директории
3. **Права на запись** — сервер должен иметь доступ к директории

### База растёт слишком быстро

Сейчас нет лимита на количество сообщений. Если нужно — добавь очистку:

```python
# В main.py, в функции save_message
conn.execute("""
    DELETE FROM messages 
    WHERE id NOT IN (
        SELECT id FROM messages 
        WHERE chat_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1000
    ) AND chat_id = ?
""", (chat_id, chat_id))
```

Это оставит только последние 1000 сообщений на чат.

---

Готово! Теперь твой Rex запоминает всё 🧠
