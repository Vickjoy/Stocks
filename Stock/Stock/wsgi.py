import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stock.settings')

application = get_wsgi_application()
application = WhiteNoise(
    application, 
    root=r'C:\Users\tr\Desktop\backend\Stocks\Stock\staticfiles',
    prefix='static'
)