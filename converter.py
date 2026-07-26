import sys
import os
import io
import json
import logging
import ctypes
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QComboBox, QHBoxLayout,
    QMessageBox, QTabWidget, QMainWindow, QAction, QDialog, QProgressBar, QGraphicsDropShadowEffect, QFrame,
    QStyledItemDelegate
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import fitz  # PyMuPDF
from PIL import Image, ImageDraw


def get_app_data_dir():
    """Ayar ve log dosyaları için kullanıcıya özel, her zaman yazılabilir bir klasör döndürür."""
    base = os.getenv('APPDATA') or os.path.expanduser('~')
    app_dir = os.path.join(base, 'MN PDF Converter')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


def ensure_arrow_icons():
    dark_path = os.path.join(get_app_data_dir(), 'arrow_dark.png')
    light_path = os.path.join(get_app_data_dir(), 'arrow_light.png')
    try:
        img_dark = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw_dark = ImageDraw.Draw(img_dark)
        draw_dark.line([(8, 12), (16, 20), (24, 12)], fill='#94a3b8', width=4)
        img_dark.save(dark_path)

        img_light = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw_light = ImageDraw.Draw(img_light)
        draw_light.line([(8, 12), (16, 20), (24, 12)], fill='#64748b', width=4)
        img_light.save(light_path)
    except Exception as e:
        logging.warning(f"Arrow icons could not be generated: {e}")

    return dark_path.replace('\\', '/'), light_path.replace('\\', '/')


DARK_ARROW_PATH, LIGHT_ARROW_PATH = ensure_arrow_icons()


