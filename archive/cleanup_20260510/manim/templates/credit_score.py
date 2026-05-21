"""
Credit Score Gauge Animation
Shows credit score on a gauge/meter display
"""
from manim import *

class CreditScoreMeter(Scene):
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
            "YOUR CREDIT SCORE",
            font="Montserrat",
            weight="BOLD",
            color="white",
            font_size=40
        )
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        
        # Create gauge
        gauge = AnnularSector(
            inner_radius=2.5,
            outer_radius=3,
            angle=PI,
            start_angle=PI,
            color="gray",
            fill_opacity=0.3
        )
        
        # Color zones
        zones = [
            (300, 579, "#E94560"),   # Bad
            (580, 669, "#F5A623"),   # Fair
            (670, 739, "#4ECDC4"),   # Good
            (740, 799, "#00D4AA"),   # Very Good
            (800, 850, "#FFD700"),   # Excellent
        ]
        
        zone_sectors = VGroup()
        for low, high, color in zones:
            start_angle = PI + (low - 300) / 550 * PI
            angle = (high - low) / 550 * PI
            sector = AnnularSector(
                inner_radius=2.5,
                outer_radius=3,
                angle=angle,
                start_angle=start_angle,
                color=color,
                fill_opacity=0.6
            )
            zone_sectors.add(sector)
        
        gauge.move_to(ORIGIN)
        zone_sectors.move_to(ORIGIN)
        
        self.play(Create(gauge))
        self.play(*[FadeIn(z) for z in zone_sectors], run_time=1)
        
        # Score labels
        score_labels = VGroup()
        for s in [300, 500, 670, 740, 800, 850]:
            angle = PI + (s - 300) / 550 * PI
            pos = np.array([3.3 * np.cos(angle), 3.3 * np.sin(angle), 0])
            label = Text(str(s), font="Inter", color="gray", font_size=16)
            label.move_to(pos)
            score_labels.add(label)
        
        self.play(*[Write(l) for l in score_labels])
        
        # Needle animation
        needle = Arrow(
            start=ORIGIN,
            end=UP * 2.8,
            color="#00D4AA",
            stroke_width=3,
            max_tip_length_to_length_ratio=0.1
        )
        needle.move_to(ORIGIN)
        
        # Animate needle moving to score
        target_score = 750
        target_angle = PI + (target_score - 300) / 550 * PI
        
        def update_needle(mob, alpha):
            angle = interpolate(PI, target_angle, alpha)
            mob.rotate(angle - mob.get_angle())
        
        self.play(
            Create(needle),
            UpdateFromAlphaFunc(needle, update_needle),
            run_time=3
        )
        
        # Score display
        score_text = Text(
            "800+",
            font="Montserrat",
            weight="BOLD",
            color="#FFD700",
            font_size=96
        )
        score_text.move_to(DOWN * 0.5)
        
        self.play(
            Write(score_text),
            needle.animate.set_color("#FFD700"),
            run_time=1
        )
        
        self.wait(2)
