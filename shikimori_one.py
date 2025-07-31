import os
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional

# Конфигурация
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'shikimori_cache.json')  # Полный путь к файлу кэша
CACHE_EXPIRE_MINUTES = 30
REQUEST_DELAY = 2  # секунды между запросами
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36'
}


class ShikimoriParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    @staticmethod
    def clean_text(text: str) -> str:
        """Очистка текста от лишних пробелов и спецсимволов"""
        if not text:
            return ''

        # Удаляем множественные пробелы и переносы строк
        text = ' '.join(text.split())
        # Дополнительная очистка при необходимости
        text = text.replace('\u200b', '').replace('\ufeff', '')
        return text.strip()

    def make_request(self, url: str) -> Optional[str]:
        """Выполнение HTTP-запроса с задержкой"""
        try:
            print(f"Делаем запрос к {url}")
            time.sleep(REQUEST_DELAY)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Проверка что это действительно страница Shikimori
            if '<!DOCTYPE html>' not in response.text or 'shikimori' not in response.text.lower():
                print("Получена неожиданная страница (возможно капча или редирект)")
                return None

            return response.text
        except Exception as e:
            print(f"Ошибка запроса: {str(e)}")
            return None

    def parse_news_page(self, html: str) -> List[Dict[str, str]]:
        """Парсинг страницы с новостями (актуальные селекторы на июль 2025)"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            news_items = soup.find_all('article', class_='b-topic')  # Основной контейнер новостей

            news_list = []
            for item in news_items:
                try:
                    # Заголовок новости
                    title_elem = item.find('a', class_='name')
                    # Основной текст новости
                    content_elem = item.find('div', class_='body-inner')
                    # Дата публикации
                    date_elem = item.find('time', {'datetime': True})
                    # Ссылка на новость
                    link_elem = item.find('a', class_='name')
                    # Изображение (если есть)
                    image_elem = item.find('img')

                    if not all([title_elem, content_elem, date_elem]):
                        continue

                    news_data = {
                        'title': self.clean_text(title_elem.get_text(strip=True)),
                        'content': self.clean_text(content_elem.get_text(' ', strip=True)),
                        'date': date_elem['datetime'],
                        'url': link_elem['href'] if link_elem else '',
                        'image': image_elem['src'] if image_elem else ''
                    }

                    # Добавляем теги, если они есть
                    tags = item.find_all('div', class_='b-anime_status_tag')
                    if tags:
                        news_data['tags'] = [self.clean_text(tag.get_text(strip=True)) for tag in tags]

                    news_list.append(news_data)
                except Exception as e:
                    print(f"Ошибка при парсинге элемента новости: {str(e)}")
                    continue

            return news_list
        except Exception as e:
            print(f"Ошибка при парсинге страницы новостей: {str(e)}")
            return []

    def parse_ongoings_page(self, html: str) -> List[Dict[str, str]]:
        """Парсинг страницы с онгоингами (обновленные селекторы на июль 2025)"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # Основной контейнер для всех аниме
            ongoing_blocks = soup.find_all('div', class_='block m0')

            episodes_list = []

            for block in ongoing_blocks:
                # Получаем дату выхода (например "сегодня, 29 июля")
                date_elem = block.find('div', class_='headline')
                date = self.clean_text(date_elem.get_text()) if date_elem else 'Неизвестная дата'

                # Находим все аниме в этом блоке
                anime_items = block.find_all('article', class_='c-column')

                for item in anime_items:
                    try:
                        # Название аниме (русское или английское)
                        title_elem = item.find('span', class_='name-ru') or item.find('span', class_='name-en')
                        # Информация о эпизоде
                        episode_elem = item.find('span', class_='misc')
                        # Ссылка на аниме
                        link_elem = item.find('a', class_='cover')
                        # Изображение
                        image_elem = item.find('img')

                        if not title_elem:
                            continue

                        anime_data = {
                            'title': self.clean_text(title_elem.get_text(strip=True)),
                            'episode_info': self.clean_text(
                                episode_elem.get_text(' ', strip=True)) if episode_elem else 'Нет информации',
                            'date': date,
                            'url': link_elem['href'] if link_elem else '',
                            'image': image_elem['src'] if image_elem else ''
                        }

                        episodes_list.append(anime_data)
                    except Exception as e:
                        print(f"Ошибка при парсинге элемента аниме: {str(e)}")
                        continue

            return episodes_list
        except Exception as e:
            print(f"Ошибка при парсинге страницы онгоингов: {str(e)}")
            return []

    def load_from_cache(self) -> Optional[Dict]:
        """Загрузка данных из кэша"""
        try:
            if not os.path.exists(CACHE_FILE):
                print("Файл кэша не существует")
                return None

            if os.path.getsize(CACHE_FILE) == 0:
                print("Файл кэша пуст")
                return None

            file_time = os.path.getmtime(CACHE_FILE)
            if (time.time() - file_time) > (CACHE_EXPIRE_MINUTES * 60):
                print("Кэш устарел")
                return None

            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print("Данные успешно загружены из кэша")
                return data
        except json.JSONDecodeError:
            print("Ошибка декодирования JSON в файле кэша")
            return None
        except Exception as e:
            print(f"Неожиданная ошибка при загрузке кэша: {str(e)}")
            return None

    def save_to_cache(self, data: Dict) -> bool:
        """Сохранение данных в кэш"""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Данные успешно сохранены в кэш ({CACHE_FILE})")
            return True
        except Exception as e:
            print(f"Ошибка при сохранении в кэш: {str(e)}")
            return False

    def get_data(self, use_cache: bool = True) -> Dict:
        """Основной метод получения данных"""
        # Проверяем кэш
        if use_cache:
            cached_data = self.load_from_cache()
            if cached_data:
                return cached_data

        # Получаем свежие данные
        news_html = self.make_request('https://shikimori.one/news')
        time.sleep(REQUEST_DELAY)
        ongoing_html = self.make_request('https://shikimori.one/ongoings')

        result = {
            'timestamp': datetime.now().isoformat(),
            'news': self.parse_news_page(news_html) if news_html else [],
            'episodes': self.parse_ongoings_page(ongoing_html) if ongoing_html else [],
            'status': 'success' if (news_html or ongoing_html) else 'error'
        }

        # Сохраняем в кэш только если есть данные
        if result['news'] or result['episodes']:
            self.save_to_cache(result)
        else:
            print("Нет данных для сохранения в кэш")

        return result

    def debug_page_content(self, url: str, filename: str = 'debug_page.html'):
        """Сохраняет HTML страницу для диагностики"""
        html = self.make_request(url)
        if html:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Страница сохранена как {filename}")
        else:
            print("Не удалось получить страницу для диагностики")


