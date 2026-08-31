def test_login_success(client, user):
    # Enviar una solicitud POST con las credenciales correctas
    response = client.post('/', data={
        'nameUser': user.nameUser,
        'passwordUser': user.passwordUser
    }, follow_redirects=True)
    
    # Verificar que el login fue exitoso y que el usuario fue redirigido al dashboard
    assert response.status_code == 200
    
    expected_message = f"Welcome".encode('utf-8')
    assert expected_message in response.data
    
def test_login_invalid_credentials(client):
  # Enviar una solicitud POST con credenciales incorrectas
  response = client.post('/', data={
      'nameUser': 'wronguser',
      'passwordUser': 'wrongskdfghgpassword'
  }, follow_redirects=True)

  # Verificar que el login fue rechazado
  assert response.status_code == 200
  assert b"Invalid credentials. Please try again." in response.data
  
# test_auth.py
from flask_login import login_user

def test_login_already_authenticated(client, user):
    # Simular un usuario autenticado
    with client:
        with client.session_transaction() as session:
          # Simula que el usuario está autenticado
          session['_user_id'] = str(user.idUser)
        
        # El usuario ya autenticado debería ser redirigido al dashboard
        response = client.get('/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b"This is your dashboard" in response.data  # Asumiendo que hay un texto "Dashboard" en la página
