import concurrent.futures
import contextlib
import functools
import multiprocessing

import PIL.ImageTk
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
from rocket_league_utils import rarity_utils, color_utils, certified_utils, slot_utils
import rocket_league_gameflip_api as rl_gameflip_api


@functools.lru_cache
def generate_gradient_by_rarity(rarity: str, size: int = 125):
    if rarity_utils.is_exactly(rl_utils.COMMON, rarity) or rarity_utils.is_exactly(rl_utils.UNCOMMON, rarity):
        return None
    else:
        rarity = rarity_utils.get_repr(rarity)
        base = rl_utils.RGB_TABLE[rarity] + (0,)
        top = rl_utils.RGB_TABLE[rarity] + (80,)
        return generate_gradient(base, top, size, size)


def resize_image(photo, size: int = 125):
    return photo.resize((size, size))


def process_image(base_image: Image.Image, name: str, rarity: str, size: int = 125):
    start_time = datetime.datetime.now()
    print(f"Processing item {name} image.")
    image = Image.new("RGB", (size, size), (0, 0, 0))
    image.paste(base_image)
    image = image.convert("RGBA")
    gradient = generate_gradient_by_rarity(rarity, size)
    if gradient is not None:
        image = Image.alpha_composite(image, gradient)
    finish_time = datetime.datetime.now()
    print(f"Processed item {name} image in {finish_time - start_time}.")
    return image


async def get_image(url: str, size: int = 125):
    start_time = datetime.datetime.now()
    print(f"Creating image {url} at {start_time}")
    downloaded = 0
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            buffer = tempfile.SpooledTemporaryFile()
            async for chunk in response.content.iter_chunked(1024):
                downloaded += len(chunk)
                buffer.write(chunk)
            buffer.seek(0)
            image = Image.open(io.BytesIO(buffer.read()))
    finish_time = datetime.datetime.now()
    print(f"Created image {url} in {finish_time - start_time}")
    return resize_image(image, size)


def generate_gradient(colour1: tuple[int, int, int, int], colour2: tuple[int, int, int, int],
                      width: int, height: int) -> Image:
    """Generate a vertical gradient."""
    base = Image.new('RGBA', (width, height), colour1)
    top = Image.new('RGBA', (width, height), colour2)
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
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, height=height, width=width)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, height=height, width=width)
        self.scrollable_frame.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox(tk.ALL)))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=self.scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


class ItemImageStyle:
    def __init__(self, size: int = 125, font: str = "Segoe"):
        self.size = size
        self.font = (font, int(size * 0.07))


DEFAULT_ITEM_IMAGE_STYLE = ItemImageStyle()


