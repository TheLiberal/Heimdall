import io
import sys
from typing import Any, Callable, Optional

import pyperclip
import pytesseract
from PIL import Image
from pynput import keyboard
from PyQt5 import QtCore, QtGui, QtWidgets

# If needed, specify path to tesseract executable
# pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"


class ScreenshotOverlay(QtWidgets.QWidget):
    selectionComplete = QtCore.pyqtSignal(QtCore.QRect)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowState(QtCore.Qt.WindowFullScreen)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        # Semi-transparent overlay color
        self.overlay_color = QtGui.QColor(0, 0, 0, 128)
        self.start_point = None
        self.end_point = None
        self.rubber_band = QtWidgets.QRubberBand(
            QtWidgets.QRubberBand.Rectangle, self
        )

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self.overlay_color)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.start_point = event.pos()
            self.rubber_band.setGeometry(
                QtCore.QRect(self.start_point, QtCore.QSize())
            )
            self.rubber_band.show()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.start_point is not None:
            rect = QtCore.QRect(self.start_point, event.pos()).normalized()
            self.rubber_band.setGeometry(rect)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.end_point = event.pos()
            self.rubber_band.hide()
            rect = QtCore.QRect(self.start_point, self.end_point).normalized()
            self.selectionComplete.emit(rect)
            self.close()


class MainApp(QtWidgets.QApplication):
    def __init__(self, args: list[str]) -> None:
        super().__init__(args)
        self.overlay: Optional[ScreenshotOverlay] = None

    def start_overlay(self) -> None:
        # If already visible, don't open again
        if self.overlay and self.overlay.isVisible():
            return
        self.overlay = ScreenshotOverlay()
        self.overlay.selectionComplete.connect(self.handle_selection)
        self.overlay.show()

    def handle_selection(self, rect: QtCore.QRect) -> None:
        try:
            # Grab the screenshot of the entire desktop
            screen = self.primaryScreen()
            screenshot = screen.grabWindow(0)
            selected_pixmap = screenshot.copy(rect)

            # Convert QPixmap to PIL Image
            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.WriteOnly)
            selected_pixmap.save(buffer, "PNG")
            pil_image = Image.open(io.BytesIO(buffer.data()))

            # Perform OCR using Tesseract
            text = pytesseract.image_to_string(pil_image)

            # Copy extracted text to clipboard
            pyperclip.copy(text.strip())
            print("Extracted text copied to clipboard:", text.strip())
        except pytesseract.TesseractError as e:
            print(f"OCR Error: {e}")
        except Exception as e:
            print(f"Error processing screenshot: {e}")


def for_canonical(f: Callable) -> Callable:
    def wrapper(*args: Any) -> Any:
        return f(*args)
    return wrapper


def create_app() -> MainApp:
    return MainApp(sys.argv)


if __name__ == "__main__":
    app = create_app()

    def on_activate() -> None:
        # Trigger the overlay when the hotkey is pressed
        app.start_overlay()

    # Set up global hotkey: Shift+Alt+4
    # Using pynput to detect hotkey
    hotkey = keyboard.HotKey(
        keyboard.HotKey.parse("<shift>+<alt>+s"),
        on_activate
    )

    def on_press(key: Any) -> None:
        print(f"Key pressed: {key}", flush=True)

        try:
            hotkey.press(key)
        except AttributeError as e:
            print(f"Invalid key pressed: {e}")
        except Exception as e:
            print(f"Error handling key press: {e}")

    def on_release(key: Any) -> None:
        print(f"Key released: {key}", flush=True)

        try:
            hotkey.release(key)
        except AttributeError as e:
            print(f"Invalid key released: {e}")
        except Exception as e:
            print(f"Error handling key release: {e}")

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    sys.exit(app.exec_())
