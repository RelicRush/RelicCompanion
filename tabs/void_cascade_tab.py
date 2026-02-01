"""
Void Cascade Tab for the Warframe Relic Companion.
Track rewards earned during Void Cascade runs.
"""

import customtkinter as ctk
from tkinter import ttk
from datetime import datetime
from api import WFCDRelicDatabase
from database import RelicDatabase


class VoidCascadeTab:
    """Void Cascade run tracker - clean and modern."""
    
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
        self._ducat_cache = {}  # Cache for per-item ducat values
        self._load_data()
        
        # Run state
        self.run_active = False
        self.current_run_rewards = []
        self.run_history = self._load_history()
        self.suggestion_buttons = []
    
    def _load_data(self):
        """Load all items and prices."""
        try:
            all_items = self.wfcd_db.get_all_relic_items()
            # Store all item+rarity combinations (same item can have different rarities in different relics)
            self._all_items = [(item['item_name'], item.get('rarity', 'Common')) for item in all_items]
            self._all_items.append(("Forma Blueprint", "Forma Blueprint"))
            # Sort by name, then by rarity (Rare first for visibility)
            rarity_order = {"Rare": 0, "Uncommon": 1, "Common": 2, "Forma Blueprint": 3}
            self._all_items.sort(key=lambda x: (x[0], rarity_order.get(x[1], 2)))
            
            prices = self.wfcd_db.get_all_prices()
            self._price_cache = {p['item_name']: p['lowest_price'] or 0 for p in prices}
            
            # Load per-item ducat values from database
            self._ducat_cache = self.wfcd_db.get_all_ducats()
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def _get_ducats(self, item_name: str, rarity: str) -> int:
        """Get ducat value for an item, with rarity-based fallback."""
        # Check the per-item ducat cache first
        if item_name in self._ducat_cache:
            return self._ducat_cache[item_name]
        # Fall back to rarity-based values
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
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # ============ HEADER ============
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.grid_columnconfigure(0, weight=1)
        
        # Title row
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")
        
        title = ctk.CTkLabel(
            title_frame, 
            text="Void Cascade",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.COLORS['text']
        )
        title.pack(side="left")
        
        # Status indicator
        self.status_indicator = ctk.CTkLabel(
            title_frame,
            text="● Ready",
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text_muted']
        )
        self.status_indicator.pack(side="left", padx=(15, 0))
        
        # ============ MAIN CONTENT ============
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Left side - Current Run
        left_panel = ctk.CTkFrame(content, fg_color=self.COLORS['bg_card'], corner_radius=12)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(2, weight=1)
        
        # Run header with controls
        run_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        run_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        run_header.grid_columnconfigure(0, weight=1)
        
        # Run title (editable)
        self.title_var = ctk.StringVar(value="Untitled Run")
        self.title_entry = ctk.CTkEntry(
            run_header,
            textvariable=self.title_var,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="transparent",
            border_width=0,
            width=200,
            height=32,
            state="disabled"
        )
        self.title_entry.grid(row=0, column=0, sticky="w")
        
        # Run controls
        controls = ctk.CTkFrame(run_header, fg_color="transparent")
        controls.grid(row=0, column=1, sticky="e")
        
        self.start_btn = ctk.CTkButton(
            controls,
            text="▶ Start",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.COLORS['success'],
            hover_color="#45a049",
            width=80, height=32,
            command=self.start_run
        )
        self.start_btn.pack(side="left", padx=(0, 8))
        
        self.end_btn = ctk.CTkButton(
            controls,
            text="⏹ End",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ff6b6b",
            hover_color="#ff5252",
            width=80, height=32,
            state="disabled",
            command=self.end_run
        )
        self.end_btn.pack(side="left")
        
        # Search/Add item
        search_frame = ctk.CTkFrame(left_panel, fg_color=self.COLORS['bg_secondary'], corner_radius=8)
        search_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search items to add...",
            font=ctk.CTkFont(size=13),
            height=40,
            fg_color="transparent",
            border_width=0,
            textvariable=self.search_var,
            state="disabled"
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search)
        self.search_entry.bind("<Return>", self._on_enter)
        
        # Suggestions dropdown
        self.suggestions_frame = ctk.CTkFrame(left_panel, fg_color=self.COLORS['bg_secondary'], corner_radius=8)
        self.suggestions_frame.grid(row=2, column=0, sticky="new", padx=20)
        self.suggestions_frame.grid_remove()  # Hidden initially
        
        # Rewards list
        rewards_container = ctk.CTkFrame(left_panel, fg_color="transparent")
        rewards_container.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 15))
        rewards_container.grid_columnconfigure(0, weight=1)
        rewards_container.grid_rowconfigure(0, weight=1)
        
        self.rewards_scroll = ctk.CTkScrollableFrame(
            rewards_container,
            fg_color="transparent"
        )
        self.rewards_scroll.grid(row=0, column=0, sticky="nsew")
        self.rewards_scroll.grid_columnconfigure(0, weight=1)
        
        # Empty state
        self.empty_label = ctk.CTkLabel(
            self.rewards_scroll,
            text="Click 'Start' to begin tracking rewards",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_muted']
        )
        self.empty_label.grid(row=0, column=0, pady=50)
        
        # Run totals bar at bottom of left panel
        totals_bar = ctk.CTkFrame(left_panel, fg_color=self.COLORS['bg_secondary'], corner_radius=8)
        totals_bar.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 15))
        
        self.total_plat_label = ctk.CTkLabel(
            totals_bar,
            text="0p",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#4fc3f7"
        )
        self.total_plat_label.pack(side="left", padx=20, pady=12)
        
        self.total_ducats_label = ctk.CTkLabel(
            totals_bar,
            text="0d",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ffd54f"
        )
        self.total_ducats_label.pack(side="left", padx=(0, 20), pady=12)
        
        self.total_items_label = ctk.CTkLabel(
            totals_bar,
            text="0 items",
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text_muted']
        )
        self.total_items_label.pack(side="right", padx=20, pady=12)
        
        # Right side - History
        right_panel = ctk.CTkFrame(content, fg_color=self.COLORS['bg_card'], corner_radius=12)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)
        
        # History header
        history_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        history_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(
            history_header,
            text="📜 Run History",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLORS['text']
        ).pack(side="left")
        
        # History list
        history_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        history_scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        history_scroll.grid_columnconfigure(0, weight=1)
        self.history_container = history_scroll
        
        self._refresh_history_display()
        
        # Update row weights for proper expansion
        left_panel.grid_rowconfigure(3, weight=1)
        
        return frame
    
    def _refresh_history_display(self):
        """Refresh the history panel."""
        for widget in self.history_container.winfo_children():
            widget.destroy()
        
        if not self.run_history:
            ctk.CTkLabel(
                self.history_container,
                text="No runs yet",
                font=ctk.CTkFont(size=13),
                text_color=self.COLORS['text_muted']
            ).grid(row=0, column=0, pady=30)
            return
        
        for i, run in enumerate(self.run_history[:15]):
            self._create_history_item(run, i)
    
    def _create_history_item(self, run, index):
        """Create a history item row."""
        item = ctk.CTkFrame(
            self.history_container,
            fg_color=self.COLORS['bg_secondary'],
            corner_radius=8
        )
        item.grid(row=index, column=0, sticky="ew", pady=3)
        item.grid_columnconfigure(0, weight=1)
        
        # Main content (clickable)
        content = ctk.CTkButton(
            item,
            text="",
            fg_color="transparent",
            hover_color=self.COLORS['bg_hover'],
            height=60,
            corner_radius=8,
            command=lambda r=run: self._show_run_details(r)
        )
        content.grid(row=0, column=0, sticky="ew")
        
        # Custom content inside button
        inner = ctk.CTkFrame(content, fg_color="transparent")
        inner.place(relx=0.02, rely=0.5, anchor="w")
        
        # Title
        ctk.CTkLabel(
            inner,
            text=run['title'][:20] + "..." if len(run['title']) > 20 else run['title'],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.COLORS['text']
        ).pack(anchor="w")
        
        # Date and stats
        g, s, b = run.get('gold', 0), run.get('silver', 0), run.get('bronze', 0)
        stats_text = f"{run['date']}  •  G:{g} S:{s} B:{b}"
        ctk.CTkLabel(
            inner,
            text=stats_text,
            font=ctk.CTkFont(size=10),
            text_color=self.COLORS['text_muted']
        ).pack(anchor="w")
        
        # Values on right
        values = ctk.CTkFrame(content, fg_color="transparent")
        values.place(relx=0.98, rely=0.5, anchor="e")
        
        ctk.CTkLabel(
            values,
            text=f"{run['total_plat']}p",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#4fc3f7"
        ).pack(side="left", padx=(0, 8))
        
        ctk.CTkLabel(
            values,
            text=f"{run['total_ducats']}d",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffd54f"
        ).pack(side="left")
        
        # Delete button
        del_btn = ctk.CTkButton(
            item,
            text="×",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="transparent",
            hover_color="#ff6b6b",
            text_color=self.COLORS['text_muted'],
            width=30, height=30,
            command=lambda rid=run.get('id'): self._delete_run(rid)
        )
        del_btn.grid(row=0, column=1, padx=5)
    
    def start_run(self):
        """Start a new run."""
        self.run_active = True
        self.current_run_rewards = []
        
        self.start_btn.configure(state="disabled")
        self.end_btn.configure(state="normal")
        self.search_entry.configure(state="normal", placeholder_text="🔍 Search items to add...")
        self.title_entry.configure(state="normal")
        self.status_indicator.configure(text="● Recording", text_color=self.COLORS['success'])
        
        self._update_display()
        self.search_entry.focus()
    
    def end_run(self):
        """End current run and save."""
        if not self.current_run_rewards:
            self._reset_run()
            return
        
        # Calculate totals
        total_plat = sum(r[1] for r in self.current_run_rewards)
        total_ducats = sum(r[2] for r in self.current_run_rewards)
        gold = sum(1 for r in self.current_run_rewards if r[3] == "Rare")
        silver = sum(1 for r in self.current_run_rewards if r[3] == "Uncommon")
        bronze = sum(1 for r in self.current_run_rewards if r[3] == "Common")
        
        # Group rewards
        grouped = {}
        for name, plat, ducats, rarity in self.current_run_rewards:
            if name not in grouped:
                grouped[name] = {'count': 0, 'plat': plat, 'ducats': ducats, 'rarity': rarity}
            grouped[name]['count'] += 1
        
        run_data = {
            'title': self.title_var.get() or "Untitled Run",
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'rewards': [{'name': k, 'count': v['count'], 'plat': v['plat'], 'ducats': v['ducats'], 'rarity': v['rarity']} 
                       for k, v in grouped.items()],
            'total_plat': total_plat,
            'total_ducats': total_ducats,
            'total_items': len(self.current_run_rewards),
            'gold': gold,
            'silver': silver,
            'bronze': bronze
        }
        self._save_run(run_data)
        self._reset_run()
        self._refresh_history_display()
        self._show_run_complete(run_data)
    
    def _reset_run(self):
        """Reset run state."""
        self.run_active = False
        self.current_run_rewards = []
        self.title_var.set("Untitled Run")
        
        self.start_btn.configure(state="normal")
        self.end_btn.configure(state="disabled")
        self.search_entry.configure(state="disabled", placeholder_text="🔍 Search items to add...")
        self.title_entry.configure(state="disabled")
        self.status_indicator.configure(text="● Ready", text_color=self.COLORS['text_muted'])
        self.suggestions_frame.grid_remove()
        
        self._update_display()
    
    def _on_search(self, event=None):
        """Update search suggestions."""
        if not self.run_active:
            return
        
        query = self.search_var.get().lower().strip()
        
        for btn in self.suggestion_buttons:
            btn.destroy()
        self.suggestion_buttons = []
        
        if len(query) < 2:
            self.suggestions_frame.grid_remove()
            return
        
        matches = []
        for item_name, rarity in self._all_items:
            if query in item_name.lower():
                plat = self._price_cache.get(item_name, 0)
                ducats = self._get_ducats(item_name, rarity)
                priority = 0 if item_name.lower().startswith(query) else 1
                matches.append((priority, item_name, rarity, plat, ducats))
        
        matches.sort(key=lambda x: (x[0], x[1]))
        
        if not matches:
            self.suggestions_frame.grid_remove()
            return
        
        self.suggestions_frame.grid()
        
        for _, item_name, rarity, plat, ducats in matches[:6]:
            color = "#ffd54f" if rarity == "Rare" else "#90caf9" if rarity == "Uncommon" else self.COLORS['text']
            rarity_short = "R" if rarity == "Rare" else "U" if rarity == "Uncommon" else "C"
            
            btn = ctk.CTkButton(
                self.suggestions_frame,
                text=f"[{rarity_short}] {item_name}",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=self.COLORS['bg_hover'],
                text_color=color,
                height=36,
                anchor="w",
                command=lambda n=item_name, p=plat, d=ducats, r=rarity: self._add_item(n, p, d, r)
            )
            btn.pack(fill="x", padx=5, pady=2)
            
            # Add plat/ducat info on right
            info = ctk.CTkLabel(
                btn,
                text=f"{plat}p • {ducats}d",
                font=ctk.CTkFont(size=11),
                text_color=self.COLORS['text_muted']
            )
            info.place(relx=0.95, rely=0.5, anchor="e")
            
            self.suggestion_buttons.append(btn)
    
    def _on_enter(self, event=None):
        """Add top match on Enter."""
        if not self.run_active or len(self.search_var.get().strip()) < 2:
            return
        
        query = self.search_var.get().lower().strip()
        for item_name, rarity in self._all_items:
            if query in item_name.lower():
                plat = self._price_cache.get(item_name, 0)
                ducats = self._get_ducats(item_name, rarity)
                self._add_item(item_name, plat, ducats, rarity)
                return
    
    def _add_item(self, item_name, plat, ducats, rarity="Common"):
        """Add item to current run."""
        if not self.run_active:
            return
        
        self.current_run_rewards.append((item_name, plat, ducats, rarity))
        self.search_var.set("")
        self.suggestions_frame.grid_remove()
        
        for btn in self.suggestion_buttons:
            btn.destroy()
        self.suggestion_buttons = []
        
        self._update_display()
        self.search_entry.focus()
    
    def _remove_item(self, item_name):
        """Remove one instance of an item."""
        for i, (name, _, _, _) in enumerate(self.current_run_rewards):
            if name == item_name:
                self.current_run_rewards.pop(i)
                self._update_display()
                return
    
    def _update_display(self):
        """Update the rewards display."""
        for widget in self.rewards_scroll.winfo_children():
            widget.destroy()
        
        if not self.current_run_rewards:
            msg = "Search and add rewards above" if self.run_active else "Click 'Start' to begin tracking rewards"
            self.empty_label = ctk.CTkLabel(
                self.rewards_scroll,
                text=msg,
                font=ctk.CTkFont(size=14),
                text_color=self.COLORS['text_muted']
            )
            self.empty_label.grid(row=0, column=0, pady=50)
            self.total_plat_label.configure(text="0p")
            self.total_ducats_label.configure(text="0d")
            self.total_items_label.configure(text="0 items")
            return
        
        total_plat = 0
        total_ducats = 0
        
        # Group rewards
        grouped = {}
        for name, plat, ducats, rarity in self.current_run_rewards:
            total_plat += plat
            total_ducats += ducats
            if name not in grouped:
                grouped[name] = {'count': 0, 'plat': plat, 'ducats': ducats, 'rarity': rarity}
            grouped[name]['count'] += 1
        
        # Create reward rows
        for i, (item_name, data) in enumerate(grouped.items()):
            self._create_reward_row(item_name, data, i)
        
        self.total_plat_label.configure(text=f"{total_plat}p")
        self.total_ducats_label.configure(text=f"{total_ducats}d")
        self.total_items_label.configure(text=f"{len(self.current_run_rewards)} items")
    
    def _create_reward_row(self, item_name, data, index):
        """Create a reward row in the list."""
        count = data['count']
        plat = data['plat']
        ducats = data['ducats']
        rarity = data['rarity']
        
        # Row color based on rarity
        row_color = "#3d3522" if rarity == "Rare" else "#2a3340" if rarity == "Uncommon" else self.COLORS['bg_secondary']
        
        row = ctk.CTkFrame(self.rewards_scroll, fg_color=row_color, corner_radius=8)
        row.grid(row=index, column=0, sticky="ew", pady=3, padx=2)
        
        # Rarity indicator bar on left
        rarity_color = "#ffd54f" if rarity == "Rare" else "#90caf9" if rarity == "Uncommon" else self.COLORS['text_muted']
        indicator = ctk.CTkFrame(row, fg_color=rarity_color, width=4, height=28, corner_radius=2)
        indicator.pack(side="left", padx=(10, 12), pady=8)
        
        # Item name with count
        text = f"{item_name}" + (f"  ×{count}" if count > 1 else "")
        name_label = ctk.CTkLabel(
            row,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text']
        )
        name_label.pack(side="left", pady=10)
        
        # Buttons on right
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.pack(side="right", padx=(0, 8))
        
        remove_btn = ctk.CTkButton(
            btn_frame,
            text="−",
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="transparent",
            hover_color="#ff6b6b",
            text_color=self.COLORS['text_muted'],
            width=32, height=32,
            command=lambda n=item_name: self._remove_item(n)
        )
        remove_btn.pack(side="right")
        
        add_btn = ctk.CTkButton(
            btn_frame,
            text="+",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="transparent",
            hover_color=self.COLORS['success'],
            text_color="#4fc3f7",
            width=32, height=32,
            command=lambda n=item_name, p=plat, d=ducats, r=rarity: self._add_item(n, p, d, r)
        )
        add_btn.pack(side="right")
        
        # Values next to buttons
        values = ctk.CTkLabel(
            row,
            text=f"{plat*count}p • {ducats*count}d",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        )
        values.pack(side="right", padx=10)
    
    def _delete_run(self, run_id):
        """Delete a run from history."""
        if run_id:
            self.db.delete_run(run_id)
            self.run_history = self._load_history()
            self._refresh_history_display()
    
    def _show_run_complete(self, run_data):
        """Show run completion popup."""
        popup = ctk.CTkToplevel(self.app)
        popup.title("Run Complete!")
        popup.geometry("320x220")
        popup.transient(self.app)
        popup.grab_set()
        popup.configure(fg_color=self.COLORS['bg_card'])
        
        popup.update_idletasks()
        x = self.app.winfo_x() + (self.app.winfo_width() - 320) // 2
        y = self.app.winfo_y() + (self.app.winfo_height() - 220) // 2
        popup.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(
            popup,
            text="✓ Run Saved!",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.COLORS['success']
        ).pack(pady=(25, 5))
        
        ctk.CTkLabel(
            popup,
            text=run_data['title'],
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text']
        ).pack()
        
        stats = ctk.CTkFrame(popup, fg_color="transparent")
        stats.pack(pady=20)
        
        ctk.CTkLabel(
            stats,
            text=f"{run_data['total_plat']}p",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#4fc3f7"
        ).pack(side="left", padx=15)
        
        ctk.CTkLabel(
            stats,
            text=f"{run_data['total_ducats']}d",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#ffd54f"
        ).pack(side="left", padx=15)
        
        ctk.CTkButton(
            popup,
            text="Done",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['accent_hover'],
            width=100, height=36,
            command=popup.destroy
        ).pack(pady=10)
    
    def _show_run_details(self, run):
        """Show detailed view of a run."""
        popup = ctk.CTkToplevel(self.app)
        popup.title(run['title'])
        popup.geometry("400x500")
        popup.transient(self.app)
        popup.grab_set()
        popup.configure(fg_color=self.COLORS['bg_card'])
        
        popup.update_idletasks()
        x = self.app.winfo_x() + (self.app.winfo_width() - 400) // 2
        y = self.app.winfo_y() + (self.app.winfo_height() - 500) // 2
        popup.geometry(f"400x500+{x}+{y}")
        
        # Header
        ctk.CTkLabel(
            popup,
            text=run['title'],
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS['text']
        ).pack(pady=(20, 5))
        
        ctk.CTkLabel(
            popup,
            text=run['date'],
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        ).pack()
        
        # Totals
        totals = ctk.CTkFrame(popup, fg_color=self.COLORS['bg_secondary'], corner_radius=10)
        totals.pack(fill="x", padx=25, pady=15)
        
        ctk.CTkLabel(
            totals,
            text=f"{run['total_plat']}p",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#4fc3f7"
        ).pack(side="left", padx=20, pady=15)
        
        ctk.CTkLabel(
            totals,
            text=f"{run['total_ducats']}d",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#ffd54f"
        ).pack(side="left", padx=20)
        
        g, s, b = run.get('gold', 0), run.get('silver', 0), run.get('bronze', 0)
        ctk.CTkLabel(
            totals,
            text=f"G:{g}  S:{s}  B:{b}",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        ).pack(side="right", padx=20)
        
        # Rewards header
        ctk.CTkLabel(
            popup,
            text="Rewards",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS['text']
        ).pack(anchor="w", padx=25, pady=(5, 5))
        
        # Rewards list
        scroll = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=25, pady=(0, 15))
        
        for reward in run.get('rewards', []):
            rarity = reward.get('rarity', 'Common')
            row_color = "#3d3522" if rarity == "Rare" else "#2a3340" if rarity == "Uncommon" else self.COLORS['bg_secondary']
            
            row = ctk.CTkFrame(scroll, fg_color=row_color, corner_radius=6, height=38)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            
            name = reward['name']
            count = reward['count']
            plat = reward['plat'] * count
            ducats = reward['ducats'] * count
            
            text = f"{name}" + (f"  ×{count}" if count > 1 else "")
            ctk.CTkLabel(
                row,
                text=text,
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text']
            ).pack(side="left", padx=12, pady=8)
            
            ctk.CTkLabel(
                row,
                text=f"{plat}p • {ducats}d",
                font=ctk.CTkFont(size=11),
                text_color=self.COLORS['text_muted']
            ).pack(side="right", padx=12)
        
        ctk.CTkButton(
            popup,
            text="Close",
            font=ctk.CTkFont(size=13),
            fg_color=self.COLORS['bg_hover'],
            hover_color=self.COLORS['accent'],
            width=100, height=36,
            command=popup.destroy
        ).pack(pady=15)
    
    # Compatibility methods
    def add_reward(self, item_name, plat_value, ducat_value, rarity):
        self._add_item(item_name, plat_value, ducat_value, rarity)
    
    def start_new_run(self):
        self.start_run()
    
    def clear_current_run(self):
        self.current_run_rewards = []
        self._update_display()
    
    def refresh_display(self):
        self._load_data()
        self._update_display()
        self._refresh_history_display()

