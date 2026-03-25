import logging
import sys
import threading
import tkinter as tk

from aws_env.gui import MainWindow

log = logging.getLogger(__name__)


def setup_tray(root: tk.Tk):
    """Optional system tray icon — left-click toggles window, right-click exits."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        log.debug("pystray/Pillow not available — skipping system tray")
        return None

    def create_icon_image(color="green"):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=color, outline="white", width=2)
        return img

    visible = [True]

    def toggle_window(icon, item):
        if visible[0]:
            root.after(0, root.withdraw)
            visible[0] = False
        else:
            root.after(0, root.deiconify)
            visible[0] = True

    def quit_app(icon, item):
        icon.stop()
        root.after(0, root.destroy)

    icon = pystray.Icon(
        "aws-env",
        create_icon_image(),
        "AWS Environment Tool",
        menu=pystray.Menu(
            pystray.MenuItem("Show/Hide", toggle_window, default=True),
            pystray.MenuItem("Exit", quit_app),
        ),
    )
    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()
    return icon


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )

    root = tk.Tk()
    app = MainWindow(root)
    tray_icon = setup_tray(root)

    def on_close():
        if tray_icon:
            tray_icon.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
