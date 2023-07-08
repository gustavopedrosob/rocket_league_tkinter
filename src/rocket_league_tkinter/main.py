import contextlib
import functools
import aiohttp
import datetime
import io
import tempfile
import tkinter as tk
import typing
import pathlib
import asyncio
from tkinter import ttk
from PIL import Image, ImageTk
import rocket_league_utils as rl_utils
from rocket_league_utils import rarity_utils, color_utils, certified_utils, slot_utils, constants
import rocket_league_gameflip_api as rl_gameflip_api


def resize_image(photo, size: int = 125):
    return photo.resize((size, size))


async def get_image(url: str, size: int = 125):
    start_time = datetime.datetime.now()
    print(f"Creating image {url} at {start_time}")
    downloaded = 0
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=1) as response:
            buffer = tempfile.SpooledTemporaryFile()
            async for chunk in response.content.iter_chunked(1024):
                downloaded += len(chunk)
                buffer.write(chunk)
            buffer.seek(0)
            image = Image.open(io.BytesIO(buffer.read()))
    finish_time = datetime.datetime.now()
    print(f"Created image {url} in {finish_time - start_time}")
    return resize_image(image, size)


def generate_gradient(color_1: tuple[int, int, int, int], color_2: tuple[int, int, int, int], width: int,
                      height: int) -> Image:
    """Generate a vertical gradient."""
    base = Image.new('RGBA', (width, height), color_1)
    top = Image.new('RGBA', (width, height), color_2)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        for x in range(width):
            mask_data.append(int(255 * (y / height)))
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, height: int, width: int, *args, **kwargs):
        self.frame = ttk.Frame(container)
        self.canvas = tk.Canvas(self.frame, height=height, width=width)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.canvas.yview)
        super().__init__(self.canvas, height=height, width=width)
        self.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox(tk.ALL)))
        self.canvas.create_window((0, 0), window=self, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


class ItemImageStyle:
    def __init__(self, size: int = 125, font: str = "Segoe"):
        self.size = size
        self.font = (font, int(size * 0.07))


DEFAULT_ITEM_IMAGE_STYLE = ItemImageStyle()


class ShowItem(tk.Canvas, rl_utils.Item):
    trade_lock_image = Image.open(str(pathlib.Path(__file__).parent) + r"\source\tradelock.png")

    def __init__(self, master: typing.Union[tk.Widget, tk.Tk, tk.Toplevel],
                 gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                 name: str, slot: str, rarity: str, quantity: int, blueprint: bool, serie: str,
                 trade_lock: bool,
                 platform: str, acquired: datetime.datetime, favorite: bool = False,
                 archived: bool = False,
                 color: str = constants.DEFAULT, certified: str = constants.NONE,
                 style: ItemImageStyle = DEFAULT_ITEM_IMAGE_STYLE,
                 base_image: typing.Optional[Image.Image] = None):
        self._gradient = None
        self._base_image = base_image
        self._processed_image = None
        self.style = style
        self._gameflip_api = gameflip_api
        self.loaded_image = False
        trade_lock_size = int(style.size * 0.15)
        trade_lock_image = self.trade_lock_image.resize((trade_lock_size, trade_lock_size))
        self._trade_lock_image = ImageTk.PhotoImage(trade_lock_image)
        super().__init__(master, width=style.size, height=style.size)
        self.create_rectangle(0, 0, self.style.size, self.style.size, fill="black")
        self.create_image(0, 0, anchor=tk.NW, tags="image")
        self.create_text(style.size / 2, int(style.size * 0.1), font=style.font, fill="white", justify=tk.CENTER,
                         tags=("name", "attribute"))
        self.create_text(style.size / 2, int(style.size * 0.8), font=style.font, tags=("color", "attribute"))
        self.create_text(style.size / 2, int(style.size * 0.9), font=style.font, fill="white",
                         tags=("certified", "attribute"))
        self.create_text(int(style.size * 0.95), int(style.size * 0.05), anchor=tk.NE, font=style.font, fill="white",
                         tags=("quantity", "attribute"))
        self.create_image(5, 5, anchor=tk.NW, image=self._trade_lock_image, tags=("trade_lock", "attribute"))
        self.create_text(style.size / 2, style.size / 2, width=style.size, text="Imagem não encontrada.",
                         justify=tk.CENTER, tags="notfound", fill="white")
        rl_utils.Item.__init__(self, name, slot, rarity, quantity, blueprint, serie, trade_lock, platform, acquired,
                               favorite, archived, color, certified)

    @property
    def rarity(self):
        return self._rarity

    @rarity.setter
    def rarity(self, rarity: str):
        if "_rarity" in dir(self) and rarity_utils.compare(self._rarity, rarity):
            pass
        else:
            with contextlib.suppress(KeyError):
                self._gradient = self.generate_gradient_by_rarity(rarity, self.style.size)
        self._rarity = rarity

    @property
    def certified(self):
        return self._certified

    @certified.setter
    def certified(self, certified: str):
        if certified_utils.is_exactly(rl_utils.NONE, certified):
            self.itemconfigure("certified", state=tk.HIDDEN)
        else:
            self.itemconfigure("certified", text=certified, state=tk.NORMAL)
        self._certified = certified

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, quantity: int):
        self.itemconfigure("quantity", text=str(quantity), state=tk.NORMAL if quantity > 1 else tk.HIDDEN)
        self._quantity = quantity

    @property
    def trade_lock(self):
        return self._trade_lock

    @trade_lock.setter
    def trade_lock(self, trade_lock: bool):
        self.itemconfigure("trade_lock", state=tk.NORMAL if trade_lock else tk.HIDDEN)
        self._trade_lock = trade_lock

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color: str):
        if "_color" in dir(self) and color_utils.compare(color, self.color):
            pass
        else:
            if color_utils.is_exactly(rl_utils.DEFAULT, color):
                self.itemconfigure("color", state=tk.HIDDEN)
            else:
                hex_code = rl_utils.HEX_TABLE[rl_utils.color_utils.get_repr(color)]
                self.itemconfigure("color", state=tk.NORMAL, fill=hex_code, text=color)
        self._color = color

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str):
        self.itemconfigure("name", text=name, state=tk.NORMAL)
        self._name = name

    def update_image(self, base_image=None):
        if base_image:
            self._base_image = base_image
        else:
            self._base_image = asyncio.run(self.get_photo(self, self._gameflip_api, self.style.size))
        self.set_state("normal")
        self._processed_image = ImageTk.PhotoImage(self.process_image(self._base_image, self.name, self.style.size,
                                                                      self._gradient))
        self.itemconfigure("image", image=self._processed_image)

    def set_state(self, state: typing.Literal["notfound", "normal"]):
        if state == "normal":
            self.itemconfigure("attribute", state=tk.NORMAL)
            self.itemconfigure("image", state=tk.NORMAL)
            self.itemconfigure("notfound", state=tk.HIDDEN)
        else:
            self.itemconfigure("attribute", state=tk.HIDDEN)
            self.itemconfigure("image", state=tk.HIDDEN)
            self.itemconfigure("notfound", state=tk.NORMAL)

    def get_state(self) -> typing.Literal["notfound", "normal"]:
        if self.itemcget("image", "state") == tk.NORMAL:
            return "normal"
        else:
            return "notfound"

    @staticmethod
    async def get_photo(item: rl_utils.ReprItem,
                        gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI, size: int = 125):
        data_item = gameflip_api.get_data_item(item)
        if isinstance(data_item, rl_gameflip_api.ColorfulDataItem):
            item_url = data_item.get_full_icon_url(data_item.get_icon_by_color(item.color))
        else:
            item_url = data_item.get_full_icon_url(data_item.icon)
        return await get_image(item_url, size)

    @staticmethod
    @functools.lru_cache
    def generate_gradient_by_rarity(rarity: str, size: int = 125):
        if rarity_utils.is_exactly(rl_utils.COMMON, rarity) or rarity_utils.is_exactly(rl_utils.UNCOMMON, rarity):
            return None
        else:
            rarity = rarity_utils.get_repr(rarity)
            base = rl_utils.RGB_TABLE[rarity] + (0,)
            top = rl_utils.RGB_TABLE[rarity] + (80,)
            return generate_gradient(base, top, size, size)

    @staticmethod
    def process_image(base_image: Image.Image, name: str, size: int = 125, gradient=None):
        start_time = datetime.datetime.now()
        print(f"Processing item {name} image.")
        image = Image.new("RGB", (size, size), (0, 0, 0))
        image.paste(base_image)
        image = image.convert("RGBA")
        if gradient is not None:
            image = Image.alpha_composite(image, gradient)
        finish_time = datetime.datetime.now()
        print(f"Processed item {name} image in {finish_time - start_time}.")
        return image


