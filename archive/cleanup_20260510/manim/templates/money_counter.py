"""
Money Counter Animation
Shows money growing with particle effects
"""
from manim import *

class MoneyCounter(Scene):
    def construct(self):
        # Background
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#0F0F1A",
            fill_opacity=1,
            stroke_width=0
        )
        self.add(bg)
        
        # Starting amount
        start_amount = 0
        target_amount = 1000000
        
        # Counter text
        counter = always_redraw(lambda:
            Text(
                f"${self.get_counter_value():,.0f}",
                font="Montserrat",
                weight="BOLD",
                color="#00D4AA",
                font_size=72
            )
        )
        
        # Track value
        self.counter_value = start_amount
        counter.move_to(ORIGIN)
        
        # Particles representing money
        particles = VGroup()
        for _ in range(50):
            particle = Dot(
                radius=0.03,
                color=random.choice(["#00D4AA", "#E94560", "#FFD700"])
            )
            particle.move_to(np.array([
                random.uniform(-6, 6),
                random.uniform(-3, 3),
                0
            ]))
            particles.add(particle)
        
        # Animations
        self.play(FadeIn(counter, scale=1.5))
        self.play(
            counter.animate.scale(1.0),
            run_time=1
        )
        
        # Animate particles
        self.play(
            *[p.animate.shift(
                np.array([0, random.uniform(2, 4), 0])
            ).set_opacity(0) for p in particles],
            run_time=2
        )
        
        # Count up
        def update_value(mob, alpha):
            self.counter_value = interpolate(start_amount, target_amount, alpha)
        
        self.play(
            UpdateFromAlphaFunc(counter, update_value),
            run_time=3,
            rate_func=smooth
        )
        
        self.wait(0.5)
        
        # Burst effect
        burst = VGroup(*[
            Line(
                ORIGIN,
                np.array([random.uniform(-1, 1), random.uniform(-1, 1), 0]) * 3,
                color="#FFD700",
                stroke_width=2
            )
            for _ in range(20)
        ])
        
        self.play(
            *[Create(line) for line in burst],
            run_time=0.5
        )
        self.play(
            *[Uncreate(line) for line in burst],
            run_time=0.3
        )
        
        self.wait(0.5)
    
    def get_counter_value(self):
        return self.counter_value
