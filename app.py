from flask import Flask, render_template, jsonify, request, redirect, url_for
import logging
from datetime import datetime
import json
import ast
from config import Config, db_connections

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация подключений к базам данных
db_connections.init_app(app)
mongo = db_connections.get_mongo()
redis_client = db_connections.get_redis()

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
        sub = mongo.db[Config.COLLECTION_CURRENT_AUTO].find_one({'user_id': str(user_id)})
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
        result = mongo.db[Config.COLLECTION_CURRENT_AUTO].insert_one({
            'brand': data.get('brand'),
            'model': data.get('model'),
            'year_min': data.get('year_min'),
            'year_max': data.get('year_max'),
            'price_min': data.get('price_min'),
            'price_max': data.get('price_max'),
            'mileage_min': data.get('mileage_min'),
            'mileage_max': data.get('mileage_max'),
            'fuel_type': data.get('fuel_type'),
            'power_min': data.get('power_min'),
            'power_max': data.get('power_max'),
            'gearbox': data.get('gearbox'),
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
            search_filter['year_min'] = {'$gte': int(year_from)}
        if year_to:
            search_filter['year_max'] = {'$lte': int(year_to)}
        if price_from:
            search_filter['price_min'] = {'$gte': float(price_from)}
        if price_to:
            search_filter['price_max'] = {'$lte': float(price_to)}
        if mileage_from:
            search_filter['mileage_min'] = {'$gte': float(mileage_from)}
        if mileage_to:
            search_filter['mileage_max'] = {'$lte': float(mileage_to)}
        if fuel_type:
            search_filter['fuel_type'] = fuel_type
        if power_from:
            search_filter['power_min'] = {'$gte': float(power_from)}
        if power_to:
            search_filter['power_max'] = {'$lte': float(power_to)}
        if transmission:
            search_filter['gearbox'] = transmission

        # Ищем автомобили по фильтру
        autos = list(mongo.db[Config.COLLECTION_CURRENT_AUTO].find(search_filter))
        
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
        if mongo.db[Config.COLLECTION_CURRENT_AUTO].find_one({'user_id': str(user_id)}):
            return jsonify({'success': False, 'error': 'Уже есть подписка'}), 400
        
        # Преобразуем данные в требуемый формат
        formatted_data = {
            'brand': data.get('brand', ''),
            'model': data.get('model', ''),
            'year_min': data.get('year_from', ''),
            'year_max': data.get('year_to', ''),
            'price_min': data.get('price_from', ''),
            'price_max': data.get('price_to', ''),
            'mileage_min': data.get('mileage_from', ''),
            'mileage_max': data.get('mileage_to', ''),
            'fuel_type': data.get('fuel_type', ''),
            'power_min': data.get('power_from', ''),
            'power_max': data.get('power_to', ''),
            'gearbox': data.get('transmission', ''),
            'user_id': str(user_id)
        }
        
        # Удаляем лишнее поле UserID если оно есть
        if 'UserID' in formatted_data:
            del formatted_data['UserID']
            
        mongo.db[Config.COLLECTION_CURRENT_AUTO].insert_one(formatted_data)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error subscribing auto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/my_auto')
def my_auto():
    try:
        user_id = request.args.get('user_id')
        sub = mongo.db[Config.COLLECTION_CURRENT_AUTO].find_one({'user_id': str(user_id)})
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
        mongo.db[Config.COLLECTION_CURRENT_AUTO].delete_one({'user_id': str(user_id)})
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error unsubscribing auto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)