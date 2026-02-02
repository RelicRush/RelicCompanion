"""
Prices Tab for the Warframe Relic Companion.
"""

import customtkinter as ctk
from tkinter import ttk
import threading
import time
from api import PriceData, WFCDRelicDatabase, WarframeMarketAPI, convert_to_url_name


class PricesTab:
    """Price check tab functionality with database price sync."""
    
    def __init__(self, app):
        self.app = app
        self.COLORS = app.COLORS
        self.price_entry = None
        self.price_results = None
        self.prices_tree = None
        self.sync_status = None
        self.sync_progress = None
        self.wfcd_db = WFCDRelicDatabase()
        self._syncing = False
    
    def create_frame(self, parent):
        """Create the price check frame."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(header_frame, text="Price Updater 69",
                            font=ctk.CTkFont(size=28, weight="bold"),
                            text_color=self.COLORS['text'])
        title.grid(row=0, column=0, sticky="w")
        
        subtitle = ctk.CTkLabel(header_frame, text="Fetch Prices For Rare Items from WFM",
                               font=ctk.CTkFont(size=13),
                               text_color=self.COLORS['text_muted'])
        subtitle.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        # Sync controls
        sync_frame = ctk.CTkFrame(frame, fg_color=self.COLORS['bg_card'], corner_radius=12)
        sync_frame.grid(row=1, column=0, sticky="ew", pady=(10, 15))
        sync_frame.grid_columnconfigure(1, weight=1)
        
        # Sync buttons
        btn_frame = ctk.CTkFrame(sync_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=0, padx=15, pady=15)
        
        sync_relics_btn = ctk.CTkButton(
            btn_frame,
            text="⟳ Sync Relics",
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS['bg_secondary'],
            hover_color=self.COLORS['bg_hover'],
            height=35,
            width=120,
            corner_radius=8,
            command=self.sync_wfcd_relics
        )
        sync_relics_btn.pack(side="left", padx=(0, 10))
        
        sync_prices_btn = ctk.CTkButton(
            btn_frame,
            text="💰 Sync All Prices",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['accent_hover'],
            height=35,
            width=140,
            corner_radius=8,
            command=self.sync_all_prices
        )
        sync_prices_btn.pack(side="left")
        
        # Status and progress
        status_frame = ctk.CTkFrame(sync_frame, fg_color="transparent")
        status_frame.grid(row=0, column=1, padx=15, pady=15, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.sync_status = ctk.CTkLabel(
            status_frame,
            text="Ready to sync",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_secondary']
        )
        self.sync_status.grid(row=0, column=0, sticky="w")
        
        self.sync_progress = ctk.CTkProgressBar(
            status_frame,
            height=8,
            corner_radius=4,
            fg_color=self.COLORS['bg_secondary'],
            progress_color=self.COLORS['accent']
        )
        self.sync_progress.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.sync_progress.set(0)
        
        # Stats display
        self.stats_label = ctk.CTkLabel(
            sync_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_muted']
        )
        self.stats_label.grid(row=0, column=2, padx=15)
        self.update_stats_display()
        
        # Search bar for filtering
        search_frame = ctk.CTkFrame(frame, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.filter_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Filter items...",
            font=ctk.CTkFont(size=13),
            height=38,
            corner_radius=8,
            fg_color=self.COLORS['bg_card'],
            border_color=self.COLORS['border']
        )
        self.filter_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.filter_entry.bind("<KeyRelease>", self.filter_prices)
        
        # Sort dropdown
        self.sort_var = ctk.StringVar(value="Price (High)")
        sort_combo = ctk.CTkComboBox(
            search_frame,
            values=["Price (High)", "Price (Low)", "Name (A-Z)", "Name (Z-A)"],
            variable=self.sort_var,
            width=130,
            height=38,
            fg_color=self.COLORS['bg_card'],
            command=self.refresh_prices_table
        )
        sort_combo.grid(row=0, column=1)
        
        # Prices table
        table_frame = ctk.CTkFrame(frame, fg_color=self.COLORS['bg_secondary'], corner_radius=12)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        # Style the treeview
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure alternating row colors
        self.prices_tree_odd_color = "#2a2a35"
        self.prices_tree_even_color = "#232329"
        
        style.configure("Prices.Treeview",
                       background=self.prices_tree_even_color,
                       foreground=self.COLORS['text'],
                       fieldbackground=self.prices_tree_even_color,
                       borderwidth=0,
                       font=('Segoe UI', 12),
                       rowheight=42)
        style.configure("Prices.Treeview.Heading",
                       background="#1e1e24",
                       foreground=self.COLORS['text_secondary'],
                       font=('Segoe UI', 11, 'bold'),
                       borderwidth=0,
                       relief='flat',
                       padding=(10, 8))
        style.map("Prices.Treeview",
                 background=[('selected', self.COLORS['accent'])],
                 foreground=[('selected', '#ffffff')])
        
        # Create treeview
        columns = ("item", "price", "avg", "relics")
        self.prices_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Prices.Treeview",
            selectmode="browse"
        )
        
        self.prices_tree.heading("item", text="Item Name")
        self.prices_tree.heading("price", text="Lowest ₽")
        self.prices_tree.heading("avg", text="Avg ₽")
        self.prices_tree.heading("relics", text="Source Relics")
        
        self.prices_tree.column("item", width=280, minwidth=200)
        self.prices_tree.column("price", width=90, minwidth=70, anchor="center")
        self.prices_tree.column("avg", width=90, minwidth=70, anchor="center")
        self.prices_tree.column("relics", width=350, minwidth=200)
        
        # Configure tag for alternating rows
        self.prices_tree.tag_configure('oddrow', background=self.prices_tree_odd_color)
        self.prices_tree.tag_configure('evenrow', background=self.prices_tree_even_color)
        
        # Bind click event to copy relics
        self.prices_tree.bind('<Double-1>', self.on_row_double_click)
        self.prices_tree.bind('<Button-3>', self.on_row_right_click)  # Right-click
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.prices_tree.yview)
        self.prices_tree.configure(yscrollcommand=scrollbar.set)
        
        self.prices_tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=10, padx=(0, 5))
        
        # Load initial data
        self.refresh_prices_table()
        
        return frame
    
    def update_stats_display(self):
        """Update the stats label."""
        try:
            stats = self.wfcd_db.get_price_stats()
            relic_stats = self.wfcd_db.get_stats()
            
            priced = stats.get('priced_items', 0)
            total = stats.get('total_unique_items', 0)
            relics = relic_stats.get('total_relics', 0)
            
            if total > 0:
                text = f"📊 {priced}/{total} items priced  •  📦 {relics} relics"
            else:
                text = "No data - sync relics first"
            
            self.stats_label.configure(text=text)
        except Exception as e:
            self.stats_label.configure(text="")
    
    def sync_wfcd_relics(self):
        """Sync relics from WFCD database."""
        if self._syncing:
            return
        
        self._syncing = True
        self.sync_status.configure(text="Syncing relics from WFCD...")
        self.sync_progress.set(0.2)
        
        def do_sync():
            try:
                def progress(msg):
                    self.app.after(0, lambda: self.sync_status.configure(text=msg))
                
                stats = self.wfcd_db.sync_from_wfcd(progress_callback=progress)
                
                self.app.after(0, lambda: self.sync_progress.set(1.0))
                self.app.after(0, lambda: self.sync_status.configure(
                    text=f"✓ Synced {stats['total_relics']} relics, {stats['total_rare_items']} rare items"
                ))
                self.app.after(0, self.update_stats_display)
                self.app.after(0, self.refresh_prices_table)
            except Exception as e:
                self.app.after(0, lambda: self.sync_status.configure(text=f"Error: {str(e)[:50]}"))
            finally:
                self._syncing = False
        
        threading.Thread(target=do_sync, daemon=True).start()
    
    def sync_all_prices(self):
        """Sync prices for all rare items from warframe.market."""
        if self._syncing:
            return
        
        self._syncing = True
        
        def format_time(seconds):
            """Format seconds into human readable time."""
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                mins = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{mins}m {secs}s"
            else:
                hours = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                return f"{hours}h {mins}m"
        
        def do_sync():
            try:
                # Get unique rare items
                items = self.wfcd_db.get_unique_rare_items()
                
                if not items:
                    self.app.after(0, lambda: self.sync_status.configure(
                        text="No items found - sync relics first!"
                    ))
                    self._syncing = False
                    return
                
                total = len(items)
                success = 0
                failed = 0
                market_api = WarframeMarketAPI()
                
                # Estimate time (0.5s per item)
                est_seconds = total * 0.5
                self.app.after(0, lambda: self.sync_status.configure(
                    text=f"Fetching {total} items... ~{format_time(est_seconds)} remaining"
                ))
                
                import time as time_module
                start_time = time_module.time()
                
                for i, item_name in enumerate(items):
                    if not self._syncing:  # Allow cancellation
                        break
                    
                    try:
                        # Update progress with time estimate
                        progress = (i + 1) / total
                        remaining = total - (i + 1)
                        
                        # Calculate ETA based on actual elapsed time
                        elapsed = time_module.time() - start_time
                        if i > 0:
                            avg_per_item = elapsed / (i + 1)
                            eta_seconds = remaining * avg_per_item
                        else:
                            eta_seconds = remaining * 0.5
                        
                        eta_str = format_time(eta_seconds) if remaining > 0 else ""
                        
                        self.app.after(0, lambda p=progress: self.sync_progress.set(p))
                        self.app.after(0, lambda n=item_name, c=i+1, t=total, eta=eta_str: 
                            self.sync_status.configure(text=f"[{c}/{t}] {n[:30]}... ~{eta} left" if eta else f"[{c}/{t}] {n[:40]}..."))
                        
                        # Fetch price from market
                        url_name = convert_to_url_name(item_name)
                        price_data = market_api.get_price_data(item_name)
                        
                        if price_data and price_data.lowest_price is not None:
                            # Save to database
                            self.wfcd_db.save_item_price(
                                item_name=item_name,
                                url_name=url_name,
                                lowest_price=price_data.lowest_price,
                                avg_price=price_data.avg_price,
                                volume=price_data.volume
                            )
                            success += 1
                        else:
                            failed += 1
                        
                        # Rate limiting - v2 API allows 3/sec, but we use 0.5s for safety
                        time.sleep(0.5)
                        
                    except Exception as e:
                        failed += 1
                        print(f"Failed to get price for {item_name}: {e}")
                        # Extra delay on error to back off
                        time.sleep(1.0)
                    
                    # Refresh table every 10 items
                    if (i + 1) % 10 == 0:
                        self.app.after(0, self.refresh_prices_table)
                
                self.app.after(0, lambda: self.sync_progress.set(1.0))
                self.app.after(0, lambda: self.sync_status.configure(
                    text=f"✓ Complete! {success} priced, {failed} failed"
                ))
                self.app.after(0, self.update_stats_display)
                self.app.after(0, self.refresh_prices_table)
                
            except Exception as e:
                self.app.after(0, lambda: self.sync_status.configure(
                    text=f"Error: {str(e)[:50]}"
                ))
            finally:
                self._syncing = False
        
        threading.Thread(target=do_sync, daemon=True).start()
    
    def refresh_prices_table(self, *args):
        """Refresh the prices table from database."""
        if not self.prices_tree:
            return
        
        # Clear existing items
        for item in self.prices_tree.get_children():
            self.prices_tree.delete(item)
        
        try:
            # Get prices with relic info
            prices = self.wfcd_db.get_prices_for_rare_items()
            
            # Filter
            filter_text = self.filter_entry.get().lower() if self.filter_entry else ""
            if filter_text:
                prices = [p for p in prices if filter_text in p['item_name'].lower()]
            
            # Sort
            sort_by = self.sort_var.get() if hasattr(self, 'sort_var') else "Price (High)"
            
            if sort_by == "Price (High)":
                prices.sort(key=lambda x: x['lowest_price'] or 0, reverse=True)
            elif sort_by == "Price (Low)":
                prices.sort(key=lambda x: x['lowest_price'] or 999999)
            elif sort_by == "Name (A-Z)":
                prices.sort(key=lambda x: x['item_name'])
            elif sort_by == "Name (Z-A)":
                prices.sort(key=lambda x: x['item_name'], reverse=True)
            
            # Populate table with alternating row colors
            for idx, item in enumerate(prices):
                lowest = f"{item['lowest_price']}p" if item['lowest_price'] else "-"
                avg = f"{item['avg_price']:.1f}p" if item['avg_price'] else "-"
                relics = item['relics'] or ""
                
                # Apply alternating row tag
                row_tag = 'oddrow' if idx % 2 == 1 else 'evenrow'
                
                self.prices_tree.insert("", "end", values=(
                    item['item_name'],
                    lowest,
                    avg,
                    relics
                ), tags=(row_tag,))
                
        except Exception as e:
            print(f"Error refreshing prices: {e}")
    
    def filter_prices(self, event=None):
        """Filter prices table based on search."""
        self.refresh_prices_table()
    
    def on_row_double_click(self, event):
        """Handle double-click on a row - copy relics to clipboard."""
        self.copy_selected_relics()
    
    def on_row_right_click(self, event):
        """Handle right-click on a row - copy relics to clipboard."""
        # Select the row under cursor
        item = self.prices_tree.identify_row(event.y)
        if item:
            self.prices_tree.selection_set(item)
            self.copy_selected_relics()
    
    def copy_selected_relics(self):
        """Copy selected row's relics as Warframe chat links."""
        selection = self.prices_tree.selection()
        if not selection:
            return
        
        try:
            # Get the values from selected row
            values = self.prices_tree.item(selection[0], 'values')
            if len(values) < 4:
                return
            
            item_name = values[0]
            relics_text = values[3]  # Source Relics column
            
            if not relics_text or relics_text == "-":
                self.show_copy_feedback("No relics to copy")
                return
            
            # Parse relics and format as Warframe chat links
            # Input: "Axi A11, Axi A6, Lith V2"
            # Output: "[Axi A11 Relic] [Axi A6 Relic] [Lith V2 Relic]"
            relic_list = [r.strip() for r in relics_text.split(',')]
            chat_links = ' '.join(f'[{relic} Relic]' for relic in relic_list)
            
            # Copy to clipboard
            self.app.clipboard_clear()
            self.app.clipboard_append(chat_links)
            self.app.update()  # Required for clipboard to persist
            
            # Show feedback
            self.show_copy_feedback(f"Copied {len(relic_list)} relic links!")
            
        except Exception as e:
            print(f"Error copying relics: {e}")
            self.show_copy_feedback("Error copying")
    
    def show_copy_feedback(self, message: str):
        """Show temporary feedback message in the status label."""
        original_text = self.sync_status.cget("text")
        self.sync_status.configure(text=f"📋 {message}")
        
        # Restore original text after 2 seconds
        self.app.after(2000, lambda: self.sync_status.configure(text=original_text))
