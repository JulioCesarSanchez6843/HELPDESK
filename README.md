HELPDESK ATO

# 1. Activar el entorno virtual (el venv del zip es de tu PC, úsalo tal cual)
.\venv\Scripts\Activate.ps1

# 2. Instalar dependencias (solo si falta algo)
pip install -r requirements\dev.txt

# 3. Aplicar migraciones (las migraciones ya existen, no necesitas makemigrations)
python manage.py migrate

# 4. Crear tu primer administrador (si no lo tienes ya)
python manage.py createsuperuser

# 5. Levantar el servidor
python manage.py runserver