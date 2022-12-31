import asyncio
import datetime
import tkinter as tk
import rocket_league_utils as rl_utils
import rocket_league_gameflip_api as rl_gameflip_api
import rocket_league_tkinter as rl_tk
import bakkes_mod_inventory
import typing
from rocket_league_utils import rarity_utils, slot_utils


def gameflip_filter(item: bakkes_mod_inventory.Item) -> bool:
    return rarity_utils.is_valid(item.rarity) and not item.trade_lock


def main():
    gameflip_api = rl_gameflip_api.RocketLeagueGameflipAPI()
    inventory = bakkes_mod_inventory.read_inventory()
    inventory = tuple(filter(lambda item_: gameflip_filter(item_), inventory))
    window = tk.Tk()
    tk_inventory = rl_tk.Inventory(window)
    items = [rl_utils.Item(item.name, item.slot, item.rarity, item.quantity, item.blueprint, item.serie,
                           item.trade_lock, item.platform, datetime.datetime.now(), color=item.color,
                           certified=item.certified) for item in inventory]
    tk_inventory.add_items(items, gameflip_api)
    tk_inventory.pack()
    window.mainloop()


def item_window():
    gameflip_api = rl_gameflip_api.RocketLeagueGameflipAPI()
    window = rl_tk.ItemWindow("Adicionar Item", gameflip_api)
    window.mainloop()


if __name__ == '__main__':
    main()
