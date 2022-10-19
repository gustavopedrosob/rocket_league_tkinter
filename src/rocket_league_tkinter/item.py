from tkinter import Canvas, NW, NE, Frame, Button, X, CENTER, Widget
from PIL import Image, ImageTk
from rocket_league_tkinter.pil import generate_gradient
from rl_data_utils.rarity.rarity import get_rgba_rarity
from rl_data_utils.item.item import Item
from abc import ABC, abstractmethod

# TODO: Adicionar classe de configuração.
# TODO: Transformar ItemImage em método.


class ABCItemCanvas:
    @abstractmethod
    def get_canvas(self) -> Canvas:
        pass


class OutLine(ABCItemCanvas):
    def create_outline(self, color, size, tag):
        canvas = self.get_canvas()
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        canvas.create_line(0, size, width, size, width=size, fill=color, tags=tag)
        canvas.create_line(size, size, size, height, width=size, fill=color, tags=tag)
        canvas.create_line(0, height - size, width, height - size, width=size, fill=color, tags=tag)
        canvas.create_line(width - size, 0, width - size, height,  width=size, fill=color, tags=tag)


class Selectable(OutLine):
    def bind_select(self):
        self.get_canvas().bind("<Button-1>", lambda e: self.select())

    def is_selected(self):
        return self.get_canvas().find_withtag("select")

    def select(self):
        self.create_outline(self.get_select_outline_color(), self.get_select_outline_size(), "select")

    def unselect(self):
        self.get_canvas().delete("select")

    def get_select_outline_color(self):
        return "#3ABEFF"

    def get_select_outline_size(self):
        return 4


class Hoverable(OutLine):
    def bind_hover(self):
        canvas = self.get_canvas()
        canvas.bind("<Enter>", lambda e: self.hover())
        canvas.bind("<Leave>", lambda e: self.unhover())

    def hover(self):
        self.create_outline(self.get_hover_outline_color(), self.get_hover_outline_size(), "hover")

    def unhover(self):
        self.get_canvas().delete("hover")

    def get_hover_outline_color(self):
        return "#26FFE6"

    def get_hover_outline_size(self):
        return 4


class Interactable(Widget):
    def bind_interact(self):
        self.bind("Button-3", self._open_interaction_widget_by_event)

    def _open_interaction_widget_by_event(self, event):
        iw = self.get_interaction_widget()
        if iw.winfo_viewable():
            iw.place_forget()
        else:
            tw = event.widget.winfo_toplevel()
            x = event.x_root - tw.winfo_rootx()
            y = event.y_root - tw.winfo_rooty()
            iw.place(x=x, y=y)

    @abstractmethod
    def get_interaction_widget(self) -> Widget:
        pass