if __name__ == "__main__":
    print("=== Запуск парсера Shikimori ===")
    parser = ShikimoriParser()

    # Для диагностики
    # parser.debug_page_content('https://shikimori.one/news', 'debug_news.html')
    # parser.debug_page_content('https://shikimori.one/ongoings', 'debug_ongoings.html')

    print("\nПолучаем данные...")
    data = parser.get_data()

    if not data.get('news') and not data.get('episodes'):
        print("\n⚠️ Внимание: не удалось получить данные!")
        print("Возможные причины:")
        print("- Проблемы с интернет-соединением")
        print("- Изменилась структура сайта")
        print("- Сайт временно недоступен")
    else:
        print("\n=== Последние новости ===")
        for i, news_item in enumerate(data['news'][:], 1):
            print(f"\n{i}. Дата: {news_item['date']}")
            print(f"   Заголовок: {news_item['title']}")
            print(f"   Содержание: {news_item['content'][:100]}...")

        print("\n=== Ближайшие выходы серий ===")
        for i, episode in enumerate(data['episodes'][:], 1):
            print(f"\n{i}. Аниме: {episode['title']}")
            print(f"   Информация: {episode['episode_info']}")

    print(f"\nСтатус: {data.get('status', 'unknown')}")
    print(f"Время обновления: {data.get('timestamp', 'неизвестно')}")