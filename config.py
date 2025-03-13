from decouple import config

BOT_TOKEN = config('BOT_TOKEN')
ADMIN_ID = config('ADMIN_ID', cast=int)
CHANNEL_ID = config('CHANNEL_ID')
NEWSAPI_KEY = config('NEWSAPI_KEY')