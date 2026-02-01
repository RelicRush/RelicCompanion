"""
Calculator Tab for the Warframe Relic Companion.
"""

import customtkinter as ctk
from models import RelicRefinement, RewardRarity, DROP_CHANCES


class CalculatorTab:
    """Relic value calculator tab functionality."""
    
    def __init__(self, app):
        self.app = app
        self.COLORS = app.COLORS
        self.calc_era = None
        self.calc_relic = None
        self.calc_ref = None
        self.calc_results = None
    
    def create_frame(self, parent):
        """Create the relic value calculator frame."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        
        # Header
        header = ctk.CTkLabel(frame, text="Relic Calculator", font=ctk.CTkFont(size=28, weight="bold"), text_color=self.COLORS['text'])
        header.pack(anchor="w", padx=30, pady=(30, 0))

        # Add spacing between header and subtitle
        spacer = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=2))
        spacer.pack(anchor="w", padx=30, pady=(0, 0))

        subtitle = ctk.CTkLabel(frame, text="Calculate expected platinum value based on drop chances", font=ctk.CTkFont(size=13), text_color=self.COLORS['text_muted'])
        subtitle.pack(anchor="w", padx=30, pady=(0, 20))
        
        # Relic selector
        selector_frame = ctk.CTkFrame(frame, fg_color=self.COLORS['bg_card'], corner_radius=12)
        selector_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        era_label = ctk.CTkLabel(selector_frame, text="Era:",
                                font=ctk.CTkFont(size=12),
                                text_color=self.COLORS['text_muted'])
        era_label.pack(side="left", padx=(15, 5), pady=15)
        
        self.calc_era = ctk.CTkComboBox(
            selector_frame,
            values=["Lith", "Meso", "Neo", "Axi"],
            width=100,
            corner_radius=6,
            fg_color=self.COLORS['bg_secondary'],
            command=self.update_relic_selector
        )
        self.calc_era.set("Lith")
        self.calc_era.pack(side="left", padx=(0, 20), pady=15)
        
        relic_label = ctk.CTkLabel(selector_frame, text="Relic:",
                                  font=ctk.CTkFont(size=12),
                                  text_color=self.COLORS['text_muted'])
        relic_label.pack(side="left", padx=(0, 5), pady=15)
        
        self.calc_relic = ctk.CTkComboBox(
            selector_frame,
            values=["Select..."],
            width=150,
            corner_radius=6,
            fg_color=self.COLORS['bg_secondary']
        )
        self.calc_relic.pack(side="left", padx=(0, 20), pady=15)
        
        ref_label = ctk.CTkLabel(selector_frame, text="Refinement:",
                                font=ctk.CTkFont(size=12),
                                text_color=self.COLORS['text_muted'])
        ref_label.pack(side="left", padx=(0, 5), pady=15)
        
        self.calc_ref = ctk.CTkComboBox(
            selector_frame,
            values=["Intact", "Exceptional", "Flawless", "Radiant"],
            width=120,
            corner_radius=6,
            fg_color=self.COLORS['bg_secondary']
        )
        self.calc_ref.set("Intact")
        self.calc_ref.pack(side="left", padx=(0, 20), pady=15)
        
        calc_btn = ctk.CTkButton(
            selector_frame,
            text="Calculate",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['accent_hover'],
            height=38,
            corner_radius=8,
            command=self.calculate_value
        )
        calc_btn.pack(side="right", padx=15, pady=15)
        
        # Results
        self.calc_results = ctk.CTkScrollableFrame(
            frame,
            fg_color=self.COLORS['bg_secondary'],
            corner_radius=12
        )
        self.calc_results.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        
        # Init relic selector
        self.update_relic_selector()
        
        return frame
    
    def update_relic_selector(self, *args):
        """Update relic dropdown based on era."""
        era = self.calc_era.get()
        relics = [r.name for r in self.app.relics if r.era.value == era]
        self.calc_relic.configure(values=relics if relics else ["No relics"])
        if relics:
            self.calc_relic.set(relics[0])
    
    def calculate_value(self):
        """Calculate relic value."""
        era_str = self.calc_era.get()
        relic_name = self.calc_relic.get()
        ref_str = self.calc_ref.get()
        
        # Find relic
        relic = None
        for r in self.app.relics:
            if r.era.value == era_str and r.name == relic_name:
                relic = r
                break
        
        if not relic:
            return
        
        # Clear results
        for widget in self.calc_results.winfo_children():
            widget.destroy()
        
        # Header
        header = ctk.CTkLabel(
            self.calc_results,
            text=f"{era_str} {relic_name} ({ref_str})",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text']
        )
        header.pack(row=0, column=0, sticky="w", padx=15, pady=(15, 20))
        
        # Get refinement enum
        ref_map = {
            "Intact": RelicRefinement.INTACT,
            "Exceptional": RelicRefinement.EXCEPTIONAL,
            "Flawless": RelicRefinement.FLAWLESS,
            "Radiant": RelicRefinement.RADIANT
        }
        refinement = ref_map.get(ref_str, RelicRefinement.INTACT)
        
        # Show rewards with drop chances
        drops = DROP_CHANCES.get(refinement, DROP_CHANCES[RelicRefinement.INTACT])
        
        for i, reward in enumerate(relic.rewards):
            chance = drops.get(reward.rarity, 0.0)
            
            row = ctk.CTkFrame(self.calc_results, fg_color=self.COLORS['bg_card'], corner_radius=8)
            row.pack(row=i+1, column=0, sticky="ew", padx=10, pady=4)
            row.grid_columnconfigure(1, weight=1)
            
            # Rarity color
            rarity_colors = {
                RewardRarity.COMMON: self.COLORS['text_muted'],
                RewardRarity.UNCOMMON: self.COLORS['text_secondary'],
                RewardRarity.RARE: self.COLORS['gold']
            }
            
            name = ctk.CTkLabel(
                row, text=reward.name,
                font=ctk.CTkFont(size=13),
                text_color=rarity_colors.get(reward.rarity, self.COLORS['text'])
            )
            name.grid(row=0, column=0, padx=15, pady=12, sticky="w")
            
            chance_lbl = ctk.CTkLabel(
                row, text=f"{chance*100:.1f}%",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            )
            chance_lbl.grid(row=0, column=1, padx=10, pady=12)
        
        # Note about prices
        note = ctk.CTkLabel(
            self.calc_results,
            text="💡 Use the Price Check tab to look up individual item values",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        )
        note.pack(row=len(relic.rewards)+2, column=0, pady=(20, 15))
