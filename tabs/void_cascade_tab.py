"""
Void Cascade Tab for The Relic Vault.
Track drops earned during Void Cascade runs.
"""

import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
from datetime import datetime
from api import WFCDRelicDatabase
from database import RelicDatabase


class VoidCascadeTab:
    """Void Cascade drop tracker - log rewards per run."""
    
    DUCAT_VALUES = {
        "Common": 15,
        "Uncommon": 45,
        "Rare": 100,
        "Forma Blueprint": 0,
    }
    
    def __init__(self, app):
        self.app = app
        self.COLORS = app.COLORS
        self.wfcd_db = WFCDRelicDatabase()
        self.db = RelicDatabase()
        self._all_items = []
        self._price_cache = {}
        self._ducat_cache = {}
        self._load_data()
        
        # Run state
        self.run_active = False
        self.current_run_drops = {}  # Dict: item_name -> {'rarity': str, 'plat': int, 'ducats': int, 'qty': int}
        self.run_history = self._load_history()
    
    def _load_data(self):
        """Load all items and prices."""
        try:
            all_items = self.wfcd_db.get_all_relic_items()
            self._all_items = [(item['item_name'], item.get('rarity', 'Common')) for item in all_items]
            self._all_items.append(("Forma Blueprint", "Forma Blueprint"))
            rarity_order = {"Rare": 0, "Uncommon": 1, "Common": 2, "Forma Blueprint": 3}
            self._all_items.sort(key=lambda x: (x[0], rarity_order.get(x[1], 2)))
            
            prices = self.wfcd_db.get_all_prices()
            self._price_cache = {p['item_name']: p['lowest_price'] or 0 for p in prices}
            self._ducat_cache = self.wfcd_db.get_all_ducats()
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def _get_ducats(self, item_name: str, rarity: str) -> int:
        """Get ducat value for an item."""
        # Forma Blueprint has no ducat value
        if "Forma" in item_name or rarity == "Forma Blueprint":
            return 0
        if item_name in self._ducat_cache:
            return self._ducat_cache[item_name]
        return self.DUCAT_VALUES.get(rarity, 15)
    
    def _load_history(self):
        """Load run history from database."""
        try:
            return self.db.get_run_history()
        except Exception as e:
            print(f"Error loading history: {e}")
            return []
    
    def _save_run(self, run_data):
        """Save a run to the database."""
        try:
            self.db.save_run(run_data)
            self.run_history = self._load_history()
        except Exception as e:
            print(f"Error saving run: {e}")
    
    def create_frame(self, parent):
        """Create the Void Cascade tracker frame."""
        frame = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_primary'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header
        self._create_header(frame)
        
        # Main content - single run panel (full width)
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Run Panel (the only panel now)
        self._create_run_panel(content)
        
        return frame
    
    def _create_header(self, parent):
        """Create the header section."""
        header = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header.grid_columnconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            header,
            text="⚡ Void Cascade Tracker",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.COLORS['text']
        )
        title.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Status
        self.status_label = ctk.CTkLabel(
            header,
            text="Ready to track",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        )
        self.status_label.grid(row=0, column=1, padx=20, pady=15, sticky="w")
        
        # New Run button
        self.new_run_btn = ctk.CTkButton(
            header,
            text="+ New Run",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.COLORS['success'],
            hover_color="#1ea34b",
            width=120,
            height=36,
            command=self.start_new_run
        )
        self.new_run_btn.grid(row=0, column=2, padx=20, pady=15)
    
    def _create_run_panel(self, parent):
        """Create the main run panel."""
        self.run_panel = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        self.run_panel.grid(row=0, column=0, sticky="nsew")
        self.run_panel.grid_columnconfigure(0, weight=1)
        self.run_panel.grid_rowconfigure(2, weight=1)
        
        self._show_empty_state()
    
    def _clear_run_panel(self):
        """Clear the run panel contents."""
        for widget in self.run_panel.winfo_children():
            widget.destroy()
    
    def _show_empty_state(self):
        """Show empty state when no run is active."""
        self._clear_run_panel()
        
        empty = ctk.CTkLabel(
            self.run_panel,
            text="⚡\n\nClick '+ New Run' to start tracking drops\n\nView past runs in the History tab",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_muted'],
            justify="center"
        )
        empty.place(relx=0.5, rely=0.5, anchor="center")
    
    def _show_active_run(self):
        """Show the active run interface for logging drops."""
        self._clear_run_panel()
        self.run_panel.grid_rowconfigure(2, weight=0)
        self.run_panel.grid_rowconfigure(3, weight=1)
        
        # Header with title and controls
        header = ctk.CTkFrame(self.run_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        header.grid_columnconfigure(1, weight=1)
        
        # Run title (editable)
        self.run_title_var = ctk.StringVar(value=f"Run {len(self.run_history) + 1}")
        self.title_entry = ctk.CTkEntry(
            header,
            textvariable=self.run_title_var,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.COLORS['bg_card'],
            border_width=0,
            width=200,
            height=36
        )
        self.title_entry.grid(row=0, column=0, sticky="w")
        
        # Finish run button
        end_btn = ctk.CTkButton(
            header,
            text="✓ Finish Run",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['accent_hover'],
            width=110,
            height=36,
            command=self._show_finish_preview
        )
        end_btn.grid(row=0, column=2)
        
        # Cancel button
        cancel_btn = ctk.CTkButton(
            header,
            text="✕",
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['error'],
            width=36,
            height=36,
            command=self.cancel_run
        )
        cancel_btn.grid(row=0, column=3, padx=(10, 0))
        
        # Add drop section
        add_frame = ctk.CTkFrame(self.run_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        add_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        add_frame.grid_columnconfigure(0, weight=1)
        
        # Search entry
        self.search_var = ctk.StringVar()
        search = ctk.CTkEntry(
            add_frame,
            textvariable=self.search_var,
            placeholder_text="🔍 Type to add a drop (e.g., 'Paris Prime Grip')...",
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=0,
            height=44
        )
        search.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        search.bind("<KeyRelease>", self._on_search)
        search.bind("<Return>", self._on_enter)
        search.focus()
        
        # Suggestions frame (hidden until search)
        self.suggestions_frame = ctk.CTkFrame(self.run_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        self.suggestions_frame.grid(row=2, column=0, sticky="new", padx=20)
        self.suggestions_frame.grid_remove()
        
        # Setup treeview style for drops
        self._setup_drops_treeview_style()
        
        # Drops treeview container
        drops_container = ctk.CTkFrame(self.run_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        drops_container.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 10))
        drops_container.grid_columnconfigure(0, weight=1)
        drops_container.grid_rowconfigure(0, weight=1)
        
        # Create treeview with scrollbar
        tree_frame = tk.Frame(drops_container, bg="#1e1e1e")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=8)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Treeview for drops with +/- columns
        self.drops_tree = ttk.Treeview(
            tree_frame,
            columns=("item", "plat", "ducats", "plus", "minus"),
            show="headings",
            style="Drops.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="browse"
        )
        self.drops_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.drops_tree.yview)
        
        # Configure columns
        self.drops_tree.heading("item", text="Item")
        self.drops_tree.heading("plat", text="Plat")
        self.drops_tree.heading("ducats", text="Ducats")
        self.drops_tree.heading("plus", text="")
        self.drops_tree.heading("minus", text="")
        
        self.drops_tree.column("item", width=340, anchor="w")
        self.drops_tree.column("plat", width=70, anchor="center")
        self.drops_tree.column("ducats", width=70, anchor="center")
        self.drops_tree.column("plus", width=28, anchor="center")
        self.drops_tree.column("minus", width=28, anchor="center")
        
        # Configure tags for rarity colors
        self.drops_tree.tag_configure('rare', foreground='#ffd700')
        self.drops_tree.tag_configure('uncommon', foreground='#c0c0c0')
        self.drops_tree.tag_configure('common', foreground='#cd7f32')
        self.drops_tree.tag_configure('forma', foreground='#60a5fa')
        self.drops_tree.tag_configure('oddrow', background='#2a2a35')
        self.drops_tree.tag_configure('evenrow', background='#232329')
        
        # Bind click to handle +/- buttons
        self.drops_tree.bind('<ButtonRelease-1>', self._on_tree_click)
        
        # Totals bar
        totals = ctk.CTkFrame(self.run_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        totals.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 15))
        
        totals_inner = ctk.CTkFrame(totals, fg_color="transparent")
        totals_inner.pack(pady=12)
        
        # Clickable GSB label
        self.gsb_label = ctk.CTkButton(
            totals_inner,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color=self.COLORS['bg_hover'],
            text_color=self.COLORS['accent'],
            width=0,
            height=24,
            command=self._copy_gsb_to_clipboard
        )
        self.gsb_label.pack(side="left")
        self.gsb_label.pack_forget()  # Hide initially
        
        self.totals_label = ctk.CTkLabel(
            totals_inner,
            text="0 drops  •  0p  •  0 ducats",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS['text']
        )
        self.totals_label.pack(side="left")
        
        self._current_gsb = ""  # Store current GSB string
        
        self._refresh_drops_list()
    
    def _setup_drops_treeview_style(self):
        """Setup ttk style for drops treeview."""
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure(
            "Drops.Treeview",
            background="#232329",
            foreground=self.COLORS['text'],
            fieldbackground="#232329",
            borderwidth=0,
            font=('Segoe UI', 12),
            rowheight=38
        )
        
        style.configure(
            "Drops.Treeview.Heading",
            background="#1e1e24",
            foreground=self.COLORS['text_secondary'],
            font=('Segoe UI', 11, 'bold'),
            borderwidth=0,
            relief='flat',
            padding=(10, 8)
        )
        
        style.map(
            "Drops.Treeview",
            background=[('selected', self.COLORS['accent'])],
            foreground=[('selected', '#ffffff')]
        )
    
    def _on_tree_click(self, event):
        """Handle click on treeview - detect +/- column clicks."""
        region = self.drops_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.drops_tree.identify_column(event.x)
        item = self.drops_tree.identify_row(event.y)
        
        if not item:
            return
        
        values = self.drops_tree.item(item, 'values')
        if not values or values[0] == "No drops yet - search above to add":
            return
        
        # Extract item name (remove bullet and quantity)
        item_name = values[0]
        if ' x' in item_name:
            item_name = item_name.rsplit(' x', 1)[0]
        item_name = item_name.replace('● ', '')
        
        # column #4 is plus, #5 is minus
        if column == '#4':
            self._increase_drop(item_name)
        elif column == '#5':
            self._decrease_drop(item_name)
    
    def _refresh_drops_list(self):
        """Refresh the current run's drops display using treeview."""
        if not hasattr(self, 'drops_tree'):
            return
        
        # Clear existing items
        for item in self.drops_tree.get_children():
            self.drops_tree.delete(item)
        
        if not self.current_run_drops:
            # Show empty message in first row
            self.drops_tree.insert("", "end", values=("No drops yet - search above to add", "", "", "", ""), tags=('evenrow',))
        else:
            # Sort by rarity: Rare -> Uncommon -> Common -> Forma
            rarity_order = {'Rare': 0, 'Uncommon': 1, 'Common': 2, 'Forma Blueprint': 3}
            sorted_drops = sorted(
                self.current_run_drops.items(),
                key=lambda x: (rarity_order.get(x[1]['rarity'], 2), x[0])
            )
            
            for i, (item_name, drop_data) in enumerate(sorted_drops):
                rarity = drop_data['rarity']
                plat = drop_data['plat']
                ducats = drop_data['ducats']
                qty = drop_data['qty']
                
                # Get rarity tag
                rarity_tag = {
                    'Rare': 'rare',
                    'Uncommon': 'uncommon',
                    'Common': 'common',
                    'Forma Blueprint': 'forma'
                }.get(rarity, 'common')
                
                # Row color tag
                row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                
                # Build display text
                qty_text = f" x{qty}" if qty > 1 else ""
                display_name = f"● {item_name}{qty_text}"
                
                # Calculate totals
                total_plat = plat * qty
                total_ducats = ducats * qty
                
                self.drops_tree.insert(
                    "", "end",
                    values=(display_name, f"{total_plat}p", f"{total_ducats}d", "➕", "➖"),
                    tags=(rarity_tag, row_tag)
                )
        
        self._update_totals()
    
    def _update_totals(self):
        """Update the totals display with rarity counters."""
        if not hasattr(self, 'totals_label'):
            return
        
        total_plat = sum(d['plat'] * d['qty'] for d in self.current_run_drops.values())
        total_ducats = sum(d['ducats'] * d['qty'] for d in self.current_run_drops.values())
        count = sum(d['qty'] for d in self.current_run_drops.values())
        
        # Count by rarity
        gold = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Rare')
        silver = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Uncommon')
        bronze = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Common')
        
        # Build rarity counter string
        rarity_parts = []
        if gold > 0:
            rarity_parts.append(f"{gold}G")
        if silver > 0:
            rarity_parts.append(f"{silver}S")
        if bronze > 0:
            rarity_parts.append(f"{bronze}B")
        
        rarity_str = " ".join(rarity_parts) if rarity_parts else ""
        self._current_gsb = rarity_str
        
        if rarity_str:
            self.gsb_label.configure(text=f"📋 {rarity_str}  •  ")
            self.gsb_label.pack(side="left")
            self.totals_label.configure(text=f"{count} drops  •  {total_plat}p  •  {total_ducats} ducats")
        else:
            self.gsb_label.pack_forget()
            self.totals_label.configure(text=f"{count} drops  •  {total_plat}p  •  {total_ducats} ducats")
    
    def _copy_gsb_to_clipboard(self):
        """Copy GSB string to clipboard."""
        if self._current_gsb:
            self.app.clipboard_clear()
            self.app.clipboard_append(self._current_gsb)
            # Show brief feedback
            original_text = self.gsb_label.cget("text")
            self.gsb_label.configure(text="✓ Copied!  •  ")
            self.app.after(1000, lambda: self.gsb_label.configure(text=original_text))
    
    def _on_search(self, event):
        """Handle search input."""
        query = self.search_var.get().strip().lower()
        
        if len(query) < 2:
            self.suggestions_frame.grid_remove()
            return
        
        # Find matches
        matches = []
        seen = set()
        for item_name, rarity in self._all_items:
            if query in item_name.lower() and item_name not in seen:
                matches.append((item_name, rarity))
                seen.add(item_name)
        
        # Sort by rarity: Rare -> Uncommon -> Common -> Forma
        rarity_order = {'Rare': 0, 'Uncommon': 1, 'Common': 2, 'Forma Blueprint': 3}
        matches.sort(key=lambda x: (rarity_order.get(x[1], 2), x[0]))
        matches = matches[:8]  # Limit after sorting
        
        # Clear old suggestions
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()
        
        if matches:
            self.suggestions_frame.grid()
            for i, (name, rarity) in enumerate(matches):
                self._create_suggestion(name, rarity, i)
        else:
            self.suggestions_frame.grid_remove()
    
    def _create_suggestion(self, item_name, rarity, index):
        """Create a suggestion button."""
        rarity_colors = {
            'Common': '#cd7f32',
            'Uncommon': '#c0c0c0',
            'Rare': '#ffd700',
            'Forma Blueprint': '#60a5fa'
        }
        color = rarity_colors.get(rarity, self.COLORS['text'])
        
        btn = ctk.CTkButton(
            self.suggestions_frame,
            text=f"● {item_name}",
            font=ctk.CTkFont(size=12),
            text_color=color,
            fg_color="transparent",
            hover_color=self.COLORS['bg_hover'],
            anchor="w",
            height=36,
            command=lambda: self._add_drop(item_name, rarity)
        )
        btn.pack(fill="x", padx=5, pady=2)
    
    def _on_enter(self, event):
        """Handle Enter key - add first suggestion."""
        query = self.search_var.get().strip().lower()
        if not query:
            return
        
        for item_name, rarity in self._all_items:
            if query in item_name.lower():
                self._add_drop(item_name, rarity)
                break
    
    def _add_drop(self, item_name, rarity):
        """Add a drop to the current run (or increase quantity if exists)."""
        if item_name in self.current_run_drops:
            self.current_run_drops[item_name]['qty'] += 1
        else:
            plat = self._price_cache.get(item_name, 0)
            ducats = self._get_ducats(item_name, rarity)
            self.current_run_drops[item_name] = {
                'rarity': rarity,
                'plat': plat,
                'ducats': ducats,
                'qty': 1
            }
        
        # Clear search
        self.search_var.set("")
        self.suggestions_frame.grid_remove()
        
        self._refresh_drops_list()
    
    def _increase_drop(self, item_name):
        """Increase quantity of a drop."""
        if item_name in self.current_run_drops:
            self.current_run_drops[item_name]['qty'] += 1
            self._refresh_drops_list()
    
    def _decrease_drop(self, item_name):
        """Decrease quantity of a drop (remove if qty reaches 0)."""
        if item_name in self.current_run_drops:
            self.current_run_drops[item_name]['qty'] -= 1
            if self.current_run_drops[item_name]['qty'] <= 0:
                del self.current_run_drops[item_name]
            self._refresh_drops_list()
    
    def start_new_run(self):
        """Start a new run."""
        if self.run_active:
            return
        
        self.run_active = True
        self.current_run_drops = {}
        
        self.new_run_btn.configure(state="disabled")
        self.status_label.configure(text="Recording run...", text_color="#22c55e")
        
        self._show_active_run()
    
    def _show_finish_preview(self):
        """Show a preview dialog before finishing the run."""
        if not self.run_active:
            return
        
        # Calculate totals
        total_drops = sum(d['qty'] for d in self.current_run_drops.values())
        total_plat = sum(d['plat'] * d['qty'] for d in self.current_run_drops.values())
        total_ducats = sum(d['ducats'] * d['qty'] for d in self.current_run_drops.values())
        
        # Count by rarity
        gold = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Rare')
        silver = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Uncommon')
        bronze = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Common')
        forma = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Forma Blueprint')
        
        # Create preview dialog
        dialog = ctk.CTkToplevel(self.app)
        dialog.title("Run Summary")
        dialog.geometry("400x350")
        dialog.configure(fg_color=self.COLORS['bg_primary'])
        dialog.transient(self.app)
        dialog.grab_set()
        
        # Center on parent
        dialog.update_idletasks()
        x = self.app.winfo_x() + (self.app.winfo_width() // 2) - 200
        y = self.app.winfo_y() + (self.app.winfo_height() // 2) - 175
        dialog.geometry(f"+{x}+{y}")
        
        # Title
        title = ctk.CTkLabel(
            dialog,
            text="⚡ Run Complete!",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS['text']
        )
        title.pack(pady=(20, 5))
        
        # Run name
        run_name = self.run_title_var.get() or f"Run {len(self.run_history) + 1}"
        name_lbl = ctk.CTkLabel(
            dialog,
            text=run_name,
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_secondary']
        )
        name_lbl.pack(pady=(0, 15))
        
        # Stats card
        stats_frame = ctk.CTkFrame(dialog, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        stats_frame.pack(fill="x", padx=30, pady=10)
        
        # Big numbers row
        big_row = ctk.CTkFrame(stats_frame, fg_color="transparent")
        big_row.pack(pady=15)
        
        # Total drops
        ctk.CTkLabel(
            big_row,
            text=f"{total_drops}",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.COLORS['text']
        ).pack(side="left", padx=15)
        ctk.CTkLabel(
            big_row,
            text="drops",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        ).pack(side="left", padx=(0, 20))
        
        # Plat
        ctk.CTkLabel(
            big_row,
            text=f"{total_plat}p",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#60a5fa"
        ).pack(side="left", padx=15)
        
        # Ducats
        ctk.CTkLabel(
            big_row,
            text=f"{total_ducats}d",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#fbbf24"
        ).pack(side="left", padx=15)
        
        # Rarity breakdown
        rarity_row = ctk.CTkFrame(stats_frame, fg_color="transparent")
        rarity_row.pack(pady=(0, 15))
        
        if gold > 0:
            ctk.CTkLabel(
                rarity_row,
                text=f"🥇 {gold}",
                font=ctk.CTkFont(size=14),
                text_color="#ffd700"
            ).pack(side="left", padx=10)
        if silver > 0:
            ctk.CTkLabel(
                rarity_row,
                text=f"🥈 {silver}",
                font=ctk.CTkFont(size=14),
                text_color="#c0c0c0"
            ).pack(side="left", padx=10)
        if bronze > 0:
            ctk.CTkLabel(
                rarity_row,
                text=f"🥉 {bronze}",
                font=ctk.CTkFont(size=14),
                text_color="#cd7f32"
            ).pack(side="left", padx=10)
        if forma > 0:
            ctk.CTkLabel(
                rarity_row,
                text=f"⚙ {forma}",
                font=ctk.CTkFont(size=14),
                text_color="#60a5fa"
            ).pack(side="left", padx=10)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def save_and_close():
            dialog.destroy()
            self.end_run()
        
        def go_back():
            dialog.destroy()
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="💾 Save Run",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.COLORS['success'],
            hover_color="#1ea34b",
            width=130,
            height=40,
            command=save_and_close
        )
        save_btn.pack(side="left", padx=10)
        
        back_btn = ctk.CTkButton(
            btn_frame,
            text="← Back",
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['bg_hover'],
            text_color=self.COLORS['text_secondary'],
            width=100,
            height=40,
            command=go_back
        )
        back_btn.pack(side="left", padx=10)
    
    def end_run(self):
        """End the current run and save it."""
        if not self.run_active:
            return
        
        # Build run data
        total_plat = sum(d['plat'] * d['qty'] for d in self.current_run_drops.values())
        total_ducats = sum(d['ducats'] * d['qty'] for d in self.current_run_drops.values())
        
        # Count by rarity (total quantity per rarity)
        gold = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Rare')
        silver = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Uncommon')
        bronze = sum(d['qty'] for d in self.current_run_drops.values() if d['rarity'] == 'Common')
        
        # Expand dict to list for storage (one entry per quantity)
        rewards_list = []
        for item_name, d in self.current_run_drops.items():
            for _ in range(d['qty']):
                rewards_list.append({'item': item_name, 'rarity': d['rarity'], 'plat': d['plat'], 'ducats': d['ducats']})
        
        run_data = {
            'title': self.run_title_var.get() or f"Run {len(self.run_history) + 1}",
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'rewards': rewards_list,
            'total_plat': total_plat,
            'total_ducats': total_ducats,
            'gold': gold,
            'silver': silver,
            'bronze': bronze
        }
        
        self._save_run(run_data)
        
        self.run_active = False
        self.current_run_drops = {}
        
        self.new_run_btn.configure(state="normal")
        self.status_label.configure(text="Run saved!", text_color=self.COLORS['success'])
        
        self._show_empty_state()
    
    def cancel_run(self):
        """Cancel the current run without saving."""
        from tkinter import messagebox
        if self.current_run_drops:
            if not messagebox.askyesno("Cancel Run", "Discard this run without saving?"):
                return
        
        self.run_active = False
        self.current_run_drops = {}
        
        self.new_run_btn.configure(state="normal")
        self.status_label.configure(text="Run cancelled", text_color=self.COLORS['text_muted'])
        
        self._show_empty_state()
