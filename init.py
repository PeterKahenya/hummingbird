import depends
import utils
from config import settings

if __name__ == '__main__':
    try:
        depends.get_db()
        utils.initialize_db(settings,is_test=False)
    except Exception as e:
        print(f"Error initializing app: {e}")
        raise e