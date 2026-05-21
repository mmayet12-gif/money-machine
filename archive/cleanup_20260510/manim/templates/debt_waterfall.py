"""
Debt Reduction Waterfall Chart
Shows debt decreasing over time with waterfall effect
"""
from manim import *

class DebtWaterfall(Scene):
    def construct(self):
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        title = Text(
            "DEBT SNOWBALL METHOD",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=40
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Debt data
        debts = [
            ("Credit Card A", 5000, "#E94560"),
            ("Credit Card B", 3000, "#F5A623"),
            ("Car Loan", 15000, "#4ECDC4"),
            ("Student Loan", 25000, "#9B59B6"),
        ]
        
        bars = VGroup()
        max_debt = max(d[1] for d in debts)
        
        for i, (name, amount, color) in enumerate(debts):
            bar_height = (amount / max_debt) * 4
            bar = Rectangle(
                width=1.5,
                height=bar_height,
                fill_color=color,
                fill_opacity=0.8,
                stroke_color=color,
                stroke_width=2
            )
            bar.move_to(np.array([i * 2.2 - 3.3, -2 + bar_height/2, 0]))
            
            label = Text(
                name,
                font="Inter",
                color="white",
                font_size=16
            )
            label.next_to(bar, DOWN, buff=0.2)
            
            amount_text = Text(
                f"${amount:,}",
                font="Inter",
                color=color,
                font_size=20,
                weight="BOLD"
            )
            amount_text.next_to(bar, UP, buff=0.2)
            
            bars.add(VGroup(bar, label, amount_text))
        
        # Animate bars growing
        for bar_group in bars:
            self.play(
                bar_group[0].animate.stretch_to_fit_height(bar_group[0].height),
                Write(bar_group[1]),
                Write(bar_group[2]),
                run_time=1
            )
        
        # Snowball effect arrows
        arrows = VGroup()
        for i in range(len(bars) - 1):
            arrow = CurvedArrow(
                bars[i].get_right(),
                bars[i+1].get_left(),
                color="#00D4AA",
                angle=-0.3
            )
            arrows.add(arrow)
        
        self.play(*[Create(a) for a in arrows], run_time=2)
        
        self.wait(2)
