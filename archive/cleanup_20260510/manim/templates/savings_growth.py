"""
Compound Interest Growth Graph
Shows exponential savings growth over time
"""
from manim import *

class SavingsGrowth(Scene):
    def construct(self):
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        # Title
        title = Text(
            "THE POWER OF COMPOUND INTEREST",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=36
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Create axes
        axes = Axes(
            x_range=[0, 30, 5],
            y_range=[0, 1000000, 200000],
            x_length=10,
            y_length=6,
            axis_config={"color": "gray"},
            x_axis_config={"numbers_to_include": range(0, 31, 5)},
            y_axis_config={
                "numbers_to_include": range(0, 1000001, 200000),
                "formatter": lambda x: f"${x:,.0f}"
            }
        )
        axes.move_to(ORIGIN)
        
        labels = axes.get_axis_labels(
            x_label="Years",
            y_label="Value"
        )
        
        self.play(Create(axes), Write(labels))
        
        # Plot compound growth
        def compound_value(x):
            # $500/month at 8% annual return
            monthly_investment = 500
            monthly_rate = 0.08 / 12
            months = x * 12
            if months == 0:
                return 0
            return monthly_investment * ((1 + monthly_rate) ** months - 1) / monthly_rate
        
        graph = axes.plot(
            compound_value,
            x_range=[0, 30],
            color="#00D4AA",
            stroke_width=4
        )
        
        # Animate graph drawing
        self.play(
            Create(graph),
            run_time=4,
            rate_func=linear
        )
        
        # Highlight key points
        dots = VGroup()
        for year in [5, 10, 20, 30]:
            value = compound_value(year)
            dot = Dot(
                axes.coords_to_point(year, value),
                color="#FFD700",
                radius=0.1
            )
            label = Text(
                f"${value:,.0f}",
                font="Inter",
                color="#FFD700",
                font_size=20
            )
            label.next_to(dot, UP + RIGHT, buff=0.2)
            dots.add(VGroup(dot, label))
        
        for dot_group in dots:
            self.play(
                FadeIn(dot_group, scale=2),
                run_time=0.5
            )
        
        self.wait(2)
