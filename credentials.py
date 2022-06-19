import os
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv("bot_token")
db_url = os.getenv("DATABASE_URL")


tx_guild_id = 884460833097273455
request_list_id = 927347064801722419
staff_update_channel_id = 949727899949359105