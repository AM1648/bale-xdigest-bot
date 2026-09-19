import logging
from bot import BaleXBot

class DropBaleUpdateLogs(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return not ("tapi.bale.ai" in msg and "getUpdates" in msg and "200" in msg)

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("balethon.network.connection").setLevel(logging.WARNING)
    logging.getLogger("httpx").addFilter(DropBaleUpdateLogs())
    bot = BaleXBot()
    bot.run()

if __name__ == "__main__":
    main()