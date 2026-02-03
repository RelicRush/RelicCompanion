"""
History Tab for The Relic Vault.
Shows a log of all relic inventory changes and Void Cascade runs.
"""

import customtkinter as ctk
from tkinter import ttk
from datetime import datetime
from database import RelicDatabase


class HistoryTab:
    """History tracker - view inventory changes and Void Cascade runs."""
    
    def __init__(self, app):
        self.app = app
        self.COLORS = app.COLORS
        self.db = RelicDatabase()
        self.history_tree = None
        self.filter_var = None
        self.current_section = "relics"  # "relics" or "cascade"
        self.selected_run = None
    
    def create_frame(self, parent) -> ctk.CTkFrame:
        """Create the history tab frame."""
        frame = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_primary'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header with section toggle
        self._create_header(frame)
        
        # Content area (switches between relic history and cascade runs)
        self.content_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Show relic history by default
        self._show_relic_history()
        
        return frame
    
    def _create_header(self, parent):
        """Create the header with section toggle."""
        header = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            header,
            text="📜 History",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS['text']
        )
        title.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Section toggle buttons
        toggle_frame = ctk.CTkFrame(header, fg_color="transparent")
        toggle_frame.grid(row=0, column=1, padx=20, pady=15)
        
        self.relic_btn = ctk.CTkButton(
            toggle_frame,
            text="🎒 Relic Changes",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['accent_hover'],
            width=140,
            height=32,
            command=self._show_relic_history
        )
        self.relic_btn.pack(side="left", padx=(0, 5))
        
        self.cascade_btn = ctk.CTkButton(
            toggle_frame,
            text="⚡ Void Cascade Runs",
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['bg_hover'],
            text_color=self.COLORS['text_secondary'],
            width=160,
            height=32,
            command=self._show_cascade_runs
        )
        self.cascade_btn.pack(side="left")
    
    def _update_toggle_buttons(self):
        """Update toggle button appearance based on current section."""
        if self.current_section == "relics":
            self.relic_btn.configure(
                fg_color=self.COLORS['accent'],
                text_color=self.COLORS['text'],
                font=ctk.CTkFont(size=12, weight="bold")
            )
            self.cascade_btn.configure(
                fg_color=self.COLORS['bg_card'],
                text_color=self.COLORS['text_secondary'],
                font=ctk.CTkFont(size=12)
            )
        else:
            self.cascade_btn.configure(
                fg_color=self.COLORS['accent'],
                text_color=self.COLORS['text'],
                font=ctk.CTkFont(size=12, weight="bold")
            )
            self.relic_btn.configure(
                fg_color=self.COLORS['bg_card'],
                text_color=self.COLORS['text_secondary'],
                font=ctk.CTkFont(size=12)
            )
    
    def _clear_content(self):
        """Clear the content frame."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    # ==================== RELIC HISTORY SECTION ====================
    
    def _show_relic_history(self):
        """Show the relic inventory history section."""
        self.current_section = "relics"
        self._update_toggle_buttons()
        self._clear_content()
        
        # Filter bar
        filter_frame = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS['bg_secondary'], corner_radius=8)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        filter_label = ctk.CTkLabel(
            filter_frame,
            text="Filter:",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_secondary']
        )
        filter_label.pack(side="left", padx=(15, 10), pady=10)
        
        self.filter_var = ctk.StringVar(value="All")
        filter_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            values=["All", "Added", "Removed", "Sold", "Opened"],
            variable=self.filter_var,
            font=ctk.CTkFont(size=12),
            dropdown_font=ctk.CTkFont(size=12),
            fg_color=self.COLORS['bg_card'],
            button_color=self.COLORS['bg_hover'],
            button_hover_color=self.COLORS['accent'],
            dropdown_fg_color=self.COLORS['bg_card'],
            dropdown_hover_color=self.COLORS['bg_hover'],
            command=lambda _: self.refresh_history()
        )
        filter_dropdown.pack(side="left")
        
        # Stats label
        self.stats_label = ctk.CTkLabel(
            filter_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_muted']
        )
        self.stats_label.pack(side="left", padx=20)
        
        # Clear button
        clear_btn = ctk.CTkButton(
            filter_frame,
            text="🗑️ Clear",
            font=ctk.CTkFont(size=11),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['error'],
            text_color=self.COLORS['text_secondary'],
            width=70,
            height=28,
            command=self.clear_history
        )
        clear_btn.pack(side="right", padx=15, pady=10)
        
        # History list
        self._create_relic_history_list()
        self.refresh_history()
    
    def _create_relic_history_list(self):
        """Create the relic history treeview."""
        tree_frame = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
        
        # Style the treeview
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("History.Treeview",
                       background="#232329",
                       foreground=self.COLORS['text'],
                       fieldbackground="#232329",
                       borderwidth=0,
                       rowheight=32,
                       font=('Segoe UI', 11))
        
        style.configure("History.Treeview.Heading",
                       background=self.COLORS['bg_card'],
                       foreground=self.COLORS['text'],
                       borderwidth=0,
                       font=('Segoe UI', 11, 'bold'))
        
        style.map("History.Treeview",
                 background=[('selected', self.COLORS['accent'])],
                 foreground=[('selected', '#ffffff')])
        
        columns = ("timestamp", "action", "relic", "refinement", "qty", "plat")
        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="History.Treeview",
            selectmode="browse"
        )
        
        self.history_tree.heading("timestamp", text="Time")
        self.history_tree.heading("action", text="Action")
        self.history_tree.heading("relic", text="Relic")
        self.history_tree.heading("refinement", text="Refinement")
        self.history_tree.heading("qty", text="Qty")
        self.history_tree.heading("plat", text="Plat")
        
        self.history_tree.column("timestamp", width=150, minwidth=120)
        self.history_tree.column("action", width=80, minwidth=60)
        self.history_tree.column("relic", width=200, minwidth=150)
        self.history_tree.column("refinement", width=100, minwidth=80)
        self.history_tree.column("qty", width=60, minwidth=40)
        self.history_tree.column("plat", width=80, minwidth=60)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.grid(row=0, column=0, sticky="nsew", padx=(15, 0), pady=15)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=15, padx=(0, 15))
        
        self.history_tree.tag_configure('added', foreground='#22c55e')
        self.history_tree.tag_configure('removed', foreground='#ef4444')
        self.history_tree.tag_configure('sold', foreground='#60a5fa')
        self.history_tree.tag_configure('opened', foreground='#fbbf24')
    
    def refresh_history(self):
        """Refresh the relic history display."""
        if not self.history_tree:
            return
        
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        filter_value = self.filter_var.get() if self.filter_var else "All"
        action_filter = filter_value.lower() if filter_value != "All" else None
        
        history = self.app.db.get_relic_history(limit=500, action_filter=action_filter)
        
        for entry in history:
            try:
                ts = datetime.fromisoformat(entry['timestamp'])
                time_str = ts.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = entry['timestamp'][:16] if entry['timestamp'] else "Unknown"
            
            relic_str = f"{entry['era']} {entry['name']}"
            plat_str = f"{entry['platinum_value']:.0f}p" if entry['platinum_value'] > 0 else ""
            action_display = entry['action'].capitalize()
            
            self.history_tree.insert(
                "", "end",
                values=(time_str, action_display, relic_str, entry['refinement'], 
                        entry['quantity'], plat_str),
                tags=(entry['action'],)
            )
        
        self._update_stats()
    
    def _update_stats(self):
        """Update the stats label."""
        stats = self.app.db.get_history_stats()
        stats_text = (
            f"📥 {stats['total_added']}  |  📤 {stats['total_removed']}  |  "
            f"💰 {stats['total_sold']} ({stats['total_plat_earned']:.0f}p)"
        )
        self.stats_label.configure(text=stats_text)
    
    def clear_history(self):
        """Clear relic history."""
        from tkinter import messagebox
        if messagebox.askyesno("Clear History", "Clear all relic history?"):
            self.app.db.clear_relic_history()
            self.refresh_history()
    
    # ==================== VOID CASCADE RUNS SECTION ====================
    
    def _show_cascade_runs(self):
        """Show the Void Cascade runs section."""
        self.current_section = "cascade"
        self._update_toggle_buttons()
        self._clear_content()
        self.selected_run = None
        
        # Two columns: runs list and run details
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=2)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Left - Runs list
        self._create_runs_list()
        
        # Right - Run details
        self._create_run_details_panel()
    
    def _create_runs_list(self):
        """Create the cascade runs list."""
        panel = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkLabel(
            panel,
            text="⚡ Void Cascade Runs",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS['text']
        )
        header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        self.runs_scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.runs_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 15))
        self.runs_scroll.grid_columnconfigure(0, weight=1)
        
        self._refresh_runs_list()
    
    def _refresh_runs_list(self):
        """Refresh the runs list."""
        for widget in self.runs_scroll.winfo_children():
            widget.destroy()
        
        runs = self.db.get_run_history()
        
        if not runs:
            empty = ctk.CTkLabel(
                self.runs_scroll,
                text="No runs yet\n\nStart tracking in the\nVoid Cascade tab",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted'],
                justify="center"
            )
            empty.grid(row=0, column=0, pady=40)
            return
        
        for i, run in enumerate(runs[:30]):
            self._create_run_row(run, i)
    
    def _create_run_row(self, run, index):
        """Create a clickable row for a run."""
        is_selected = self.selected_run and self.selected_run.get('id') == run.get('id')
        bg_color = self.COLORS['accent'] if is_selected else self.COLORS['bg_card']
        
        row = ctk.CTkButton(
            self.runs_scroll,
            text="",
            fg_color=bg_color,
            hover_color=self.COLORS['bg_hover'],
            height=65,
            corner_radius=8,
            command=lambda r=run: self._select_run(r)
        )
        row.grid(row=index, column=0, sticky="ew", pady=2)
        
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9)
        inner.bind("<Button-1>", lambda e, r=run: self._select_run(r))
        
        title_text = run.get('title', 'Untitled')[:20]
        date_text = run.get('date', '')[:10]
        drops = len(run.get('rewards', []))
        plat = run.get('total_plat', 0)
        
        title_lbl = ctk.CTkLabel(
            inner,
            text=title_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.COLORS['text']
        )
        title_lbl.pack(anchor="w")
        title_lbl.bind("<Button-1>", lambda e, r=run: self._select_run(r))
        
        stats_lbl = ctk.CTkLabel(
            inner,
            text=f"{date_text}  •  {drops} drops  •  {plat}p",
            font=ctk.CTkFont(size=10),
            text_color=self.COLORS['text_secondary']
        )
        stats_lbl.pack(anchor="w")
        stats_lbl.bind("<Button-1>", lambda e, r=run: self._select_run(r))
    
    def _create_run_details_panel(self):
        """Create the run details panel."""
        self.details_panel = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        self.details_panel.grid(row=0, column=1, sticky="nsew")
        self.details_panel.grid_columnconfigure(0, weight=1)
        self.details_panel.grid_rowconfigure(1, weight=1)
        
        self._show_empty_run_details()
    
    def _show_empty_run_details(self):
        """Show empty state for run details."""
        for widget in self.details_panel.winfo_children():
            widget.destroy()
        
        empty = ctk.CTkLabel(
            self.details_panel,
            text="⚡\n\nSelect a run to view details",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_muted'],
            justify="center"
        )
        empty.place(relx=0.5, rely=0.5, anchor="center")
    
    def _select_run(self, run):
        """Select a run to view details."""
        self.selected_run = run
        self._refresh_runs_list()
        self._show_run_details(run)
    
    def _show_run_details(self, run):
        """Show details of a selected run."""
        for widget in self.details_panel.winfo_children():
            widget.destroy()
        
        self.details_panel.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkFrame(self.details_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        header.grid_columnconfigure(1, weight=1)
        
        title = ctk.CTkLabel(
            header,
            text=run.get('title', 'Untitled Run'),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLORS['text']
        )
        title.grid(row=0, column=0, sticky="w")
        
        date = ctk.CTkLabel(
            header,
            text=run.get('date', ''),
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_muted']
        )
        date.grid(row=0, column=1, padx=15, sticky="w")
        
        delete_btn = ctk.CTkButton(
            header,
            text="🗑️",
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['error'],
            width=36,
            height=32,
            command=lambda: self._delete_run(run)
        )
        delete_btn.grid(row=0, column=2)
        
        # Drops list
        drops_scroll = ctk.CTkScrollableFrame(self.details_panel, fg_color="transparent")
        drops_scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 10))
        drops_scroll.grid_columnconfigure(0, weight=1)
        
        rewards = run.get('rewards', [])
        if rewards:
            # Consolidate duplicates
            consolidated = {}
            for drop in rewards:
                item = drop.get('item', drop.get('name', 'Unknown'))
                if item in consolidated:
                    consolidated[item]['qty'] += 1
                else:
                    consolidated[item] = {
                        'rarity': drop.get('rarity', 'Common'),
                        'plat': drop.get('plat', 0),
                        'ducats': drop.get('ducats', 0),
                        'qty': 1
                    }
            
            for i, (item_name, data) in enumerate(consolidated.items()):
                self._create_drop_row(drops_scroll, item_name, data, i)
        else:
            empty = ctk.CTkLabel(
                drops_scroll,
                text="No drops recorded",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            )
            empty.grid(row=0, column=0, pady=30)
        
        # Totals
        totals = ctk.CTkFrame(self.details_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        totals.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        total_drops = len(rewards)
        total_plat = run.get('total_plat', 0)
        total_ducats = run.get('total_ducats', 0)
        
        ctk.CTkLabel(
            totals,
            text=f"{total_drops} drops  •  {total_plat}p  •  {total_ducats} ducats",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.COLORS['text']
        ).pack(pady=10)
    
    def _create_drop_row(self, parent, item_name, data, index):
        """Create a drop row for run details."""
        row = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_card'], corner_radius=6)
        row.grid(row=index, column=0, sticky="ew", pady=2)
        row.grid_columnconfigure(0, weight=1)
        
        rarity_colors = {
            'Common': '#cd7f32',
            'Uncommon': '#c0c0c0',
            'Rare': '#ffd700',
            'Forma Blueprint': '#60a5fa'
        }
        color = rarity_colors.get(data['rarity'], self.COLORS['text'])
        
        qty_text = f" x{data['qty']}" if data['qty'] > 1 else ""
        name_lbl = ctk.CTkLabel(
            row,
            text=f"● {item_name}{qty_text}",
            font=ctk.CTkFont(size=11, weight="bold" if data['qty'] > 1 else "normal"),
            text_color=color
        )
        name_lbl.grid(row=0, column=0, padx=10, pady=6, sticky="w")
        
        total_plat = data['plat'] * data['qty']
        total_ducats = data['ducats'] * data['qty']
        vals = ctk.CTkLabel(
            row,
            text=f"{total_plat}p  •  {total_ducats}d",
            font=ctk.CTkFont(size=10),
            text_color=self.COLORS['text_secondary']
        )
        vals.grid(row=0, column=1, padx=10, pady=6, sticky="e")
    
    def _delete_run(self, run):
        """Delete a cascade run."""
        from tkinter import messagebox
        if not messagebox.askyesno("Delete Run", f"Delete '{run.get('title', 'this run')}'?"):
            return
        
        try:
            run_id = run.get('id')
            if run_id:
                self.db.delete_run(run_id)
                self.selected_run = None
                self._refresh_runs_list()
                self._show_empty_run_details()
        except Exception as e:
            print(f"Error deleting run: {e}")
