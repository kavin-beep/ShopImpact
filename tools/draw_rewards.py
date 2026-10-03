"""Generate a leaf with Python turtle navigation; optionally show real Turtle.

Default SVG export uses turtle.TNavigator for genuine forward/turn geometry
without creating a Tk window. --preview runs the same commands on turtle.Turtle.
The app displays the committed SVG, so its cloud server does not need Tk.
"""
import argparse
from pathlib import Path
import turtle


class SvgTurtle(turtle.TNavigator):
    """Small SVG pen adapter around the standard-library navigation engine."""

    def __init__(self):
        super().__init__()
        self.drawing = True
        self.paths = []
        self.current = []
        self.colour = "#28644F"
        self.width = 3

    def _goto(self, end):
        if self.drawing:
            if not self.current:
                self.current.append(tuple(self._position))
            self.current.append(tuple(end))
        super()._goto(end)

    def flush(self):
        if self.current:
            self.paths.append((self.current, self.colour, self.width))
            self.current = []

    def penup(self):
        self.flush()
        self.drawing = False

    def pendown(self):
        self.drawing = True

    def pencolor(self, colour):
        self.flush()
        self.colour = colour

    def pensize(self, width):
        self.flush()
        self.width = width

    def svg(self):
        self.flush()
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-125 -165 260 235" role="img" aria-labelledby="title">',
                 '<title id="title">Turtle leaf reward for a lower-factor shopping choice</title>',
                 '<rect x="-125" y="-165" width="260" height="235" rx="24" fill="#EAEFE5"/>']
        for points, colour, width in self.paths:
            coordinates = " ".join(f"{x:.2f},{-y:.2f}" for x, y in points)
            parts.append(f'<polyline points="{coordinates}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')
        parts.append('</svg>')
        return "\n".join(parts)


def draw_leaf(pen):
    """One drawing recipe usable by the SVG adapter and desktop Turtle."""
    pen.pencolor("#28644F")
    pen.pensize(5)
    pen.penup()
    pen.goto(-70, -40)
    pen.setheading(0)
    pen.pendown()
    # Two curved sides: repeated forward steps and left turns.
    for _ in range(2):
        for _ in range(60):
            pen.forward(3)
            pen.left(1.5)
        pen.left(90)
    pen.penup()
    pen.goto(-85, -55)
    pen.setheading(45)
    pen.pendown()
    pen.forward(180)
    pen.pensize(3)
    for offset in [25, 50, 75, 100]:
        for direction in [-1, 1]:
            pen.penup()
            pen.goto(-70 + offset * 0.7071, -40 + offset * 0.7071)
            pen.setheading(45 + direction * 45)
            pen.pendown()
            pen.forward(22)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="Draw using desktop turtle.Turtle (requires Tk)")
    args = parser.parse_args()
    pen = SvgTurtle()
    draw_leaf(pen)
    target = Path(__file__).resolve().parents[1] / "assets/turtle/leaf.svg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(pen.svg(), encoding="utf-8")
    print(f"Generated {target}")
    if args.preview:
        screen = turtle.Screen()
        screen.title("ShopImpact Turtle leaf")
        screen.bgcolor("#EAEFE5")
        artist = turtle.Turtle()
        artist.speed(6)
        draw_leaf(artist)
        artist.hideturtle()
        screen.mainloop()


if __name__ == "__main__":
    main()
