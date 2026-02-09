"""
History Tab for The Relic Vault.
Shows Void Cascade run history.
"""

import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
from datetime import datetime
from database import RelicDatabase


class HistoryTab:
    """History tracker - view Void Cascade runs."""
    
    def __init__(self, app):
        self.app = app
        self.COLORS = app.COLORS
        self.db = RelicDatabase()
        self.runs_detail_tree = None
        self.selected_run = None
        self._drops_style_configured = False
    
    def create_frame(self, parent) -> ctk.CTkFrame:
        """Create the history tab frame."""
        frame = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_primary'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header
        self._create_header(frame)
        
        # Content area - Void Cascade runs
        self.content_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=2)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Left - Runs list
        self._create_runs_list()
        
        # Right - Run details
        self._create_run_details_panel()
        
        return frame
    
    def _setup_drops_treeview_style(self):
        """Setup treeview styling for run drops."""
        if self._drops_style_configured:
            return
        
        style = ttk.Style()
        
        # Configure the treeview (don't call theme_use - it resets other styles)
        style.configure(
            "RunDrops.Treeview",
            background=self.COLORS['bg_secondary'],
            foreground=self.COLORS['text'],
            fieldbackground=self.COLORS['bg_secondary'],
            borderwidth=0,
            relief="flat",
            rowheight=32,
            font=('Segoe UI', 10)
        )
        
        style.configure(
            "RunDrops.Treeview.Heading",
            background=self.COLORS['bg_card'],
            foreground=self.COLORS['text_secondary'],
            borderwidth=0,
            relief="flat",
            font=('Segoe UI', 10, 'bold')
        )
        
        style.map("RunDrops.Treeview",
            background=[('selected', self.COLORS['accent'])],
            foreground=[('selected', self.COLORS['text'])]
        )
        
        style.map("RunDrops.Treeview.Heading",
            background=[('active', self.COLORS['bg_hover'])]
        )
        
        style.layout("RunDrops.Treeview", [
            ('Treeview.treearea', {'sticky': 'nswe'})
        ])
        
        self._drops_style_configured = True

    def _create_header(self, parent):
        """Create the header."""
        header = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(1, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            header,
            text="⚡ Void Cascade History",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS['text']
        )
        title.grid(row=0, column=0, padx=20, pady=15, sticky="w")
    
    def _create_runs_list(self):
        """Create the cascade runs list."""
        panel = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkLabel(
            panel,
            text="📋 Runs",
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
        
        # Setup treeview style
        self._setup_drops_treeview_style()
        
        # Drops treeview container
        tree_container = ctk.CTkFrame(self.details_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        tree_container.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 10))
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)
        
        # Create treeview
        columns = ("item", "values")
        self.runs_detail_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            style="RunDrops.Treeview",
            selectmode="browse"
        )
        
        # Configure columns
        self.runs_detail_tree.heading("item", text="Item", anchor="w")
        self.runs_detail_tree.heading("values", text="Value", anchor="e")
        self.runs_detail_tree.column("item", width=300, minwidth=200, anchor="w")
        self.runs_detail_tree.column("values", width=100, minwidth=80, anchor="e")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.runs_detail_tree.yview)
        self.runs_detail_tree.configure(yscrollcommand=scrollbar.set)
        
        self.runs_detail_tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=10, padx=(0, 5))
        
        # Configure row tags for rarity colors
        self.runs_detail_tree.tag_configure('rare', foreground='#ffd700')
        self.runs_detail_tree.tag_configure('uncommon', foreground='#c0c0c0')
        self.runs_detail_tree.tag_configure('common', foreground='#cd7f32')
        self.runs_detail_tree.tag_configure('forma', foreground='#60a5fa')
        self.runs_detail_tree.tag_configure('evenrow', background=self.COLORS['bg_card'])
        self.runs_detail_tree.tag_configure('oddrow', background=self.COLORS['bg_secondary'])
        
        rewards = run.get('rewards', [])
        gold_count = 0
        silver_count = 0
        bronze_count = 0
        
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
            
            # Sort by rarity: Rare -> Uncommon -> Common -> Forma
            rarity_order = {'Rare': 0, 'Uncommon': 1, 'Common': 2, 'Forma Blueprint': 3}
            sorted_items = sorted(
                consolidated.items(),
                key=lambda x: (rarity_order.get(x[1]['rarity'], 2), x[0])
            )
            
            # Insert rows
            for i, (item_name, data) in enumerate(sorted_items):
                rarity = data['rarity']
                qty = data['qty']
                total_plat = data['plat'] * qty
                total_ducats = data['ducats'] * qty
                
                # Count by rarity
                if rarity == 'Rare':
                    gold_count += qty
                elif rarity == 'Uncommon':
                    silver_count += qty
                elif rarity == 'Common':
                    bronze_count += qty
                
                # Determine tag
                if rarity == 'Rare':
                    tag = 'rare'
                elif rarity == 'Uncommon':
                    tag = 'uncommon'
                elif rarity == 'Forma Blueprint' or 'Forma' in item_name:
                    tag = 'forma'
                else:
                    tag = 'common'
                
                row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                
                qty_text = f" x{qty}" if qty > 1 else ""
                item_text = f"● {item_name}{qty_text}"
                value_text = f"{total_plat}p • {total_ducats}d"
                
                self.runs_detail_tree.insert(
                    "", "end",
                    values=(item_text, value_text),
                    tags=(tag, row_tag)
                )
        
        # Totals with G/S/B counter
        totals = ctk.CTkFrame(self.details_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        totals.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        total_drops = len(rewards)
        total_plat = run.get('total_plat', 0)
        total_ducats = run.get('total_ducats', 0)
        
        # Build totals text with G/S/B
        gsb_parts = []
        if gold_count > 0:
            gsb_parts.append(f"🥇{gold_count}")
        if silver_count > 0:
            gsb_parts.append(f"🥈{silver_count}")
        if bronze_count > 0:
            gsb_parts.append(f"🥉{bronze_count}")
        gsb_text = " ".join(gsb_parts) + "  •  " if gsb_parts else ""
        
        ctk.CTkLabel(
            totals,
            text=f"{gsb_text}{total_drops} drops  •  {total_plat}p  •  {total_ducats} ducats",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.COLORS['text']
        ).pack(pady=10)
    
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
