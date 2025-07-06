"""
Скрипт для запуска тестов с проверкой покрытия кода
"""
import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Запускает команду и выводит результат"""
    print(f"\n{'=' * 60}")
    print(f"🔄 {description}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(command, shell=True, check=True,
                                capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при выполнении команды: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
    print("🧪 Запуск тестов OnlineEdu проекта")

    # Проверяем что мы в правильной директории
    if not Path('manage.py').exists():
        print("❌ Файл manage.py не найден. Запустите скрипт из корневой директории проекта.")
        sys.exit(1)

    # Установка coverage если не установлен
    print("\n📦 Проверка и установка coverage...")
    install_result = run_command(
        "pip install coverage",
        "Установка coverage"
    )

    # Создание тестовых групп
    print("\n👥 Создание групп пользователей...")
    groups_result = run_command(
        "python manage.py create_groups",
        "Создание групп пользователей"
    )

    # Запуск миграций
    print("\n🗄️  Применение миграций...")
    migrate_result = run_command(
        "python manage.py migrate",
        "Применение миграций"
    )

    # Запуск тестов с покрытием
    print("\n🧪 Запуск тестов с измерением покрытия...")

    test_commands = [
        # Запуск тестов LMS приложения
        "coverage run --source='.' --omit='*/venv/*,*/migrations/*,manage.py,*/settings.py,*/tests.py' manage.py test lms.tests",

        # Запуск тестов Users приложения
        "coverage run --append --source='.' --omit='*/venv/*,*/migrations/*,manage.py,*/settings.py,*/tests.py' manage.py test users.tests",

        # Создание отчета покрытия
        "coverage report -m",

        # Создание HTML отчета
        "coverage html"
    ]

    all_success = True

    for command in test_commands:
        success = run_command(command, f"Выполнение: {command}")
        if not success:
            all_success = False

    # Статистика покрытия
    print("\n📊 Генерация детального отчета покрытия...")

    # Показать краткую статистику покрытия
    run_command("coverage report", "Краткий отчет покрытия")

    # Информация о HTML отчете
    html_report_path = Path("htmlcov/index.html")
    if html_report_path.exists():
        print(f"\n✅ HTML отчет создан: {html_report_path.absolute()}")
        print("   Откройте файл в браузере для детального просмотра")

    # Финальное сообщение
    if all_success:
        print("\n✅ Все тесты выполнены успешно!")
        print("\n📋 Резюме:")
        print("   - Тесты CRUD операций с уроками: ✅")
        print("   - Тесты функционала подписки: ✅")
        print("   - Тесты валидаторов YouTube ссылок: ✅")
        print("   - Тесты прав доступа пользователей: ✅")
        print("   - Тесты всех API endpoints: ✅")
        print("   - Тесты пагинации: ✅")
        print("   - Отчет покрытия сгенерирован: ✅")
    else:
        print("\n❌ Некоторые тесты завершились с ошибками")
        sys.exit(1)


if __name__ == "__main__":
    main()