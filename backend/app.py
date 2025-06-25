from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, '..', 'frontend')

app = Flask(__name__, template_folder=TEMPLATES_DIR) 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)

# MODELOS
class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ciudad = db.Column(db.String(100), nullable=False)
    habitaciones = db.relationship('Habitacion', backref='hotel', lazy=True)

class Habitacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    capacidad = db.Column(db.Integer, nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    reservas = db.relationship('Reserva', backref='habitacion', lazy=True)

class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habitacion_id = db.Column(db.Integer, db.ForeignKey('habitacion.id'), nullable=False)
    fecha_inicio = db.Column(db.String(10), nullable=False)
    fecha_fin = db.Column(db.String(10), nullable=False)

class Tarifa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    tipo_habitacion = db.Column(db.String(50), nullable=False)
    temporada = db.Column(db.String(10), nullable=False)
    valor = db.Column(db.Float, nullable=False)

# ENDPOINTS

@app.route('/disponibilidad', methods=['GET'])
def disponibilidad():
    ciudad = request.args.get('ciudad')
    tipo = request.args.get('tipo')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    habitaciones = Habitacion.query.join(Hotel).filter(
        Hotel.ciudad == ciudad,
        Habitacion.tipo == tipo
    ).all()

    disponibles = []
    for h in habitaciones:
        reservas = Reserva.query.filter(
            Reserva.habitacion_id == h.id,
            Reserva.fecha_inicio <= fecha_fin,
            Reserva.fecha_fin >= fecha_inicio
        ).all()
        if not reservas:
            disponibles.append({
                'hotel': h.hotel.nombre,
                'tipo': h.tipo,
                'capacidad': h.capacidad,
                'id': h.id
            })

    return render_template('disponibilidad.html', resultados=disponibles, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)


@app.route('/tarifa', methods=['GET'])
def tarifa():
    ciudad = request.args.get('ciudad')
    personas = request.args.get('personas')
    habitaciones = request.args.get('habitaciones')
    tipo = request.args.get('tipo')
    temporada = request.args.get('temporada')

    if not ciudad or not personas or not habitaciones or not tipo or not temporada:
        return render_template('tarifa.html')

    try:
        personas = int(personas)
        habitaciones = int(habitaciones)
    except ValueError:
        return render_template('tarifa_resultado.html', error='Número de personas o habitaciones inválido')

    hotel = Hotel.query.filter_by(ciudad=ciudad).first()
    if not hotel:
        return render_template('tarifa_resultado.html', error='Hotel no encontrado')

    tarifa = Tarifa.query.filter_by(
        hotel_id=hotel.id,
        tipo_habitacion=tipo,
        temporada=temporada
    ).first()

    if tarifa:
        total = tarifa.valor * personas * habitaciones
        return render_template('tarifa_resultado.html', total=total)

    return render_template('tarifa_resultado.html', error='Tarifa no encontrada')

@app.route('/reservar', methods=['POST'])
def reservar():
    habitacion_id = request.form.get('habitacion_id')
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    if not habitacion_id or not fecha_inicio or not fecha_fin:
        return "Datos de reserva incompletos", 400

    nueva_reserva = Reserva(
        habitacion_id=int(habitacion_id),
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )
    db.session.add(nueva_reserva)
    db.session.commit()

    return render_template('reserva_exitosa.html', habitacion_id=habitacion_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

@app.route('/')
def index():
    return render_template('index.html')

# FUNCIONES DE INICIALIZACIÓN
def cargar_datos():
    if Hotel.query.first():
        return  

    hoteles_info = [
        ("Hotel Barranquilla", "Barranquilla", [("estandar", 4, 30), ("premium", 4, 3)]),
        ("Hotel Cali", "Cali", [("premium", 6, 20), ("VIP", 6, 2)]),
        ("Hotel Cartagena", "Cartagena", [("estandar", 8, 10), ("premium", 8, 1)]),
        ("Hotel Bogotá", "Bogotá", [("estandar", 6, 20), ("premium", 6, 20), ("VIP", 6, 2)])
    ]

    for nombre, ciudad, habitaciones in hoteles_info:
        hotel = Hotel(nombre=nombre, ciudad=ciudad)
        db.session.add(hotel)
        db.session.commit()
        for tipo, capacidad, cantidad in habitaciones:
            for _ in range(cantidad):
                h = Habitacion(tipo=tipo, capacidad=capacidad, hotel_id=hotel.id)
                db.session.add(h)

    for hotel in Hotel.query.all():
        for tipo in ["estandar", "premium", "VIP"]:
            for temporada, valor in [("alta", 100000), ("baja", 60000)]:
                db.session.add(Tarifa(hotel_id=hotel.id, tipo_habitacion=tipo, temporada=temporada, valor=valor))

    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        cargar_datos()  
    app.run(debug=True)