class ShowItem(tk.Canvas):
    trade_lock_image = Image.open(str(pathlib.Path(__file__).parent) + r"\source\tradelock.png")

    def __init__(self, master: typing.Union[tk.Widget, tk.Tk, tk.Toplevel], item: rl_utils.Item,
                 gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                 style: ItemImageStyle = DEFAULT_ITEM_IMAGE_STYLE,
                 images: typing.Optional[typing.Tuple[Image.Image, typing.Optional[Image.Image]]] = None):
        super().__init__(master, width=style.size, height=style.size)
        self.item = item
        self.style = style
        trade_lock_size = int(style.size * 0.15)
        trade_lock_image = self.trade_lock_image.resize((trade_lock_size, trade_lock_size))
        self._trade_lock_image = ImageTk.PhotoImage(trade_lock_image)
        self._base_image = None
        self._processed_image = None
        self._current_image = None
        self.create_image(0, 0, anchor=tk.NW, tags="image")
        self.create_text(style.size / 2, int(style.size * 0.1), font=style.font, fill="white", justify=tk.CENTER,
                         tags=("name", "attribute"))
        self.create_text(style.size / 2, int(style.size * 0.8), font=style.font, tags=("color", "attribute"))
        self.create_text(style.size / 2, int(style.size * 0.9), font=style.font, fill="white",
                         tags=("certified", "attribute"))
        self.create_text(int(style.size * 0.95), int(style.size * 0.05), anchor=tk.NE, font=style.font, fill="white",
                         tags=("quantity", "attribute"))
        self.create_image(5, 5, anchor=tk.NW, image=self._trade_lock_image, tags=("tradelock", "attribute"))
        self.create_text(style.size / 2, style.size / 2, text="Imagem não encontrada.", justify=tk.CENTER,
                         tags="notfound")
        ShowItem.update_item(self, item, gameflip_api, images, force_replacement=True)

    def update_item(self, item: rl_utils.Item, gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                    images: typing.Optional[typing.Tuple[Image.Image, typing.Optional[Image.Image]]] = None,
                    force_replacement: bool = False):
        self.config_item(item.name, item.slot, item.color, item.blueprint, item.rarity, item.certified,
                         item.trade_lock, item.quantity, gameflip_api, images, force_replacement)

    def config_item(self, name: str, slot: str, color: str, blueprint: bool, rarity: str, certified: str,
                    trade_lock: bool, quantity: int, gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                    images: typing.Optional[typing.Tuple[Image.Image, typing.Optional[Image.Image]]] = None,
                    force_replacement: bool = False):
        if images is None:
            base_image, processed_image = None, None
        else:
            base_image, processed_image = images
        try:
            same_repr = rl_utils.ReprItem(name, slot, blueprint, color).compare_repr(self.item)
            self.config_repr(name, slot, color, blueprint, gameflip_api, base_image, force_replacement)
        except rl_utils.ItemNotFound:
            self.set_state("notfound")
        else:
            self.set_state("normal")
            self.config_rarity(rarity, processed_image, force_replacement=not same_repr or force_replacement)
            self.config_certified(certified)
            self.config_trade_lock(trade_lock)
            self.config_quantity(quantity)
            self.config_image(self._base_image if self._processed_image is None else self._processed_image)

    def update_repr(self, item: rl_utils.ReprItem, gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                    base_image: typing.Optional[Image.Image] = None, force_replacement: bool = False):
        if not self.item.compare_repr(item) or force_replacement:
            if base_image is None:
                self._base_image = asyncio.run(self.get_photo(item, gameflip_api, self.style.size))
            else:
                self._base_image = base_image
            self.itemconfigure("name", text=item.name, state=tk.NORMAL)
            if color_utils.is_exactly(rl_utils.DEFAULT, item.color):
                self.itemconfigure("color", state=tk.HIDDEN)
            else:
                hex_code = rl_utils.HEX_TABLE[rl_utils.color_utils.get_repr(item.color)]
                self.itemconfigure("color", state=tk.NORMAL, fill=hex_code, text=item.color)
            for attr in ("name", "slot", "color", "blueprint"):
                setattr(self.item, attr, getattr(item, attr))
            self._processed_image = None

    def config_repr(self, name: str, slot: str, color: str,  blueprint: bool,
                    gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                    base_image: typing.Optional[Image.Image] = None, force_replacement: bool = False):
        self.update_repr(rl_utils.ReprItem(name, slot, blueprint, color), gameflip_api, base_image, force_replacement)

    def config_image(self, image: Image.Image):
        self._current_image = ImageTk.PhotoImage(image)
        self.itemconfigure("image", image=self._current_image)

    def config_rarity(self, rarity: str, processed_image: typing.Optional[Image.Image] = None,
                      force_replacement: bool = False):
        if not rarity_utils.compare(self.item.rarity, rarity) or force_replacement:
            if self._base_image is not None:
                with contextlib.suppress(KeyError):
                    if processed_image is None:
                        self._processed_image = process_image(self._base_image, self.item.name, rarity, self.style.size)
                    else:
                        self._processed_image = processed_image
                    self.item.rarity = rarity

    def config_certified(self, certified: str):
        if certified_utils.is_exactly(rl_utils.NONE, certified):
            self.itemconfigure("certified", state=tk.HIDDEN)
        else:
            self.itemconfigure("certified", text=certified, state=tk.NORMAL)
        self.item.certified = certified

    def config_trade_lock(self, trade_lock: bool):
        self.itemconfigure("tradelock", state=tk.NORMAL if trade_lock else tk.HIDDEN)
        self.item.trade_lock = trade_lock

    def config_quantity(self, quantity: int):
        self.itemconfigure("quantity", text=str(quantity), state=tk.NORMAL if quantity > 1 else tk.HIDDEN)
        self.item.quantity = quantity

    def set_state(self, state: typing.Literal["notfound", "normal"]):
        if state == "normal":
            self.itemconfigure("attribute", state=tk.NORMAL)
            self.itemconfigure("image", state=tk.NORMAL)
            self.itemconfigure("notfound", state=tk.HIDDEN)
        else:
            self.itemconfigure("attribute", state=tk.HIDDEN)
            self.itemconfigure("image", state=tk.HIDDEN)
            self.itemconfigure("notfound", state=tk.NORMAL)

    @staticmethod
    async def get_photo(item: rl_utils.ReprItem,
                        gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI, size: int = 125):
        data_item = gameflip_api.get_data_item(item)
        if isinstance(data_item, rl_gameflip_api.ColorfulDataItem):
            item_url = data_item.get_full_icon_url(data_item.get_icon_by_color(item.color))
        else:
            item_url = data_item.get_full_icon_url(data_item.icon)
        return await get_image(item_url, size)


