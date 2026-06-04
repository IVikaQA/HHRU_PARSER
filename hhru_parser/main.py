import argparse
import asyncio
from hhru_parser.src.methods.hh_pars import HHParser      
from hhru_parser.src.methods.bd import Database           
from tqdm import tqdm
from collections import Counter
import matplotlib.pyplot as plt
import sys

def main():
    parser = argparse.ArgumentParser(description='Парсер вакансий hh.ru')
    parser.add_argument('query', type=str, help='Поисковый запрос (например: "ML Engineer AND NLP")')
    parser.add_argument('--pages', type=int, default=1, help='Количество страниц для парсинга')
    parser.add_argument('--per-page', type=int, default=5, help='Вакансий на странице (топ-N)')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--grafik', action='store_true', help='Построить график топ-10 компаний')
    parser.add_argument('--no-cache', action='store_true', help='Не использовать кеш')
    
    args = parser.parse_args()
    
    # Запуск парсера
    vacancies = asyncio.run(run_parser(args.query, args.pages, args.per_page, args.no_cache))
    
    if not vacancies:
        print("Вакансии не найдены")
        sys.exit(1)
    
    print(f"\n Найдено вакансий: {len(vacancies)}")
    
    # Показываем топ-5
    print("\n ТОП-5 ВАКАНСИЙ:")
    for i, vac in enumerate(vacancies[:5], 1):
        print(f"\n{i}. {vac.get('title', 'Нет названия')}")
        print(f"   Компания: {vac.get('company', 'Не указана')}")
        print(f"   Зарплата: {vac.get('salary', 'Не указана')}")
        print(f"   Город: {vac.get('city', 'Не указан')}")
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
            if vac.get('city'):
                stats.cities[vac['city']] += 1
        
        stats.calculate_salary_ranges(vacancies)
        stats.calculate_avg_responses(vacancies)
        
        print(f"\n РАСШИРЕННАЯ СТАТИСТИКА:")
        print(f"Всего вакансий: {stats.total_count}")
        
        print(f"\n Топ 5 компаний:")
        for company, count in stats.companies.most_common(5):
            print(f"  • {company}: {count} вакансий")
        
        print(f"\n Распределение зарплат:")
        for range_name, count in stats.salary_ranges.items():
            if count > 0:
                print(f"  • {range_name}: {count} вакансий")
        
        print(f"\n Форматы работы:")
        for format_name, count in stats.work_formats.most_common():
            print(f"  • {format_name}: {count} вакансий")
        
        print(f"\n Топ 3 города:")
        for city, count in stats.cities.most_common(3):
            print(f"  • {city}: {count} вакансий")
        
        print(f"\n Среднее количество откликов: {stats.avg_responses:.1f}")
    
    # График
    if args.grafik:
        grafik_companies_chart(vacancies)

async def run_parser(query: str, pages: int, per_page: int, no_cache: bool):
    """Запуск парсера с кешированием"""
    db = Database()
    
    # Проверяем кеш
    if not no_cache:
        cached = db.get_cached_vacancies(query)
        if cached:
            print(f" Найдено {len(cached)} вакансий в кеше")
            use_cache = input("Использовать кеш? (y/n): ").lower() == 'y'
            if use_cache:
                db.close()
                return cached
    
    # Парсим новые вакансии
    parser = HHParser()
    vacancies = []
    
    with tqdm(total=pages, desc="Парсинг страниц") as pbar:
        for page in range(pages):
            page_vacancies = await parser.search_vacancies(query, page_num=page, per_page=per_page)
            vacancies.extend(page_vacancies)
            pbar.update(1)
    
    # Сохраняем в БД
    if vacancies:
        db.save_vacancies(query, vacancies)
        print(f" Сохранено {len(vacancies)} вакансий в базу данных")
    
    db.close()
    return vacancies

def grafik_companies_chart(vacancies: list):
    """Построение графика топ-10 компаний"""
    
    # Собираем компании (исключая "Не указано")
    companies = [vac.get('company', '') for vac in vacancies 
                if vac.get('company') and vac.get('company') != "Не указано"]
    
    if not companies:
        print("\n Нет данных о компаниях для построения графика")
        return
    
    # Подсчитываем количество вакансий по компаниям
    company_counts = Counter(companies)
    top_companies = dict(company_counts.most_common(10))
    
    # Создаем график
    plt.figure(figsize=(12, 8))
    
    # Строим горизонтальную гистограмму
    bars = plt.barh(list(top_companies.keys()), list(top_companies.values()))
    
    # Настройка внешнего вида
    plt.xlabel('Количество вакансий', fontsize=12)
    plt.ylabel('Компании', fontsize=12)
    plt.title(f'Топ-10 компаний по количеству вакансий\n(всего вакансий: {len(vacancies)})', 
              fontsize=14, fontweight='bold')
    
    # Добавляем значения на бары
    for i, (company, count) in enumerate(top_companies.items()):
        plt.text(count + 0.2, i, str(count), va='center', fontsize=10)
    
    # Раскрашиваем бары
    colors = plt.cm.Set3(range(len(top_companies)))
    for bar, color in zip(bars, colors):
        bar.set_color(color)
    
    # Настраиваем сетку
    plt.grid(True, alpha=0.3, axis='x')
    
    # Убираем верхнюю и правую границу
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()