class Item(ShowItem):
    def __init__(self, master: typing.Union[tk.Widget, tk.Tk, tk.Toplevel],
                 gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                 name: str, slot: str, rarity: str, quantity: int, blueprint: bool, serie: str,
                 trade_lock: bool,
                 platform: str, acquired: datetime.datetime, favorite: bool = False,
                 archived: bool = False,
                 color: str = constants.DEFAULT, certified: str = constants.NONE,
                 style: ItemImageStyle = DEFAULT_ITEM_IMAGE_STYLE,
                 base_image: typing.Optional[Image.Image] = None):
        super().__init__(master, gameflip_api, name, slot, rarity, quantity, blueprint, serie, trade_lock, platform,
                         acquired, favorite, archived, color, certified, style, base_image)
        self._outline = self.create_rectangle(3, 3, style.size - 3 + 1, style.size - 3 + 1, width=3, outline="")
        self.bind("<Button-1>", lambda event: self._on_click())
        self.bind("<Enter>", lambda event: self._on_enter())
        self.bind("<Leave>", lambda event: self._on_leave())

    def _on_click(self):
        if self.is_selected():
            self.unselect()
        else:
            self.select()

    def select(self):
        self.itemconfigure(self._outline, outline="#00A3F5")

    def unselect(self):
        self.itemconfigure(self._outline, outline="")

    def is_selected(self) -> bool:
        return self.itemcget(self._outline, "outline") == "#00A3F5"

    def _on_leave(self):
        if not self.is_selected():
            self.itemconfigure(self._outline, outline="")

    def _on_enter(self):
        if not self.is_selected():
            self.itemconfigure(self._outline, outline="#85D6FF")


