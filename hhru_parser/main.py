import argparse
import asyncio
from hhru_parser.src.methods.hhtp import HHParser
from hhru_parser.src.methods.db import Database
from tqdm import tqdm
from collections import Counter
from dataclasses import dataclass
import matplotlib.pyplot as plt
import sys

def main():
    parser = argparse.ArgumentParser(description='Парсер вакансий hh.ru')
    parser.add_argument('query', type=str, help='Поисковый запрос (например: "ML Engineer AND NLP")')
    parser.add_argument('--pages', type=int, default=1, help='Количество страниц для парсинга')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--plot', action='store_true', help='Построить графики')
    parser.add_argument('--no-cache', action='store_true', help='Не использовать кеш')
    
    args = parser.parse_args()
    
    # Запуск парсера
    vacancies = asyncio.run(run_parser(args.query, args.pages, args.no_cache))
    
    if not vacancies:
        print("❌ Вакансии не найдены")
        sys.exit(1)
    
    print(f"\n✅ Найдено вакансий: {len(vacancies)}")
    
    # Показываем топ-5
    print("\n📋 ТОП-5 ВАКАНСИЙ:")
    for i, vac in enumerate(vacancies[:5], 1):
        print(f"\n{i}. {vac.get('title', 'Нет названия')}")
        print(f"   Компания: {vac.get('company', 'Не указана')}")
        print(f"   Зарплата: {vac.get('salary', 'Не указана')}")
        print(f"   Откликов: {vac.get('responses', 0)}")
        print(f"   Формат: {vac.get('work_format', 'Не указан')}")
    
    # Статистика
    if args.stats:
        from hhru_parser.src.methods.stats import VacancyStats
        stats = VacancyStats()
        stats.total_count = len(vacancies)
        
        for vac in vacancies:
            if vac.get('company'):
                stats.companies[vac['company']] += 1
            if vac.get('work_format'):
                stats.work_formats[vac['work_format']] += 1
        
        stats.calculate_salary_ranges(vacancies)
        stats.calculate_avg_responses(vacancies)
        
        print(f"\n📊 РАСШИРЕННАЯ СТАТИСТИКА:")
        print(f"Всего вакансий: {stats.total_count}")
        print(f"\nТоп 5 компаний:")
        for company, count in stats.companies.most_common(5):
            print(f"  • {company}: {count} вакансий")
        
        print(f"\nРаспределение зарплат:")
        for range_name, count in stats.salary_ranges.items():
            if count > 0:
                print(f"  • {range_name}: {count} вакансий")
        
        print(f"\nФорматы работы:")
        for format_name, count in stats.work_formats.most_common():
            print(f"  • {format_name}: {count} вакансий")
        
        print(f"\nСреднее количество откликов: {stats.avg_responses:.1f}")
    
    # Графики
    if args.plot:
        plot_statistics(vacancies)

async def run_parser(query: str, pages: int, no_cache: bool):
    """Запуск парсера с кешированием"""
    db = Database()
    
    # Проверяем кеш
    if not no_cache:
        cached = db.get_cached_vacancies(query)
        if cached:
            print(f"📦 Найдено {len(cached)} вакансий в кеше")
            use_cache = input("Использовать кеш? (y/n): ").lower() == 'y'
            if use_cache:
                return cached
    
    # Парсим новые вакансии
    parser = HHParser()
    vacancies = []
    
    with tqdm(total=pages, desc="Парсинг страниц") as pbar:
        for page in range(pages):
            page_vacancies = await parser.search_vacancies(query, start_page=page, per_page=1)
            vacancies.extend(page_vacancies)
            pbar.update(1)
    
    # Сохраняем в БД
    if vacancies:
        db.save_vacancies(query, vacancies)
        print(f"💾 Сохранено {len(vacancies)} вакансий в базу данных")
    
    return vacancies

def plot_statistics(vacancies: list):
    """Построение расширенных графиков"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. Топ компаний
    companies = [vac.get('company', 'Unknown') for vac in vacancies if vac.get('company')]
    company_counts = Counter(companies)
    top_companies = dict(company_counts.most_common(10))
    
    axes[0, 0].barh(list(top_companies.keys()), list(top_companies.values()))
    axes[0, 0].set_xlabel('Количество вакансий')
    axes[0, 0].set_title('Топ-10 компаний по количеству вакансий')
    
    # 2. Распределение откликов
    responses = [vac.get('responses', 0) for vac in vacancies]
    axes[0, 1].hist(responses, bins=20, edgecolor='black')
    axes[0, 1].set_xlabel('Количество откликов')
    axes[0, 1].set_ylabel('Количество вакансий')
    axes[0, 1].set_title('Распределение откликов на вакансии')
    
    # 3. Форматы работы
    formats = [vac.get('work_format', 'Не указан') for vac in vacancies]
    format_counts = Counter(formats)
    axes[1, 0].pie(format_counts.values(), labels=format_counts.keys(), autopct='%1.1f%%')
    axes[1, 0].set_title('Форматы работы')
    
    # 4. Зарплаты по компаниям (топ-5)
    top5_companies = [c for c, _ in company_counts.most_common(5)]
    salaries_by_company = defaultdict(list)
    
    for vac in vacancies:
        if vac.get('company') in top5_companies:
            salary = vac.get('salary', '')
            import re
            numbers = re.findall(r'\d+', salary)
            if numbers:
                salaries_by_company[vac['company']].append(int(numbers[0]))
    
    if salaries_by_company:
        axes[1, 1].boxplot(salaries_by_company.values(), labels=salaries_by_company.keys())
        axes[1, 1].set_ylabel('Зарплата (тыс. руб)')
        axes[1, 1].set_title('Распределение зарплат по компаниям')
        axes[1, 1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()