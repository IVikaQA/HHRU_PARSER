from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import List, Dict
import re

@dataclass
class VacancyStats:
    total_count: int = 0
    companies: Counter = field(default_factory=Counter)
    salary_ranges: defaultdict = field(default_factory=lambda: defaultdict(int))
    work_formats: Counter = field(default_factory=Counter)
    avg_responses: float = 0
    
    def calculate_salary_ranges(self, vacancies: List[Dict]):
        """Группировка зарплат по диапазонам"""
        ranges = {
            '0-50k': 0,
            '50-100k': 0,
            '100-150k': 0,
            '150-200k': 0,
            '200k+': 0
        }
        
        for vac in vacancies:
            salary = vac.get('salary', '')
            # Извлекаем числа из строки зарплаты
            numbers = re.findall(r'\d+', salary)
            if numbers:
                amount = int(numbers[0])
                if amount < 50000:
                    ranges['0-50k'] += 1
                elif amount < 100000:
                    ranges['50-100k'] += 1
                elif amount < 150000:
                    ranges['100-150k'] += 1
                elif amount < 200000:
                    ranges['150-200k'] += 1
                else:
                    ranges['200k+'] += 1
        
        self.salary_ranges = ranges
    
    def calculate_avg_responses(self, vacancies: List[Dict]):
        responses = [v.get('responses', 0) for v in vacancies if v.get('responses')]
        self.avg_responses = sum(responses) / len(responses) if responses else 0