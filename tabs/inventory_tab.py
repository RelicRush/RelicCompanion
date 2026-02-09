"""
Inventory Tab for the Warframe Relic Companion.
"""

import os
import customtkinter as ctk
from tkinter import ttk
from PIL import Image
from models import InventoryItem, RelicEra, RelicRefinement, RewardRarity
from api import WFCDRelicDatabase
from icon_manager import get_platinum_icon_path, get_ducats_icon_path


class InventoryTab:
    """Inventory management tab functionality."""
    
    def __init__(self, app):
        self.app = app
        self.COLORS = app.COLORS
        self.inv_stats_label = None
        self.inv_search = None
        self.inv_era_filter = None
        self.inv_sort = None
        self.inv_tree = None
        self.profit_toggle = None
        self.rad_toggle = None
        self.ducats_toggle = None
        # Load saved filter preferences
        self.profit_enabled = app.settings.get('inv_profit_filter', False)
        self.rad_enabled = app.settings.get('inv_rad_filter', False)
        self.ducats_enabled = app.settings.get('inv_ducats_filter', False)
        self.cascade_label = None
        self.wfcd_db = WFCDRelicDatabase()
        self._price_cache = {}  # Cache relic -> price lookups
    
    def create_frame(self, parent):
        """Create the inventory management frame."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        
        # Header row
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header.grid_columnconfigure(0, weight=1)
        
        # Title and stats
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")
        
        title = ctk.CTkLabel(title_frame, text="My Inventory",
                            font=ctk.CTkFont(size=28, weight="bold"),
                            text_color=self.COLORS['text'])
        title.pack(side="left")
        
        # Stats frame to hold multiple labels for different colors
        stats_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        stats_frame.pack(side="left", padx=(20, 0))
        
        # Plat icon for shown/profitable relics
        self.stats_plat_icon = None
        plat_icon_path = get_platinum_icon_path(14)
        if plat_icon_path and os.path.exists(plat_icon_path):
            try:
                plat_pil = Image.open(plat_icon_path)
                self.stats_plat_icon = ctk.CTkImage(light_image=plat_pil, dark_image=plat_pil, size=(14, 14))
            except Exception:
                pass
        
        # Ducat icon for ducat filter
        self.stats_ducat_icon = None
        ducat_icon_path = get_ducats_icon_path(14)
        if ducat_icon_path and os.path.exists(ducat_icon_path):
            try:
                ducat_pil = Image.open(ducat_icon_path)
                self.stats_ducat_icon = ctk.CTkImage(light_image=ducat_pil, dark_image=ducat_pil, size=(14, 14))
            except Exception:
                pass
        
        # Left icon (plat or ducat depending on filter)
        self.filter_icon_label = ctk.CTkLabel(stats_frame, text="", image=self.stats_plat_icon, width=14)
        self.filter_icon_label.pack(side="left", padx=(0, 4))
        self.filter_icon_label.pack_forget()  # Hide initially
        
        # Label for shown/filtered relics (color changes based on filter)
        self.inv_shown_label = ctk.CTkLabel(stats_frame, text="",
                                           font=ctk.CTkFont(size=13, weight="bold"),
                                           text_color="#ffd700")
        self.inv_shown_label.pack(side="left")
        
        # Right icon (plat or ducat depending on filter)
        self.filter_icon_label_right = ctk.CTkLabel(stats_frame, text="", image=self.stats_plat_icon, width=14)
        self.filter_icon_label_right.pack(side="left", padx=(4, 0))
        self.filter_icon_label_right.pack_forget()  # Hide initially
        
        # Regular label for total stats (also bold)
        self.inv_stats_label = ctk.CTkLabel(stats_frame, text="",
                                           font=ctk.CTkFont(size=13, weight="bold"),
                                           text_color=self.COLORS['text_muted'])
        self.inv_stats_label.pack(side="left")
        
        # Filter bar
        filter_frame = ctk.CTkFrame(frame, fg_color=self.COLORS['bg_card'], corner_radius=12)
        filter_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        
        # Search
        self.inv_search = ctk.CTkEntry(
            filter_frame,
            placeholder_text="🔍 Search relics, drops, refinement...",
            font=ctk.CTkFont(size=12),
            height=36,
            width=220,
            corner_radius=8,
            fg_color=self.COLORS['bg_secondary'],
            border_color=self.COLORS['border']
        )
        self.inv_search.pack(side="left", padx=15, pady=12)
        self.inv_search.bind("<KeyRelease>", lambda e: self.refresh_inventory())
        
        # Era filter
        era_label = ctk.CTkLabel(filter_frame, text="Era:",
                                font=ctk.CTkFont(size=12),
                                text_color=self.COLORS['text_muted'])
        era_label.pack(side="left", padx=(15, 5))
        
        self.inv_era_filter = ctk.CTkComboBox(
            filter_frame,
            values=["All", "Lith", "Meso", "Neo", "Axi"],
            width=90,
            height=32,
            corner_radius=6,
            fg_color=self.COLORS['bg_secondary'],
            border_color=self.COLORS['border'],
            button_color=self.COLORS['accent'],
            dropdown_fg_color=self.COLORS['bg_card'],
            command=lambda e: self.on_filter_change()
        )
        self.inv_era_filter.set(self.app.settings.get('inv_era_filter', 'All'))
        self.inv_era_filter.pack(side="left", padx=(0, 15))
        
        # Sort options
        sort_label = ctk.CTkLabel(filter_frame, text="Sort:",
                                 font=ctk.CTkFont(size=12),
                                 text_color=self.COLORS['text_muted'])
        sort_label.pack(side="left", padx=(0, 5))
        
        self.inv_sort = ctk.CTkComboBox(
            filter_frame,
            values=["Quantity ↓", "Quantity ↑", "Plat ↓", "Plat ↑"],
            width=120,
            height=32,
            corner_radius=6,
            fg_color=self.COLORS['bg_secondary'],
            border_color=self.COLORS['border'],
            button_color=self.COLORS['accent'],
            dropdown_fg_color=self.COLORS['bg_card'],
            command=lambda e: self.on_filter_change()
        )
        self.inv_sort.set(self.app.settings.get('inv_sort', 'Quantity ↓'))
        self.inv_sort.pack(side="left", padx=(0, 15))
        
        # Profit Relics checkbox
        self.profit_toggle = ctk.CTkCheckBox(
            filter_frame,
            text="💰 Profit (20p+)",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted'],
            fg_color=self.COLORS['success'],
            hover_color=self.COLORS['success'],
            border_color=self.COLORS['text_muted'],
            checkmark_color=self.COLORS['bg_primary'],
            command=self.toggle_profit_filter
        )
        self.profit_toggle.pack(side="left", padx=(10, 10))
        # Restore saved profit toggle state
        if self.profit_enabled:
            self.profit_toggle.select()
            self.profit_toggle.configure(text_color=self.COLORS['success'])
        
        # Rad checkbox
        self.rad_toggle = ctk.CTkCheckBox(
            filter_frame,
            text="✨ Radiant",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted'],
            fg_color="#ff9800",
            hover_color="#ff9800",
            border_color=self.COLORS['text_muted'],
            checkmark_color=self.COLORS['bg_primary'],
            command=self.toggle_rad_filter
        )
        self.rad_toggle.pack(side="left", padx=(0, 10))
        # Restore saved rad toggle state
        if self.rad_enabled:
            self.rad_toggle.select()
            self.rad_toggle.configure(text_color="#ff9800")
        
        # Ducats checkbox - show relics worth less than 18p (good for ducat farming)
        self.ducats_toggle = ctk.CTkCheckBox(
            filter_frame,
            text="🪙 Ducats (<18p)",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted'],
            fg_color="#fbbf24",
            hover_color="#fbbf24",
            border_color=self.COLORS['text_muted'],
            checkmark_color=self.COLORS['bg_primary'],
            command=self.toggle_ducats_filter
        )
        self.ducats_toggle.pack(side="left", padx=(0, 15))
        # Restore saved ducats toggle state
        if self.ducats_enabled:
            self.ducats_toggle.select()
            self.ducats_toggle.configure(text_color="#fbbf24")
        
        # Inventory list using Treeview for performance
        tree_frame = ctk.CTkFrame(frame, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Style the treeview
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure alternating row colors
        self.inv_tree_odd_color = "#2a2a35"
        self.inv_tree_even_color = "#232329"
        
        style.configure("Inventory.Treeview",
                       background=self.inv_tree_even_color,
                       foreground=self.COLORS['text'],
                       fieldbackground=self.inv_tree_even_color,
                       borderwidth=0,
                       font=('Segoe UI', 12),
                       rowheight=42)
        style.configure("Inventory.Treeview.Heading",
                       background="#1e1e24",
                       foreground=self.COLORS['text_secondary'],
                       font=('Segoe UI', 11, 'bold'),
                       borderwidth=0,
                       relief='flat',
                       padding=(10, 8))
        style.map("Inventory.Treeview",
                 background=[('selected', self.COLORS['accent'])],
                 foreground=[('selected', '#ffffff')])
        
        # Create treeview
        columns = ('relic', 'gold_drop', 'price', 'refinement', 'quantity')
        self.inv_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', 
                                     style="Inventory.Treeview", selectmode='browse')
        
        self.inv_tree.heading('relic', text='RELIC')
        self.inv_tree.heading('gold_drop', text='GOLD DROP')
        self.inv_tree.heading('price', text='PLAT')
        self.inv_tree.heading('refinement', text='REFINE')
        self.inv_tree.heading('quantity', text='QTY')
        
        self.inv_tree.column('relic', width=120, anchor='center', minwidth=100)
        self.inv_tree.column('gold_drop', width=280, anchor='center', minwidth=200)
        self.inv_tree.column('price', width=70, anchor='center', minwidth=60)
        self.inv_tree.column('refinement', width=100, anchor='center', minwidth=80)
        self.inv_tree.column('quantity', width=60, anchor='center', minwidth=50)
        
        # Configure tag for alternating rows
        self.inv_tree.tag_configure('oddrow', background=self.inv_tree_odd_color)
        self.inv_tree.tag_configure('evenrow', background=self.inv_tree_even_color)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=scrollbar.set)
        
        self.inv_tree.grid(row=0, column=0, sticky="nsew", padx=(15, 0), pady=15)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=15, padx=(0, 5))
        
        # Bind double-click to edit quantity
        self.inv_tree.bind('<Double-1>', self.on_inventory_double_click)
        self.inv_tree.bind('<Delete>', self.on_inventory_delete)
        
        # Bottom bar frame (full width)
        bottom_frame = ctk.CTkFrame(frame, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        # Void Cascade info (left side)
        cascade_frame = ctk.CTkFrame(bottom_frame, fg_color=self.COLORS['bg_card'], corner_radius=8)
        cascade_frame.grid(row=0, column=0, sticky="w")
        
        self.cascade_label = ctk.CTkLabel(
            cascade_frame,
            text="⚡ Void Cascade: 0 runs (0 Radiant)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00ffa0"  # Void Cascade green
        )
        self.cascade_label.pack(padx=12, pady=8)
        
        # Quantity buttons frame (right side)
        qty_btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        qty_btn_frame.grid(row=0, column=1, sticky="e")
        
        minus_btn = ctk.CTkButton(
            qty_btn_frame, text="− Remove 1",
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['error'],
            text_color=self.COLORS['text_secondary'],
            height=32,
            corner_radius=6,
            command=lambda: self.change_selected_quantity(-1)
        )
        minus_btn.pack(side="left", padx=5)
        
        plus_btn = ctk.CTkButton(
            qty_btn_frame, text="+ Add 1",
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['success'],
            text_color=self.COLORS['text_secondary'],
            height=32,
            corner_radius=6,
            command=lambda: self.change_selected_quantity(1)
        )
        plus_btn.pack(side="left", padx=5)
        
        delete_btn = ctk.CTkButton(
            qty_btn_frame, text="🗑 Delete",
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['error'],
            text_color=self.COLORS['text_secondary'],
            height=32,
            corner_radius=6,
            command=self.delete_selected_relic
        )
        delete_btn.pack(side="left", padx=5)
        
        # Load price cache on init
        self._load_price_cache()
        self.refresh_inventory()
        
        return frame
    
    def _load_price_cache(self):
        """Load rare item prices and relic-to-rare mapping into cache."""
        try:
            # Load prices
            prices = self.wfcd_db.get_all_prices()
            self._price_cache = {p['item_name']: p['lowest_price'] for p in prices if p['lowest_price']}
            
            # Load relic -> rare item mapping from WFCD database
            self._relic_rare_cache = {}
            rare_items = self.wfcd_db.get_all_rare_items()
            for item in rare_items:
                self._relic_rare_cache[item.relic_full] = item.item_name
        except Exception as e:
            print(f"Error loading price cache: {e}")
            self._price_cache = {}
            self._relic_rare_cache = {}
    
    def get_relic_gold_price(self, relic) -> int:
        """Get the price of the gold (rare) drop from a relic."""
        if not relic:
            return 0
        
        # Build relic full name (e.g., "Axi A11")
        relic_full = f"{relic.era.value} {relic.name}"
        
        # Look up the rare item from WFCD database
        rare_item_name = self._relic_rare_cache.get(relic_full)
        if not rare_item_name:
            return 0
        
        # Look up the price
        return self._price_cache.get(rare_item_name, 0)
    
    def on_filter_change(self):
        """Handle filter change - save and refresh."""
        self.save_filter_preferences()
        self.refresh_inventory()
    
    def save_filter_preferences(self):
        """Save current filter settings."""
        self.app.settings['inv_era_filter'] = self.inv_era_filter.get() if self.inv_era_filter else 'All'
        self.app.settings['inv_sort'] = self.inv_sort.get() if self.inv_sort else 'Quantity ↓'
        self.app.settings['inv_profit_filter'] = self.profit_enabled
        self.app.settings['inv_rad_filter'] = self.rad_enabled
        self.app.settings['inv_ducats_filter'] = self.ducats_enabled
        self.app.save_settings()
    
    def toggle_profit_filter(self):
        """Toggle the profit filter on/off."""
        self.profit_enabled = self.profit_toggle.get() == 1
        # Update text color based on state
        if self.profit_enabled:
            self.profit_toggle.configure(text_color=self.COLORS['success'])
        else:
            self.profit_toggle.configure(text_color=self.COLORS['text_muted'])
        # Disable ducats filter if profit is enabled (they're mutually exclusive)
        if self.profit_enabled and self.ducats_enabled:
            self.ducats_enabled = False
            self.ducats_toggle.deselect()
            self.ducats_toggle.configure(text_color=self.COLORS['text_muted'])
        self.save_filter_preferences()
        self.refresh_inventory()
    
    def toggle_rad_filter(self):
        """Toggle the radiant filter on/off."""
        self.rad_enabled = self.rad_toggle.get() == 1
        # Update text color based on state
        if self.rad_enabled:
            self.rad_toggle.configure(text_color="#ff9800")
        else:
            self.rad_toggle.configure(text_color=self.COLORS['text_muted'])
        self.save_filter_preferences()
        self.refresh_inventory()
    
    def toggle_ducats_filter(self):
        """Toggle the ducats filter on/off (shows relics < 18p)."""
        self.ducats_enabled = self.ducats_toggle.get() == 1
        # Update text color based on state
        if self.ducats_enabled:
            self.ducats_toggle.configure(text_color="#fbbf24")
        else:
            self.ducats_toggle.configure(text_color=self.COLORS['text_muted'])
        # Disable profit filter if ducats is enabled (they're mutually exclusive)
        if self.ducats_enabled and self.profit_enabled:
            self.profit_enabled = False
            self.profit_toggle.deselect()
            self.profit_toggle.configure(text_color=self.COLORS['text_muted'])
        self.save_filter_preferences()
        self.refresh_inventory()
    
    def on_inventory_double_click(self, event):
        """Handle double-click on inventory item."""
        self.change_selected_quantity(1)
    
    def on_inventory_delete(self, event):
        """Handle delete key on inventory item."""
        self.delete_selected_relic()
    
    def change_selected_quantity(self, delta: int):
        """Change quantity of selected inventory item."""
        selection = self.inv_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        # Find the inventory item by matching the tree item
        values = self.inv_tree.item(item_id, 'values')
        # Columns: relic, gold_drop, price, refinement, quantity
        relic_name, gold_drop, price, ref, qty = values
        # Parse era and name from combined relic column
        parts = relic_name.split(' ', 1)
        era = parts[0] if len(parts) > 0 else ''
        name = parts[1] if len(parts) > 1 else ''
        
        for inv_item in self.app.inventory:
            if (inv_item.relic and 
                inv_item.relic.era.value == era and 
                inv_item.relic.name == name and
                inv_item.refinement.value == ref):
                inv_item.quantity += delta
                
                # Log to history
                action = 'added' if delta > 0 else 'removed'
                self.app.db.log_relic_action(action, era, name, ref, abs(delta))
                
                if inv_item.quantity <= 0:
                    self.app.inventory.remove(inv_item)
                break
        
        self.app.save_inventory()
        self.refresh_inventory()
    
    def delete_selected_relic(self):
        """Delete selected relic from inventory."""
        selection = self.inv_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        values = self.inv_tree.item(item_id, 'values')
        # Columns: relic, gold_drop, price, refinement, quantity
        relic_name, gold_drop, price, ref, qty = values
        # Parse era and name from combined relic column
        parts = relic_name.split(' ', 1)
        era = parts[0] if len(parts) > 0 else ''
        name = parts[1] if len(parts) > 1 else ''
        
        for inv_item in self.app.inventory:
            if (inv_item.relic and 
                inv_item.relic.era.value == era and 
                inv_item.relic.name == name and
                inv_item.refinement.value == ref):
                # Log to history before removing
                self.app.db.log_relic_action('removed', era, name, ref, inv_item.quantity)
                self.app.inventory.remove(inv_item)
                break
        
        self.app.save_inventory()
        self.refresh_inventory()
    
    def refresh_inventory(self):
        """Refresh the inventory display."""
        print(f"DEBUG refresh_inventory: app.inventory has {len(self.app.inventory)} items")
        
        # Clear existing items
        if hasattr(self, 'inv_tree') and self.inv_tree:
            for item in self.inv_tree.get_children():
                self.inv_tree.delete(item)
        else:
            print("DEBUG: inv_tree not ready, returning")
            return
        
        # Get filter values
        search_query = self.inv_search.get().strip().lower() if self.inv_search else ""
        era_filter = self.inv_era_filter.get() if self.inv_era_filter else "All"
        sort_by = self.inv_sort.get() if self.inv_sort else "Quantity ↓"
        
        # Filter inventory
        filtered = []
        for item in self.app.inventory:
            # Era filter
            if era_filter != "All":
                if not item.relic or item.relic.era.value != era_filter:
                    continue
            
            # Radiant filter
            if self.rad_enabled:
                if item.refinement.value != "Radiant":
                    continue
            
            # Search filter
            if search_query:
                # Special shortcut: "upgrade" shows all non-Intact relics
                if search_query == "upgrade" or search_query == "upgraded":
                    if item.refinement.value == "Intact":
                        continue
                else:
                    relic_name = f"{item.relic.era.value} {item.relic.name}".lower() if item.relic else ""
                    
                    # Get rare drop name from WFCD cache (most reliable source)
                    rare_drop = ""
                    if item.relic:
                        relic_full = f"{item.relic.era.value} {item.relic.name}"
                        rare_drop = self._relic_rare_cache.get(relic_full, "").lower()
                    
                    # Get refinement name
                    refinement = item.refinement.value.lower() if item.refinement else ""
                    
                    if search_query not in relic_name and search_query not in rare_drop and search_query not in refinement:
                        continue
            
            # Profit filter - only show relics with 20p+ gold parts
            if self.profit_enabled:
                gold_price = self.get_relic_gold_price(item.relic)
                if gold_price < 20:
                    continue
            
            # Ducats filter - only show relics with gold parts worth less than 18p
            if self.ducats_enabled:
                gold_price = self.get_relic_gold_price(item.relic)
                if gold_price >= 18:
                    continue
            
            filtered.append(item)
        
        print(f"DEBUG: After filtering: {len(filtered)} items")
        
        # Sort
        try:
            if sort_by == "Quantity ↓":
                filtered.sort(key=lambda x: -x.quantity)
            elif sort_by == "Quantity ↑":
                filtered.sort(key=lambda x: x.quantity)
            elif sort_by == "Plat ↓":
                filtered.sort(key=lambda x: self.get_relic_gold_price(x.relic), reverse=True)
            elif sort_by == "Plat ↑":
                filtered.sort(key=lambda x: self.get_relic_gold_price(x.relic))
        except Exception as e:
            print(f"DEBUG: Sort error: {e}")
        
        # Update stats
        total_filtered = sum(item.quantity for item in filtered)
        total_all = sum(item.quantity for item in self.app.inventory)
        
        if len(filtered) != len(self.app.inventory):
            # Determine which icon and color to use based on active filter
            if self.ducats_enabled:
                # Ducat filter active - use ducat icon and ducat gold color
                active_icon = self.stats_ducat_icon
                active_color = "#fbbf24"  # Matches ducat toggle color
            else:
                # Profit or other filter - use plat icon and bright gold
                active_icon = self.stats_plat_icon
                active_color = "#ffd700"  # Bright gold for plat
            
            # Update icon images
            if active_icon:
                self.filter_icon_label.configure(image=active_icon)
                self.filter_icon_label_right.configure(image=active_icon)
                self.filter_icon_label.pack(side="left", padx=(0, 4), before=self.inv_shown_label)
                self.filter_icon_label_right.pack(side="left", padx=(4, 0), after=self.inv_shown_label)
            
            # Update text color to match
            self.inv_shown_label.configure(text=f"{len(filtered)} shown ({total_filtered} relics)", text_color=active_color)
            self.inv_stats_label.configure(text=f" • {len(self.app.inventory)} total types ({total_all} relics)")
        else:
            # Hide icons when showing all
            self.filter_icon_label.pack_forget()
            self.filter_icon_label_right.pack_forget()
            self.inv_shown_label.configure(text="")
            self.inv_stats_label.configure(text=f"{len(self.app.inventory)} types • {total_all} relics")
        
        # Update Void Cascade counter (27 radiants per run)
        radiant_count = sum(
            item.quantity for item in self.app.inventory 
            if item.refinement.value == "Radiant"
        )
        cascade_runs = radiant_count // 27
        if self.cascade_label:
            self.cascade_label.configure(
                text=f"⚡ Void Cascade: {cascade_runs} runs ({radiant_count} Radiant)"
            )
        
        # Insert items into treeview with alternating row colors
        for idx, item in enumerate(filtered):
            if item.relic:
                era = item.relic.era.value
                name = item.relic.name
                relic_full = f"{era} {name}"
                gold_drop = self._relic_rare_cache.get(relic_full, "—")
                price = self.get_relic_gold_price(item.relic)
                price_str = f"{price}p" if price > 0 else "—"
            else:
                era = "?"
                name = "Unknown"
                gold_drop = "—"
                price_str = "—"
            
            # Apply alternating row tag
            row_tag = 'oddrow' if idx % 2 == 1 else 'evenrow'
            
            # Combined relic name (e.g., "Meso N14")
            relic_combined = f"{era} {name}"
            
            self.inv_tree.insert('', 'end', values=(
                relic_combined,
                gold_drop,
                price_str,
                item.refinement.value,
                item.quantity
            ), tags=(row_tag,))
        
        print(f"DEBUG: Inserted {len(filtered)} items, treeview has {len(self.inv_tree.get_children())} children")
