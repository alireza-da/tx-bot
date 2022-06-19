from model import TxEmployee
from credentials import db_url
import psycopg2
import logging

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logger = logging.getLogger(__name__)


def add_mcs_to_db(mechanics_list):
    # users = db["users"]
    con, cursor = create_connection()

    insert_query = """INSERT INTO mechanics(roster_id, ic_name, discord_id, rank, warns, strikes, points) """ \
                   """VALUES(%s, %s, %s, %s, %s, %s, %s)"""
    values = []
    mcs = {mc.discord_id: mc for mc in get_all_mechanics()}

    for mechanic in mechanics_list:
        try:
            mc = mcs[mechanic.discord_id]

            if mc and (
                    mc.ic_name != mechanic.ic_name or mc.roster_id != mechanic.roster_id or mc.rank != mechanic.rank):
                update_mc(mechanic)
                continue
        except Exception as e:
            value = (
                mechanic.roster_id, mechanic.ic_name, str(mechanic.discord_id), str(mechanic.rank), str(mechanic.warns),
                str(mechanic.strikes), str(mechanic.points))
            values.append(value)
            print(e)

        # if not get_user(_user.id):
        #     users.append(json.dumps(_user.__dict__))

    cursor.executemany(insert_query, values)
    con.commit()
    cursor.close()
    con.close()
    # print_tables()


def setup_tables(list_users):
    # print(f"[INFO]: user detail: {[user for user in list_users]}")
    con, cursor = create_connection()
    try:
        cursor.execute("""SELECT table_name FROM information_schema.tables
               """)
        tables = cursor.fetchall()
        print("[INFO]: Creating Tables")
        if ("mechanics_temp",) not in tables:
            cursor.execute(
                """CREATE TABLE mechanics(
                    roster_id VARCHAR(255),
                    ic_name VARCHAR(255),
                    discord_id BIGINT PRIMARY KEY,
                    rank INTEGER,
                    warns INTEGER,
                    strikes INTEGER,
                    steam_hex VARCHAR(255),
                    points INTEGER
                )""")
        if ("punishments",) not in tables:
            cursor.execute(
                """CREATE TABLE punishments (
                    punish_type VARCHAR(255),
                    date VARCHAR(255),
                    discord_id BIGINT
                )""")
        cursor.close()
        con.commit()
        con.close()
    except Exception as e:
        print(f"[Error][Setup Tables]: {e}")
    add_mcs_to_db(list_users)
    # add_admins(list_users)
    # print_tables()


def del_punishments(_id, date, punish_type):
    query = "DELETE FROM punishments WHERE discord_id=%s and date=%s and punish_type=%s"
    con, cursor = create_connection()
    try:
        print(f"Deleting Punishment {_id}")
        print(cursor.execute(query, (_id, date, punish_type)))
        con.commit()
        cursor.close()
        con.close()
        print("Done")
    except Exception as e:
        print(f"[Error][del_punishments]: {e}")


def get_punishments(_id):
    search_query = "SELECT * FROM punishments WHERE discord_id=%s"
    con, cursor = create_connection()
    try:
        cursor.execute(search_query, (_id,))
        result = cursor.fetchall()
        result = [Punishment.decoder_static(ps) for ps in result]
        con.commit()
        cursor.close()
        con.close()
        return result
    except Exception as e:
        print(f"[Error][get_punishments]: {e}")


# def save_punish(ps: Punishment):
#     insert_query = """INSERT INTO punishments(punish_type, date, discord_id) """ \
#                    """VALUES(%s, %s, %s)"""
#     con, cursor = create_connection()
#     try:
#         cursor.execute(insert_query, (ps.punish_type, ps.date, ps.em_id))
#         con.commit()
#         cursor.close()
#         con.close()
#     except Exception as e:
#         print(e)


def print_tables():
    print("[INFO]: Printing mechanics Table")
    con, cursor = create_connection()
    cursor.execute("SELECT * FROM mechanics")
    result = cursor.fetchall()
    for r in result:
        print(r)
    cursor.close()
    con.commit()


