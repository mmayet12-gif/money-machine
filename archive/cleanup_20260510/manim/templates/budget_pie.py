"""
Budget Pie Chart Animation
Shows expense breakdown with animated slices
"""
from manim import *

class BudgetPieChart(Scene):
    def construct(self):
        # Data
        categories = ["Housing", "Food", "Transport", "Savings", "Entertainment"]
        values = [35, 20, 15, 20, 10]
        colors = ["#E94560", "#F5A623", "#4ECDC4", "#00D4AA", "#9B59B6"]
        
        total = sum(values)
        angles = [v/total * TAU for v in values]
        
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
            "MONTHLY BUDGET BREAKDOWN",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=36
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Create pie slices
        slices = VGroup()
        current_angle = 0
        
        for i, (angle, color) in enumerate(zip(angles, colors)):
            sector = AnnularSector(
                inner_radius=0,
                outer_radius=2.5,
                angle=angle,
                start_angle=current_angle,
                color=color,
                fill_opacity=0.8
            )
            slices.add(sector)
            current_angle += angle
        
        slices.move_to(ORIGIN)
        
        # Animate slices appearing one by one
        for i, sector in enumerate(slices):
            self.play(
                Create(sector),
                run_time=0.5
            )
        
        # Add labels
        labels = VGroup()
        current_angle = 0
        for i, (category, value, angle, color) in enumerate(
            zip(categories, values, angles, colors)
        ):
            mid_angle = current_angle + angle / 2
            label_pos = np.array([
                3.5 * np.cos(mid_angle),
                3.5 * np.sin(mid_angle),
                0
            ])
            
            label = VGroup(
                Text(category, font="Inter", color=color, font_size=20),
                Text(f"{value}%", font="Inter", color="white", font_size=16)
            )
            label.arrange(DOWN, buff=0.1)
            label.move_to(label_pos)
            labels.add(label)
            current_angle += angle
        
        self.play(
            *[FadeIn(label, shift=label.get_center()*0.2) for label in labels],
            run_time=2
        )
        
        self.wait(2)
