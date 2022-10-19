from tkinter import Tk
from rocket_league_tkinter.item import Item
from rocket_league_tkinter.inventory import Inventory

i = Tk()
inventory = Inventory(i, 6, [])
inventory.add_item("48d394e52f1585159717.png", "Rocket League Esports [Breakout]", "Import", "Body", 20000, 'Pink', "Striker", 100, 200)
inventory.add_item("dingo.png", "Dingo", "Import", "Body", 1)
inventory.get_widget().pack()
i.mainloop()