def get_user(_id):
    user_ret = "SELECT * FROM mechanics WHERE discord_id = %s"
    con, cursor = create_connection()
    try:
        cursor.execute(user_ret, (_id,))
        _user = cursor.fetchall()
        # print(f"[INFO]: Retrieving database user : {_user[0]}")
        user = TxEmployee.decoder_static(_user[0])
        # print(f"[INFO]: Retrieving object user : {user}")
        con.commit()
        cursor.close()
        con.close()
        return user

    except Exception as e:
        print(f"[Error][get_user]: {e}")
        return None


def get_all_mechanics():
    sql = "SELECT * FROM mechanics"
    con, cursor = create_connection()
    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        con.commit()
        cursor.close()
        con.close()
        result = [TxEmployee.decoder_static(mc) for mc in result]
        return result
    except Exception as e:
        print(f"[Error]: {e}")


def update_mc(mc: TxEmployee):
    update_query = "UPDATE mechanics SET roster_id = %s, ic_name = %s, discord_id = %s, rank = %s, warns = %s, " \
                   "strikes = %s, steam_hex = %s, points = %s WHERE discord_id = %s "
    con, cursor = create_connection()
    try:
        print(f"[INFO]: Saving mechanic: {mc.ic_name}")
        cursor.execute(update_query, (mc.roster_id, mc.ic_name, mc.discord_id, mc.rank, mc.warns, mc.strikes,
                                      mc.steam_hex, mc.points, mc.discord_id))
        con.commit()
        cursor.close()
        con.close()
        print("Done")
    except Exception as e:
        print(f"[Error][update_mc]: {e}")


# def get_admin(user):
#     admin_ret = "SELECT * FROM admins WHERE id = %s"
#     con, cursor = create_connection()
#     try:
#         cursor.execute(admin_ret, (user.id,))
#         _user = cursor.fetchall()
#         print(f"[INFO]: Retrieving database admin : {_user[0]}")
#         admin = Admin.user_decoder_static(_user[0])
#         print(f"[INFO]: Retrieving object admin : {admin}")
#         con.commit()
#         cursor.close()
#         con.close()
#         return admin
#     except Exception as e:
#         print(f"[Error]: {e}")
#         return None


def delete_db():
    update_query = "DROP TABLE mechanics"
    con, cursor = create_connection()
    try:
        cursor.execute(update_query)
        con.commit()
        cursor.close()
        con.close()
    except Exception as e:
        print(f"[Error][delete_db]: {e}")


def create_connection():
    try:
        con = psycopg2.connect(db_url)
        #  print(f"[INFO]: Connected to DB {con}")
        return con, con.cursor()
    except Exception as e:
        logger.error(f"{e}")


def create_temp_tables(list_users):
    # print(f"[INFO]: user detail: {[user for user in list_users]}")
    con, cursor = create_connection()
    try:
        cursor.execute("""SELECT table_name FROM information_schema.tables
               """)
        tables = cursor.fetchall()
        print("[INFO]: Creating Tables")
        if ("mechanics_temp",) not in tables:
            cursor.execute(
                """CREATE TABLE mechanics(
                    roster_id INTEGER,
                    ic_name VARCHAR(255),
                    discord_id BIGINT PRIMARY KEY,
                    rank INTEGER,
                    warns INTEGER,
                    strikes INTEGER,
                    steam_hex VARCHAR(255),
                    points INTEGER
                )""")
        if ("punishments",) not in tables:
            cursor.execute(
                """CREATE TABLE punishments (
                    punish_type VARCHAR(255),
                    date VARCHAR(255),
                    discord_id BIGINT
                )""")
        cursor.close()
        con.commit()
        con.close()
    except Exception as e:
        print(f"[Error][Setup Tables]: {e}")
    add_mcs_to_db(list_users)
    # add_admins(list_users)
    # print_tables()


# delete_db()
# mc = get_user(741264245433434112)
# print(mc.ic_name)
# mc.points = 412
# update_mc(mc)
# setup_tables([])