def resource_path(relative_path):
    """PyInstaller ile paketlendiğinde geçici çıkarma klasörünü, geliştirme ortamında script klasörünü döndürür."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def set_dark_title_bar(window, dark=True):
    """Windows DWM API ile pencere başlık çubuğunun rengini koyu/açık temaya göre ayarlar."""
    if sys.platform == "win32":
        try:
            hwnd = int(window.winId())
            value = ctypes.c_int(1 if dark else 0)
            dwm = ctypes.windll.dwmapi
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Win11 / Win10 20H1+)
            res = dwm.DwmSetWindowAttribute(
                hwnd,
                20,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
            if res != 0:
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 19 (Önceki Win10 sürümleri)
                dwm.DwmSetWindowAttribute(
                    hwnd,
                    19,
                    ctypes.byref(value),
                    ctypes.sizeof(value)
                )
        except Exception as e:
            logging.debug(f"Title bar theme could not be set: {e}")


# Log dosyası her açılışta silinmesin diye 1 MB'a ulaşınca döndürülüyor,
# son 3 dosya saklanıyor; böylece önceki çalıştırmaların logu kaybolmuyor.
_log_handler = RotatingFileHandler(
    os.path.join(get_app_data_dir(), 'app.log'),
    maxBytes=1_000_000,
    backupCount=3,
    encoding='utf-8'
)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[_log_handler],
    force=True
)

# Ayar dosyası (dil + tema)
SETTINGS_FILE = os.path.join(get_app_data_dir(), 'settings.json')

# Varsayılan dil İngilizce
DEFAULT_LANGUAGE = 'en'

# Varsayılan tema koyu
DEFAULT_THEME = 'dark'

# Büyük PDF'leri tek görselde birleştirirken kullanıcıyı uyarmak için sayfa eşiği
LARGE_MERGE_PAGE_THRESHOLD = 150

# JPEG formatının kesin piksel sınırı (libjpeg); aşılırsa "broken data stream when
# writing image file" hatasıyla kayıt başarısız olur, bu yüzden PNG'ye düşülür.
JPEG_MAX_DIMENSION = 65500

# Uygulama adı marka olduğu için dile göre çevrilmiyor.
APP_NAME = "PDFlip"
APP_VERSION = "1.1"

THEMES = {
    'dark': f"""
        QMainWindow, QWidget {{ background-color: #141517; color: #f2f3f5; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; font-size: 13px; }}
        QLabel {{ color: #f2f3f5; font-size: 13px; }}
        QTabWidget::pane {{ border: 1px solid #31353c; background-color: #222429; border-radius: 8px; }}
        QTabBar::tab {{ background-color: #1a1c1f; color: #9aa0a6; padding: 8px 20px; font-weight: 600; min-width: 130px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }}
        QTabBar::tab:selected {{ background-color: #222429; color: #ffffff; border-top: 2px solid #3b82f6; }}
        QTabBar::tab:hover:!selected {{ background-color: #1f2125; color: #f2f3f5; }}
        QMenuBar {{ background-color: #141517; color: #f2f3f5; font-size: 13px; }}
        QMenuBar::item {{ padding: 6px 10px; border-radius: 4px; }}
        QMenuBar::item:selected {{ background-color: #222429; }}
        QMenu {{ background-color: #222429; color: #f2f3f5; border: 1px solid #31353c; border-radius: 8px; padding: 4px; }}
        QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 4px; }}
        QMenu::item:selected {{ background-color: #2d3037; color: #ffffff; }}
        QDialog {{ background-color: #1c1e22; color: #f2f3f5; }}
        QDialog QLabel {{ background-color: transparent; }}
        QProgressBar {{ background-color: #1c1e22; color: #f2f3f5; border: 1px solid #31353c; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold; }}
        QProgressBar::chunk {{ background-color: #22c55e; border-radius: 6px; }}

        /* General Buttons */
        QPushButton {{
            background-color: #2d3037;
            color: #f2f3f5;
            border: 1px solid #3d414a;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            min-height: 28px;
        }}
        QPushButton:hover {{
            background-color: #353942;
            border-color: #60a5fa;
            color: #ffffff;
        }}
        QPushButton:pressed {{
            background-color: #3e434d;
        }}
        QPushButton:disabled {{
            background-color: #18191c;
            color: #64748b;
            border-color: #27292e;
        }}

        /* Settings Save / Primary Button */
        QPushButton#saveSettingsButton {{
            background-color: #2563eb;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 14px;
            font-weight: bold;
            min-height: 32px;
        }}
        QPushButton#saveSettingsButton:hover {{
            background-color: #3b82f6;
        }}
        QPushButton#saveSettingsButton:pressed {{
            background-color: #1d4ed8;
        }}

        /* QComboBox styling */
        QComboBox {{
            background-color: #2d3037;
            color: #f2f3f5;
            border: 1px solid #3d414a;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 14px;
            font-weight: 500;
            min-height: 32px;
        }}
        QComboBox:hover {{
            border: 1px solid #60a5fa;
        }}
        QComboBox:focus {{
            border: 1px solid #3b82f6;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: url("{DARK_ARROW_PATH}");
            width: 14px;
            height: 14px;
            margin-right: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #222429;
            color: #f2f3f5;
            border: 1px solid #31353c;
            selection-background-color: #2d3037;
            selection-color: #ffffff;
            outline: none;
            padding: 8px;
            border-radius: 8px;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 56px;
            padding: 16px 20px;
            border-radius: 6px;
            font-size: 15px;
            font-weight: 500;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #2d3037;
            color: #ffffff;
        }}
    """,
    'light': f"""
        QMainWindow, QWidget {{ background-color: #f8fafc; color: #0f172a; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; font-size: 13px; }}
        QLabel {{ color: #0f172a; font-size: 13px; }}
        QTabWidget::pane {{ border: 1px solid #e2e8f0; background-color: #ffffff; border-radius: 8px; }}
        QTabBar::tab {{ background-color: #f1f5f9; color: #64748b; padding: 8px 20px; font-weight: 600; min-width: 130px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }}
        QTabBar::tab:selected {{ background-color: #ffffff; color: #2563eb; border-bottom: 2px solid #2563eb; }}
        QTabBar::tab:hover:!selected {{ background-color: #e2e8f0; color: #0f172a; }}
        QMenuBar {{ background-color: #f8fafc; color: #0f172a; font-size: 13px; }}
        QMenuBar::item {{ padding: 6px 10px; border-radius: 4px; }}
        QMenuBar::item:selected {{ background-color: #e2e8f0; }}
        QMenu {{ background-color: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; }}
        QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 4px; }}
        QMenu::item:selected {{ background-color: #eff6ff; color: #2563eb; }}
        QDialog {{ background-color: #ffffff; color: #0f172a; }}
        QDialog QLabel {{ background-color: transparent; }}
        QProgressBar {{ background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold; }}
        QProgressBar::chunk {{ background-color: #16a34a; border-radius: 6px; }}

        /* General Buttons */
        QPushButton {{
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            min-height: 28px;
        }}
        QPushButton:hover {{
            background-color: #f1f5f9;
            border-color: #2563eb;
            color: #2563eb;
        }}
        QPushButton:pressed {{
            background-color: #e2e8f0;
        }}
        QPushButton:disabled {{
            background-color: #f1f5f9;
            color: #94a3b8;
            border-color: #e2e8f0;
        }}

        /* Settings Save / Primary Button */
        QPushButton#saveSettingsButton {{
            background-color: #2563eb;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 14px;
            font-weight: bold;
            min-height: 32px;
        }}
        QPushButton#saveSettingsButton:hover {{
            background-color: #1d4ed8;
        }}
        QPushButton#saveSettingsButton:pressed {{
            background-color: #1e40af;
        }}

        /* QComboBox styling */
        QComboBox {{
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 14px;
            font-weight: 500;
            min-height: 32px;
        }}
        QComboBox:hover {{
            border: 1px solid #2563eb;
        }}
        QComboBox:focus {{
            border: 1px solid #2563eb;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: url("{LIGHT_ARROW_PATH}");
            width: 14px;
            height: 14px;
            margin-right: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            selection-background-color: #eff6ff;
            selection-color: #2563eb;
            outline: none;
            padding: 8px;
            border-radius: 8px;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 56px;
            padding: 16px 20px;
            border-radius: 6px;
            font-size: 15px;
            font-weight: 500;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #eff6ff;
            color: #2563eb;
        }}
    """,
}

# QSS renkleri normal metin için kullanılıyor; zengin metin (About penceresindeki) linkler
# ise kendi renklerini HTML içinde taşıdığından temaya göre ayrıca uyarlanıyor.
LINK_COLORS = {
    'dark': '#8ab4f8',
    'light': '#1a73e8',
}


def format_size(num_bytes):
    size = float(num_bytes)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return f"{size:.0f} {unit}" if unit == 'B' else f"{size:.1f} {unit}"
        size /= 1024


def unique_path(path):
    """Aynı isimde bir dosya zaten varsa üzerine yazmak yerine ' (2)', ' (3)' ... ekleyerek
    benzersiz bir yol döndürür."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 2
    while True:
        candidate = f"{base} ({counter}){ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1

# Dil metinleri
translations = {
    'en': {
        'tab1': 'PDF to Image',
        'tab2': 'Image to PDF',
        'select_pdf': 'Select PDF',
        'select_output_folder': 'Select Output Folder',
        'convert_to_image': 'Convert to image',
        'merge_vertically': 'Convert to image & Merge Vertically',
        'merge_horizontally': 'Convert to image & Merge Horizontally',
        'start_conversion': 'Start Conversion',
        'select_images': 'Select Images',
        'image_file_filter': 'Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)',
        'convert_to_pdf': 'Convert to PDF',
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'conversion_successful': 'Conversion successful!',
        'format_changed_to_png_note': '(saved as PNG -- the merged image was too large for JPEG)',
        'conversion_failed': 'Conversion failed: ',
        'select_pdf_file_error': 'Please select a PDF file.',
        'select_output_folder_error': 'Please select an output folder.',
        'select_image_folder_error': 'Please select one or more images.',
        'no_images_found_error': 'No images found in the selected folder.',
        'pdf_created_success': 'PDF created successfully: ',
        'selected_images_prefix': 'Selected Image: ',
        'images_selected_count': 'images selected',
        'large_merge_warning_message': 'You are about to merge {count} pages into a single image. This may use a large amount of memory and could fail. Do you want to continue?',
        'password_protected_error': 'This PDF is password protected. Please remove the password and try again.',
        'selected_pdf_prefix': 'Selected PDF: ',
        'output_folder_prefix': 'Output Folder: ',
        'selected_folder_prefix': 'Selected Folder: ',
        'save': 'Save',
        'open_folder': 'Open Folder',
        'tab3': 'Compress PDF',
        'tab4': 'Extract Images',
        'select_pdf_to_compress': 'Select PDF to Compress',
        'select_pdf_to_extract': 'Select PDF',
        'compression_level': 'Compression Level',
        'compression_extreme': 'Extreme (Smallest Size)',
        'compression_basic': 'Basic (Low Quality)',
        'compression_balanced': 'Balanced (Standard)',
        'compression_high': 'High Quality (Optimized)',
        'start_compression': 'Compress PDF',
        'start_extraction': 'Extract Images',
        'compression_successful': 'PDF compressed: {before} → {after} ({percent}% smaller)',
        'images_extracted_success': 'Extracted {count} image(s) to: ',
        'no_embedded_images_error': 'No embedded images were found in this PDF.',
        'menu_settings': 'Settings',
        'menu_about': 'About',
        'about_message': (
            '<b>Creator:</b> Mehmet Nevresoğlu<br>'
            '<b>Contact:</b> <a href="mailto:mehmet@nevresoglu.net" style="color:{link_color};">mehmet@nevresoglu.net</a><br>'
            '<b>LinkedIn:</b> <a href="https://www.linkedin.com/in/mehmet-nevresoglu-bb44341a/" style="color:{link_color};">Click here</a><br><br>'
            'You can use this program anywhere as long as you cite it as a reference. No license required.'
        ),
        'settings_language': 'Language',
        'language_english': 'English',
        'language_turkish': 'Türkçe',
        'settings_theme': 'Theme',
        'theme_dark': 'Dark',
        'theme_light': 'Light'
    },
    'tr': {
        'tab1': 'PDF\'den Görsele',
        'tab2': 'Görselden PDF\'ye',
        'select_pdf': 'PDF Seç',
        'select_output_folder': 'Çıktı Klasörünü Seç',
        'convert_to_image': 'Görüntüye dönüştür',
        'merge_vertically': 'Görüntüye dönüştür ve Dikey Birleştir',
        'merge_horizontally': 'Görüntüye dönüştür ve Yatay Birleştir',
        'start_conversion': 'Dönüştürmeyi Başlat',
        'select_images': 'Resimleri Seç',
        'image_file_filter': 'Görseller (*.png *.jpg *.jpeg *.bmp *.webp);;Tüm Dosyalar (*)',
        'convert_to_pdf': 'PDF\'ye Dönüştür',
        'success': 'Başarılı',
        'error': 'Hata',
        'warning': 'Uyarı',
        'conversion_successful': 'Dönüştürme başarılı!',
        'format_changed_to_png_note': '(PNG olarak kaydedildi -- birleştirilen görsel JPEG için çok büyüktü)',
        'conversion_failed': 'Dönüştürme başarısız: ',
        'select_pdf_file_error': 'Lütfen bir PDF dosyası seçin.',
        'select_output_folder_error': 'Lütfen bir çıktı klasörü seçin.',
        'select_image_folder_error': 'Lütfen en az bir resim seçin.',
        'no_images_found_error': 'Seçilen klasörde resim bulunamadı.',
        'pdf_created_success': 'PDF başarıyla oluşturuldu: ',
        'selected_images_prefix': 'Seçilen Resim: ',
        'images_selected_count': 'resim seçildi',
        'large_merge_warning_message': '{count} sayfayı tek bir görselde birleştirmek üzeresiniz. Bu işlem çok fazla bellek kullanabilir ve başarısız olabilir. Devam etmek istiyor musunuz?',
        'password_protected_error': 'Bu PDF parola korumalı. Lütfen parolayı kaldırıp tekrar deneyin.',
        'selected_pdf_prefix': 'Seçilen PDF: ',
        'output_folder_prefix': 'Çıktı Klasörü: ',
        'selected_folder_prefix': 'Seçilen Klasör: ',
        'save': 'Kaydet',
        'open_folder': 'Klasörü Aç',
        'tab3': 'PDF Sıkıştır',
        'tab4': 'Resimleri Çıkar',
        'select_pdf_to_compress': 'Sıkıştırılacak PDF Seç',
        'select_pdf_to_extract': 'PDF Seç',
        'compression_level': 'Sıkıştırma Seviyesi',
        'compression_extreme': 'Aşırı (En Küçük Boyut)',
        'compression_basic': 'Temel (Düşük Kalite)',
        'compression_balanced': 'Dengeli (Standart)',
        'compression_high': 'Yüksek Kalite (Optimize)',
        'start_compression': 'PDF\'yi Sıkıştır',
        'start_extraction': 'Resimleri Çıkar',
        'compression_successful': 'PDF sıkıştırıldı: {before} → {after} (%{percent} küçüldü)',
        'images_extracted_success': '{count} resim çıkarıldı: ',
        'no_embedded_images_error': 'Bu PDF içinde gömülü resim bulunamadı.',
        'menu_settings': 'Ayarlar',
        'menu_about': 'Hakkında',
        'about_message': (
            '<b>Geliştirici:</b> Mehmet Nevresoğlu<br>'
            '<b>İletişim:</b> <a href="mailto:mehmet@nevresoglu.net" style="color:{link_color};">mehmet@nevresoglu.net</a><br>'
            '<b>LinkedIn:</b> <a href="https://www.linkedin.com/in/mehmet-nevresoglu-bb44341a/" style="color:{link_color};">Buraya tıklayın</a><br><br>'
            'Bu programı kaynak belirttiğiniz sürece her yerde kullanabilirsiniz. Lisans gerektirmez.'
        ),
        'settings_language': 'Dil',
        'language_english': 'İngilizce',
        'language_turkish': 'Türkçe',
        'settings_theme': 'Tema',
        'theme_dark': 'Koyu',
        'theme_light': 'Açık'
    }
}


class ToastNotification(QFrame):
    """Sıkıntısız, OK butonuna tıklama gerektirmeyen, pencerenin ortasında beliren toast bildirimi."""
    def __init__(self, parent, message, folder_to_open=None, open_folder_text='', duration=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #22c55e;
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 14, 14)
        layout.setSpacing(16)

        label = QLabel(f"✔  {message}")
        label.setWordWrap(True)
        label.setStyleSheet("background: transparent; border: none; color: #4ade80; font-weight: bold; font-size: 13px;")
        layout.addWidget(label, 1)

        if folder_to_open:
            open_btn = QPushButton(open_folder_text)
            open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.setStyleSheet("""
                QPushButton { background-color: #22c55e; color: #0f172a; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold; }
                QPushButton:hover { background-color: #4ade80; }
            """)
            open_btn.clicked.connect(lambda: self._open_folder(folder_to_open))
            layout.addWidget(open_btn)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self.adjustSize()
        max_w = max(240, parent.width() - 60)
        if self.width() > max_w:
            self.setFixedWidth(max_w)
            self.adjustSize()

        parent_rect = parent.rect()
        x = (parent_rect.width() - self.width()) // 2
        y = (parent_rect.height() - self.height()) // 2
        self.move(x, y)
        self.show()
        self.raise_()

        if duration is None:
            duration = 5500 if folder_to_open else 3800
        QTimer.singleShot(duration, self.close)

    def _open_folder(self, path):
        try:
            os.startfile(path)
        except OSError as e:
            logging.warning(f"Could not open folder {path}: {e}")


def load_settings_file():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as file:
                data = json.load(file)
                language = data.get('language', DEFAULT_LANGUAGE)
                theme = data.get('theme', DEFAULT_THEME)
                last_output_dir = data.get('last_output_dir', '')
                last_input_dir = data.get('last_input_dir', '')
                valid_output_dir = last_output_dir if last_output_dir and os.path.isdir(last_output_dir) else ''
                valid_input_dir = last_input_dir if last_input_dir and os.path.isdir(last_input_dir) else ''
                return (
                    language if language in translations else DEFAULT_LANGUAGE,
                    theme if theme in THEMES else DEFAULT_THEME,
                    valid_output_dir,
                    valid_input_dir
                )
        except (json.JSONDecodeError, OSError):
            logging.warning("settings.json could not be read, falling back to defaults")
    return DEFAULT_LANGUAGE, DEFAULT_THEME, '', ''


def save_settings_file(language, theme, last_output_dir='', last_input_dir=''):
    data = {
        'language': language,
        'theme': theme,
        'last_output_dir': last_output_dir,
        'last_input_dir': last_input_dir,
    }
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(data, file)


class PdfToImageWorker(QThread):
    """PDF sayfalarını görsele çeviren işi arayüz thread'inin dışında yürütür."""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, pdf_path, save_path, combine_mode, file_type):
        super().__init__()
        self.pdf_path = pdf_path
        self.save_path = save_path
        self.combine_mode = combine_mode  # 'single', 'vertical' or 'horizontal'
        self.file_type = file_type

    def _extract_all_pages(self, doc, mat, page_count):
        images = []
        for i in range(page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
            self.progress.emit(i + 1, page_count)
            logging.debug(f"Image extracted from page {i}")
        return images

    def _save_combined_image(self, combined_image, base_name):
        """JPEG'in 65500px'lik kesin sınırını aşan birleştirilmiş görselleri PNG'ye
        düşürerek kaydeder; aksi halde Pillow "broken data stream when writing
        image file" hatasıyla kayda hiç başlamadan çöker."""
        file_type = self.file_type
        if file_type == 'jpg' and max(combined_image.size) > JPEG_MAX_DIMENSION:
            file_type = 'png'
            logging.warning(
                f"Combined image {combined_image.size} exceeds JPEG's {JPEG_MAX_DIMENSION}px limit, saving as PNG instead"
            )
        combined_image.save(os.path.join(self.save_path, f"{base_name}.{file_type}"))
        return file_type != self.file_type

    def run(self):
        doc = None
        try:
            doc = fitz.open(self.pdf_path)
            if doc.needs_pass:
                raise ValueError("PDF_PASSWORD_PROTECTED")

            page_count = len(doc)
            zoom = 3  # 3x zoom, resulting in 216 DPI
            mat = fitz.Matrix(zoom, zoom)
            format_changed = False

            if self.combine_mode == 'vertical' and page_count > 1:
                images = self._extract_all_pages(doc, mat, page_count)
                widths, heights = zip(*(img.size for img in images))
                combined_image = Image.new("RGB", (max(widths), sum(heights)))
                y_offset = 0
                for img in images:
                    combined_image.paste(img, (0, y_offset))
                    y_offset += img.height
                format_changed = self._save_combined_image(combined_image, "output_combined_vertical")
                logging.debug("Images merged vertically")
            elif self.combine_mode == 'horizontal' and page_count > 1:
                images = self._extract_all_pages(doc, mat, page_count)
                widths, heights = zip(*(img.size for img in images))
                combined_image = Image.new("RGB", (sum(widths), max(heights)))
                x_offset = 0
                for img in images:
                    combined_image.paste(img, (x_offset, 0))
                    x_offset += img.width
                format_changed = self._save_combined_image(combined_image, "output_combined_horizontal")
                logging.debug("Images merged horizontally")
            else:
                # Sayfaları listede biriktirmeden tek tek diske yazıyoruz;
                # böylece büyük PDF'lerde bellek kullanımı sabit kalır.
                for i in range(page_count):
                    page = doc.load_page(i)
                    pix = page.get_pixmap(matrix=mat)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img.save(os.path.join(self.save_path, f"output_page_{i + 1}.{self.file_type}"))
                    logging.debug(f"Image saved: output_page_{i + 1}.{self.file_type}")
                    self.progress.emit(i + 1, page_count)

            self.finished.emit(True, "FORMAT_CHANGED_TO_PNG" if format_changed else "")
            logging.info("Conversion successful")
        except Exception as e:
            logging.error(f"Conversion failed: {e}")
            self.finished.emit(False, str(e))
        finally:
            if doc is not None:
                doc.close()


class ImageToPdfWorker(QThread):
    """Görselleri PyMuPDF ile sayfa sayfa PDF'e yazar; tüm görselleri aynı anda bellekte tutmaz."""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, image_files, pdf_path):
        super().__init__()
        self.image_files = image_files
        self.pdf_path = pdf_path

    def run(self):
        doc = None
        try:
            total = len(self.image_files)
            doc = fitz.open()
            for idx, path in enumerate(self.image_files):
                with Image.open(path) as img:
                    width, height = img.size
                page = doc.new_page(width=width, height=height)
                page.insert_image(fitz.Rect(0, 0, width, height), filename=path)
                logging.debug(f"Image added to PDF: {path}")
                self.progress.emit(idx + 1, total)

            doc.save(self.pdf_path)
            self.finished.emit(True, "")
            logging.info(f"PDF created successfully: {self.pdf_path}")
        except Exception as e:
            logging.error(f"Conversion failed: {e}")
            self.finished.emit(False, str(e))
        finally:
            if doc is not None:
                doc.close()


class PdfCompressWorker(QThread):
    """Gömülü resimleri yeniden sıkıştırarak PDF boyutunu küçültür; metin/vektör içerik korunur."""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)

    QUALITY_PRESETS = {
        'extreme':  {'jpeg_quality': 25, 'max_dimension': 800},
        'basic':    {'jpeg_quality': 45, 'max_dimension': 1200},
        'balanced': {'jpeg_quality': 65, 'max_dimension': 1600},
        'high':     {'jpeg_quality': 85, 'max_dimension': 2400},
    }

    def __init__(self, pdf_path, save_path, level):
        super().__init__()
        self.pdf_path = pdf_path
        self.save_path = save_path
        self.level = level

    def _recompress_image(self, extracted, preset):
        pil_img = Image.open(io.BytesIO(extracted['image']))
        has_alpha = bool(extracted.get('smask')) or pil_img.mode in ('RGBA', 'LA') or (
            pil_img.mode == 'P' and 'transparency' in pil_img.info
        )

        width, height = pil_img.size
        max_dim = preset['max_dimension']
        if max(width, height) > max_dim:
            scale = max_dim / max(width, height)
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        if has_alpha:
            pil_img.convert('RGBA').save(buf, format='PNG', optimize=True)
        else:
            pil_img.convert('RGB').save(buf, format='JPEG', quality=preset['jpeg_quality'])
        return buf.getvalue()

    def run(self):
        doc = None
        try:
            original_size = os.path.getsize(self.pdf_path)
            doc = fitz.open(self.pdf_path)
            if doc.needs_pass:
                raise ValueError("PDF_PASSWORD_PROTECTED")

            preset = self.QUALITY_PRESETS[self.level]
            page_count = len(doc)
            seen_xrefs = set()

            for i in range(page_count):
                page = doc.load_page(i)
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    try:
                        extracted = doc.extract_image(xref)
                        new_bytes = self._recompress_image(extracted, preset)
                        # Zaten iyi sıkıştırılmış küçük görselleri büyütmemek için kontrol ediyoruz.
                        if len(new_bytes) < len(extracted['image']):
                            page.replace_image(xref, stream=new_bytes)
                    except Exception as image_error:
                        logging.warning(f"Skipping image xref {xref} during compression: {image_error}")
                self.progress.emit(i + 1, page_count)

            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            out_path = unique_path(os.path.join(self.save_path, f"{base_name}_compressed_{self.level}.pdf"))
            doc.save(out_path, garbage=4, deflate=True, clean=True)

            new_size = os.path.getsize(out_path)
            self.finished.emit(True, f"{original_size}|{new_size}")
            logging.info(f"PDF compressed: {original_size} -> {new_size} bytes")
        except Exception as e:
            logging.error(f"Compression failed: {e}")
            self.finished.emit(False, str(e))
        finally:
            if doc is not None:
                doc.close()


class ImageExtractWorker(QThread):
    """PDF içine gömülü resimleri orijinal bytes hâliyle (yeniden kodlamadan) diske yazar."""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, pdf_path, save_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.save_path = save_path

    def run(self):
        doc = None
        try:
            doc = fitz.open(self.pdf_path)
            if doc.needs_pass:
                raise ValueError("PDF_PASSWORD_PROTECTED")

            page_count = len(doc)
            seen_xrefs = set()
            extracted_count = 0

            for i in range(page_count):
                page = doc.load_page(i)
                for img_index, img_info in enumerate(page.get_images(full=True), start=1):
                    xref = img_info[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    extracted = doc.extract_image(xref)
                    out_name = f"page{i + 1}_image{img_index}.{extracted['ext']}"
                    with open(os.path.join(self.save_path, out_name), 'wb') as f:
                        f.write(extracted['image'])
                    extracted_count += 1
                    logging.debug(f"Extracted embedded image: {out_name}")
                self.progress.emit(i + 1, page_count)

            if extracted_count == 0:
                self.finished.emit(False, "NO_EMBEDDED_IMAGES")
            else:
                self.finished.emit(True, str(extracted_count))
                logging.info(f"Extracted {extracted_count} embedded image(s)")
        except Exception as e:
            logging.error(f"Image extraction failed: {e}")
            self.finished.emit(False, str(e))
        finally:
            if doc is not None:
                doc.close()


class ComboBoxItemDelegate(QStyledItemDelegate):
    """QComboBox açılır listesindeki öğeler için QSS'teki min-height/padding Qt'nin
    varsayılan delegate'i tarafından yok sayılıyor (satır yüksekliği stylesheet'ten değil
    font metriklerinden hesaplanıyor) -- bu yüzden yüksekliği burada elle zorluyoruz."""
    def __init__(self, parent=None, item_height=56):
        super().__init__(parent)
        self.item_height = item_height

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(self.item_height)
        return size


class DropdownComboBox(QComboBox):
    """Varsayılan QComboBox popup'ı, açılırken seçili öğeyi butonun üzerine hizalamaya
    çalışır -- bu da alta değil üstüne/kaymalı açılmasına yol açar. Burada popup'ı her
    zaman kutunun hemen altına, standart bir menü gibi zorluyoruz."""
    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        popup.move(self.mapToGlobal(self.rect().bottomLeft()))


class PDFToImageConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language, self.theme, self.last_output_dir, self.last_input_dir = load_settings_file()
        self.translations = translations[self.language]
        self.pdf_worker = None
        self.image_worker = None
        self.compress_worker = None
        self.extract_worker = None

        self.pdf_path = ''
        self.save_path = self.last_output_dir if self.last_output_dir else ''
        self.selected_image_files = []
        self.image_save_path = self.last_output_dir if self.last_output_dir else ''
        self.compress_pdf_path = ''
        self.compress_output_path = self.last_output_dir if self.last_output_dir else ''
        self.extract_pdf_path = ''
        self.extract_output_path = self.last_output_dir if self.last_output_dir else ''

        self.initUI()
        self.update_button_states()
        logging.debug("UI initialized")

    def apply_theme(self):
        QApplication.instance().setStyleSheet(THEMES[self.theme])
        set_dark_title_bar(self, dark=(self.theme == 'dark'))

    def initUI(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.apply_theme()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout()
        central_widget.setLayout(self.layout)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(15)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setElideMode(Qt.ElideNone)
        self.pdf_to_image_tab = QWidget()
        self.image_to_pdf_tab = QWidget()
        self.compress_pdf_tab = QWidget()
        self.extract_images_tab = QWidget()

        self.tabs.addTab(self.pdf_to_image_tab, self.translations['tab1'])
        self.tabs.addTab(self.image_to_pdf_tab, self.translations['tab2'])
        self.tabs.addTab(self.compress_pdf_tab, self.translations['tab3'])
        self.tabs.addTab(self.extract_images_tab, self.translations['tab4'])

        self.init_pdf_to_image_tab()
        self.init_image_to_pdf_tab()
        self.init_compress_pdf_tab()
        self.init_extract_images_tab()

        self.layout.addWidget(self.tabs)
        self.create_menu()

        # Set window icon
        self.setWindowIcon(QIcon(resource_path('icon.ico')))

        self.setMinimumSize(880, 520)
        self.resize(880, 520)

    def create_menu(self):
        self.menubar = self.menuBar()

        self.settings_action = QAction(self.translations['menu_settings'], self)
        self.settings_action.triggered.connect(self.show_settings)
        self.menubar.addAction(self.settings_action)

        self.about_action = QAction(self.translations['menu_about'], self)
        self.about_action.triggered.connect(self.show_about)
        self.menubar.addAction(self.about_action)

    def init_pdf_to_image_tab(self):
        font = QFont()
        font.setPointSize(12)

        self.pdf_to_image_layout = QVBoxLayout()
        self.pdf_to_image_layout.setAlignment(Qt.AlignTop)

        self.upload_btn = QPushButton(self.translations['select_pdf'], self)
        self.upload_btn.setFont(font)
        self.upload_btn.clicked.connect(self.upload_pdf)
        self.upload_btn.setStyleSheet("color: white; padding: 10px; background-color: #3b3b3b; border-radius: 5px;")
        self.pdf_to_image_layout.addWidget(self.upload_btn)

        self.pdf_label = QLabel('', self)
        self.pdf_label.setFont(QFont("", 12))  # Bilgi etiketlerinin fontu 12
        self.pdf_to_image_layout.addWidget(self.pdf_label)

        self.save_btn = QPushButton(self.translations['select_output_folder'], self)
        self.save_btn.setFont(font)
        self.save_btn.clicked.connect(self.save_location)
        self.save_btn.setStyleSheet("color: white; padding: 10px; background-color: #3b3b3b; border-radius: 5px;")
        self.pdf_to_image_layout.addWidget(self.save_btn)

        self.output_label = QLabel('', self)
        self.output_label.setFont(QFont("", 12))  # Bilgi etiketlerinin fontu 12
        self.pdf_to_image_layout.addWidget(self.output_label)

        self.combine_options = DropdownComboBox(self)
        self.combine_options.setFont(font)
        self.combine_options.setItemDelegate(ComboBoxItemDelegate(self.combine_options))
        self.combine_options.addItem(self.translations['convert_to_image'], 'single')
        self.combine_options.addItem(self.translations['merge_vertically'], 'vertical')
        self.combine_options.addItem(self.translations['merge_horizontally'], 'horizontal')
        self.combine_options.currentIndexChanged.connect(self.clear_status)
        self.pdf_to_image_layout.addWidget(self.combine_options)

        self.file_type_options = DropdownComboBox(self)
        self.file_type_options.setFont(font)
        self.file_type_options.setItemDelegate(ComboBoxItemDelegate(self.file_type_options))
        self.file_type_options.addItem("PNG")
        self.file_type_options.addItem("JPG")
        self.file_type_options.currentIndexChanged.connect(self.clear_status)
        self.pdf_to_image_layout.addWidget(self.file_type_options)

        self.process_btn = QPushButton(self.translations['start_conversion'], self)
        self.process_btn.setFont(font)
        self.process_btn.clicked.connect(self.process_pdf)
        self.process_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.pdf_to_image_layout.addWidget(self.process_btn)

        self.pdf_progress_bar = QProgressBar(self)
        self.pdf_progress_bar.setVisible(False)
        self.pdf_to_image_layout.addWidget(self.pdf_progress_bar)

        self.status_label = QLabel('', self)
        self.status_label.setFont(font)
        self.pdf_to_image_layout.addWidget(self.status_label)

        self.pdf_to_image_tab.setLayout(self.pdf_to_image_layout)

    def init_image_to_pdf_tab(self):
        font = QFont()
        font.setPointSize(12)

        self.image_to_pdf_layout = QVBoxLayout()
        self.image_to_pdf_layout.setAlignment(Qt.AlignTop)

        self.select_images_btn = QPushButton(self.translations['select_images'], self)
        self.select_images_btn.setFont(font)
        self.select_images_btn.clicked.connect(self.select_images)
        self.select_images_btn.setStyleSheet("color: white; padding: 10px; background-color: #ff6961; border-radius: 5px;")
        self.image_to_pdf_layout.addWidget(self.select_images_btn)

        self.images_label = QLabel('', self)
        self.images_label.setFont(QFont("", 12))  # Bilgi etiketlerinin fontu 12
        self.image_to_pdf_layout.addWidget(self.images_label)

        self.image_output_btn = QPushButton(self.translations['select_output_folder'], self)
        self.image_output_btn.setFont(font)
        self.image_output_btn.clicked.connect(self.select_image_output_folder)
        self.image_output_btn.setStyleSheet("color: white; padding: 10px; background-color: #3b3b3b; border-radius: 5px;")
        self.image_to_pdf_layout.addWidget(self.image_output_btn)

        self.image_output_label = QLabel('', self)
        self.image_output_label.setFont(QFont("", 12))
        self.image_to_pdf_layout.addWidget(self.image_output_label)

        self.convert_images_btn = QPushButton(self.translations['convert_to_pdf'], self)
        self.convert_images_btn.setFont(font)
        self.convert_images_btn.clicked.connect(self.convert_images_to_pdf)
        self.convert_images_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.image_to_pdf_layout.addWidget(self.convert_images_btn)

        self.image_progress_bar = QProgressBar(self)
        self.image_progress_bar.setVisible(False)
        self.image_to_pdf_layout.addWidget(self.image_progress_bar)

        self.image_to_pdf_status_label = QLabel('', self)
        self.image_to_pdf_status_label.setFont(font)
        self.image_to_pdf_layout.addWidget(self.image_to_pdf_status_label)

        self.image_to_pdf_tab.setLayout(self.image_to_pdf_layout)

    def init_compress_pdf_tab(self):
        font = QFont()
        font.setPointSize(12)

        self.compress_layout = QVBoxLayout()
        self.compress_layout.setAlignment(Qt.AlignTop)

        self.compress_select_btn = QPushButton(self.translations['select_pdf_to_compress'], self)
        self.compress_select_btn.setFont(font)
        self.compress_select_btn.clicked.connect(self.select_compress_pdf)
        self.compress_select_btn.setStyleSheet("color: white; padding: 10px; background-color: #3b3b3b; border-radius: 5px;")
        self.compress_layout.addWidget(self.compress_select_btn)

        self.compress_pdf_label = QLabel('', self)
        self.compress_pdf_label.setFont(QFont("", 12))
        self.compress_layout.addWidget(self.compress_pdf_label)

        self.compress_output_btn = QPushButton(self.translations['select_output_folder'], self)
        self.compress_output_btn.setFont(font)
        self.compress_output_btn.clicked.connect(self.select_compress_output)
        self.compress_output_btn.setStyleSheet("color: white; padding: 10px; background-color: #3b3b3b; border-radius: 5px;")
        self.compress_layout.addWidget(self.compress_output_btn)

        self.compress_output_label = QLabel('', self)
        self.compress_output_label.setFont(QFont("", 12))
        self.compress_layout.addWidget(self.compress_output_label)

        self.compression_level_options = DropdownComboBox(self)
        self.compression_level_options.setFont(font)
        self.compression_level_options.setItemDelegate(ComboBoxItemDelegate(self.compression_level_options))
        self.compression_level_options.addItem(self.translations['compression_extreme'], 'extreme')
        self.compression_level_options.addItem(self.translations['compression_basic'], 'basic')
        self.compression_level_options.addItem(self.translations['compression_balanced'], 'balanced')
        self.compression_level_options.addItem(self.translations['compression_high'], 'high')
        self.compression_level_options.setCurrentIndex(2)  # Dengeli (Standart) varsayılan
        self.compression_level_options.currentIndexChanged.connect(self.clear_compress_status)
        self.compress_layout.addWidget(self.compression_level_options)

        self.compress_start_btn = QPushButton(self.translations['start_compression'], self)
        self.compress_start_btn.setFont(font)
        self.compress_start_btn.clicked.connect(self.process_compress_pdf)
        self.compress_start_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.compress_layout.addWidget(self.compress_start_btn)

        self.compress_progress_bar = QProgressBar(self)
        self.compress_progress_bar.setVisible(False)
        self.compress_layout.addWidget(self.compress_progress_bar)

        self.compress_status_label = QLabel('', self)
        self.compress_status_label.setFont(font)
        self.compress_layout.addWidget(self.compress_status_label)

        self.compress_pdf_tab.setLayout(self.compress_layout)

    def init_extract_images_tab(self):
        font = QFont()
        font.setPointSize(12)

        self.extract_layout = QVBoxLayout()
        self.extract_layout.setAlignment(Qt.AlignTop)

        self.extract_select_btn = QPushButton(self.translations['select_pdf_to_extract'], self)
        self.extract_select_btn.setFont(font)
        self.extract_select_btn.clicked.connect(self.select_extract_pdf)
        self.extract_select_btn.setStyleSheet("color: white; padding: 10px; background-color: #3b3b3b; border-radius: 5px;")
        self.extract_layout.addWidget(self.extract_select_btn)

        self.extract_pdf_label = QLabel('', self)
        self.extract_pdf_label.setFont(QFont("", 12))
        self.extract_layout.addWidget(self.extract_pdf_label)

        self.extract_output_btn = QPushButton(self.translations['select_output_folder'], self)
        self.extract_output_btn.setFont(font)
        self.extract_output_btn.clicked.connect(self.select_extract_output)
        self.extract_output_btn.setStyleSheet("color: white; padding: 10px; background-color: #3b3b3b; border-radius: 5px;")
        self.extract_layout.addWidget(self.extract_output_btn)

        self.extract_output_label = QLabel('', self)
        self.extract_output_label.setFont(QFont("", 12))
        self.extract_layout.addWidget(self.extract_output_label)

        self.extract_start_btn = QPushButton(self.translations['start_extraction'], self)
        self.extract_start_btn.setFont(font)
        self.extract_start_btn.clicked.connect(self.process_extract_images)
        self.extract_start_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.extract_layout.addWidget(self.extract_start_btn)

        self.extract_progress_bar = QProgressBar(self)
        self.extract_progress_bar.setVisible(False)
        self.extract_layout.addWidget(self.extract_progress_bar)

        self.extract_status_label = QLabel('', self)
        self.extract_status_label.setFont(font)
        self.extract_layout.addWidget(self.extract_status_label)

        self.extract_images_tab.setLayout(self.extract_layout)

    def update_button_states(self):
        if self.pdf_path:
            self.upload_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
            self.pdf_label.setText(f"{self.translations['selected_pdf_prefix']}{self.pdf_path}")
        else:
            self.upload_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")
            self.pdf_label.setText("")

        if self.save_path:
            self.save_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
            self.output_label.setText(f"{self.translations['output_folder_prefix']}{self.save_path}")
        else:
            self.save_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")
            self.output_label.setText("")

        if self.selected_image_files:
            self.select_images_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
        else:
            self.select_images_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")

        if self.image_save_path:
            self.image_output_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
            self.image_output_label.setText(f"{self.translations['output_folder_prefix']}{self.image_save_path}")
        else:
            self.image_output_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")
            self.image_output_label.setText("")

        if self.compress_pdf_path:
            self.compress_select_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
            self.compress_pdf_label.setText(f"{self.translations['selected_pdf_prefix']}{self.compress_pdf_path}")
        else:
            self.compress_select_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")
            self.compress_pdf_label.setText("")

        if self.compress_output_path:
            self.compress_output_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
            self.compress_output_label.setText(f"{self.translations['output_folder_prefix']}{self.compress_output_path}")
        else:
            self.compress_output_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")
            self.compress_output_label.setText("")

        if self.extract_pdf_path:
            self.extract_select_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
            self.extract_pdf_label.setText(f"{self.translations['selected_pdf_prefix']}{self.extract_pdf_path}")
        else:
            self.extract_select_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")
            self.extract_pdf_label.setText("")

        if self.extract_output_path:
            self.extract_output_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
            self.extract_output_label.setText(f"{self.translations['output_folder_prefix']}{self.extract_output_path}")
        else:
            self.extract_output_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")
            self.extract_output_label.setText("")

    def clear_status(self):
        self.status_label.setText('')

    def upload_pdf(self):
        options = QFileDialog.Options()
        initial_dir = self.last_input_dir if (self.last_input_dir and os.path.isdir(self.last_input_dir)) else ""
        chosen, _ = QFileDialog.getOpenFileName(self, self.translations['select_pdf'], initial_dir, "PDF Files (*.pdf);;All Files (*)", options=options)
        if chosen:
            self.pdf_path = chosen
            self.last_input_dir = os.path.dirname(chosen)
            save_settings_file(self.language, self.theme, self.last_output_dir, self.last_input_dir)
            self.update_button_states()
            self.clear_status()
            logging.debug(f"PDF selected: {self.pdf_path}")

    def save_location(self):
        options = QFileDialog.Options()
        initial_dir = self.last_output_dir if (self.last_output_dir and os.path.isdir(self.last_output_dir)) else ""
        chosen = QFileDialog.getExistingDirectory(self, self.translations['select_output_folder'], initial_dir, options=options)
        if chosen:
            self.save_path = chosen
            self.last_output_dir = chosen
            save_settings_file(self.language, self.theme, self.last_output_dir, self.last_input_dir)
            self.update_button_states()
            self.clear_status()
            logging.debug(f"Output folder selected: {self.save_path}")

    def _set_pdf_controls_enabled(self, enabled):
        self.upload_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
        self.combine_options.setEnabled(enabled)
        self.file_type_options.setEnabled(enabled)
        self.process_btn.setEnabled(enabled)

    def process_pdf(self):
        if not self.pdf_path:
            self.show_message(self.translations['error'], self.translations['select_pdf_file_error'])
            logging.error("PDF file not selected")
            return

        if not self.save_path:
            self.show_message(self.translations['error'], self.translations['select_output_folder_error'])
            logging.error("Output folder not selected")
            return

        if self.pdf_worker is not None and self.pdf_worker.isRunning():
            return

        combine_mode = self.combine_options.currentData()
        file_type = self.file_type_options.currentText().lower()

        # Çok sayfalı PDF'leri tek görselde birleştirmek yüksek bellek kullanabileceğinden önceden uyarıyoruz.
        if combine_mode in ('vertical', 'horizontal'):
            page_count = None
            try:
                doc = fitz.open(self.pdf_path)
                try:
                    page_count = len(doc)
                finally:
                    doc.close()
            except Exception:
                page_count = None

            if page_count and page_count > LARGE_MERGE_PAGE_THRESHOLD:
                reply = QMessageBox.question(
                    self,
                    self.translations['warning'],
                    self.translations['large_merge_warning_message'].format(count=page_count),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

        self._set_pdf_controls_enabled(False)
        self.process_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border: 2px solid green; border-radius: 5px;")
        self.pdf_progress_bar.setVisible(True)
        self.pdf_progress_bar.setValue(0)
        self.status_label.setText('')

        self.pdf_worker = PdfToImageWorker(self.pdf_path, self.save_path, combine_mode, file_type)
        self.pdf_worker.progress.connect(self.on_pdf_progress)
        self.pdf_worker.finished.connect(self.on_pdf_conversion_finished)
        self.pdf_worker.start()

    def show_toast(self, message, folder_to_open=None):
        ToastNotification(self, message, folder_to_open=folder_to_open, open_folder_text=self.translations['open_folder'])

    def on_pdf_progress(self, current, total):
        self.pdf_progress_bar.setMaximum(total)
        self.pdf_progress_bar.setValue(current)
        self.status_label.setText(f"{current}/{total}")

    def on_pdf_conversion_finished(self, success, error_message):
        self._set_pdf_controls_enabled(True)
        self.process_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.pdf_progress_bar.setVisible(False)

        if success:
            message = self.translations['conversion_successful']
            if error_message == "FORMAT_CHANGED_TO_PNG":
                message += f" {self.translations['format_changed_to_png_note']}"
            self.show_toast(message, folder_to_open=self.save_path)
            self.reset_state()
        elif error_message == "PDF_PASSWORD_PROTECTED":
            self.show_message(self.translations['error'], self.translations['password_protected_error'])
        else:
            self.show_message(self.translations['error'], f"{self.translations['conversion_failed']}{error_message}")

        self.pdf_worker = None

    def select_images(self):
        options = QFileDialog.Options()
        initial_dir = self.last_input_dir if (self.last_input_dir and os.path.isdir(self.last_input_dir)) else ""
        files, _ = QFileDialog.getOpenFileNames(self, self.translations['select_images'], initial_dir, self.translations['image_file_filter'], options=options)
        if files:
            self.selected_image_files = files
            self.last_input_dir = os.path.dirname(files[0])
            if not self.image_save_path:
                self.image_save_path = self.last_input_dir
            save_settings_file(self.language, self.theme, self.last_output_dir, self.last_input_dir)
            self.update_button_states()
            if len(files) == 1:
                self.images_label.setText(f"{self.translations['selected_images_prefix']}{os.path.basename(files[0])}")
            else:
                self.images_label.setText(f"{len(files)} {self.translations['images_selected_count']}")
            logging.debug(f"{len(files)} image file(s) selected: {files}")

    def select_image_output_folder(self):
        options = QFileDialog.Options()
        initial_dir = self.image_save_path if (self.image_save_path and os.path.isdir(self.image_save_path)) else (
            self.last_output_dir if (self.last_output_dir and os.path.isdir(self.last_output_dir)) else ""
        )
        chosen = QFileDialog.getExistingDirectory(self, self.translations['select_output_folder'], initial_dir, options=options)
        if chosen:
            self.image_save_path = chosen
            self.last_output_dir = chosen
            save_settings_file(self.language, self.theme, self.last_output_dir, self.last_input_dir)
            self.update_button_states()
            logging.debug(f"Image to PDF output folder selected: {self.image_save_path}")

    def _set_image_controls_enabled(self, enabled):
        self.select_images_btn.setEnabled(enabled)
        self.image_output_btn.setEnabled(enabled)
        self.convert_images_btn.setEnabled(enabled)

    def convert_images_to_pdf(self):
        if not self.selected_image_files:
            self.show_message(self.translations['error'], self.translations['select_image_folder_error'])
            logging.error("No images selected")
            return

        if not self.image_save_path:
            self.show_message(self.translations['error'], self.translations['select_output_folder_error'])
            logging.error("Output folder not selected for Image to PDF")
            return

        if self.image_worker is not None and self.image_worker.isRunning():
            return

        # os.path.join uses a backslash on Windows even when image_save_path came from Qt's
        # dialog (which always uses forward slashes) -- normalize so the path shown in the
        # toast doesn't mix separators.
        pdf_path = unique_path(os.path.join(self.image_save_path, "output.pdf")).replace("\\", "/")

        self._set_image_controls_enabled(False)
        self.convert_images_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border: 2px solid green; border-radius: 5px;")
        self.image_progress_bar.setVisible(True)
        self.image_progress_bar.setValue(0)
        self.image_to_pdf_status_label.setText('')

        self.image_worker = ImageToPdfWorker(list(self.selected_image_files), pdf_path)
        self.image_worker.progress.connect(self.on_image_progress)
        self.image_worker.finished.connect(lambda success, error_message: self.on_image_conversion_finished(success, error_message, pdf_path))
        self.image_worker.start()

    def on_image_progress(self, current, total):
        self.image_progress_bar.setMaximum(total)
        self.image_progress_bar.setValue(current)
        self.image_to_pdf_status_label.setText(f"{current}/{total}")

    def on_image_conversion_finished(self, success, error_message, pdf_path):
        self._set_image_controls_enabled(True)
        self.convert_images_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.image_progress_bar.setVisible(False)

        if success:
            self.show_toast(f"{self.translations['pdf_created_success']}{pdf_path}", folder_to_open=self.image_save_path)
            self.reset_state()
        else:
            self.show_message(self.translations['error'], f"{self.translations['conversion_failed']}{error_message}")

        self.image_worker = None

    def select_compress_pdf(self):
        options = QFileDialog.Options()
        initial_dir = self.last_input_dir if (self.last_input_dir and os.path.isdir(self.last_input_dir)) else ""
        chosen, _ = QFileDialog.getOpenFileName(self, self.translations['select_pdf_to_compress'], initial_dir, "PDF Files (*.pdf);;All Files (*)", options=options)
        if chosen:
            self.compress_pdf_path = chosen
            self.last_input_dir = os.path.dirname(chosen)
            save_settings_file(self.language, self.theme, self.last_output_dir, self.last_input_dir)
            self.update_button_states()
            self.clear_compress_status()
            logging.debug(f"PDF selected for compression: {self.compress_pdf_path}")

    def select_compress_output(self):
        options = QFileDialog.Options()
        initial_dir = self.last_output_dir if (self.last_output_dir and os.path.isdir(self.last_output_dir)) else ""
        chosen = QFileDialog.getExistingDirectory(self, self.translations['select_output_folder'], initial_dir, options=options)
        if chosen:
            self.compress_output_path = chosen
            self.last_output_dir = chosen
            save_settings_file(self.language, self.theme, self.last_output_dir, self.last_input_dir)
            self.update_button_states()
            self.clear_compress_status()
            logging.debug(f"Output folder selected for compression: {self.compress_output_path}")

    def clear_compress_status(self):
        self.compress_status_label.setText('')

    def _set_compress_controls_enabled(self, enabled):
        self.compress_select_btn.setEnabled(enabled)
        self.compress_output_btn.setEnabled(enabled)
        self.compression_level_options.setEnabled(enabled)
        self.compress_start_btn.setEnabled(enabled)

    def process_compress_pdf(self):
        if not self.compress_pdf_path:
            self.show_message(self.translations['error'], self.translations['select_pdf_file_error'])
            logging.error("PDF file not selected for compression")
            return

        if not self.compress_output_path:
            self.show_message(self.translations['error'], self.translations['select_output_folder_error'])
            logging.error("Output folder not selected for compression")
            return

        if self.compress_worker is not None and self.compress_worker.isRunning():
            return

        level = self.compression_level_options.currentData()

        self._set_compress_controls_enabled(False)
        self.compress_start_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border: 2px solid green; border-radius: 5px;")
        self.compress_progress_bar.setVisible(True)
        self.compress_progress_bar.setValue(0)
        self.compress_status_label.setText('')

        self.compress_worker = PdfCompressWorker(self.compress_pdf_path, self.compress_output_path, level)
        self.compress_worker.progress.connect(self.on_compress_progress)
        self.compress_worker.finished.connect(self.on_compress_finished)
        self.compress_worker.start()

    def on_compress_progress(self, current, total):
        self.compress_progress_bar.setMaximum(total)
        self.compress_progress_bar.setValue(current)
        self.compress_status_label.setText(f"{current}/{total}")

    def on_compress_finished(self, success, payload):
        self._set_compress_controls_enabled(True)
        self.compress_start_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.compress_progress_bar.setVisible(False)

        if success:
            before_str, after_str = payload.split('|')
            before, after = int(before_str), int(after_str)
            percent = round((1 - after / before) * 100) if before else 0
            message = self.translations['compression_successful'].format(
                before=format_size(before), after=format_size(after), percent=percent
            )
            self.show_toast(message, folder_to_open=self.compress_output_path)
            self.reset_compress_state()
        elif payload == "PDF_PASSWORD_PROTECTED":
            self.show_message(self.translations['error'], self.translations['password_protected_error'])
        else:
            self.show_message(self.translations['error'], f"{self.translations['conversion_failed']}{payload}")

        self.compress_worker = None

    def reset_compress_state(self):
        self.compress_pdf_path = ""
        self.compress_output_path = self.last_output_dir if self.last_output_dir else ""
        self.update_button_states()
        self.compress_status_label.setText("")

    def select_extract_pdf(self):
        options = QFileDialog.Options()
        initial_dir = self.last_input_dir if (self.last_input_dir and os.path.isdir(self.last_input_dir)) else ""
        chosen, _ = QFileDialog.getOpenFileName(self, self.translations['select_pdf_to_extract'], initial_dir, "PDF Files (*.pdf);;All Files (*)", options=options)
        if chosen:
            self.extract_pdf_path = chosen
            self.last_input_dir = os.path.dirname(chosen)
            save_settings_file(self.language, self.theme, self.last_output_dir, self.last_input_dir)
            self.update_button_states()
            self.clear_extract_status()
            logging.debug(f"PDF selected for image extraction: {self.extract_pdf_path}")

    def select_extract_output(self):
        options = QFileDialog.Options()
        initial_dir = self.last_output_dir if (self.last_output_dir and os.path.isdir(self.last_output_dir)) else ""
        chosen = QFileDialog.getExistingDirectory(self, self.translations['select_output_folder'], initial_dir, options=options)
        if chosen:
            self.extract_output_path = chosen
            self.last_output_dir = chosen
            save_settings_file(self.language, self.theme, self.last_output_dir, self.last_input_dir)
            self.update_button_states()
            self.clear_extract_status()
            logging.debug(f"Output folder selected for image extraction: {self.extract_output_path}")

    def clear_extract_status(self):
        self.extract_status_label.setText('')

    def _set_extract_controls_enabled(self, enabled):
        self.extract_select_btn.setEnabled(enabled)
        self.extract_output_btn.setEnabled(enabled)
        self.extract_start_btn.setEnabled(enabled)

    def process_extract_images(self):
        if not self.extract_pdf_path:
            self.show_message(self.translations['error'], self.translations['select_pdf_file_error'])
            logging.error("PDF file not selected for image extraction")
            return

        if not self.extract_output_path:
            self.show_message(self.translations['error'], self.translations['select_output_folder_error'])
            logging.error("Output folder not selected for image extraction")
            return

        if self.extract_worker is not None and self.extract_worker.isRunning():
            return

        self._set_extract_controls_enabled(False)
        self.extract_start_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border: 2px solid green; border-radius: 5px;")
        self.extract_progress_bar.setVisible(True)
        self.extract_progress_bar.setValue(0)
        self.extract_status_label.setText('')

        self.extract_worker = ImageExtractWorker(self.extract_pdf_path, self.extract_output_path)
        self.extract_worker.progress.connect(self.on_extract_progress)
        self.extract_worker.finished.connect(self.on_extract_finished)
        self.extract_worker.start()

    def on_extract_progress(self, current, total):
        self.extract_progress_bar.setMaximum(total)
        self.extract_progress_bar.setValue(current)
        self.extract_status_label.setText(f"{current}/{total}")

    def on_extract_finished(self, success, payload):
        self._set_extract_controls_enabled(True)
        self.extract_start_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.extract_progress_bar.setVisible(False)

        if success:
            message = f"{self.translations['images_extracted_success'].format(count=payload)}{self.extract_output_path}"
            self.show_toast(message, folder_to_open=self.extract_output_path)
            self.reset_extract_state()
        elif payload == "PDF_PASSWORD_PROTECTED":
            self.show_message(self.translations['error'], self.translations['password_protected_error'])
        elif payload == "NO_EMBEDDED_IMAGES":
            self.show_message(self.translations['error'], self.translations['no_embedded_images_error'])
        else:
            self.show_message(self.translations['error'], f"{self.translations['conversion_failed']}{payload}")

        self.extract_worker = None

    def reset_extract_state(self):
        self.extract_pdf_path = ""
        self.extract_output_path = self.last_output_dir if self.last_output_dir else ""
        self.update_button_states()
        self.extract_status_label.setText("")

    def reset_state(self):
        self.pdf_path = ""
        self.save_path = self.last_output_dir if self.last_output_dir else ""
        self.selected_image_files = []
        self.image_save_path = self.last_output_dir if self.last_output_dir else ""
        self.update_button_states()
        self.pdf_label.setText("")
        self.images_label.setText("")
        self.status_label.setText("")
        self.image_to_pdf_status_label.setText("")

    def show_message(self, title, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def show_about(self):
        about_text = self.translations['about_message'].format(link_color=LINK_COLORS[self.theme])
        about_msg = QMessageBox(self)
        about_msg.setWindowTitle(self.translations['menu_about'])
        about_msg.setTextFormat(Qt.RichText)
        about_msg.setText(about_text)
        about_msg.exec_()

    def show_settings(self):
        settings_dialog = QDialog(self)
        settings_dialog.setWindowFlags(settings_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        settings_dialog.setWindowTitle(self.translations['menu_settings'])
        settings_dialog.setFixedWidth(360)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Language section
        lang_layout = QVBoxLayout()
        lang_layout.setSpacing(6)
        language_label = QLabel(self.translations['settings_language'])
        language_label.setStyleSheet("background: transparent; font-weight: 600; font-size: 13px; color: #94a3b8;" if self.theme == 'dark' else "background: transparent; font-weight: 600; font-size: 13px; color: #64748b;")

        language_combo = DropdownComboBox()
        language_combo.setItemDelegate(ComboBoxItemDelegate(language_combo))
        language_combo.addItem(self.translations['language_english'], 'en')
        language_combo.addItem(self.translations['language_turkish'], 'tr')
        language_combo.setCurrentIndex(0 if self.language == 'en' else 1)
        lang_layout.addWidget(language_label)
        lang_layout.addWidget(language_combo)
        layout.addLayout(lang_layout)

        # Theme section
        theme_layout = QVBoxLayout()
        theme_layout.setSpacing(6)
        theme_label = QLabel(self.translations['settings_theme'])
        theme_label.setStyleSheet("background: transparent; font-weight: 600; font-size: 13px; color: #94a3b8;" if self.theme == 'dark' else "background: transparent; font-weight: 600; font-size: 13px; color: #64748b;")

        theme_combo = DropdownComboBox()
        theme_combo.setItemDelegate(ComboBoxItemDelegate(theme_combo))
        theme_combo.addItem(self.translations['theme_dark'], 'dark')
        theme_combo.addItem(self.translations['theme_light'], 'light')
        theme_combo.setCurrentIndex(0 if self.theme == 'dark' else 1)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(theme_combo)
        layout.addLayout(theme_layout)

        layout.addSpacing(6)

        # Save button
        save_button = QPushButton(self.translations['save'])
        save_button.setObjectName("saveSettingsButton")
        save_button.setCursor(Qt.PointingHandCursor)

        def on_save_clicked():
            lang = language_combo.currentData()
            thm = theme_combo.currentData()
            self.save_settings(lang, thm, settings_dialog)

        save_button.clicked.connect(on_save_clicked)
        layout.addWidget(save_button)

        settings_dialog.setLayout(layout)
        settings_dialog.adjustSize()
        set_dark_title_bar(settings_dialog, dark=(self.theme == 'dark'))
        settings_dialog.exec_()

    def save_settings(self, language, theme, dialog):
        self.language = language
        self.theme = theme
        save_settings_file(language, theme, self.last_output_dir, self.last_input_dir)
        self.translations = translations[self.language]
        self.apply_theme()
        self.retranslate_ui()
        dialog.accept()

    def retranslate_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.tabs.setTabText(0, self.translations['tab1'])
        self.tabs.setTabText(1, self.translations['tab2'])
        self.tabs.setTabText(2, self.translations['tab3'])
        self.tabs.setTabText(3, self.translations['tab4'])
        self.upload_btn.setText(self.translations['select_pdf'])
        self.save_btn.setText(self.translations['select_output_folder'])
        self.process_btn.setText(self.translations['start_conversion'])
        self.select_images_btn.setText(self.translations['select_images'])
        self.image_output_btn.setText(self.translations['select_output_folder'])
        self.convert_images_btn.setText(self.translations['convert_to_pdf'])
        self.combine_options.setItemText(0, self.translations['convert_to_image'])
        self.combine_options.setItemText(1, self.translations['merge_vertically'])
        self.combine_options.setItemText(2, self.translations['merge_horizontally'])
        self.compress_select_btn.setText(self.translations['select_pdf_to_compress'])
        self.compress_output_btn.setText(self.translations['select_output_folder'])
        self.compress_start_btn.setText(self.translations['start_compression'])
        self.compression_level_options.setItemText(0, self.translations['compression_extreme'])
        self.compression_level_options.setItemText(1, self.translations['compression_basic'])
        self.compression_level_options.setItemText(2, self.translations['compression_balanced'])
        self.compression_level_options.setItemText(3, self.translations['compression_high'])
        self.extract_select_btn.setText(self.translations['select_pdf_to_extract'])
        self.extract_output_btn.setText(self.translations['select_output_folder'])
        self.extract_start_btn.setText(self.translations['start_extraction'])
        self.settings_action.setText(self.translations['menu_settings'])
        self.about_action.setText(self.translations['menu_about'])
        self.update_button_states()

    def closeEvent(self, event):
        # Arka planda çalışan bir dönüştürme varsa pencereyi kapatmadan önce bitmesini bekle;
        # aksi halde çalışan bir QThread yok edilirken çökme riski oluşur.
        for worker in (self.pdf_worker, self.image_worker, self.compress_worker, self.extract_worker):
            if worker is not None and worker.isRunning():
                worker.wait()
        event.accept()


if __name__ == "__main__":
    try:
        # Enable High DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

        app = QApplication(sys.argv)
        # Windows'un yerel stili (windowsvista) bazı QSS özelliklerini (padding, border-radius, vb.)
        # tutarsız uyguluyor; Fusion tüm platformlarda aynı, öngörülebilir şekilde render ediyor.
        app.setStyle("Fusion")
        app.setWindowIcon(QIcon(resource_path("icon.ico")))  # Set app icon

        ex = PDFToImageConverter()
        ex.setMinimumSize(880, 520)
        ex.resize(880, 520)

        screen = app.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - ex.width()) // 2
        y = (screen_geometry.height() - ex.height()) // 2
        ex.move(x, y)
        ex.show()
        logging.info("Application started")
        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"An error occurred: {e}")
