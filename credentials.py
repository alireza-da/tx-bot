import os
from dotenv import load_dotenv

load_dotenv()

bot_token = os.environ["bot_token"]
db_url = os.environ["DATABASE_URL"]

tx_guild_id = 884460833097273455
request_list_id = 927347064801722419
staff_update_channel_id = 949727899949359105
rank_role_ids = {1: 884818872153292932, 2: 884815969061593141, 3: 884815956860338237, 4:884815944617177128}