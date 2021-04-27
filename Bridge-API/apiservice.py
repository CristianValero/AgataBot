from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from routes.agata import AgataRouter
from routes.auth import AuthRouter

API_ADRESS_SOURCES = {
    'translator': {
        'es': 'http://0.0.0.0:3002/translator/es/',
        'en': 'http://0.0.0.0:3002/translator/en/'
    },
    'agata': {
        'answer': 'http://0.0.0.0:3001/agata/answer/'
    }
}

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = 'Th1s1ss3cr3t'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://///home/cristian/Desktop/AgataBot-v2/AgataBot/Bridge-API/authapi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.Integer)
    email = db.Column(db.String(150))
    password = db.Column(db.String(50))

routers = [
    AuthRouter('AuthRouter', app, db, Users, API_ADRESS_SOURCES),
    AgataRouter('AgataRouter', app, db, Users, API_ADRESS_SOURCES)
]

@app.route('/', methods=['GET', 'POST'])
def home_route():
    return jsonify({
        'message': 'Welcome to the Bridge API.',
        'info': 'This API intercommunicates all the rest of the microservices in the network to balance and distribute all the incoming requests.',
        'developer': 'Cristian Valero Abundio'
    }), 200

@app.errorhandler(404)
def route_not_found(exc):
    return jsonify({
        'code': 404,
        'message': 'The route you requested not found. Please, try again or contact with an administrator.'
    }), 404

if __name__ == '__main__':
    for router in routers:
         app.register_blueprint(router.config_routes())
    app.run(host='0.0.0.0', port=3000)