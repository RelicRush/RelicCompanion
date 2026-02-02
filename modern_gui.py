"""
Warframe Relic Companion - Modern GUI Application
A sleek 2026 interface using CustomTkinter
"""

import customtkinter as ctk
import json
import os
import re
import threading
from PIL import Image

from models import (
    Relic, InventoryItem,
    RelicEra, RelicRefinement, DROP_CHANCES
)
from relic_data import get_sample_relics
from api import WarframeMarketAPI, PriceData
from api import AlecaFrameAPI, AlecaFrameProfile
from database import RelicDatabase, get_db_dir
from icon_manager import get_mastery_icon_path, get_platinum_icon_path, get_credits_icon_path, get_ducats_icon_path

# Import tab modules
from tabs import PricesTab, CalculatorTab, InventoryTab, VoidCascadeTab

# Set appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ModernRelicApp(ctk.CTk):
    """Modern GUI Application for the Warframe Relic Companion."""
    
    COLORS = {
        'bg_primary': '#0a0a0a',
        'bg_secondary': '#141414',
        'bg_card': '#1e1e1e',
        'bg_hover': '#2a2a2a',
        'accent': '#8b5cf6',
        'accent_hover': '#a78bfa',
        'accent_dim': '#7c3aed',
        'success': '#22c55e',
        'warning': '#f59e0b',
        'error': '#ef4444',
        'text': '#ffffff',
        'text_secondary': '#a1a1aa',
        'text_muted': '#71717a',
        'gold': '#fbbf24',
        'platinum': '#60a5fa',
        'border': '#2a2a2a',
    }
    
    # Fun custom titles for specific users (case-insensitive)
    CUSTOM_TITLES = {
        'itsveilor': ('👑 The Creator', '#ffd700'),
        'relichunter': ('🎯 Relic God', '#8b5cf6'),
        'barohunter': ('🪙 Ducat Daddy', '#fbbf24'),
        'formafarm': ('⚡ Forma Fiend', '#60a5fa'),
        'primepapi': ('💎 Prime Papi', '#22c55e'),
        # Add more custom titles here!
    }
    
    def __init__(self):
        super().__init__()
        
        # Settings file path (in DB folder)
        self.settings_file = os.path.join(get_db_dir(), "settings.json")
        
        # Window setup
        self.title("Relic Companion")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(fg_color=self.COLORS['bg_primary'])
        
        # Initialize database
        self.db = RelicDatabase()
        
        # Load data from database (or sample data if empty)
        self.relics = self.db.get_all_relics()
        if not self.relics:
            # First run - load sample data
            self.relics = get_sample_relics()
            self.db.save_relics_batch(self.relics)
        
        # Load inventory from database
        self.inventory: list[InventoryItem] = self.db.get_all_inventory()
        print(f"DEBUG: Loaded {len(self.inventory)} inventory items from database")
        
        # Load settings
        self.settings = self.load_settings()
        
        # Initialize API clients
        self.market_api = WarframeMarketAPI()
        self.alecaframe_api = AlecaFrameAPI(self.settings.get('alecaframe_token'))
        self.price_cache: dict[str, PriceData] = {}
        
        # Initialize tab handlers

        self.prices_tab = PricesTab(self)
        self.calculator_tab = CalculatorTab(self)
        self.inventory_tab = InventoryTab(self)
        self.cascade_tab = VoidCascadeTab(self)
        
        # Build UI
        self.create_layout()
        
        # Load saved profile on startup
        self.load_saved_profile()
        
        # Start auto-sync timer if enabled
        self.auto_sync_job = None
        self.start_auto_sync_timer()
        
    def load_saved_profile(self):
        """Load profile from database if available."""
        try:
            profile_data = self.db.get_profile()
            if profile_data and profile_data.get('username'):
                # Convert to AlecaFrameProfile object
                profile = AlecaFrameProfile(
                    username=profile_data['username'],
                    mastery_rank=profile_data['mastery_rank'],
                    mastery_percentage=profile_data['mastery_percentage'],
                    platinum=profile_data['platinum'],
                    credits=profile_data['credits'],
                    endo=profile_data['endo'],
                    ducats=profile_data['ducats'],
                    aya=profile_data.get('aya', 0),
                    relics_opened=profile_data.get('relics_opened', 0),
                    trades=profile_data.get('trades', 0)
                )
                self.update_profile_display(profile)
        except Exception as e:
            print(f"Error loading saved profile: {e}")
    
    def start_auto_sync_timer(self):
        """Start or restart the auto-sync timer based on settings."""
        # Cancel existing timer if any
        if self.auto_sync_job:
            self.after_cancel(self.auto_sync_job)
            self.auto_sync_job = None
        
        # Check if auto-sync is enabled
        if self.settings.get('auto_sync', False) and self.settings.get('alecaframe_token'):
            # Schedule sync every 2 minutes (120000 ms)
            self.auto_sync_job = self.after(120000, self.auto_sync_tick)
            print("Auto-sync enabled: will sync every 2 minutes")
    
    def auto_sync_tick(self):
        """Perform auto-sync and reschedule."""
        if self.settings.get('auto_sync', False):
            print("Auto-sync: syncing AlecaFrame...")
            self.sync_alecaframe()
            # Reschedule
            self.auto_sync_job = self.after(120000, self.auto_sync_tick)
        
    def load_settings(self):
        """Load application settings."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_settings(self):
        """Save application settings."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    def save_inventory(self):
        """Save inventory to database."""
        try:
            self.db.save_inventory_batch(self.inventory)
        except Exception as e:
            print(f"Error saving inventory: {e}")
    
    def create_layout(self):
        """Create the main application layout."""
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.create_sidebar()
        
        # Main content area
        self.main_frame = ctk.CTkFrame(self, fg_color=self.COLORS['bg_primary'], corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Content frames for each section
        self.frames = {}
        self.create_content_frames()
        
        # Show inventory by default
        self.show_frame("inventory")
    
    def create_sidebar(self):
        """Create the modern sidebar navigation."""
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, 
                              fg_color=self.COLORS['bg_secondary'])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(10, weight=1)  # Push bottom items down
        
        # Logo/Title section (row 0)
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(25, 15), sticky="ew")
        
        # Accent bar
        accent = ctk.CTkFrame(logo_frame, width=4, height=32, 
                             fg_color=self.COLORS['accent'], corner_radius=2)
        accent.pack(side="left", padx=(0, 12))
        
        title_label = ctk.CTkLabel(logo_frame, text="RELIC", 
                                  font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                                  text_color=self.COLORS['text'])
        title_label.pack(side="left")
        
        title_label2 = ctk.CTkLabel(logo_frame, text="COMPANION", 
                                   font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                                   text_color=self.COLORS['accent'])
        title_label2.pack(side="left", padx=(6, 0))
        
        # Profile section at top (row 1) - shows after sync
        self.profile_frame = ctk.CTkFrame(sidebar, fg_color=self.COLORS['bg_card'], corner_radius=10)
        self.profile_frame.grid(row=1, column=0, padx=12, pady=(5, 15), sticky="ew")
        
        # Profile header with MR icon
        profile_header = ctk.CTkFrame(self.profile_frame, fg_color="transparent")
        profile_header.pack(fill="x", padx=12, pady=(12, 8))
        
        # MR badge - using CTkLabel with image support
        self.mr_image = None  # Will store CTkImage
        self.mr_image_label = ctk.CTkLabel(profile_header, text="", width=44, height=44)
        self.mr_image_label.pack(side="left")
        
        # Username and percentage
        name_frame = ctk.CTkFrame(profile_header, fg_color="transparent")
        name_frame.pack(side="left", padx=(10, 0), fill="x", expand=True)
        
        # Username row (name + title)
        username_row = ctk.CTkFrame(name_frame, fg_color="transparent")
        username_row.pack(anchor="w")
        
        self.username_label = ctk.CTkLabel(username_row, text="Not synced",
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           text_color=self.COLORS['text'])
        self.username_label.pack(side="left")
        
        # Custom title label (hidden by default)
        self.title_label = ctk.CTkLabel(username_row, text="",
                                        font=ctk.CTkFont(size=10),
                                        text_color=self.COLORS['gold'])
        self.title_label.pack(side="left", padx=(6, 0))
        self.title_label.pack_forget()  # Hide until we have a title
        
        # Stats row with icons
        stats_frame = ctk.CTkFrame(self.profile_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=8, pady=(0, 12))
        
        # Platinum, Credits, Ducats mini-stats
        self.stat_labels = {}
        self.plat_icon_image = None  # Store reference
        self.credits_icon_image = None
        self.ducats_icon_image = None
        
        # Platinum stat (with icon)
        plat_mini = ctk.CTkFrame(stats_frame, fg_color="transparent")
        plat_mini.pack(side="left", expand=True)
        
        # Try to load platinum icon
        plat_icon_path = get_platinum_icon_path(16)
        if plat_icon_path and os.path.exists(plat_icon_path):
            try:
                plat_pil = Image.open(plat_icon_path)
                self.plat_icon_image = ctk.CTkImage(light_image=plat_pil, dark_image=plat_pil, size=(16, 16))
                plat_icon_lbl = ctk.CTkLabel(plat_mini, text="", image=self.plat_icon_image, width=16)
                plat_icon_lbl.pack(side="left")
            except:
                pass
        
        plat_lbl = ctk.CTkLabel(plat_mini, text="0",
                               font=ctk.CTkFont(size=10),
                               text_color=self.COLORS['text_secondary'])
        plat_lbl.pack(side="left", padx=(2, 0))
        self.stat_labels['plat'] = plat_lbl
        
        # Credits stat (with icon)
        credits_mini = ctk.CTkFrame(stats_frame, fg_color="transparent")
        credits_mini.pack(side="left", expand=True)
        
        # Try to load credits icon
        credits_icon_path = get_credits_icon_path(16)
        if credits_icon_path and os.path.exists(credits_icon_path):
            try:
                credits_pil = Image.open(credits_icon_path)
                self.credits_icon_image = ctk.CTkImage(light_image=credits_pil, dark_image=credits_pil, size=(16, 16))
                credits_icon_lbl = ctk.CTkLabel(credits_mini, text="", image=self.credits_icon_image, width=16)
                credits_icon_lbl.pack(side="left")
            except:
                pass
        
        credits_lbl = ctk.CTkLabel(credits_mini, text="0",
                                   font=ctk.CTkFont(size=10),
                                   text_color=self.COLORS['text_secondary'])
        credits_lbl.pack(side="left", padx=(2, 0))
        self.stat_labels['credits'] = credits_lbl
        
        # Ducats stat (with icon)
        ducats_mini = ctk.CTkFrame(stats_frame, fg_color="transparent")
        ducats_mini.pack(side="left", expand=True)
        
        # Try to load ducats icon
        ducats_icon_path = get_ducats_icon_path(16)
        if ducats_icon_path and os.path.exists(ducats_icon_path):
            try:
                ducats_pil = Image.open(ducats_icon_path)
                self.ducats_icon_image = ctk.CTkImage(light_image=ducats_pil, dark_image=ducats_pil, size=(16, 16))
                ducats_icon_lbl = ctk.CTkLabel(ducats_mini, text="", image=self.ducats_icon_image, width=16)
                ducats_icon_lbl.pack(side="left")
            except:
                pass
        
        ducats_lbl = ctk.CTkLabel(ducats_mini, text="0",
                                  font=ctk.CTkFont(size=10),
                                  text_color=self.COLORS['text_secondary'])
        ducats_lbl.pack(side="left", padx=(2, 0))
        self.stat_labels['ducats'] = ducats_lbl
        
        # Hide profile section initially if not synced
        self.profile_frame.grid_remove()
        
        # Navigation buttons (rows 2-4)
        nav_items = [
            ("💰", "Prices", "prices"),
            ("📊", "Calculator", "calculator"),
            ("🎒", "Inventory", "inventory"),
            ("⚡", "Void Cascade", "cascade"),
        ]
        
        self.nav_buttons = {}
        for i, (icon, text, frame_name) in enumerate(nav_items):
            btn = ctk.CTkButton(
                sidebar,
                text=f"  {icon}   {text}",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="transparent",
                text_color=self.COLORS['text_secondary'],
                hover_color=self.COLORS['bg_hover'],
                anchor="w",
                height=42,
                corner_radius=8,
                command=lambda f=frame_name: self.show_frame(f)
            )
            btn.grid(row=i+2, column=0, padx=12, pady=2, sticky="ew")
            self.nav_buttons[frame_name] = btn
        
        # Bottom section - Settings and Sync
        bottom_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom_frame.grid(row=11, column=0, padx=12, pady=20, sticky="sew")
        
        # AlecaFrame sync button
        sync_btn = ctk.CTkButton(
            bottom_frame,
            text="⟳  Sync AlecaFrame",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=self.COLORS['bg_card'],
            hover_color=self.COLORS['bg_hover'],
            text_color=self.COLORS['text_secondary'],
            height=38,
            corner_radius=8,
            command=self.sync_alecaframe
        )
        sync_btn.pack(fill="x", pady=(0, 8))
        
        # Settings button
        settings_btn = ctk.CTkButton(
            bottom_frame,
            text="⚙  Settings",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="transparent",
            hover_color=self.COLORS['bg_hover'],
            text_color=self.COLORS['text_muted'],
            height=38,
            corner_radius=8,
            command=self.open_settings
        )
        settings_btn.pack(fill="x")
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            bottom_frame,
            text="● Online",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLORS['success']
        )
        self.status_label.pack(pady=(15, 0))
        
        # Last sync timestamp
        self.last_sync_label = ctk.CTkLabel(
            bottom_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLORS['text_muted']
        )
        self.last_sync_label.pack(pady=(2, 0))
        
        # Load last sync time from database
        self._update_last_sync_display()
    
    def show_frame(self, frame_name):
        """Switch to a different content frame."""
        # Update nav button states
        for name, btn in self.nav_buttons.items():
            if name == frame_name:
                btn.configure(fg_color=self.COLORS['accent'], 
                            text_color=self.COLORS['text'])
            else:
                btn.configure(fg_color="transparent", 
                            text_color=self.COLORS['text_secondary'])
        
        # Show the selected frame
        for name, frame in self.frames.items():
            if name == frame_name:
                frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
            else:
                frame.grid_forget()
    
    def create_content_frames(self):
        """Create all content frames."""
        self.frames["prices"] = self.prices_tab.create_frame(self.main_frame)
        self.frames["calculator"] = self.calculator_tab.create_frame(self.main_frame)
        self.frames["inventory"] = self.inventory_tab.create_frame(self.main_frame)
        self.frames["cascade"] = self.cascade_tab.create_frame(self.main_frame)
    
    def refresh_inventory(self):
        """Refresh the inventory display (delegate to tab)."""
        self.inventory_tab.refresh_inventory()
    
    def add_relic_dialog(self):
        """Open dialog to add a relic."""
        dialog = AddRelicDialog(self, self.relics, self.COLORS)
        self.wait_window(dialog)
        
        if dialog.result:
            relic, refinement, quantity = dialog.result
            # Check if already exists
            for item in self.inventory:
                if item.relic == relic and item.refinement == refinement:
                    item.quantity += quantity
                    break
            else:
                self.inventory.append(InventoryItem(relic, refinement, quantity))
            
            self.save_inventory()
            self.refresh_inventory()
    
    def update_profile_display(self, profile: AlecaFrameProfile):
        """Update the sidebar profile display with AlecaFrame data."""
        try:
            # Show the profile frame
            self.profile_frame.grid()
            
            # Update MR badge with hexagon icon
            try:
                mr_icon_path = get_mastery_icon_path(profile.mastery_rank, 44)
                if mr_icon_path and os.path.exists(mr_icon_path):
                    mr_pil = Image.open(mr_icon_path)
                    self.mr_image = ctk.CTkImage(light_image=mr_pil, dark_image=mr_pil, size=(44, 44))
                    self.mr_image_label.configure(image=self.mr_image, text="")
                else:
                    self.mr_image_label.configure(text=str(profile.mastery_rank))
            except Exception as e:
                print(f"Error loading MR icon: {e}")
                self.mr_image_label.configure(text=str(profile.mastery_rank))
            
            # Update username and custom title
            if profile.username:
                self.username_label.configure(text=profile.username)
                
                # Check for custom title
                username_lower = profile.username.lower()
                if username_lower in self.CUSTOM_TITLES:
                    title_text, title_color = self.CUSTOM_TITLES[username_lower]
                    self.title_label.configure(text=title_text, text_color=title_color)
                    self.title_label.pack(side="left", padx=(6, 0))
                else:
                    self.title_label.pack_forget()
            
            # Update stat labels (now using icon images instead of emojis)
            self.stat_labels['plat'].configure(text=f"{profile.platinum:,}")
            self.stat_labels['credits'].configure(text=f"{profile.format_credits()}")
            self.stat_labels['ducats'].configure(text=f"{profile.ducats:,}")
            
        except Exception as e:
            print(f"Error updating profile display: {e}")
    
    def sync_alecaframe(self):
        """Sync inventory with AlecaFrame."""
        token = self.settings.get('alecaframe_token')
        if not token:
            self.open_settings()
            return
        
        # Show loading
        self.status_label.configure(text="⟳ Syncing...", text_color=self.COLORS['warning'])
        self.update()
        
        def do_sync():
            try:
                self.alecaframe_api.set_token(token)
                
                # Fetch profile data
                profile = self.alecaframe_api.get_profile()
                if not profile.error:
                    # Save profile to database
                    self.db.save_profile({
                        'username': profile.username,
                        'mastery_rank': profile.mastery_rank,
                        'mastery_percentage': profile.mastery_percentage,
                        'platinum': profile.platinum,
                        'credits': profile.credits,
                        'endo': profile.endo,
                        'ducats': profile.ducats,
                        'aya': profile.aya,
                        'relics_opened': profile.relics_opened,
                        'trades': profile.trades
                    })
                    self.after(0, lambda p=profile: self.update_profile_display(p))
                
                # Fetch inventory
                inventory = self.alecaframe_api.get_inventory()
                
                if inventory.error:
                    self.after(0, lambda: self.status_label.configure(
                        text="✗ " + inventory.error[:20],
                        text_color=self.COLORS['error']
                    ))
                    print(f"Sync error: {inventory.error}")
                    return
                
                if inventory.relics:
                    # Merge inventory
                    self.inventory.clear()
                    new_relics = []
                    
                    for relic_item in inventory.relics:
                        # Find matching relic
                        matching_relic = None
                        for relic in self.relics:
                            if relic.era.value == relic_item.era and relic.name == relic_item.identifier:
                                matching_relic = relic
                                break
                        
                        if not matching_relic:
                            # Create new relic entry
                            era_map = {'Lith': RelicEra.LITH, 'Meso': RelicEra.MESO,
                                       'Neo': RelicEra.NEO, 'Axi': RelicEra.AXI}
                            era = era_map.get(relic_item.era, RelicEra.LITH)
                            matching_relic = Relic(era, relic_item.identifier, [], False)
                            self.relics.append(matching_relic)
                            new_relics.append(matching_relic)
                        
                        ref_map = {'Intact': RelicRefinement.INTACT,
                                   'Exceptional': RelicRefinement.EXCEPTIONAL,
                                   'Flawless': RelicRefinement.FLAWLESS,
                                   'Radiant': RelicRefinement.RADIANT}
                        refinement = ref_map.get(relic_item.refinement, RelicRefinement.INTACT)
                        
                        self.inventory.append(InventoryItem(matching_relic, refinement, relic_item.quantity))
                    
                    # Save new relics to database
                    if new_relics:
                        self.db.save_relics_batch(new_relics)
                    
                    # Save inventory to database
                    self.save_inventory()
                    
                    # Update sync metadata
                    self.db.update_sync_metadata("AlecaFrame")
                    
                    self.after(0, self.refresh_inventory)
                    self.after(0, lambda: self.status_label.configure(
                        text=f"✓ Synced {len(self.inventory)} relics",
                        text_color=self.COLORS['success']
                    ))
                    self.after(0, self._update_last_sync_display)
                else:
                    self.after(0, lambda: self.status_label.configure(
                        text="✗ No relics found",
                        text_color=self.COLORS['error']
                    ))
            except Exception as e:
                self.after(0, lambda: self.status_label.configure(
                    text=f"✗ Error",
                    text_color=self.COLORS['error']
                ))
                print(f"Sync error: {e}")
        
        threading.Thread(target=do_sync, daemon=True).start()
    
    def _update_last_sync_display(self):
        """Update the last sync timestamp display."""
        try:
            sync_info = self.db.get_last_sync()
            if sync_info and sync_info.get('last_sync'):
                from datetime import datetime
                last_sync_str = sync_info['last_sync']
                # Parse the datetime string
                try:
                    last_sync = datetime.fromisoformat(last_sync_str)
                    # Format as "Last sync: 2:30 PM" or "Last sync: Jan 31, 2:30 PM"
                    now = datetime.now()
                    if last_sync.date() == now.date():
                        time_str = last_sync.strftime("%I:%M %p").lstrip("0")
                    else:
                        time_str = last_sync.strftime("%b %d, %I:%M %p").lstrip("0")
                    self.last_sync_label.configure(text=f"Last sync: {time_str}")
                except:
                    self.last_sync_label.configure(text=f"Last sync: {last_sync_str[:16]}")
            else:
                self.last_sync_label.configure(text="")
        except Exception as e:
            print(f"Error updating last sync display: {e}")
    
    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self, self.settings, self.COLORS)
        self.wait_window(dialog)
        
        if dialog.result:
            self.settings = dialog.result
            self.save_settings()
            self.alecaframe_api = AlecaFrameAPI(self.settings.get('alecaframe_token'))
            # Restart auto-sync timer with new settings
            self.start_auto_sync_timer()