class Item(ShowItem):
    def __init__(self, master: typing.Union[tk.Widget, tk.Tk, tk.Toplevel], item: rl_utils.Item,
                 gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                 style: ItemImageStyle = DEFAULT_ITEM_IMAGE_STYLE,
                 images: typing.Optional[typing.Tuple[Image.Image, typing.Optional[Image.Image]]] = None):
        super().__init__(master, item, gameflip_api, style, images)
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


class ItemWithPrice(Item):
    def __init__(self, master: typing.Union[tk.Widget, tk.Tk, tk.Toplevel], item: rl_utils.ItemWithPrice,
                 gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                 style: ItemImageStyle = DEFAULT_ITEM_IMAGE_STYLE,
                 images: typing.Optional[typing.Tuple[Image.Image, typing.Optional[Image.Image]]] = None):
        super().__init__(master, item, gameflip_api, style, images)
        self.price = self.create_text(style.size / 2, int(style.size * 0.2), font=style.font, fill="white")
        self.config_price(item.price)

    def update_item(self, item: rl_utils.ItemWithPrice, gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI,
                    images: typing.Optional[typing.Tuple[Image.Image, typing.Optional[Image.Image]]] = None,
                    force_replacement: bool = False):
        super().update_item(item, gameflip_api, images)
        self.config_price(item.price)

    def config_price(self, price: typing.Tuple[int, int]):
        self.itemconfigure(self.price, text=f"{price[0]} - {price[1]}")


