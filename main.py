import logging
from bot import BaleXBot

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("balethon.network.connection").setLevel(logging.WARNING)
    bot = BaleXBot()
    bot.run()

if __name__ == "__main__":
    main()