class AddRelicDialog(ctk.CTkToplevel):
    """Dialog to add a relic to inventory."""
    
    def __init__(self, parent, relics, colors):
        super().__init__(parent)
        
        self.title("Add Relic")
        self.geometry("400x350")
        self.configure(fg_color=colors['bg_primary'])
        
        self.transient(parent)
        self.grab_set()
        
        self.relics = relics
        self.colors = colors
        self.result = None
        
        # Era
        era_frame = ctk.CTkFrame(self, fg_color="transparent")
        era_frame.pack(fill="x", padx=30, pady=(30, 15))
        
        ctk.CTkLabel(era_frame, text="Era", 
                    font=ctk.CTkFont(size=13),
                    text_color=colors['text_muted']).pack(anchor="w")
        
        self.era_combo = ctk.CTkComboBox(
            era_frame,
            values=["Lith", "Meso", "Neo", "Axi"],
            fg_color=colors['bg_card'],
            command=self.update_relics
        )
        self.era_combo.set("Lith")
        self.era_combo.pack(fill="x", pady=(5, 0))
        
        # Relic
        relic_frame = ctk.CTkFrame(self, fg_color="transparent")
        relic_frame.pack(fill="x", padx=30, pady=15)
        
        ctk.CTkLabel(relic_frame, text="Relic",
                    font=ctk.CTkFont(size=13),
                    text_color=colors['text_muted']).pack(anchor="w")
        
        self.relic_combo = ctk.CTkComboBox(
            relic_frame,
            values=["Select..."],
            fg_color=colors['bg_card']
        )
        self.relic_combo.pack(fill="x", pady=(5, 0))
        
        # Refinement
        ref_frame = ctk.CTkFrame(self, fg_color="transparent")
        ref_frame.pack(fill="x", padx=30, pady=15)
        
        ctk.CTkLabel(ref_frame, text="Refinement",
                    font=ctk.CTkFont(size=13),
                    text_color=colors['text_muted']).pack(anchor="w")
        
        self.ref_combo = ctk.CTkComboBox(
            ref_frame,
            values=["Intact", "Exceptional", "Flawless", "Radiant"],
            fg_color=colors['bg_card']
        )
        self.ref_combo.set("Intact")
        self.ref_combo.pack(fill="x", pady=(5, 0))
        
        # Quantity
        qty_frame = ctk.CTkFrame(self, fg_color="transparent")
        qty_frame.pack(fill="x", padx=30, pady=15)
        
        ctk.CTkLabel(qty_frame, text="Quantity",
                    font=ctk.CTkFont(size=13),
                    text_color=colors['text_muted']).pack(anchor="w")
        
        self.qty_entry = ctk.CTkEntry(
            qty_frame,
            fg_color=colors['bg_card'],
            placeholder_text="1"
        )
        self.qty_entry.insert(0, "1")
        self.qty_entry.pack(fill="x", pady=(5, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=30)
        
        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color=colors['bg_card'],
            hover_color=colors['bg_hover'],
            command=self.destroy
        )
        cancel_btn.pack(side="left", expand=True, padx=(0, 10))
        
        add_btn = ctk.CTkButton(
            btn_frame, text="Add",
            fg_color=colors['accent'],
            hover_color=colors['accent_hover'],
            command=self.add_relic
        )
        add_btn.pack(side="right", expand=True, padx=(10, 0))
        
        self.update_relics()
    
    def update_relics(self, *args):
        """Update relic dropdown."""
        era = self.era_combo.get()
        relics = [r.name for r in self.relics if r.era.value == era]
        self.relic_combo.configure(values=relics if relics else ["No relics"])
        if relics:
            self.relic_combo.set(relics[0])
    
    def add_relic(self):
        """Add the relic."""
        era = self.era_combo.get()
        relic_name = self.relic_combo.get()
        ref = self.ref_combo.get()
        
        try:
            qty = int(self.qty_entry.get())
        except:
            qty = 1
        
        # Find relic
        relic = None
        for r in self.relics:
            if r.era.value == era and r.name == relic_name:
                relic = r
                break
        
        if relic:
            ref_map = {
                "Intact": RelicRefinement.INTACT,
                "Exceptional": RelicRefinement.EXCEPTIONAL,
                "Flawless": RelicRefinement.FLAWLESS,
                "Radiant": RelicRefinement.RADIANT
            }
            self.result = (relic, ref_map[ref], qty)
        
        self.destroy()


