from agent import run_scheduler
from config import INITIAL_CAPITAL
from utils import ensure_logs

def main():
    ensure_logs()
    account = {"balance": INITIAL_CAPITAL}
    run_scheduler(account)

if __name__ == "__main__":
    main()