class ItemWithPrice(Item, rl_utils.ItemWithPrice):
    def __init__(self, master: typing.Union[tk.Widget, tk.Tk, tk.Toplevel],
                 gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                 name: str, slot: str, rarity: str, quantity: int, blueprint: bool, platform: str,
                 price: typing.Tuple[int, int], crafting_cost: int, serie: str, trade_lock: bool,
                 acquired: datetime.datetime, favorite: bool = False, archived: bool = False,
                 color: str = constants.DEFAULT, certified: str = constants.NONE,
                 style: ItemImageStyle = DEFAULT_ITEM_IMAGE_STYLE,
                 base_image: typing.Optional[Image.Image] = None):
        super().__init__(master, gameflip_api, name, slot, rarity, quantity, blueprint, serie, trade_lock, platform,
                         acquired, favorite, archived, color, certified, style, base_image)
        rl_utils.ItemWithPrice.__init__(self, name, slot, rarity, quantity, blueprint, platform, price, crafting_cost,
                                        serie, trade_lock, acquired, favorite, archived, color, certified)
        self.create_text(style.size / 2, int(style.size * 0.2), font=style.font, fill="white", tags="price")

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, price: typing.Tuple[int, int]):
        self.itemconfigure("price", text=f"{price[0]} - {price[1]}")
        self._price = price


