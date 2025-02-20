#!/usr/bin/env python3

import csv;
import configparser;
import os;
import OpenGL;
OpenGL.FULL_LOGGING = True;
from OpenGL.GL import *;
import glfw;
from imgui_bundle import imgui;
import ctypes;
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer;
from pathlib import Path;
from cowtools import *;


config = configparser.ConfigParser();
config.read("ledger.ini");
default_actors = config["CONFIG"]["default_actors"].split(", ");
default_actors = [x.lower() for x in default_actors];
sales_tax = float(config["CONFIG"]["sales_tax"]);
commie_list = config["CONFIG"]["commie_list"].split(", ");
commie_list = [x.lower() for x in commie_list];
width = int(config["CONFIG"]["width"]);
height = int(config["CONFIG"]["height"]);


class Purchase:
    def __init__(self, item, cost, quantity, taxed):
        self.item = item;
        self.cost = cost;
        self.quantity = quantity;
        self.taxed = taxed;

class Division:
    def __init__(self):
        self.actors = [];

    def subscribe(self, actor):
        self.actors.append(actor);

    def unsubscribe(self, actor):
        self.actors.remove(actor);
    
    def is_subscribed(self, actor):
        return actor in self.actors;

    def get_share(self, actor):
        actor = actor.lower();
        if actor in self.actors:
            return 1.0/float(len(self.actors));
        return 0.0;


class Ledger:
    def __init__(self):
        self.purchases = [];
        self.divisions = {};
        self.tax = 0.0;

    def add_purchase(self, purchase):
        self.purchases.append(purchase);
        self.divisions[purchase] = Division();

    def get_total(self):
        total = 0.0;
        for purchase in self.purchases:
            total += purchase.cost * purchase.quantity;
        return total;
    
    def get_tax(self):
        total = 0.0;
        for purchase in self.purchases:
            if purchase.taxed:
                total += purchase.cost * purchase.quantity;
        return total * self.tax;
    
    def get_actor_partial(self, purchase, actor):
        division = self.divisions[purchase];
        return purchase.cost * purchase.quantity * division.get_share(actor);

    def get_actor_total(self, actor):
        total = 0.0;
        for purchase in self.purchases:
            total += self.get_actor_partial(purchase, actor);
        return total;

    def get_actor_tax(self, actor):
        total = 0.0;
        for purchase in self.purchases:
            if purchase.taxed:
                division = self.divisions[purchase];
                if division.is_subscribed(actor):
                    total += purchase.cost * purchase.quantity * division.get_share(actor);
        return total * self.tax;
    
    def get_percent_paid(self):
        count = 0;
        for purchase in self.purchases:
            division = self.divisions[purchase];
            if len(division.actors) > 0:
                count += 1;
        return 100 * (count / len(self.purchases));

ledger = None;
		

def glfw_error_callback(error, description):
 	print(f"[GLFW ERROR] {error}: {description}");
glfw.set_error_callback(glfw_error_callback);
if not glfw.init():
	print("Failed to initialize GLFW. Exiting");
	exit();
glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3);
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3);
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE);
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE);
handle = glfw.create_window(width, height, "Ledger", None, None);
if not handle:
	print("Failed to create window. Exiting");
	glfw.terminate();
	exit();
glfw.make_context_current(handle);
print("Renderer:", glGetString(GL_RENDERER).decode("utf-8"));
print("GL Version:", glGetString(GL_VERSION).decode("utf-8"));
print("SL Version:", glGetString(GL_SHADING_LANGUAGE_VERSION).decode("utf-8"));

imgui.create_context();
imgui_io = imgui.get_io();
imgui_io.config_windows_move_from_title_bar_only = True;
imgui.style_colors_dark()
impl = GlfwRenderer(handle);

window_flag_list = [
	imgui.WindowFlags_.no_saved_settings,
	imgui.WindowFlags_.no_move,
	imgui.WindowFlags_.no_resize,
	imgui.WindowFlags_.no_nav_inputs,
	imgui.WindowFlags_.no_nav_focus,
	imgui.WindowFlags_.no_collapse,
	imgui.WindowFlags_.no_background,
	imgui.WindowFlags_.no_bring_to_front_on_focus,
];
window_flags = foldl(lambda a, b : a | b, 0, window_flag_list);

