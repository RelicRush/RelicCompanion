"""
Void Relics Tab for The Relic Vault.
Displays relics with gold (rare) drops worth 20+ platinum.
Fetches relic prices from WFM in-game sellers for buying.
Uses ttk.Treeview for high-performance scrolling.
"""

import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
import threading
import webbrowser
from api import WFCDRelicDatabase, WarframeMarketAPI, convert_to_url_name


class VoidRelicsTab:
    """Void Relics tab - shows profitable relics to buy from WFM."""
    
    def __init__(self, app):
        self.app = app
        self.COLORS = app.COLORS
        self.wfcd_db = WFCDRelicDatabase()
        self.market_api = WarframeMarketAPI()
        self.relic_data = []  # List of dicts with relic + gold reward info
        self.sort_column = "profit"
        self.sort_reverse = True  # High to low by default
        self.min_gold_price = 20
        self._fetching = False
        self._cancel_fetch = False
        self._auto_fetch_active = False  # Track if auto-fetch loop is running
        self._auto_fetch_job = None      # Store the after() job ID for cancellation
        
        # UI references
        self.fetch_btn = None
        self.tree = None
        self.status_label = None
        self.count_label = None
        self.filter_var = None
        self.progress_bar = None
        self.tree_frame = None
        self.console_text = None
        self.console_frame = None
    
    def create_frame(self, parent):
        """Create the void relics frame."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=3)  # Treeview gets more space
        frame.grid_rowconfigure(3, weight=1)  # Console gets less space
        
        # Header
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)
        
        title = ctk.CTkLabel(header_frame, text="Profit Relics",
                            font=ctk.CTkFont(size=28, weight="bold"),
                            text_color=self.COLORS['text'])
        title.grid(row=0, column=0, sticky="w")
        
        subtitle = ctk.CTkLabel(header_frame, text="Find relics with valuable gold drops to buy from WFM",
                               font=ctk.CTkFont(size=13),
                               text_color=self.COLORS['text_muted'])
        subtitle.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        # Controls bar
        controls = ctk.CTkFrame(frame, fg_color=self.COLORS['bg_card'], corner_radius=12)
        controls.grid(row=1, column=0, sticky="ew", pady=(10, 15))
        controls.grid_columnconfigure(2, weight=1)
        
        # Fetch button (toggles auto-fetch on/off)
        self.fetch_btn = ctk.CTkButton(
            controls,
            text="▶ Start Fetch",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.COLORS['success'],
            hover_color='#16a34a',
            height=38,
            width=120,
            corner_radius=8,
            command=self._toggle_auto_fetch
        )
        self.fetch_btn.grid(row=0, column=0, padx=(15, 10), pady=15)
        
        # Era filter dropdown
        filter_frame = ctk.CTkFrame(controls, fg_color="transparent")
        filter_frame.grid(row=0, column=1, padx=10, pady=15)
        
        ctk.CTkLabel(
            filter_frame,
            text="Era:",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_secondary']
        ).pack(side="left", padx=(0, 8))
        
        self.filter_var = ctk.StringVar(value="All")
        era_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.filter_var,
            values=["All", "Lith", "Meso", "Neo", "Axi"],
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS['bg_secondary'],
            button_color=self.COLORS['bg_hover'],
            button_hover_color=self.COLORS['accent'],
            dropdown_fg_color=self.COLORS['bg_card'],
            width=100,
            height=32,
            command=self._apply_filter
        )
        era_dropdown.pack(side="left")
        
        # Status and progress
        status_frame = ctk.CTkFrame(controls, fg_color="transparent")
        status_frame.grid(row=0, column=2, padx=15, pady=15, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_secondary']
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(
            status_frame,
            height=6,
            corner_radius=3,
            fg_color=self.COLORS['bg_secondary'],
            progress_color=self.COLORS['gold']
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()  # Hidden initially
        
        # Count label
        self.count_label = ctk.CTkLabel(
            controls,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.COLORS['success']
        )
        self.count_label.grid(row=0, column=3, padx=15)
        
        # Treeview container with dark theme (matching Prices tab)
        self.tree_frame = ctk.CTkFrame(frame, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        self.tree_frame.grid(row=2, column=0, sticky="nsew")
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)
        
        # Configure dark theme for treeview
        self._setup_treeview_style()
        
        # Create treeview
        self._create_treeview()
        
        # Console log area (below treeview)
        self.console_frame = ctk.CTkFrame(frame, fg_color=self.COLORS['bg_card'], corner_radius=12, height=120)
        self.console_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)
        
        # Console header
        console_header = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        console_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        
        ctk.CTkLabel(
            console_header,
            text="📝 Fetch Log",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.COLORS['text_secondary']
        ).pack(side="left")
        
        # Clear button
        clear_btn = ctk.CTkButton(
            console_header,
            text="Clear",
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            hover_color=self.COLORS['bg_hover'],
            text_color=self.COLORS['text_muted'],
            width=50,
            height=20,
            corner_radius=4,
            command=self._clear_console
        )
        clear_btn.pack(side="right")
        
        # Console text area
        self.console_text = ctk.CTkTextbox(
            self.console_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=self.COLORS['bg_secondary'],
            text_color=self.COLORS['text_secondary'],
            corner_radius=8,
            height=80,
            wrap="word"
        )
        self.console_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.console_text.configure(state="disabled")  # Read-only
        
        # Load data on creation
        self._load_data()
        
        return frame
    
    def _setup_treeview_style(self):
        """Configure dark theme style for treeview to match Prices tab."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure alternating row colors (matching Prices tab)
        self.tree_odd_color = "#2a2a35"
        self.tree_even_color = "#232329"
        
        style.configure(
            "Relics.Treeview",
            background=self.tree_even_color,
            foreground=self.COLORS['text'],
            fieldbackground=self.tree_even_color,
            borderwidth=0,
            font=('Segoe UI', 12),
            rowheight=42
        )
        
        style.configure(
            "Relics.Treeview.Heading",
            background="#1e1e24",
            foreground=self.COLORS['text_secondary'],
            font=('Segoe UI', 11, 'bold'),
            borderwidth=0,
            relief='flat',
            padding=(10, 8)
        )
        
        style.map(
            "Relics.Treeview",
            background=[('selected', self.COLORS['accent'])],
            foreground=[('selected', '#ffffff')]
        )
    
    def _create_treeview(self, price_mode: bool = False):
        """Create or recreate the treeview with appropriate columns."""
        # Clear existing treeview if any
        for widget in self.tree_frame.winfo_children():
            widget.destroy()
        
        # Always use the same columns layout
        columns = ("relic", "reward", "gold_price", "relic_price", "top_seller", "stock")
        headings = {
            "relic": "Relic", 
            "reward": "Gold Reward",
            "gold_price": "Reward Value",
            "relic_price": "Buy Price",
            "top_seller": "Top Seller",
            "stock": "Stock"
        }
        widths = {
            "relic": 100,
            "reward": 280,
            "gold_price": 100,
            "relic_price": 100,
            "top_seller": 140,
            "stock": 70
        }
        
        # Create treeview with scrollbar - use bg_secondary to match Prices tab
        tree_container = tk.Frame(self.tree_frame, bg="#232329")
        tree_container.pack(fill="both", expand=True, padx=10, pady=10)
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical")
        scrollbar.grid(row=0, column=1, sticky="ns", pady=0, padx=(0, 5))
        
        # Treeview
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            style="Relics.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="browse"
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(0, 0))
        scrollbar.config(command=self.tree.yview)
        
        # Configure columns and headings
        for col in columns:
            self.tree.heading(
                col, 
                text=headings[col],
                command=lambda c=col: self._sort_by(c)
            )
            anchor = "w" if col == "reward" else "center"
            self.tree.column(col, width=widths[col], anchor=anchor, minwidth=50)
        
        # Make reward column stretch
        self.tree.column("reward", stretch=True)
        
        # Configure tag colors for alternating rows (matching Prices tab)
        self.tree.tag_configure('oddrow', background=self.tree_odd_color)
        self.tree.tag_configure('evenrow', background=self.tree_even_color)
        
        # Bind click event for opening WFM links
        self.tree.bind('<ButtonRelease-1>', self._on_tree_click)
        
        # Era color tags
        self.tree.tag_configure('lith', foreground='#8b7355')
        self.tree.tag_configure('meso', foreground='#c0c0c0')
        self.tree.tag_configure('neo', foreground='#ffd700')
        self.tree.tag_configure('axi', foreground='#87ceeb')
        
        # Profit color tags
        self.tree.tag_configure('profit_good', foreground='#22c55e')
        self.tree.tag_configure('profit_bad', foreground='#ef4444')
    
    def _on_tree_click(self, event):
        """Handle click on treeview to open WFM links."""
        # Get clicked region and column
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        
        if not item:
            return
        
        # Get column index (column is like "#1", "#2", etc.)
        col_idx = int(column.replace("#", "")) - 1
        
        # Column layout is always the same
        columns = ("relic", "reward", "gold_price", "relic_price", "top_seller", "stock")
        
        if col_idx >= len(columns):
            return
        
        col_name = columns[col_idx]
        values = self.tree.item(item, 'values')
        
        # Handle clicks based on column
        if col_name == "relic":
            # Open relic page on WFM
            relic_name = values[col_idx]  # e.g., "Neo N11"
            url_name = convert_to_url_name(relic_name + " Relic")
            url = f"https://warframe.market/items/{url_name}"
            webbrowser.open(url)
        
        elif col_name == "reward":
            # Open reward item page on WFM
            reward_name = values[col_idx]  # e.g., "Trinity Prime Systems Blueprint"
            url_name = convert_to_url_name(reward_name)
            url = f"https://warframe.market/items/{url_name}"
            webbrowser.open(url)
        
        elif col_name == "top_seller":
            # Open seller's profile on WFM
            seller_name = values[col_idx]
            if seller_name and seller_name != "—":
                url = f"https://warframe.market/profile/{seller_name}"
                webbrowser.open(url)
    
    def _toggle_auto_fetch(self):
        """Toggle auto-fetch on/off."""
        if self._auto_fetch_active:
            # Turn OFF
            self._stop_auto_fetch()
        else:
            # Turn ON
            self._start_auto_fetch()
    
    def _start_auto_fetch(self):
        """Start the auto-fetch loop."""
        self._auto_fetch_active = True
        self._cancel_fetch = False
        
        # Update button to red "Stop" state
        self.fetch_btn.configure(
            text="■ Stop Fetch",
            fg_color=self.COLORS['error'],
            hover_color='#dc2626'
        )
        
        # Switch to price view columns
        self._create_treeview(price_mode=True)
        
        # Log start
        self._log_console("\n🔄 Auto-fetch started...")
        
        # Start fetching
        self._run_fetch_cycle()
    
    def _stop_auto_fetch(self):
        """Stop the auto-fetch loop."""
        self._auto_fetch_active = False
        self._cancel_fetch = True
        
        # Cancel any pending timer
        if self._auto_fetch_job:
            self.app.after_cancel(self._auto_fetch_job)
            self._auto_fetch_job = None
        
        # Update button back to green "Start" state
        self.fetch_btn.configure(
            text="▶ Start Fetch",
            fg_color=self.COLORS['success'],
            hover_color='#16a34a'
        )
        
        # Hide progress
        self.progress_bar.grid_remove()
        
        # Log stop
        self._log_console("■ Auto-fetch stopped.")
        self.status_label.configure(text="Fetch stopped")
    
    def _run_fetch_cycle(self):
        """Run one fetch cycle, then schedule next after 30 seconds."""
        if not self._auto_fetch_active:
            return
        
        # Reset prices for fresh fetch
        for relic in self.relic_data:
            relic['relic_price'] = None
            relic['top_seller'] = None
            relic['stock'] = 0
        
        self._fetching = True
        self._cancel_fetch = False
        self.status_label.configure(text="Fetching relic prices from WFM...")
        self.progress_bar.grid()
        self.progress_bar.set(0)
        
        # Show all relics immediately with placeholders
        self._refresh_display()
        
        # Start background fetch thread
        thread = threading.Thread(target=self._do_fetch_cycle, daemon=True)
        thread.start()
    
    def _load_data(self):
        """Load relic data from database."""
        self.status_label.configure(text="Loading relics...")
        
        # Get all rare items and their prices from database
        rare_items = self.wfcd_db.get_all_rare_items()
        
        # Build relic data with gold reward prices
        self.relic_data = []
        seen = set()  # Track unique relic+reward combos
        
        for item in rare_items:
            key = f"{item.relic_full}|{item.item_name}"
            if key in seen:
                continue
            seen.add(key)
            
            # Get price of gold reward from database
            price_data = self.wfcd_db.get_item_price(item.item_name)
            gold_price = price_data['lowest_price'] if price_data and price_data.get('lowest_price') else 0
            
            # Only include if gold reward price >= min threshold
            if gold_price >= self.min_gold_price:
                self.relic_data.append({
                    'era': item.relic_era,
                    'relic': item.relic_name,
                    'full_name': item.relic_full,
                    'reward': item.item_name,
                    'gold_price': gold_price,
                    'vaulted': item.is_vaulted,
                    'relic_price': None,  # To be fetched
                    'top_seller': None,   # Username of seller with most stock
                    'stock': 0,           # Stock amount of top seller
                })
        
        # Sort by gold price descending by default
        self.relic_data.sort(key=lambda x: x['gold_price'], reverse=True)
        
        # Update UI
        self._refresh_display()
        
        count = len(self.relic_data)
        self.count_label.configure(text=f"🥇 {count} relics")
        self.status_label.configure(text=f"Found {count} relics with {self.min_gold_price}+ plat gold rewards")
    
    def _do_fetch_cycle(self):
        """Background thread to fetch relic prices (for auto-fetch loop)."""
        import time
        start_time = time.time()
        
        try:
            total = len(self.relic_data)
            
            for i, relic in enumerate(self.relic_data):
                # Check for cancellation
                if self._cancel_fetch:
                    priced = sum(1 for r in self.relic_data if r['relic_price'] is not None)
                    self._update_progress(f"Cancelled. {priced} relics fetched.", (i + 1) / total)
                    break
                
                try:
                    # Build relic URL name: "lith_a1_relic"
                    url_name = f"{relic['era'].lower()}_{relic['relic'].lower()}_relic"
                    relic_name = f"{relic['era']} {relic['relic']}"
                    
                    # Fetch orders
                    listings = self.market_api.get_item_orders(url_name)
                    
                    # Filter for in-game sellers only (best prices, immediately available)
                    ingame_sellers = [
                        l for l in listings
                        if l.status == "ingame"
                    ]
                    
                    if ingame_sellers:
                        # Get lowest price from in-game sellers
                        min_price = min(l.price for l in ingame_sellers)
                        relic['relic_price'] = min_price
                        
                        # Find seller with most stock
                        top_seller = max(ingame_sellers, key=lambda l: l.quantity)
                        relic['top_seller'] = top_seller.seller
                        relic['stock'] = top_seller.quantity
                        
                        # Log to console
                        self._log_console(f"✓ {relic_name}: {min_price}p • {top_seller.seller} ({top_seller.quantity} stock)")
                    else:
                        relic['relic_price'] = None
                        relic['top_seller'] = None
                        relic['stock'] = 0
                        self._log_console(f"— {relic_name}: No in-game sellers")
                    
                    # Update this specific row in real-time
                    self.app.after(0, lambda idx=i, r=relic: self._update_row(idx, r))
                    
                    # Calculate ETA
                    elapsed = time.time() - start_time
                    avg_per_item = elapsed / (i + 1) if i > 0 else 0.4
                    remaining = total - (i + 1)
                    eta_seconds = int(remaining * avg_per_item)
                    
                    # Format as minutes and seconds
                    if eta_seconds > 0:
                        mins, secs = divmod(eta_seconds, 60)
                        if mins > 0:
                            eta_str = f"~{mins}m {secs}s left"
                        else:
                            eta_str = f"~{secs}s left"
                    else:
                        eta_str = ""
                    
                    # Update progress with ETA
                    progress = (i + 1) / total
                    self._update_progress(f"{relic['era']} {relic['relic']} ({i+1}/{total}) {eta_str}", progress)
                    
                except Exception as e:
                    print(f"Error fetching {relic['full_name']}: {e}")
                    continue
            
            # Count how many have prices
            priced = sum(1 for r in self.relic_data if r['relic_price'] is not None)
            if not self._cancel_fetch:
                self._update_progress(f"Done! {priced} relics with in-game sellers", 1.0)
                self._log_console(f"✓ Cycle complete: {priced} relics fetched")
            
            # Final sort by stock (highest first) and refresh
            self.relic_data.sort(
                key=lambda x: x['stock'] if x['stock'] else 0,
                reverse=True
            )
            self.app.after(0, self._refresh_display)
            self.app.after(500, self._on_fetch_cycle_complete)
            
        except Exception as e:
            self._update_progress(f"Error: {e}", 0)
            self._log_console(f"✗ Error: {e}")
        finally:
            self._fetching = False
    
    def _on_fetch_cycle_complete(self):
        """Called when a fetch cycle completes. Schedules next cycle if still active."""
        self.progress_bar.grid_remove()
        
        if self._auto_fetch_active and not self._cancel_fetch:
            # Schedule next cycle in 30 seconds
            self._log_console("⏳ Next fetch in 30 seconds...")
            self.status_label.configure(text="Waiting 30s until next fetch...")
            self._auto_fetch_job = self.app.after(30000, self._run_fetch_cycle)
        elif self._cancel_fetch:
            self._log_console("■ Fetch cancelled.")
    
    def _hide_fetch_ui(self):
        """Hide the fetch progress UI elements."""
        self.progress_bar.grid_remove()
    
    def _update_row(self, index: int, relic: dict):
        """Update a single row in the treeview with new price data."""
        if not self.tree:
            return
        
        # Get all items and find the one to update
        children = self.tree.get_children()
        if index >= len(children):
            return
        
        item_id = children[index]
        
        # Build new values
        relic_price = f"{relic['relic_price']}p" if relic['relic_price'] else "—"
        top_seller = relic['top_seller'] if relic['top_seller'] else "—"
        stock_text = str(relic['stock']) if relic['stock'] > 0 else "—"
        relic_name = f"{relic['era']} {relic['relic']}"
        
        values = (
            relic_name,
            relic['reward'],
            f"{relic['gold_price']}p",
            relic_price,
            top_seller,
            stock_text
        )
        
        # Update the row values
        self.tree.item(item_id, values=values)
    
    def _update_progress(self, text: str, progress: float):
        """Update status and progress (thread-safe)."""
        self.app.after(0, lambda: self.status_label.configure(text=text))
        self.app.after(0, lambda: self.progress_bar.set(progress))
    
    def _log_console(self, message: str):
        """Log a message to the console (thread-safe)."""
        def do_log():
            if self.console_text:
                self.console_text.configure(state="normal")
                self.console_text.insert("end", message + "\n")
                self.console_text.see("end")  # Auto-scroll to bottom
                self.console_text.configure(state="disabled")
        self.app.after(0, do_log)
    
    def _clear_console(self):
        """Clear the console log."""
        if self.console_text:
            self.console_text.configure(state="normal")
            self.console_text.delete("1.0", "end")
            self.console_text.configure(state="disabled")
    
    def _apply_sort(self):
        """Apply current sort to data."""
        if self.sort_column == "era":
            era_order = {'Lith': 0, 'Meso': 1, 'Neo': 2, 'Axi': 3}
            self.relic_data.sort(
                key=lambda x: era_order.get(x['era'], 99),
                reverse=self.sort_reverse
            )
        elif self.sort_column == "relic":
            self.relic_data.sort(key=lambda x: x['relic'], reverse=self.sort_reverse)
        elif self.sort_column == "reward":
            self.relic_data.sort(key=lambda x: x['reward'], reverse=self.sort_reverse)
        elif self.sort_column == "gold_price":
            self.relic_data.sort(key=lambda x: x['gold_price'], reverse=self.sort_reverse)
        elif self.sort_column == "relic_price":
            self.relic_data.sort(
                key=lambda x: x['relic_price'] if x['relic_price'] is not None else 9999,
                reverse=self.sort_reverse
            )
        elif self.sort_column == "top_seller":
            self.relic_data.sort(
                key=lambda x: x['top_seller'].lower() if x['top_seller'] else "zzz",
                reverse=self.sort_reverse
            )
        elif self.sort_column == "stock":
            self.relic_data.sort(key=lambda x: x['stock'] if x['stock'] else 0, reverse=self.sort_reverse)
        elif self.sort_column == "vaulted":
            self.relic_data.sort(key=lambda x: x['vaulted'], reverse=self.sort_reverse)
    
    def _refresh_display(self):
        """Refresh the relics list display."""
        if not self.tree:
            return
            
        # Clear current items
        self.tree.delete(*self.tree.get_children())
        
        # Update column headings with sort indicator
        columns = list(self.tree["columns"])
        for col in columns:
            current_text = self.tree.heading(col, "text")
            base_text = current_text.rstrip(" ▼▲")
            if col == self.sort_column:
                new_text = base_text + (" ▼" if self.sort_reverse else " ▲")
            else:
                new_text = base_text
            self.tree.heading(col, text=new_text)
        
        # Filter data
        filter_era = self.filter_var.get()
        filtered = self.relic_data
        if filter_era != "All":
            filtered = [r for r in self.relic_data if r['era'] == filter_era]
        
        if not filtered:
            return
        
        # Insert all rows at once (much faster than individual inserts)
        for i, relic in enumerate(filtered):
            tags = []
            
            # Alternating row colors (must be first for proper background)
            tags.append('evenrow' if i % 2 == 0 else 'oddrow')
            
            # Always use price mode columns
            relic_price = f"{relic['relic_price']}p" if relic['relic_price'] else "—"
            top_seller = relic['top_seller'] if relic['top_seller'] else "—"
            stock_text = str(relic['stock']) if relic['stock'] > 0 else "—"
            relic_name = f"{relic['era']} {relic['relic']}"
            
            values = (
                relic_name,
                relic['reward'],
                f"{relic['gold_price']}p",
                relic_price,
                top_seller,
                stock_text
            )
            
            self.tree.insert("", "end", values=values, tags=tags)
    
    def _sort_by(self, column: str):
        """Sort relics by column."""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = True if column in ("gold_price", "relic_price", "stock") else False
        
        self._apply_sort()
        self._refresh_display()
    
    def _apply_filter(self, value):
        """Apply era filter."""
        self._refresh_display()