class ItemWindow(tk.Toplevel):
    def __init__(self, title: str, gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI):
        super().__init__()
        self.title(title)
        self.resizable(False, False)
        self.item_preview_style = ItemImageStyle(size=256)
        self.item_preview = ShowItem(self, gameflip_api, "", "", "", 1, False, "", False, rl_utils.PC,
                                     datetime.datetime.now(), style=self.item_preview_style)
        self.item_preview.grid(row=0, column=0, columnspan=3)
        ttk.Label(self, text="Name").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(self, name="name", width=28).grid(row=2, column=0)
        self.blueprint_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, name="blueprint", text="Blueprint", variable=self.blueprint_var).grid(row=1, column=1,
                                                                                                    rowspan=2)
        self.trade_lock_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, name="trade_lock", text="Trade Lock", variable=self.trade_lock_var).grid(row=1, column=2,
                                                                                                       rowspan=2)
        tk.Label(self, text="Color").grid(row=3, column=0, sticky=tk.W)
        ttk.Combobox(self, name="color", values=rl_utils.COLORS, width=25).grid(row=4, column=0)
        tk.Label(self, text="Slot").grid(row=3, column=1, sticky=tk.W)
        ttk.Combobox(self, name="slot", values=rl_utils.SLOTS, width=25).grid(row=4, column=1)
        tk.Label(self, text="Rarity").grid(row=3, column=2, sticky=tk.W)
        ttk.Combobox(self, name="rarity", values=rl_utils.RARITIES, width=25).grid(row=4, column=2)
        tk.Label(self, text="Certified").grid(row=5, column=0, sticky=tk.W)
        ttk.Combobox(self, name="certified", values=rl_utils.CERTIFICATES, width=25).grid(row=6, column=0)
        tk.Label(self, text="Serie").grid(row=5, column=1, sticky=tk.W)
        ttk.Combobox(self, name="serie", values=rl_utils.SERIES, width=25).grid(row=6, column=1)
        ttk.Button(self, name="reset", text="Redefinir", command=self.reset).grid(row=7, column=0)
        ttk.Button(self, name="confirm", text="Confirmar").grid(row=7, column=1)
        ttk.Button(self, name="refresh_image", text="Atualizar Imagem", command=self.item_preview.update_image).grid(
            row=7, column=2)
        tk.Label(self, text="Quantity").grid(row=5, column=2, sticky=tk.W)
        ttk.Spinbox(self, name="quantity", from_=0, increment=1, to=1000000000,
                    validatecommand=(self.register(lambda string: bool(str.isnumeric(string))), "%P"),
                    validate="focusout", width=25).grid(row=6, column=2)
        self.grid_columnconfigure(tk.ALL, pad=25)
        self.grid_rowconfigure(tk.ALL, pad=25)
        self.grid_rowconfigure(0, pad=25)
        self.grid_rowconfigure(7, pad=25)
        self.configure(padx=25, pady=25)
        for entry_name in ("name",  "color", "slot", "rarity", "certified", "serie"):
            self.children[entry_name].bind("<FocusOut>", self._on_attribute_change)
        for entry_name in ("blueprint", "trade_lock"):
            self.children[entry_name].bind("<FocusOut>", self._on_bool_attribute_change)
        self.children["quantity"].bind("<FocusOut>", self._on_quantity_change)
        self.reset()

    def _on_attribute_change(self, event):
        setattr(self.item_preview, event.widget.winfo_name(), event.widget.get())

    def _on_bool_attribute_change(self, event):
        setattr(self.item_preview, event.widget.winfo_name(), 'selected' in event.widget.state())

    def _on_quantity_change(self, event):
        setattr(self.item_preview, "quantity", int(event.widget.get()))

    def reset(self):
        default_values = {"color": rl_utils.DEFAULT, "certified": rl_utils.NONE, "quantity": 1}
        for entry_name in ("name", "color", "slot", "rarity", "certified", "serie", "quantity"):
            self.children[entry_name].delete(0, tk.END)
            default_value = default_values.get(entry_name)
            if default_value is not None:
                self.children[entry_name].insert(0, default_value)
        self.blueprint_var.set(False)
        self.trade_lock_var.set(False)


