"""
Void Cascade Tab for The Relic Vault.
Track drops earned during Void Cascade runs.
"""

import customtkinter as ctk
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
        self.run_panel.grid_rowconfigure(2, weight=1)
        
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
        
        # Drops list
        drops_container = ctk.CTkFrame(self.run_panel, fg_color="transparent")
        drops_container.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 10))
        drops_container.grid_columnconfigure(0, weight=1)
        drops_container.grid_rowconfigure(0, weight=1)
        
        self.drops_scroll = ctk.CTkScrollableFrame(drops_container, fg_color="transparent")
        self.drops_scroll.grid(row=0, column=0, sticky="nsew")
        self.drops_scroll.grid_columnconfigure(0, weight=1)
        
        # Update row config
        self.run_panel.grid_rowconfigure(3, weight=1)
        
        # Totals bar
        totals = ctk.CTkFrame(self.run_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        totals.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 15))
        
        self.totals_label = ctk.CTkLabel(
            totals,
            text="0 drops  •  0p  •  0 ducats",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS['text']
        )
        self.totals_label.pack(pady=12)
        
        self._refresh_drops_list()
    
    def _refresh_drops_list(self):
        """Refresh the current run's drops display."""
        if not hasattr(self, 'drops_scroll'):
            return
        
        for widget in self.drops_scroll.winfo_children():
            widget.destroy()
        
        if not self.current_run_drops:
            empty = ctk.CTkLabel(
                self.drops_scroll,
                text="Add drops as you get them!\nType above to search and add items.",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted'],
                justify="center"
            )
            empty.grid(row=0, column=0, pady=40)
        else:
            for i, (item_name, drop_data) in enumerate(self.current_run_drops.items()):
                self._create_drop_row(item_name, drop_data, i)
        
        self._update_totals()
    
    def _create_drop_row(self, item_name, drop_data, index):
        """Create an editable drop row for current run with +/- buttons."""
        row = ctk.CTkFrame(self.drops_scroll, fg_color=self.COLORS['bg_card'], corner_radius=6)
        row.grid(row=index, column=0, sticky="ew", pady=2)
        row.grid_columnconfigure(0, weight=1)
        
        rarity = drop_data['rarity']
        plat = drop_data['plat']
        ducats = drop_data['ducats']
        qty = drop_data['qty']
        
        # Rarity color
        rarity_colors = {
            'Common': '#cd7f32',
            'Uncommon': '#c0c0c0',
            'Rare': '#ffd700',
            'Forma Blueprint': '#60a5fa'
        }
        color = rarity_colors.get(rarity, self.COLORS['text'])
        
        # Item name with rarity indicator and quantity
        qty_text = f" x{qty}" if qty > 1 else ""
        name_lbl = ctk.CTkLabel(
            row,
            text=f"● {item_name}{qty_text}",
            font=ctk.CTkFont(size=12, weight="bold" if qty > 1 else "normal"),
            text_color=color
        )
        name_lbl.grid(row=0, column=0, padx=12, pady=8, sticky="w")
        
        # Values (total for qty)
        total_plat = plat * qty
        total_ducats = ducats * qty
        vals = ctk.CTkLabel(
            row,
            text=f"{total_plat}p  •  {total_ducats}d",
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_secondary']
        )
        vals.grid(row=0, column=1, padx=(0, 10), pady=8)
        
        # +/- buttons frame
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=(0, 8), pady=4)
        
        # Plus button
        plus_btn = ctk.CTkButton(
            btn_frame,
            text="+",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.COLORS['bg_hover'],
            hover_color=self.COLORS['success'],
            text_color=self.COLORS['text'],
            width=28,
            height=28,
            corner_radius=4,
            command=lambda n=item_name: self._increase_drop(n)
        )
        plus_btn.pack(side="left", padx=2)
        
        # Minus button
        minus_btn = ctk.CTkButton(
            btn_frame,
            text="−",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.COLORS['bg_hover'],
            hover_color=self.COLORS['error'],
            text_color=self.COLORS['text'],
            width=28,
            height=28,
            corner_radius=4,
            command=lambda n=item_name: self._decrease_drop(n)
        )
        minus_btn.pack(side="left", padx=2)
    
    def _update_totals(self):
        """Update the totals display."""
        if not hasattr(self, 'totals_label'):
            return
        
        total_plat = sum(d['plat'] * d['qty'] for d in self.current_run_drops.values())
        total_ducats = sum(d['ducats'] * d['qty'] for d in self.current_run_drops.values())
        count = sum(d['qty'] for d in self.current_run_drops.values())
        
        self.totals_label.configure(text=f"{count} drops  •  {total_plat}p  •  {total_ducats} ducats")
    
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
            if len(matches) >= 8:
                break
        
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
