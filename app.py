from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_pymongo import PyMongo
import logging
import redis
from datetime import datetime
import json
import ast

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация MongoDB
app.config["MONGO_URI"] = "mongodb://root:otlehjoq543680@46.101.121.75:27017/Auto?authSource=admin&directConnection=true"
mongo = PyMongo(app)

# Конфигурация Redis
redis_client = redis.Redis(
    host='46.101.121.75',
    port=6379,
    password='otlehjoq',
    decode_responses=True
)

def check_user_registration(user_id):
    try:
        # Проверяем существование пользователя в Redis
        user_data = redis_client.hgetall(f'auto:user:{user_id}')
        logger.debug(f"Redis data for user {user_id}: {user_data}")
        
        # Проверяем наличие данных и статус регистрации
        registration_complete = (
            bool(user_data) and 
            user_data.get('current_step') == 'complete'
        )
        
        if not registration_complete:
            logger.debug(f"Registration check failed for user {user_id}. Data: {user_data}")
            
        return registration_complete
    except Exception as e:
        logger.error(f"Error checking Redis: {str(e)}")
        return False

def check_admin_access(user_id):
    try:
        # Получаем значение Admin из Redis
        admin_id = redis_client.hget('beer:setting', 'Admin')
        logger.debug(f"Admin ID from Redis: {admin_id}, User ID: {user_id}")
        return str(user_id) == str(admin_id)
    except Exception as e:
        logger.error(f"Error checking admin access: {str(e)}")
        return False

@app.route('/check-auth')
def check_auth():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"authorized": False, "error": "No user ID provided"})
        
        is_registered = check_user_registration(user_id)
        return jsonify({"authorized": is_registered})
    except Exception as e:
        logger.error(f"Error in check-auth: {str(e)}")
        return jsonify({"authorized": False, "error": str(e)})

@app.route('/')
def index():
    try:
        user_id = request.args.get('user_id')
        if not user_id or not check_user_registration(user_id):
            return render_template('unauthorized.html')
        # Проверка подписки пользователя
        sub = mongo.db.CurrentAuto.find_one({'user_id': str(user_id)})
        if sub:
            return redirect(url_for('my_auto', user_id=user_id))
        return render_template('main_menu.html', user_id=user_id)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/add_auto', methods=['POST'])
def add_auto():
    try:
        data = request.json
        # Добавляем автомобиль в коллекцию CurrentAuto
        result = mongo.db.CurrentAuto.insert_one({
            'brand': data.get('brand'),
            'model': data.get('model'),
            'year': data.get('year'),
            'price': data.get('price'),
            'mileage': data.get('mileage'),
            'fuel_type': data.get('fuel_type'),
            'power': data.get('power'),
            'transmission': data.get('transmission'),
            'created_at': datetime.now()
        })
        
        return jsonify({"success": True, "id": str(result.inserted_id)})
    except Exception as e:
        logger.error(f"Error adding auto: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/search_auto')
def search_auto():
    try:
        brand = request.args.get('brand')
        model = request.args.get('model')
        year_from = request.args.get('year_from')
        year_to = request.args.get('year_to')
        price_from = request.args.get('price_from')
        price_to = request.args.get('price_to')
        mileage_from = request.args.get('mileage_from')
        mileage_to = request.args.get('mileage_to')
        fuel_type = request.args.get('fuel_type')
        power_from = request.args.get('power_from')
        power_to = request.args.get('power_to')
        transmission = request.args.get('transmission')

        # Создаем фильтр для поиска
        search_filter = {}
        if brand:
            search_filter['brand'] = brand
        if model:
            search_filter['model'] = model
        if year_from:
            search_filter['year'] = {'$gte': int(year_from)}
        if year_to:
            if 'year' in search_filter:
                search_filter['year']['$lte'] = int(year_to)
            else:
                search_filter['year'] = {'$lte': int(year_to)}
        if price_from:
            search_filter['price'] = {'$gte': float(price_from)}
        if price_to:
            if 'price' in search_filter:
                search_filter['price']['$lte'] = float(price_to)
            else:
                search_filter['price'] = {'$lte': float(price_to)}
        if mileage_from:
            search_filter['mileage'] = {'$gte': float(mileage_from)}
        if mileage_to:
            if 'mileage' in search_filter:
                search_filter['mileage']['$lte'] = float(mileage_to)
            else:
                search_filter['mileage'] = {'$lte': float(mileage_to)}
        if fuel_type:
            search_filter['fuel_type'] = fuel_type
        if power_from:
            search_filter['power'] = {'$gte': float(power_from)}
        if power_to:
            if 'power' in search_filter:
                search_filter['power']['$lte'] = float(power_to)
            else:
                search_filter['power'] = {'$lte': float(power_to)}
        if transmission:
            search_filter['transmission'] = transmission

        # Ищем автомобили по фильтру
        autos = list(mongo.db.CurrentAuto.find(search_filter))
        
        # Преобразуем ObjectId в строку для JSON
        for auto in autos:
            auto['_id'] = str(auto['_id'])
            if 'created_at' in auto:
                auto['created_at'] = auto['created_at'].isoformat()

        return jsonify(autos)
    except Exception as e:
        logger.error(f"Error searching autos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_catalog')
def get_catalog():
    try:
        catalog_raw = redis_client.get('auto:catalog')
        if not catalog_raw:
            return jsonify([])
        try:
            items = ast.literal_eval(f'[{catalog_raw}]')
            items = [str(x) for x in items]
        except Exception as parse_err:
            logger.error(f"Catalog parse error: {parse_err}, raw: {catalog_raw}")
            items = [x.strip().strip('"') for x in catalog_raw.split(',')]
        return jsonify(items)
    except Exception as e:
        logger.error(f"Error getting catalog: {str(e)}")
        return jsonify([]), 500

@app.route('/subscribe_auto', methods=['POST'])
def subscribe_auto():
    try:
        data = request.json
        user_id = request.args.get('user_id') or data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Нет user_id'}), 400
        # Проверяем, есть ли уже подписка
        if mongo.db.CurrentAuto.find_one({'user_id': str(user_id)}):
            return jsonify({'success': False, 'error': 'Уже есть подписка'}), 400
        # Гарантируем, что все поля есть
        for field in ['brand', 'model', 'year_from', 'year_to', 'price_from', 'price_to', 
                     'mileage_from', 'mileage_to', 'fuel_type', 'power_from', 'power_to', 'transmission']:
            if field not in data:
                data[field] = ''
        data['user_id'] = str(user_id)
        # Удаляем лишнее поле UserID если оно есть
        if 'UserID' in data:
            del data['UserID']
        mongo.db.CurrentAuto.insert_one(data)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error subscribing auto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/my_auto')
def my_auto():
    try:
        user_id = request.args.get('user_id')
        sub = mongo.db.CurrentAuto.find_one({'user_id': str(user_id)})
        if not sub:
            return redirect(url_for('index', user_id=user_id))
        return render_template('my_auto.html', auto=sub, user_id=user_id)
    except Exception as e:
        logger.error(f"Error in my_auto: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/unsubscribe_auto', methods=['POST'])
def unsubscribe_auto():
    try:
        user_id = request.args.get('user_id') or request.json.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Нет user_id'}), 400
        mongo.db.CurrentAuto.delete_one({'user_id': str(user_id)})
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error unsubscribing auto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)