class Slots(ScrollableFrame):
    def __init__(self, master, gameflip_api, columns: int = 7, rows: int = 7):
        self.gameflip_api = gameflip_api
        self.columns = columns
        self.rows = rows
        self.items = []
        super().__init__(master, 600, 900)
        self.scrollbar.bind("<ButtonRelease-1>", lambda event: self.load_items_able_to_load())
        self.scrollbar.bind("<MouseWheel>", lambda event: self.load_items_able_to_load())
        self.scrollbar.bind("<Map>", lambda event: self.load_items_able_to_load())
        self.frame.pack()

    def load_items_able_to_load(self):
        async def get_images():
            return await asyncio.gather(*self.get_photos(items_able_to_load))

        items_able_to_load = self.get_items_able_to_load()
        base_photos = asyncio.run(get_images())
        items_and_base_photos = [(item, photo) for item, photo in zip(items_able_to_load, base_photos)
                                 if photo is not None]
        for item, image in items_and_base_photos:
            item.update_image(image)
        for item in items_able_to_load:
            item.loaded_image = True

    def get_items_able_to_load(self):
        items_able_to_load = []
        for item in self.items:
            y1 = item.winfo_rooty() + item.winfo_height()
            y2 = item.winfo_rooty()
            canvasy1 = self.canvas.winfo_rooty()
            canvasy2 = self.canvas.winfo_rooty() + self.canvas.winfo_height()
            if y1 > canvasy1 and y2 < canvasy2 and not item.loaded_image:
                items_able_to_load.append(item)
        return items_able_to_load

    def insert_items_in_grid(self, items: typing.Iterable[Item]):
        for index, item in enumerate(items):
            column = index % self.columns
            row = index // self.rows
            item.grid(column=column, row=row)

    def add_item(self, item: rl_utils.Item):
        tk_item = Item(self, self.gameflip_api, item.name, item.slot, item.rarity, item.quantity, item.blueprint,
                       item.serie, item.trade_lock, item.platform, item.acquired, item.favorite, item.archived,
                       item.color, item.certified)
        self.items.append(tk_item)

    def add_items(self, items: typing.Iterable[rl_utils.Item]):
        for item in items:
            self.add_item(item)
        self.insert_items_in_grid(self.items)

    def get_photos(self, items: typing.Iterable[rl_utils.Item]):
        for item in items:
            yield Slots.get_photo(item, self.gameflip_api)

    @staticmethod
    async def get_photo(item, gameflip_api):
        with contextlib.suppress(rl_utils.ItemNotFound):
            return await Item.get_photo(item, gameflip_api)