class ItemWindow(tk.Toplevel):
    def __init__(self, title: str, gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI):
        super().__init__()
        self.title(title)
        self.resizable(False, False)
        self.item_preview_style = ItemImageStyle(size=256)
        item = rl_utils.Item("", "", "", 1, False, "", False, rl_utils.PC, acquired=datetime.datetime.now())
        self.item_preview = ShowItem(self, item, gameflip_api, self.item_preview_style)
        self.item_preview.grid(row=0, column=0, columnspan=3)
        ttk.Label(self, text="Name").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(self, name="name", width=28).grid(row=2, column=0)
        self.blueprint_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, name="blueprint", text="Blueprint", variable=self.blueprint_var).grid(row=1, column=1,
                                                                                                    rowspan=2)
        self.trade_lock_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, name="tradelock", text="Trade Lock", variable=self.trade_lock_var).grid(row=1, column=2,
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
        ttk.Button(self, name="cancel", text="Cancelar").grid(row=7, column=0)
        ttk.Button(self, name="reset", text="Redefinir", command=self.reset).grid(row=7, column=1)
        ttk.Button(self, name="confirm", text="Confirmar").grid(row=7, column=2)
        tk.Label(self, text="Quantity").grid(row=5, column=2, sticky=tk.W)
        ttk.Spinbox(self, name="quantity", from_=0, increment=1, to=1000000000,
                    validatecommand=(self.register(lambda string: bool(str.isnumeric(string))), "%P"),
                    validate="focusout", width=25).grid(row=6, column=2)
        self.grid_columnconfigure(tk.ALL, pad=25)
        self.grid_rowconfigure(tk.ALL, pad=25)
        self.grid_rowconfigure(0, pad=25)
        self.grid_rowconfigure(7, pad=25)
        self.configure(padx=25, pady=25)
        for entry_name in ("name", "blueprint", "tradelock", "color", "slot", "rarity", "certified", "serie",
                           "quantity"):
            self.children[entry_name].bind("<FocusOut>", lambda _: self._on_attribute_change(gameflip_api))
        self.reset()

    def _on_attribute_change(self, gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI):
        self.item_preview.config_item(
            self.children["name"].get(), self.children["slot"].get(), self.children["color"].get(),
            self.blueprint_var.get(), self.children["rarity"].get(), self.children["certified"].get(),
            self.trade_lock_var.get(), int(self.children["quantity"].get()), gameflip_api)

    def reset(self):
        default_values = {"color": rl_utils.DEFAULT, "certified": rl_utils.NONE, "quantity": 1}
        for entry_name in ("name", "color", "slot", "rarity", "certified", "serie", "quantity"):
            self.children[entry_name].delete(0, tk.END)
            default_value = default_values.get(entry_name)
            if default_value is not None:
                self.children[entry_name].insert(0, default_value)
        self.blueprint_var.set(False)
        self.trade_lock_var.set(False)


class Inventory(tk.Frame):
    sort_options = {"Alphabetical": lambda tk_item: tk_item.item.name,
                    "Most Recent": lambda tk_item: tk_item.item.acquired,
                    "Quality": lambda tk_item: tk_item.item.rarity,
                    "Quantity": lambda tk_item: tk_item.item.quantity,
                    "Series": lambda tk_item: tk_item.item.serie}

    def __init__(self, master: typing.Union[tk.Widget, tk.Tk]):
        super().__init__(master)
        self.items = []
        self.current_view_items = []
        filters_frame = tk.Frame(self)
        filters_frame.pack(padx=25, pady=25)
        tk.Label(filters_frame, text="Name").grid(row=0, column=0, sticky=tk.W)
        self.name_filter = tk.Entry(filters_frame)
        self.name_filter.grid(row=1, column=0)
        tk.Label(filters_frame, text="Slot").grid(row=0, column=1, sticky=tk.W)
        self.slot_filter = ttk.Combobox(filters_frame, values=("", ) + rl_utils.SLOTS)
        self.slot_filter.grid(row=1, column=1)
        tk.Label(filters_frame, text="Color").grid(row=0, column=2, sticky=tk.W)
        self.color_filter = ttk.Combobox(filters_frame, values=("", ) + rl_utils.COLORS)
        self.color_filter.grid(row=1, column=2)
        tk.Label(filters_frame, text="Certified").grid(row=0, column=3, sticky=tk.W)
        self.certified_filter = ttk.Combobox(filters_frame, values=("", ) + rl_utils.CERTIFICATES)
        self.certified_filter.grid(row=1, column=3)
        tk.Label(filters_frame, text="Rarity").grid(row=0, column=4, sticky=tk.W)
        self.rarity_filter = ttk.Combobox(filters_frame, values=("", ) + rl_utils.RARITIES)
        self.rarity_filter.grid(row=1, column=4)
        tk.Label(filters_frame, text="Sort by").grid(row=0, column=5, sticky=tk.W)
        self.sort_by = ttk.Combobox(filters_frame, values=("", ) + tuple(self.sort_options.keys()))
        self.sort_by.grid(row=1, column=5)
        filters_frame.grid_columnconfigure(tk.ALL, pad=5.0)
        self.items_canvas = ScrollableFrame(self, 600, 900)
        self.items_canvas.pack()
        self.name_filter.bind("<KeyRelease>", lambda _: self.on_filter_or_sort())
        for filter_ in (self.slot_filter, self.color_filter, self.certified_filter, self.rarity_filter,
                        self.sort_by):
            filter_.bind("<<ComboboxSelected>>", lambda _: self.on_filter_or_sort())

    def on_filter_or_sort(self):
        items = self.items
        name = self.name_filter.get()
        if name:
            items = filter(lambda tk_item: rl_utils.contains_name(name, tk_item.item.name), items)
        slot = self.slot_filter.get()
        if slot:
            items = filter(lambda tk_item: slot_utils.is_exactly(slot, tk_item.item.slot), items)
        color = self.color_filter.get()
        if color:
            items = filter(lambda tk_item: color_utils.is_exactly(color, tk_item.item.color), items)
        certified = self.certified_filter.get()
        if certified:
            items = filter(lambda tk_item: certified_utils.is_exactly(certified, tk_item.item.certified), items)
        rarity = self.rarity_filter.get()
        if rarity:
            items = filter(lambda tk_item: rarity_utils.is_exactly(rarity, tk_item.item.rarity), items)
        items = list(items)
        sort = self.sort_by.get()
        if sort:
            items.sort(key=self.sort_options[sort])
        self.remove_items_in_grid()
        self.insert_items_in_grid(items)
        self.items_canvas.scrollbar.set(0, 0)

    def add_item(self, item: rl_utils.Item, gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI, images):
        tk_item = Item(self.items_canvas.scrollable_frame, item, gameflip_api, images=images)
        self.items.append(tk_item)

    def add_items(self, items: typing.List[rl_utils.Item], gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI):
        async def get_photos():
            return await asyncio.gather(*self.get_photos(items, gameflip_api))

        start_time = datetime.datetime.now()
        base_photos = asyncio.run(get_photos())
        items_and_base_photos = [(item, photo) for item, photo in zip(items, base_photos) if photo is not None]
        with concurrent.futures.ProcessPoolExecutor(multiprocessing.cpu_count()) as pool:
            processed_images = pool.map(Inventory.process_image, items_and_base_photos)
            for item_and_base_photo, processed_photo in zip(items_and_base_photos, processed_images):
                self.add_item(item_and_base_photo[0], gameflip_api, (item_and_base_photo[1], processed_photo))
            self.insert_items_in_grid(self.items)
        finish_time = datetime.datetime.now()
        print(f"Added all items in {finish_time - start_time}")

    @staticmethod
    def get_photos(items: typing.List[rl_utils.Item], gameflip_api: rl_gameflip_api.RocketLeagueGameflipAPI):
        for item in items:
            yield Inventory.get_photo(item, gameflip_api)

    @staticmethod
    async def get_photo(item, gameflip_api):
        try:
            item = await Item.get_photo(item, gameflip_api)
        except rl_utils.ItemNotFound:
            return None
        else:
            return item

    @staticmethod
    def process_image(item_and_base_photo):
        item, base_photo = item_and_base_photo
        return process_image(base_photo, item.name, item.rarity)

    def insert_items_in_grid(self, items: typing.Iterable[Item]):
        for index, item in enumerate(items):
            self.insert_item(index, item)

    def insert_item(self, index: int, item: Item):
        column = index % 7
        row = index // 7
        item.grid(column=column, row=row)
        self.current_view_items.append(item)

    def remove_items_in_grid(self):
        for item in self.current_view_items:
            item.grid_forget()
        self.current_view_items = []
