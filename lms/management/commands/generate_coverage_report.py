import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Генерирует отчет о покрытии тестами'

    def add_arguments(self, parser):
        parser.add_argument(
            '--html',
            action='store_true',
            help='Создать HTML отчет',
        )
        parser.add_argument(
            '--open',
            action='store_true',
            help='Открыть HTML отчет в браузере (только с --html)',
        )

    def handle(self, *args, **options):
        self.stdout.write('🧪 Запуск тестов с измерением покрытия...')

        # Запуск тестов с coverage
        coverage_cmd = [
            'coverage', 'run',
            '--source=.',
            '--omit=*/venv/*,*/migrations/*,manage.py,*/settings.py,*/wsgi.py,*/asgi.py',
            'manage.py', 'test'
        ]

        try:
            result = subprocess.run(coverage_cmd, check=True,
                                    capture_output=True, text=True)
            self.stdout.write(
                self.style.SUCCESS('✅ Тесты выполнены успешно')
            )
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка при выполнении тестов: {e}')
            )
            return

        # Генерация текстового отчета
        self.stdout.write('\n📊 Генерация отчета покрытия...')

        report_cmd = ['coverage', 'report', '-m']

        try:
            result = subprocess.run(report_cmd, check=True,
                                    capture_output=True, text=True)
            self.stdout.write(result.stdout)
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка при генерации отчета: {e}')
            )

        # Генерация HTML отчета если запрошено
        if options['html']:
            self.stdout.write('\n🌐 Создание HTML отчета...')

            html_cmd = ['coverage', 'html']

            try:
                subprocess.run(html_cmd, check=True)

                html_path = os.path.join(os.getcwd(), 'htmlcov', 'index.html')
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ HTML отчет создан: {html_path}'
                    )
                )

                # Открытие в браузере если запрошено
                if options['open']:
                    import webbrowser
                    webbrowser.open(f'file://{html_path}')
                    self.stdout.write('🌐 HTML отчет открыт в браузере')

            except subprocess.CalledProcessError as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка при создании HTML отчета: {e}')
                )

        # Статистика покрытия
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('📈 СТАТИСТИКА ПОКРЫТИЯ ТЕСТАМИ')
        self.stdout.write('=' * 60)

        try:
            # Получаем процент покрытия
            json_cmd = ['coverage', 'json']
            subprocess.run(json_cmd, check=True)

            import json
            with open('coverage.json', 'r') as f:
                coverage_data = json.load(f)

            total_coverage = coverage_data['totals']['percent_covered']

            self.stdout.write(f'Общее покрытие: {total_coverage:.1f}%')

            if total_coverage >= 90:
                self.stdout.write(
                    self.style.SUCCESS('🟢 Отличное покрытие!')
                )
            elif total_coverage >= 80:
                self.stdout.write(
                    self.style.WARNING('🟡 Хорошее покрытие')
                )
            elif total_coverage >= 70:
                self.stdout.write(
                    self.style.WARNING('🟠 Среднее покрытие')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('🔴 Низкое покрытие - нужно больше тестов!')
                )

            # Детали по модулям
            self.stdout.write('\nПокрытие по модулям:')
            for filename, data in coverage_data['files'].items():
                if not any(skip in filename for skip in ['migrations', 'tests', '__pycache__']):
                    coverage_percent = data['summary']['percent_covered']
                    self.stdout.write(f'  {filename}: {coverage_percent:.1f}%')

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Не удалось получить детальную статистику: {e}')
            )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS('✅ Отчет о покрытии сгенерирован!')
        )

        if options['html']:
            self.stdout.write(
                'Для просмотра HTML отчета откройте файл htmlcov/index.html'
            )