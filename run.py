from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    #socketio.run(app, host="0.0.0.0", port=80, debug=True, allow_unsafe_werkzeug=True)
    app.run(debug=True, host='0.0.0.0', port=5000)