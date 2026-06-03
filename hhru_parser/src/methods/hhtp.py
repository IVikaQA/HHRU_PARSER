import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import random

class HHParser:
    def __init__(self):
        self.base_url = "https://hh.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.delay = 1  # начальная задержка в секундах
        self.is_banned = False
        
    async def search_vacancies(self, query: str, pages: int = 1) -> List[Dict]:
        """Поиск вакансий по запросу"""
        vacancies = []
        
        for page in range(pages):
            if self.is_banned:
                print(f"Бан! Ждем {self.delay} секунд...")
                await asyncio.sleep(self.delay)
                self.delay *= 2  # удваиваем задержку при бане
                self.is_banned = False
            
            url = f"{self.base_url}/search/vacancy"
            params = {
                'text': query,
                'page': page,
                'items_on_page': 20
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=self.headers, params=params) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Парсим вакансии
                            vacancy_cards = soup.find_all('div', class_='vacancy-serp-item')
                            for card in vacancy_cards[:5]:  # топ-5 выдачи
                                vacancy_data = await self._parse_vacancy_card(card)
                                vacancies.append(vacancy_data)
                            
                            # Если успешно, уменьшаем задержку
                            self.delay = max(1, self.delay * 0.8)
                            await asyncio.sleep(self.delay)
                            
                        elif response.status == 403:
                            self.is_banned = True
                            print(f"Получили бан! Статус: {response.status}")
                            await asyncio.sleep(self.delay)
                        else:
                            print(f"Ошибка {response.status}")
                            
            except Exception as e:
                print(f"Ошибка при запросе: {e}")
                await asyncio.sleep(self.delay * 2)
                
        return vacancies
    
    async def _parse_vacancy_card(self, card) -> Dict:
    try:
        title_elem = card.find('a', class_='serp-item__title')
        title = title_elem.text if title_elem else "Не указано"
        
        company_elem = card.find('a', class_='bloko-link bloko-link_kind-tertiary')
        company = company_elem.text if company_elem else "Не указано"
        
        salary_elem = card.find('span', class_='bloko-header-section-3')
        salary = salary_elem.text if salary_elem else "Не указано"
        
        # Получаем детали по URL
        url = title_elem.get('href') if title_elem else None
        details = {}
        if url:
            details = await self.get_vacancy_details(url)
        
        return {
            'title': title,
            'company': company,
            'salary': salary,
            'url': url,
            **details  # добавляем responses, work_format, description
        }
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return {}

    async def get_vacancy_details(self, url: str) -> Dict:
    """Получение детальной информации о вакансии"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Количество откликов
                    responses_elem = soup.find('span', class_='vacancy-creation-stats')
                    responses_text = responses_elem.text if responses_elem else "0"
                    # Извлекаем число из текста "47 откликов"
                    responses = self._extract_number(responses_text)
                    
                    # Формат работы
                    work_format_elem = soup.find('span', {'data-qa': 'vacancy-view-employment-mode'})
                    work_format = work_format_elem.text if work_format_elem else "Не указан"
                    
                    # Описание
                    description_elem = soup.find('div', {'data-qa': 'vacancy-description'})
                    description = description_elem.text if description_elem else ""
                    
                    return {
                        'responses': responses,
                        'work_format': work_format,
                        'description': description
                    }
    except Exception as e:
        print(f"Ошибка при получении деталей: {e}")
        return {'responses': 0, 'work_format': 'Не указан', 'description': ''}

    def _extract_number(self, text: str) -> int:
        """Извлекает число из текста"""
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else 0