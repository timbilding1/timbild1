#!/usr/bin/env python3
"""
Патч для добавления персистентной истории чатов в rex35
Применяет изменения к index.html для работы с SQLite хранилищем
"""

def patch_index_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Патч 1: Исправить URL в openChat
    content = content.replace(
        "const r = await fetch('/api/chats/' + id);",
        "const r = await fetch('/api/chats/' + id + '/messages');"
    )
    
    # Патч 2: Добавить сохранение user-сообщения
    # Ищем блок создания чата и добавляем после него
    marker = "    }catch(e){console.error('create chat', e);}\n  }"
    save_user_msg = """
  // Save user message to DB
  if(currentChatId){
    try{
      await fetch('/api/chats/' + currentChatId + '/message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({role: 'user', content: content})
      });
    }catch(e){console.error('save user msg', e);}
  }"""
    
    if marker in content:
        content = content.replace(marker, marker + save_user_msg)
    else:
        print("⚠️  Не найден маркер для патча #2 — возможно код уже изменён")
    
    # Проверка что хоть что-то изменилось
    if content == original:
        print("❌ Ни один патч не применился — проверьте совместимость версий")
        return False
    
    # Бэкап оригинала
    backup_path = filepath + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original)
    print(f"✅ Создан бэкап: {backup_path}")
    
    # Записываем патченную версию
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Патч применён к {filepath}")
    
    return True

if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    
    print("🔧 Применяю патч для персистентной истории...")
    
    try:
        success = patch_index_html(filepath)
        if success:
            print("\n✅ Патч успешно применён!")
            print("\nТеперь замени main.py на main_updated.py и перезапусти сервер:")
            print("  mv main.py main_old.py")
            print("  mv main_updated.py main.py")
            print("  python main.py")
        else:
            print("\n❌ Патч не применился")
            sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Файл {filepath} не найден")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
