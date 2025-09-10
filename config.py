"""
Файл конфигурации для приложения поиска автомобилей
Содержит настройки подключения к базам данных и другие конфигурационные параметры
"""

import os
from flask_pymongo import PyMongo
import redis

class Config:
    """Основные настройки приложения"""
    
    # MongoDB настройки
    MONGODB_HOST = "46.101.121.75"
    MONGODB_PORT = 27017
    MONGODB_USERNAME = "root"
    MONGODB_PASSWORD = "otlehjoq543680"
    MONGODB_DATABASE = "Auto"
    MONGODB_AUTH_SOURCE = "admin"
    
    # Формируем URI для MongoDB
    MONGO_URI = f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_HOST}:{MONGODB_PORT}/{MONGODB_DATABASE}?authSource={MONGODB_AUTH_SOURCE}&directConnection=true"
    
    # Названия коллекций MongoDB
    COLLECTION_CURRENT_AUTO = "CurrentAuto"  # Коллекция с подписками пользователей на автомобили
    
    # Redis настройки
    REDIS_HOST = "46.101.121.75"
    REDIS_PORT = 6379
    REDIS_PASSWORD = "otlehjoq"
    
    # Flask настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'auto-search-secret-key'
    DEBUG = True

class DatabaseConnections:
    """Класс для управления подключениями к базам данных"""
    
    def __init__(self, app=None):
        self.mongo = None
        self.redis_client = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Инициализация подключений к базам данных"""
        # Настройка MongoDB
        app.config["MONGO_URI"] = Config.MONGO_URI
        self.mongo = PyMongo(app)
        
        # Настройка Redis
        self.redis_client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            password=Config.REDIS_PASSWORD,
            decode_responses=True
        )
        
    def get_mongo(self):
        """Получить объект MongoDB"""
        return self.mongo
    
    def get_redis(self):
        """Получить объект Redis"""
        return self.redis_client

# Создаем экземпляр для использования в приложении
db_connections = DatabaseConnections()
