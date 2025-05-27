from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
import traceback
import json
import os
import ssl

app = Flask(__name__)
app.config['SECRET_KEY'] = 'paste your secret key here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class ChatData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_timestamp = db.Column(db.String(50), nullable=False)
    end_timestamp = db.Column(db.String(50), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                raise ValueError("User not found")
        except Exception as e:
            return jsonify({'error': 'Token is invalid', 'details': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
            
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': new_user.id
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"Database error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Database error occurred'}), 500
        
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
            
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return jsonify({'error': 'Invalid credentials'}), 401
            
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'])
        
        return jsonify({
            'token': token,
            'user_id': user.id,
            'message': 'Login successful'
        })
        
    except Exception as e:
        app.logger.error(f"Login error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/upload', methods=['POST'])
@token_required
def upload_data(current_user):
    try:
        data = request.get_json().get('data', [])
        if not isinstance(data, list):
            return jsonify({'error': 'Invalid data format'}), 400
            
        ChatData.query.filter_by(user_id=current_user.id).delete()
        
        for item in data:
            if not all(key in item for key in ['start_timestamp', 'end_timestamp', 'summary', 'embedding']):
                continue
                
            new_data = ChatData(
                user_id=current_user.id,
                start_timestamp=item['start_timestamp'],
                end_timestamp=item['end_timestamp'],
                summary=item['summary'],
                embedding=json.dumps(item['embedding'])
            )
            db.session.add(new_data)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(data)} chat records uploaded successfully'
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Database error during upload'}), 500
        
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error during upload'}), 500

@app.route('/api/download', methods=['GET'])
@token_required
def download_data(current_user):
    try:
        chat_data = ChatData.query.filter_by(user_id=current_user.id).all()
        
        data = []
        for item in chat_data:
            try:
                embedding = json.loads(item.embedding)
            except json.JSONDecodeError:
                embedding = []
                
            data.append({
                'start_timestamp': item.start_timestamp,
                'end_timestamp': item.end_timestamp,
                'summary': item.summary,
                'embedding': embedding
            })
        
        return jsonify({
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error during download'}), 500

def get_ssl_context():
    """Create SSL context for HTTPS"""
    cert_file = 'cert.pem'
    key_file = 'key.pem'
    
    # Check if certificate files exist
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print(f"Warning: Certificate files not found!")
        print(f"Looking for: {os.path.abspath(cert_file)} and {os.path.abspath(key_file)}")
        print("Please generate certificates using the provided script and place them in the same directory as app.py")
        return None
    
    try:
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        return context
    except Exception as e:
        print(f"Error loading SSL certificates: {str(e)}")
        return None

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Try to get SSL context
    ssl_context = get_ssl_context()
    
    if ssl_context:
        print("Starting Flask app with HTTPS on https://localhost:5000")
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=ssl_context)
    else:
        print("SSL certificates not found or invalid. Starting with HTTP on http://localhost:5000")
        print("To enable HTTPS, generate certificates and place cert.pem and key.pem in the same directory as app.py")
        app.run(host='0.0.0.0', port=5000, debug=True)