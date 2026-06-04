import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, List
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HHParser:
    #Инициализация параметров парсера
    def __init__(self):
        self.base_url = "https://hh.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        self.delay = 1
        self.is_banned = False

    #Поиск вакансий на одной странице    
    async def search_vacancies(self, query: str, page_num: int = 0, per_page: int = 5) -> List[Dict]:
        if self.is_banned:
            logger.warning(f"Бан! Ждем {self.delay} секунд...")
            await asyncio.sleep(self.delay)
            self.delay *= 2
            self.is_banned = False
        
        url = f"{self.base_url}/search/vacancy"
        params = {
            'text': query,
            'page': page_num,
            'items_on_page': 20
        }
        
        try:
            # Создаем connector с отключенным SSL для macOS
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        vacancies = []
                        # Пробуем разные селекторы для поиска карточек вакансий
                        vacancy_cards = soup.find_all('div', {'data-qa': 'vacancy-serp__vacancy'})
                        if not vacancy_cards:
                            vacancy_cards = soup.find_all('div', class_=re.compile(r'vacancy-card'))
                        if not vacancy_cards:
                            vacancy_cards = soup.find_all('div', class_='serp-item')
                        if not vacancy_cards:
                            vacancy_cards = soup.find_all('div', class_='vacancy-serp-item')
                        
                        logger.info(f"Найдено {len(vacancy_cards)} вакансий на странице {page_num}")
                        
                        for card in vacancy_cards[:per_page]:
                            vacancy_data = await self._parse_vacancy_card(card)
                            if vacancy_data:
                                vacancies.append(vacancy_data)
                        
                        self.delay = max(1, self.delay * 0.8)
                        await asyncio.sleep(self.delay)
                        return vacancies
                        
                    elif response.status == 403:
                        self.is_banned = True
                        logger.error(f"Получили бан! Статус: {response.status}")
                        await asyncio.sleep(self.delay)
                        return []
                    else:
                        logger.error(f"Ошибка {response.status}")
                        return []
                       
        except Exception as e:
            logger.error(f"Ошибка при запросе: {e}")
            await asyncio.sleep(self.delay * 2)
            return []
    
    #Парсинг одной карточки вакансий
    async def _parse_vacancy_card(self, card) -> Dict:
        try:
            # Название вакансии
            title_elem = None
            title_selectors = [
                ('a', {'href': re.compile(r'/vacancy/\d+')}),
                ('a', {'data-qa': 'vacancy-serp__vacancy-title'}),
                ('a', {'class': 'serp-item__title'}),
                ('h3', {'class': 'bloko-header-section-3'})
            ]
            
            for tag, attrs in title_selectors:
                title_elem = card.find(tag, attrs)
                if title_elem:
                    break
            
            title = title_elem.text.strip() if title_elem else "Не указано"
            
            # Компания
            company = "Не указано"
            company_selectors = [
                ('span', {'data-qa': 'vacancy-serp__vacancy-employer'}),
                ('a', {'data-qa': 'vacancy-serp__vacancy-employer'}),
                ('div', {'class': 'bloko-text'}),
                ('span', {'class': 'company-name'}),
                ('div', {'data-qa': 'vacancy-serp__vacancy-employer-text'})
            ]
            
            for tag, attrs in company_selectors:
                company_elem = card.find(tag, attrs)
                if company_elem:
                    company = company_elem.text.strip()
                    break
            
            # Зарплата
            salary = "Не указано"
            salary_selectors = [
                ('span', {'data-qa': 'vacancy-serp__vacancy-compensation'}),
                ('span', {'class': 'bloko-text'}),
                ('div', {'data-qa': 'vacancy-serp__vacancy-compensation'}),
                ('span', {'class': 'fake-magritte-primary-text--Hd8jM'})  # новый селектор
            ]
            
            for tag, attrs in salary_selectors:
                salary_elem = card.find(tag, attrs)
                if salary_elem:
                    salary = salary_elem.text.strip()
                    break
            
            # Город
            city = "Не указан"
            city_selectors = [
                ('span', {'data-qa': 'vacancy-serp__vacancy-address'}),
                ('div', {'data-qa': 'vacancy-serp__vacancy-address'}),
                ('span', {'class': 'fake-magritte-primary-text--Hd8jM'}),
                ('span', {'data-qa': 'vacancy-serp__vacancy-location'})
            ]
            
            for tag, attrs in city_selectors:
                city_elem = card.find(tag, attrs)
                if city_elem:
                    city = city_elem.text.strip()
                    break
            
            # URL вакансии
            url = None
            if title_elem and title_elem.get('href'):
                url = title_elem.get('href')
                if not url.startswith('http'):
                    url = self.base_url + url
            
            # Получаем детальную информацию
            details = {}
            if url:
                details = await self.get_vacancy_details(url)
                await asyncio.sleep(0.3)
            
            return {
                'title': title,
                'company': company,
                'salary': salary,
                'city': city,
                'url': url,
                'responses': details.get('responses', 0),
                'work_format': details.get('work_format', 'Не указан'),
                'description': details.get('description', '')
            }
        except Exception as e:
            logger.error(f"Ошибка парсинга карточки: {e}")
            return {}

    #Получение деталей вакансии
    async def get_vacancy_details(self, url: str) -> Dict:
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Количество откликов
                        responses = 0
                        responses_selectors = [
                            ('span', {'data-qa': 'vacancy-view-creation-stats'}),
                            ('span', {'class': 'vacancy-creation-stats'}),
                            ('div', {'data-qa': 'vacancy-view-creation-stats'})
                        ]
                        
                        for tag, attrs in responses_selectors:
                            responses_elem = soup.find(tag, attrs)
                            if responses_elem:
                                responses_text = responses_elem.text
                                responses = self._extract_number(responses_text)
                                break
                        
                        # Формат работы
                        work_format = "Не указан"
                        format_selectors = [
                            ('span', {'data-qa': 'vacancy-view-employment-mode'}),
                            ('span', {'data-qa': 'vacancy-view-schedule'}),
                            ('p', {'data-qa': 'vacancy-view-schedule'}),
                            ('div', {'data-qa': 'vacancy-view-work-schedule'})
                        ]
                        
                        for tag, attrs in format_selectors:
                            format_elem = soup.find(tag, attrs)
                            if format_elem:
                                work_format = format_elem.text.strip()
                                break
                        
                        # Описание
                        description = ""
                        description_elem = soup.find('div', {'data-qa': 'vacancy-description'})
                        if description_elem:
                            description = description_elem.text.strip()[:500]
                        else:
                            description_elem = soup.find('div', {'class': 'vacancy-description'})
                            if description_elem:
                                description = description_elem.text.strip()[:500]
                        
                        return {
                            'responses': responses,
                            'work_format': work_format,
                            'description': description
                        }
        except Exception as e:
            logger.error(f"Ошибка при получении деталей: {e}")
        
        return {'responses': 0, 'work_format': 'Не указан', 'description': ''}

    #Извлечение числа из текста
    def _extract_number(self, text: str) -> int:
        """Извлекает число из текста"""
        if not text:
            return 0
        numbers = re.findall(r'\d+', text.replace(' ', ''))
        return int(numbers[0]) if numbers else 0