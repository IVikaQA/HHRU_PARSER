import sqlite3
from datetime import datetime
from typing import List, Dict

class Database:
    #Инициализация подключения к БД
    def __init__(self, db_path="vacancies.db"):
        self.conn = sqlite3.connect(db_path) 
        self.init_db()
    
    #Создание таблицы для хранения вакансий
    def init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS vacancies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    title TEXT,
                    company TEXT,
                    salary TEXT,
                    city TEXT,
                    url TEXT,
                    responses INTEGER,
                    work_format TEXT,
                    description TEXT,
                    parsed_at TIMESTAMP,
                    UNIQUE(query, url)
                )
            """)
    #Сохранение вакансий в таблице vacancies
    def save_vacancies(self, query: str, vacancies: List[Dict]):
        with self.conn:
            for vac in vacancies:
                self.conn.execute("""
                    INSERT OR REPLACE INTO vacancies 
                    (query, title, company, salary, city, url, responses, work_format, description, parsed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    query,
                    vac.get('title'),
                    vac.get('company'),
                    vac.get('salary'),
                    vac.get('city'),
                    vac.get('url'),
                    vac.get('responses', 0),
                    vac.get('work_format', 'Не указан'),
                    vac.get('description', ''),
                    datetime.now()
                ))
    #Получние кэшированных вакансий
    def get_cached_vacancies(self, query: str) -> List[Dict]:
        cursor = self.conn.execute(
            "SELECT * FROM vacancies WHERE query = ? ORDER BY parsed_at DESC",
            (query,)
        )
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    #Закрытие соединения с БД
    def close(self):
        self.conn.close()