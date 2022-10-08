from dotenv import load_dotenv
import os
import redis

load_dotenv()

class ApplicationConfig:
    SECRET_KEY= os.environ["SECRET_KEY"]
    
    CORS_HEADERS = 'Content-Type'
    SECRET_KEY = 'asdasdjkasdbkja'
    # SESSION_COOKIE_PATH = '/'