# class ItemImage:
#     def __init__(self, image: Image, rarity: str, width, height):
#         self.width = width
#         self.height = height
#         image = self.prepare_image(image)
#         self.image = Image.alpha_composite(image, self.get_rarity_cover(rarity))
#
#     def prepare_image(self, image) -> Image:
#         image = image.convert("RGBA")
#         return image.resize((self.width, self.height))
#
#     def get_rarity_cover(self, rarity):
#         base = get_rgba_rarity(rarity, 0)
#         top = get_rgba_rarity(rarity, 80)
#         return generate_gradient(tuple(base), tuple(top), self.width, self.height)
#
#     def to_photo_image(self):
#         return ImageTk.PhotoImage(self.image)
#
#
# class Outline:
#     def __init__(self, _canvas, color):
#         self._canvas = _canvas
#         self.color = color
#         self.ids = []
#
#     def draw(self, size=4):
#         width = self._canvas.winfo_width()
#         height = self._canvas.winfo_height()
#         self.create_line(0, size, width, size, width=size, fill=self.color)
#         self.create_line(size, size, size, height, width=size, fill=self.color)
#         self.create_line(0, height - size, width, height - size, width=size, fill=self.color)
#         self.create_line(width - size, 0, width - size, height,  width=size, fill=self.color)
#
#     def create_line(self, *args, **kwargs):
#         self.ids.append(self._canvas.create_line(*args, **kwargs))
#
#     def remove(self):
#         for id_ in self.ids:
#             self._canvas.delete(id_)
#
#
# class RightClickWidget(Frame):
#     def __init__(self, master, edit_callback=None, delete_callback=None):
#         super().__init__(master)
#         self._edit_button = Button(self, text="Edit", command=lambda: self.on_click(edit_callback))
#         self._edit_button.pack(fill=X, expand=1, ipadx=10)
#         self._delete_button = Button(self, text="Delete", command=lambda: self.on_click(delete_callback))
#         self._delete_button.pack(fill=X, expand=1, ipadx=10)
#
#     def on_click(self, callback=None):
#         self.place_forget()
#         if callback:
#             callback()
#
#
# def auto_font_size(width, multiplier=0.06) -> int:
#     return int(multiplier * width)
#
#
# class Item(ItemBase):
#     width = 150
#     height = 150
#     font = "Segoe"
#     font_size = auto_font_size(width)
#     attributes_y_pad = 7
#     bottom_margin = 10
#     sides_margin = 10
#
#     def __init__(self, master, image: str, name: str, rarity: str, type_: str, quantity: int = 1,
#                  color: str = "Default", certified: str = None, min_price=0, max_price=0, on_click_callback=None):
#         self._canvas = Canvas(master, width=self.width, height=self.height)
#         self._right_click_widget = RightClickWidget(master.winfo_toplevel())
#         self._outline_hover = Outline(self._canvas, "#26FFE6")
#         self._outline_select = Outline(self._canvas, "#3ABEFF")
#         self.set_binds(on_click_callback)
#         self.selected = False
#         self.photo = None
#         super().__init__(name, color, type_, rarity, certified, quantity)
#         self.min_price, self.max_price = min_price, max_price
#         self.draw(image)
#
#     def edit(self, image: str, name: str, rarity: str, type_: str, quantity: int = 1, color: str = "Default",
#              certified: str = None, min_price=0, max_price=0):
#         self.delete_items_on_canvas()
#         self.name = name
#         self.rarity = rarity
#         self.type = type_
#         self.quantity = quantity
#         self.color = color
#         self.certified = certified
#         self.min_price, self.max_price = min_price, max_price
#         self.draw(image)
#
#     def get_widget(self):
#         return self._canvas
#
#     def get_right_click_widget(self):
#         return self._right_click_widget
#
#     def set_binds(self, on_click_callback):
#         self._canvas.bind("<Button-3>", self._on_right_click)
#         self._canvas.bind("<Button-1>", lambda e: self._on_click(on_click_callback))
#         self._canvas.bind("<Enter>", self._on_enter)
#         self._canvas.bind("<Leave>", self._on_leave)
#
#     def get_quantity(self) -> int:
#         return self.quantity
#
#     def set_quantity(self, quantity: int):
#         self.quantity = quantity
#
#     def get_name(self):
#         return self.name
#
#     def set_name(self, name: str):
#         self.name = name
#
#     def get_rarity(self):
#         return self.rarity
#
#     def set_rarity(self, rarity: str):
#         self.rarity = rarity
#
#     def get_color(self):
#         return self.color
#
#     def set_color(self, color: str):
#         self.color = color
#
#     def get_certified(self):
#         return self.certified
#
#     def set_certified(self, certified: str):
#         self.certified = certified
#
#     def get_type(self):
#         return self.type
#
#     def set_type(self, type_: str):
#         self.type = type_
#
#     def delete_items_on_canvas(self):
#         self._canvas.delete('items')
#
#     def draw(self, image):
#         self._create_photo(image)
#         self._create_name()
#         self._create_color()
#         if self.certified:
#             self._create_certified()
#         if self.min_price and self.max_price:
#             self._create_price()
#         if self.get_quantity() > 1:
#             self._create_quantity()
#
#     def _on_click(self, on_click_callback):
#         if self.selected:
#             self.remove_select()
#         else:
#             self.add_select()
#         if on_click_callback:
#             on_click_callback(self)
#
#     def add_select(self):
#         self._outline_select.draw()
#         self.selected = True
#
#     def remove_select(self):
#         self._outline_select.remove()
#         self.selected = False
#
#     def _on_right_click(self, event):
#         if self._right_click_widget.winfo_viewable():
#             self._right_click_widget.place_forget()
#         else:
#             tw = event.widget.winfo_toplevel()
#             x = event.x_root - tw.winfo_rootx()
#             y = event.y_root - tw.winfo_rooty()
#             self._right_click_widget.place(x=x, y=y)
#
#     def _on_enter(self, event):
#         self._outline_hover.draw()
#
#     def _on_leave(self, event):
#         self._outline_hover.remove()
#
#     def _create_photo(self, image):
#         if isinstance(image, str):
#             image = Image.open(image)
#         item_image = ItemImage(image, self.get_rarity(), self.width, self.height)
#         self.photo = item_image.to_photo_image()
#         self._canvas.create_image(0, 0, anchor=NW, image=self.photo, tags=['item', 'photo'])
#
#     def _calculate_attribute_y_position(self):
#         positions = self._canvas.bbox('attribute')
#         if positions:
#             height = positions[1]
#         else:
#             height = self.height - self.bottom_margin
#         return height - self.attributes_y_pad
#
#     def _create_name(self):
#         self._canvas.create_text(
#             self.width/2, self._calculate_attribute_y_position(), font=self._get_font(),
#             fill="white", text=self.get_name(), tags=['item', 'attribute', 'name'], width=self.width - self.sides_margin,
#             justify=CENTER)
#
#     def _create_color(self):
#         hex_code = get_hex_colors(self.get_color())
#         self._canvas.create_text(
#             self.width/2, self._calculate_attribute_y_position(), font=self._get_font(),
#             fill=hex_code, text=self.get_color(), tags=['item', 'attribute', 'color'])
#
#     def _create_price(self):
#         self._canvas.create_text(
#             self.width/2, self._calculate_attribute_y_position(), font=self._get_font(),
#             fill="white", text=self._get_price_as_string(), tags=['item', 'attribute', 'price'])
#
#     def _get_price_as_string(self):
#         return f"{self.min_price} - {self.max_price}"
#
#     def _create_certified(self):
#         self._canvas.create_text(
#             self.width/2, self._calculate_attribute_y_position(), font=self._get_font(),
#             fill="white", text=self.certified, tags=['item', 'attribute', 'certified'])
#
#     def _create_quantity(self):
#         self._canvas.create_text(
#             self.width-10, 10, anchor=NE, font=self._get_font(), fill="white", text=self.get_quantity(),
#             tags=['item', 'quantity'])
#
#     def _get_font(self):
#         return self.font, self.font_size
