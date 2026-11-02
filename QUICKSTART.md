# ⚡ Быстрый старт — 3 команды

## Клонируй репо и примени патч:

```bash
# 1. Перейди в репозиторий
cd rex35

# 2. Скачай файлы из workspace (они в этом чате выше)
# Нужны: main_updated.py, apply_patch.py, README_PATCH.md

# 3. Примени патч
python3 apply_patch.py index.html

# 4. Замени main.py
mv main.py main_old.py
mv main_updated.py main.py

# 5. Перезапусти
python main.py
```

---

## Или через git (если workspace уже в репе):

```bash
git pull origin main
python3 apply_patch.py index.html
mv main_updated.py main.py
git add .
git commit -m "add persistent chat history"
git push
```

---

## Что изменилось:

### ✅ main.py
- Добавлена инициализация SQLite (`chats.db`)
- 5 новых эндпоинтов для работы с чатами
- Автосохранение сообщений в базу

### ✅ index.html
- Загрузка истории при открытии чата
- Сохранение user-сообщений в базу
- Синхронизация с бэком

---

## Проверка:

1. Открой сайт
2. Напиши "привет"
3. Обнови страницу (F5)
4. Сообщение должно остаться ✅

Если осталось — работает.
Если пропало — проверь консоль браузера (F12).

---

## Файлы из workspace:

```
workspace/
├── main_updated.py          # Обновлённый бэкенд с SQLite
├── apply_patch.py           # Скрипт для патча index.html
├── index_html_patch.txt     # Описание изменений (для ручного патча)
└── README_PATCH.md          # Полная документация
```

Скопируй `main_updated.py` и `apply_patch.py` в корень репозитория, запусти патч, замени main.py — готово.
