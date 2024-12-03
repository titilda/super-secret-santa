from datetime import datetime
from tempfile import NamedTemporaryFile
from contextlib import contextmanager
from textwrap import wrap

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from segno import make_qr

CELL_X_COUNT = 2
CELL_Y_COUNT = 7

# PDF page geometry
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 0.5 * cm
CELL_WIDTH = (PAGE_WIDTH - 2 * MARGIN) / CELL_X_COUNT
HEADER_HEIGHT = 1 * cm
CELL_HEIGHT = (PAGE_HEIGHT - 2 * MARGIN - HEADER_HEIGHT) / CELL_Y_COUNT
QR_SIZE = CELL_HEIGHT - 0.5 * cm


@contextmanager
def generate_qr_code(snowflake: int):
    with NamedTemporaryFile(suffix=".png") as f:
        # Generate QR code and save it to the file
        qr = make_qr(f"https://discord.com/users/{snowflake}")
        qr.save(f.name, scale=5, border=0)
        yield f


def generate_pdf(data_list, output_pdf):

    # Create a new PDF
    c = canvas.Canvas(output_pdf, pagesize=A4)
    draw_header(c)

    for i, (name, qr_path) in enumerate(data_list):
        col = i % CELL_X_COUNT
        row = (i // CELL_X_COUNT) % CELL_Y_COUNT
        draw_cell(c, col, row, name, qr_path)
        if row == CELL_Y_COUNT - 1 and col == CELL_X_COUNT - 1:
            c.showPage()
            draw_header(c)

    c.save()


def draw_header(c: canvas.Canvas):
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(
        PAGE_WIDTH / 2,
        PAGE_HEIGHT - MARGIN - HEADER_HEIGHT / 2,
        f"Super Secret Santa by TiTilda, rendered at {datetime.now()}",
    )
    # draw horizontal dotted line
    c.setDash(1, 1)
    c.line(0, PAGE_HEIGHT - HEADER_HEIGHT - MARGIN, PAGE_WIDTH, PAGE_HEIGHT - HEADER_HEIGHT - MARGIN)
    c.setDash()


def draw_cell(c: canvas.Canvas, col: int, row: int, name, giftee_snowflake):
    x = MARGIN + col * CELL_WIDTH
    y = MARGIN + (CELL_Y_COUNT - row - 1) * CELL_HEIGHT

    # draw cell border
    c.setDash(1, 1)
    c.rect(x, y, CELL_WIDTH, CELL_HEIGHT)
    c.setDash()

    # draw text
    FONT_SIZE = 12
    MAX_WIDTH = CELL_WIDTH - 2 * MARGIN - QR_SIZE
    text = c.beginText(x + MARGIN, y + CELL_HEIGHT - 2 * MARGIN)
    text.setFont("Helvetica-Bold", FONT_SIZE)
    text_lines = f"Gift from {name}\nMake sure to remove this text before attaching the QR code!"
    for line in text_lines.split("\n"):
        wrapped_lines = wrap(line, width=int(MAX_WIDTH / c.stringWidth("A", "Helvetica", 10)))
        for wrapped_line in wrapped_lines:
            text.textLine(wrapped_line)
    c.drawText(text)

    with generate_qr_code(giftee_snowflake) as qr_file:
        c.drawImage(
            qr_file.name,
            x + CELL_WIDTH - QR_SIZE - MARGIN,
            y + (CELL_HEIGHT - QR_SIZE) / 2,
            width=QR_SIZE,
            height=QR_SIZE,
        )


if __name__ == "__main__":
    generate_pdf([("TiTilda", 1234567890)], "output.pdf")