class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog."""
    
    def __init__(self, parent, settings, colors):
        super().__init__(parent)
        
        self.title("Settings")
        self.geometry("500x580")
        self.configure(fg_color=colors['bg_primary'])
        
        self.transient(parent)
        self.grab_set()
        
        self.settings = settings.copy()
        self.colors = colors
        self.result = None
        self.db = parent.db
        
        # Import updater
        try:
            from updater import get_version, check_for_updates_async, UpdateInfo
            self.has_updater = True
            self.current_version = get_version()
        except ImportError:
            self.has_updater = False
            self.current_version = "Unknown"
        
        # AlecaFrame section
        section = ctk.CTkFrame(self, fg_color=colors['bg_card'], corner_radius=12)
        section.pack(fill="x", padx=30, pady=(30, 15))
        
        title = ctk.CTkLabel(
            section, text="AlecaFrame Integration",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=colors['text']
        )
        title.pack(anchor="w", padx=20, pady=(20, 5))
        
        desc = ctk.CTkLabel(
            section,
            text="Paste your AlecaFrame share URL or public token to sync your relic inventory",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_muted'],
            wraplength=400
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        self.token_entry = ctk.CTkEntry(
            section,
            placeholder_text="https://alecaframe.com/Relics?token=... or just the token",
            fg_color=colors['bg_secondary'],
            height=40
        )
        self.token_entry.pack(fill="x", padx=20, pady=(0, 15))
        
        # Pre-fill
        if settings.get('alecaframe_token'):
            self.token_entry.insert(0, settings['alecaframe_token'])
        
        # Auto-sync toggle
        autosync_frame = ctk.CTkFrame(section, fg_color="transparent")
        autosync_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.autosync_var = ctk.BooleanVar(value=settings.get('auto_sync', False))
        self.autosync_toggle = ctk.CTkSwitch(
            autosync_frame,
            text="Auto-sync every 2 minutes",
            font=ctk.CTkFont(size=12),
            variable=self.autosync_var,
            onvalue=True,
            offvalue=False,
            progress_color=colors['accent']
        )
        self.autosync_toggle.pack(side="left")
        
        # Last sync info
        sync_info = self.db.get_last_sync()
        if sync_info:
            sync_frame = ctk.CTkFrame(self, fg_color=colors['bg_card'], corner_radius=12)
            sync_frame.pack(fill="x", padx=30, pady=(0, 15))
            
            sync_title = ctk.CTkLabel(
                sync_frame, text="Database Status",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=colors['text']
            )
            sync_title.pack(anchor="w", padx=20, pady=(15, 5))
            
            last_sync_text = f"Last synced: {sync_info['last_sync']}"
            if sync_info['total_relics']:
                last_sync_text += f" • {sync_info['total_relics']} relics"
            if sync_info['total_inventory']:
                last_sync_text += f" • {sync_info['total_inventory']} in inventory"
            
            sync_label = ctk.CTkLabel(
                sync_frame, text=last_sync_text,
                font=ctk.CTkFont(size=12),
                text_color=colors['text_muted']
            )
            sync_label.pack(anchor="w", padx=20, pady=(0, 15))
        
        # Updates section
        update_section = ctk.CTkFrame(self, fg_color=colors['bg_card'], corner_radius=12)
        update_section.pack(fill="x", padx=30, pady=(0, 15))
        
        update_title = ctk.CTkLabel(
            update_section, text="Updates",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=colors['text']
        )
        update_title.pack(anchor="w", padx=20, pady=(15, 5))
        
        version_label = ctk.CTkLabel(
            update_section,
            text=f"Current version: v{self.current_version}",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_muted']
        )
        version_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        update_btn_frame = ctk.CTkFrame(update_section, fg_color="transparent")
        update_btn_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.check_update_btn = ctk.CTkButton(
            update_btn_frame, text="Check for Updates",
            fg_color=colors['bg_secondary'],
            hover_color=colors['bg_hover'],
            width=150,
            command=self.check_for_updates
        )
        self.check_update_btn.pack(side="left")
        
        self.update_status_label = ctk.CTkLabel(
            update_btn_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=colors['text_muted']
        )
        self.update_status_label.pack(side="left", padx=(15, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=(0, 30))
        
        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color=colors['bg_card'],
            hover_color=colors['bg_hover'],
            command=self.destroy
        )
        cancel_btn.pack(side="left", expand=True, padx=(0, 10))
        
        save_btn = ctk.CTkButton(
            btn_frame, text="Save",
            fg_color=colors['accent'],
            hover_color=colors['accent_hover'],
            command=self.save
        )
        save_btn.pack(side="right", expand=True, padx=(10, 0))
    
    def check_for_updates(self):
        """Check GitHub for updates."""
        if not self.has_updater:
            self.update_status_label.configure(text="Updater not available")
            return
        
        self.check_update_btn.configure(state="disabled", text="Checking...")
        self.update_status_label.configure(text="")
        
        from updater import check_for_updates_async
        check_for_updates_async(self.on_update_check_complete)
    
    def on_update_check_complete(self, update_info):
        """Handle update check result (called from background thread)."""
        # Schedule UI update on main thread
        self.after(0, lambda: self._update_ui_after_check(update_info))
    
    def _update_ui_after_check(self, update_info):
        """Update UI after update check (on main thread)."""
        self.check_update_btn.configure(state="normal", text="Check for Updates")
        
        if update_info.error:
            self.update_status_label.configure(
                text=f"❌ Error checking updates",
                text_color=self.colors['warning']
            )
        elif update_info.update_available:
            self.update_status_label.configure(
                text=f"✨ v{update_info.latest_version} available!",
                text_color=self.colors['accent']
            )
            # Show download option
            self.show_update_dialog(update_info)
        else:
            self.update_status_label.configure(
                text="✓ You're up to date!",
                text_color=self.colors['success']
            )
    
    def show_update_dialog(self, update_info):
        """Show dialog with update details and auto-update option."""
        import webbrowser
        from updater import is_frozen, download_and_apply_update
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Update Available")
        dialog.geometry("420x380")
        dialog.configure(fg_color=self.colors['bg_primary'])
        dialog.transient(self)
        dialog.grab_set()
        
        title = ctk.CTkLabel(
            dialog,
            text=f"Version {update_info.latest_version} is available!",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text']
        )
        title.pack(pady=(30, 10))
        
        current = ctk.CTkLabel(
            dialog,
            text=f"Your version: v{update_info.current_version}",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_muted']
        )
        current.pack()
        
        if update_info.release_notes:
            notes_frame = ctk.CTkFrame(dialog, fg_color=self.colors['bg_card'], corner_radius=8)
            notes_frame.pack(fill="both", expand=True, padx=30, pady=20)
            
            notes_title = ctk.CTkLabel(
                notes_frame,
                text="What's New:",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.colors['text']
            )
            notes_title.pack(anchor="w", padx=15, pady=(10, 5))
            
            # Show first 200 chars of release notes
            notes_text = update_info.release_notes[:200]
            if len(update_info.release_notes) > 200:
                notes_text += "..."
            
            notes = ctk.CTkLabel(
                notes_frame,
                text=notes_text,
                font=ctk.CTkFont(size=11),
                text_color=self.colors['text_muted'],
                wraplength=320,
                justify="left"
            )
            notes.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Status label for progress
        status_label = ctk.CTkLabel(
            dialog,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.colors['text_muted']
        )
        status_label.pack(pady=(0, 10))
        
        # Progress bar
        progress_bar = ctk.CTkProgressBar(
            dialog,
            width=300,
            height=8,
            progress_color=self.colors['accent'],
            fg_color=self.colors['bg_card']
        )
        progress_bar.set(0)
        # Hidden initially
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        close_btn = ctk.CTkButton(
            btn_frame, text="Later",
            fg_color=self.colors['bg_card'],
            hover_color=self.colors['bg_hover'],
            command=dialog.destroy
        )
        close_btn.pack(side="left", expand=True, padx=(0, 5))
        
        def open_download():
            from updater import GITHUB_RELEASES_URL
            webbrowser.open(GITHUB_RELEASES_URL)
            dialog.destroy()
        
        def start_auto_update():
            """Start the auto-update process."""
            # Disable buttons
            update_btn.configure(state="disabled", text="Updating...")
            close_btn.configure(state="disabled")
            download_btn.configure(state="disabled")
            
            # Show progress bar
            progress_bar.pack(pady=(0, 10))
            
            def on_progress(status_text, downloaded, total):
                def update():
                    status_label.configure(text=status_text)
                    if total > 0:
                        progress_bar.set(downloaded / total)
                dialog.after(0, update)
            
            def on_complete(success, message):
                def update():
                    status_label.configure(text=message)
                    if success:
                        status_label.configure(text_color=self.colors['success'])
                        # Close dialog and app after short delay
                        dialog.after(1500, lambda: self._close_for_update(dialog))
                    else:
                        status_label.configure(text_color=self.colors['warning'])
                        update_btn.configure(state="normal", text="⬇ Install Update")
                        close_btn.configure(state="normal")
                        download_btn.configure(state="normal")
                dialog.after(0, update)
            
            download_and_apply_update(update_info, on_progress, on_complete)
        
        download_btn = ctk.CTkButton(
            btn_frame, text="Manual Download",
            fg_color=self.colors['bg_card'],
            hover_color=self.colors['bg_hover'],
            command=open_download
        )
        download_btn.pack(side="left", expand=True, padx=5)
        
        # Show auto-update button only for EXE with exe download URL
        if is_frozen() and update_info.exe_download_url:
            update_btn = ctk.CTkButton(
                btn_frame, text="⬇ Install Update",
                fg_color=self.colors['accent'],
                hover_color=self.colors['accent_hover'],
                command=start_auto_update
            )
            update_btn.pack(side="right", expand=True, padx=(5, 0))
        else:
            # Just make download the primary button if not EXE
            download_btn.configure(
                fg_color=self.colors['accent'],
                hover_color=self.colors['accent_hover']
            )
    
    def _close_for_update(self, dialog):
        """Close dialog and app for update."""
        dialog.destroy()
        # Close the main app - the update script will restart it
        self.master.destroy()
    
    def save(self):
        """Save settings."""
        token = self.token_entry.get().strip()
        
        # Extract token from URL if needed
        if 'token=' in token:
            import re
            match = re.search(r'[?&]token=([^&]+)', token)
            if match:
                token = match.group(1)
        
        self.settings['alecaframe_token'] = token
        self.settings['auto_sync'] = self.autosync_var.get()
        self.result = self.settings
        self.destroy()


def main():
    """Main entry point."""
    app = ModernRelicApp()
    app.mainloop()


if __name__ == "__main__":
    main()