class Inventory(tk.Frame):
    sort_options = {"Alphabetical": lambda tk_item: tk_item.name,
                    "Most Recent": lambda tk_item: tk_item.acquired,
                    "Quality": lambda tk_item: tk_item.rarity,
                    "Quantity": lambda tk_item: tk_item.quantity,
                    "Series": lambda tk_item: tk_item.serie}

    def __init__(self, master: typing.Union[tk.Widget, tk.Tk], gameflip_api):
        self.filter_results = {}
        super().__init__(master)
        filters_frame = tk.Frame(self)
        filters_frame.pack(padx=25, pady=25)
        tk.Label(filters_frame, text="Name").grid(row=0, column=0, sticky=tk.W)
        self.name_filter = tk.Entry(filters_frame, name="name")
        self.name_filter.grid(row=1, column=0)
        tk.Label(filters_frame, text="Slot").grid(row=0, column=1, sticky=tk.W)
        self.slot_filter = ttk.Combobox(filters_frame, values=("",) + rl_utils.SLOTS, name="slot")
        self.slot_filter.grid(row=1, column=1)
        tk.Label(filters_frame, text="Color").grid(row=0, column=2, sticky=tk.W)
        self.color_filter = ttk.Combobox(filters_frame, values=("",) + rl_utils.COLORS, name="color")
        self.color_filter.grid(row=1, column=2)
        tk.Label(filters_frame, text="Certified").grid(row=0, column=3, sticky=tk.W)
        self.certified_filter = ttk.Combobox(filters_frame, values=("",) + rl_utils.CERTIFICATES, name="certified")
        self.certified_filter.grid(row=1, column=3)
        tk.Label(filters_frame, text="Rarity").grid(row=0, column=4, sticky=tk.W)
        self.rarity_filter = ttk.Combobox(filters_frame, values=("",) + rl_utils.RARITIES, name="rarity")
        self.rarity_filter.grid(row=1, column=4)
        tk.Label(filters_frame, text="Sort by").grid(row=0, column=5, sticky=tk.W)
        self.sort_by = ttk.Combobox(filters_frame, values=("",) + tuple(self.sort_options.keys()))
        self.sort_by.grid(row=1, column=5)
        self.show_no_photo_items_var = tk.BooleanVar(value=False)
        self.no_photo_items_filter = ttk.Checkbutton(filters_frame, text="Show no photo items",
                                                     variable=self.show_no_photo_items_var)
        self.no_photo_items_filter.grid(row=0, column=6, rowspan=2)
        filters_frame.grid_columnconfigure(tk.ALL, pad=5.0)
        self.name_filter.bind("<KeyRelease>", lambda _: self.on_filter_or_sort())
        self.show_no_photo_items_var.trace_add("write", lambda var, index, mode: self.on_filter_or_sort())
        self.slots = Slots(self, gameflip_api)
        self.current_filter = self.slots.items
        for filter_ in (self.slot_filter, self.color_filter, self.certified_filter, self.rarity_filter,
                        self.sort_by):
            filter_.bind("<<ComboboxSelected>>", lambda _: self.on_filter_or_sort())
        self.slots.scrollbar.bind("<ButtonRelease-1>", lambda event: self.on_scroll())
        self.slots.scrollbar.bind("<MouseWheel>", lambda event: self.on_scroll())
        self.slots.scrollbar.bind("<Map>", lambda event: self.on_scroll())

    def on_scroll(self):
        self.slots.load_items_able_to_load()
        self.on_scroll_filter()
        self.apply_filter()

    def on_scroll_filter(self):
        self.filter_results["no_photo_items"] = set(filter(self.filter_no_photo_items, self.slots.items))

    def on_filter_or_sort(self):
        self.add_attribute_filter(self.name_filter, rl_utils.contains_name)
        self.add_attribute_filter(self.slot_filter, slot_utils.is_exactly)
        self.add_attribute_filter(self.color_filter, color_utils.is_exactly)
        self.add_attribute_filter(self.certified_filter, certified_utils.is_exactly)
        self.add_attribute_filter(self.rarity_filter, rarity_utils.is_exactly)
        self.apply_filter()
        self.slots.scrollbar.set(0, 0)

    def update_grid(self):
        for index, item in enumerate(self.current_filter):
            column = index % self.slots.columns
            row = index // self.slots.rows
            item.grid_configure(column=column, row=row)

    def apply_filter(self):
        new_filter = set(self.slots.items)
        for filter_result in self.filter_results.values():
            new_filter.intersection_update(filter_result)
        current_filter_set = set(self.current_filter)
        items_to_remove = current_filter_set.difference(new_filter)
        items_to_add = new_filter.difference(current_filter_set)
        self.current_filter = list(new_filter)
        if sort := self.sort_by.get():
            self.current_filter.sort(key=self.sort_options[sort])
        for item in items_to_remove:
            item.grid_remove()
        self.slots.insert_items_in_grid(items_to_add)
        if len(items_to_remove) > 0:
            self.update_grid()

    def add_attribute_filter(self, filter_widget, condition):
        attribute_name = filter_widget.winfo_name()
        if attribute := filter_widget.get():
            self.filter_results[attribute_name] = set(filter(
                lambda tk_item: condition(attribute, getattr(tk_item, attribute_name)),
                self.slots.items))
        elif attribute_name in self.filter_results:
            self.filter_results.pop(attribute_name)

    def filter_no_photo_items(self, tk_item: Item):
        if self.show_no_photo_items_var.get():
            return True
        else:
            return (tk_item.get_state() == "normal" and tk_item.loaded_image) or not tk_item.loaded_image


class Trade(tk.Frame):
    def __init__(self, items: typing.Iterable[rl_utils.Item], gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI):
        super().__init__()
        self.slots = Slots(self, gameflip_api)
        self.slots.add_items(items)