while not glfw.window_should_close(handle):
    glfw.poll_events();
    impl.process_inputs();

    glEnable(GL_PROGRAM_POINT_SIZE);
    glClearColor(0, 0, 0, 1);
    glClear(GL_COLOR_BUFFER_BIT);

    imgui.new_frame();
    imgui.set_next_window_pos((0, 0));
    imgui.set_next_window_size((width, height));
    imgui.begin("Ledger", None, flags=window_flags);
    
    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File"):
            if imgui.begin_menu("Open"):
                for path in os.listdir("receipts"):
                    if path.endswith(".csv"):
                        if imgui.menu_item_simple(path):
                            ledger_path = os.path.join("receipts", path);
                            ledger = Ledger();
                            with open(ledger_path) as file:
                                reader = csv.reader(file);
                                for row in reader:
                                    purchase = Purchase(row[0], float(row[1]), int(row[2]) if len(row) > 2 else 1, False);
                                    ledger.add_purchase(purchase);
                                    if purchase.item in commie_list:
                                        for actor in default_actors:
                                            ledger.divisions[purchase].subscribe(actor);
                imgui.end_menu();
            imgui.end_menu();
        imgui.end_main_menu_bar();

    if ledger == None:
            imgui.text("Please open a .csv receipt");
    else:
        if imgui.begin_tab_bar("Tabs"):
            if imgui.begin_tab_item("Receipt")[0]:
                imgui.push_item_width(width/10);

                ledger.tax = imgui.input_float("Tax", ledger.tax, format="%.4f")[1];
                imgui.same_line();
                if imgui.button("Sales tax"):
                    ledger.tax = sales_tax;
                imgui.separator();
                    
                i = 0;
                while i < len(ledger.purchases):
                    purchase = ledger.purchases[i];
                    imgui.push_id(str(purchase));
                    purchase.item = imgui.input_text("Item", purchase.item)[1];
                    imgui.same_line();
                    purchase.cost = imgui.input_float("Cost", purchase.cost, format="$%.2f")[1];
                    imgui.same_line();
                    purchase.quantity = imgui.input_int("Quantity", purchase.quantity)[1];
                    imgui.same_line();
                    purchase.taxed = imgui.checkbox("Taxed", purchase.taxed)[1];
                    imgui.same_line();
                    if imgui.button("X"):
                        del ledger.purchases[i];
                        i -= 1;
                    for (j, actor) in enumerate(default_actors):
                        division = ledger.divisions[purchase];
                        subscribed = division.is_subscribed(actor);
                        checked = imgui.checkbox(actor, subscribed)[1];
                        if checked and not subscribed:
                            division.subscribe(actor);
                        elif not checked and subscribed:
                            division.unsubscribe(actor);
                        if j < len(default_actors)-1:
                            imgui.same_line();
                    imgui.separator();
                    imgui.pop_id();
                    i += 1;
                
                if imgui.button("Add purchase"):
                   purchase = Purchase("", 0.0, 0, False);
                   ledger.purchases.append(purchase);

                imgui.pop_item_width();
                imgui.end_tab_item();

            if imgui.begin_tab_item("Tables")[0]:
                if imgui.collapsing_header("Receipt"):
                    if imgui.begin_table("Receipt Table", 3, imgui.TableFlags_.borders | imgui.TableFlags_.sizing_fixed_same):
                        imgui.table_setup_column("Item");
                        imgui.table_setup_column("Cost");
                        imgui.table_setup_column("Quantity");
                        imgui.table_headers_row();
                        for purchase in ledger.purchases:
                            imgui.table_next_row();
                            imgui.table_next_column();
                            imgui.text(purchase.item);
                            imgui.table_next_column();
                            imgui.text(f"${purchase.cost:.2f}");
                            imgui.table_next_column();
                            imgui.text(f"{purchase.quantity}");
                        imgui.end_table();
                        total = ledger.get_total();
                        tax = ledger.get_tax();
                        imgui.text(f"Untaxed total: ${total:.2f}");
                        imgui.text(f"Tax: ${tax:.2f}");
                        imgui.text(f"Total: ${total + tax:.2f}");
                imgui.separator();
                for actor in default_actors:
                    if imgui.collapsing_header(actor):
                        if imgui.begin_table(f"{actor} Table", 4, imgui.TableFlags_.borders | imgui.TableFlags_.sizing_fixed_same):
                            imgui.table_setup_column("Item");
                            imgui.table_setup_column("Cost");
                            imgui.table_setup_column("Quantity");
                            imgui.table_setup_column("Partial");
                            imgui.table_headers_row();
                            for purchase in ledger.purchases:
                                partial = ledger.get_actor_partial(purchase, actor);
                                if partial > 0:
                                    imgui.table_next_row();
                                    imgui.table_next_column();
                                    imgui.text(purchase.item);
                                    imgui.table_next_column();
                                    imgui.text(f"${purchase.cost:.2f}");
                                    imgui.table_next_column();
                                    imgui.text(f"{purchase.quantity}");
                                    imgui.table_next_column();
                                    imgui.text(f"${partial:.2f}");
                            imgui.end_table();
                            total = ledger.get_actor_total(actor);
                            tax = ledger.get_actor_tax(actor);
                            imgui.text(f"Untaxed total: ${total:.2f}");
                            imgui.text(f"Tax: ${tax:.2f}");
                            imgui.text(f"Total: ${total + tax:.2f}");
                percent_paid = int(ledger.get_percent_paid());
                imgui.text(f"% paid: %{percent_paid}");
                imgui.end_tab_item();

            imgui.end_tab_bar();
    
    imgui.end();
    imgui.render();
    impl.render(imgui.get_draw_data());
    imgui.end_frame();

    glfw.swap_buffers(handle);

