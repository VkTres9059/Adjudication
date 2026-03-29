from motor.motor_asyncio import AsyncIOMotorClient
import os
from core.config import ROOT_DIR
from dotenv import load_dotenv

load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
