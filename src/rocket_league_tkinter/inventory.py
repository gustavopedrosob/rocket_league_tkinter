from tkinter import Frame
from rocket_league_tkinter.item import Item
from rl_data_utils.inventory.inventory import Inventory as RlInventory


class Inventory(RlInventory):
    def __init__(self, master, columns, items, pad=2):
        self._frame = Frame(master)
        self.pad = pad
        self.columns = columns
        self.selecteds = []
        super().__init__(items)

    def from_rl_inventory_api(self):
        pass

    def _on_item_clicked(self, item):
        self.selecteds.append(item)

    def get_widget(self):
        return self._frame

    def add_item(self, image, name: str, rarity: str, type_: str, quantity: int = 1, color: str = "Default", certified: str = None, min_price=0, max_price=0):
        item = Item(self._frame, image, name, rarity, type_, quantity, color, certified, min_price, max_price, self._on_item_clicked)
        item.get_widget().grid(row=self.get_quantity() // self.columns, column=self.get_quantity() % self.columns,
                               padx=self.pad, pady=self.pad)
        super().add_item(item)

