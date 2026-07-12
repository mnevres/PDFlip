import sys
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QComboBox, QHBoxLayout,
    QMessageBox, QTabWidget, QMainWindow, QAction, QDialog, QProgressBar
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import fitz  # PyMuPDF
from PIL import Image


def resource_path(relative_path):
    """PyInstaller ile paketlendiğinde geçici çıkarma klasörünü, geliştirme ortamında script klasörünü döndürür."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def get_app_data_dir():
    """Ayar ve log dosyaları için kullanıcıya özel, her zaman yazılabilir bir klasör döndürür."""
    base = os.getenv('APPDATA') or os.path.expanduser('~')
    app_dir = os.path.join(base, 'MN PDF Converter')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


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

# Dil dosyası adı
LANGUAGE_FILE = os.path.join(get_app_data_dir(), 'language.json')

# Varsayılan dil İngilizce
DEFAULT_LANGUAGE = 'en'

# Büyük PDF'leri tek görselde birleştirirken kullanıcıyı uyarmak için sayfa eşiği
LARGE_MERGE_PAGE_THRESHOLD = 150

# Dil metinleri
translations = {
    'en': {
        'title': 'PDF & Image Converter',
        'tab1': 'PDF to Image',
        'tab2': 'Image to PDF',
        'select_pdf': 'Select PDF',
        'select_output_folder': 'Select Output Folder',
        'convert_to_image': 'Convert to image',
        'merge_vertically': 'Convert to image & Merge Vertically',
        'merge_horizontally': 'Convert to image & Merge Horizontally',
        'start_conversion': 'Start Conversion',
        'select_images': 'Select Images',
        'convert_to_pdf': 'Convert to PDF',
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'conversion_successful': 'Conversion successful!',
        'conversion_failed': 'Conversion failed: ',
        'select_pdf_error': 'Please select a PDF file and an output folder.',
        'select_image_folder_error': 'Please select an image folder.',
        'no_images_found_error': 'No images found in the selected folder.',
        'pdf_created_success': 'PDF created successfully: ',
        'large_merge_warning_message': 'You are about to merge {count} pages into a single image. This may use a large amount of memory and could fail. Do you want to continue?',
        'password_protected_error': 'This PDF is password protected. Please remove the password and try again.',
        'selected_pdf_prefix': 'Selected PDF: ',
        'output_folder_prefix': 'Output Folder: ',
        'selected_folder_prefix': 'Selected Folder: ',
        'save': 'Save',
        'menu_settings': 'Settings',
        'menu_about': 'About',
        'about_message': (
            '<b>Creator:</b> Mehmet Nevresoğlu<br>'
            '<b>Contact:</b> <a href="mailto:mehmet.nvrs@gmail.com">mehmet.nvrs@gmail.com</a><br>'
            '<b>LinkedIn:</b> <a href="https://www.linkedin.com/in/mehmet-nevresoglu-bb44341a/">Click here</a><br><br>'
            'You can use this program anywhere as long as you cite it as a reference. No license required.'
        ),
        'settings_language': 'Language',
        'language_english': 'English',
        'language_turkish': 'Türkçe'
    },
    'tr': {
        'title': 'PDF & Resim Dönüştürücü',
        'tab1': 'PDF\'den Resime Dönüştür',
        'tab2': 'Resimden PDF\'ye Dönüştür',
        'select_pdf': 'PDF Seç',
        'select_output_folder': 'Çıktı Klasörünü Seç',
        'convert_to_image': 'Görüntüye dönüştür',
        'merge_vertically': 'Görüntüye dönüştür ve Dikey Birleştir',
        'merge_horizontally': 'Görüntüye dönüştür ve Yatay Birleştir',
        'start_conversion': 'Dönüştürmeyi Başlat',
        'select_images': 'Resimleri Seç',
        'convert_to_pdf': 'PDF\'ye Dönüştür',
        'success': 'Başarılı',
        'error': 'Hata',
        'warning': 'Uyarı',
        'conversion_successful': 'Dönüştürme başarılı!',
        'conversion_failed': 'Dönüştürme başarısız: ',
        'select_pdf_error': 'Lütfen bir PDF dosyası ve bir çıktı klasörü seçin.',
        'select_image_folder_error': 'Lütfen bir resim klasörü seçin.',
        'no_images_found_error': 'Seçilen klasörde resim bulunamadı.',
        'pdf_created_success': 'PDF başarıyla oluşturuldu: ',
        'large_merge_warning_message': '{count} sayfayı tek bir görselde birleştirmek üzeresiniz. Bu işlem çok fazla bellek kullanabilir ve başarısız olabilir. Devam etmek istiyor musunuz?',
        'password_protected_error': 'Bu PDF parola korumalı. Lütfen parolayı kaldırıp tekrar deneyin.',
        'selected_pdf_prefix': 'Seçilen PDF: ',
        'output_folder_prefix': 'Çıktı Klasörü: ',
        'selected_folder_prefix': 'Seçilen Klasör: ',
        'save': 'Kaydet',
        'menu_settings': 'Ayarlar',
        'menu_about': 'Hakkında',
        'about_message': (
            '<b>Geliştirici:</b> Mehmet Nevresoğlu<br>'
            '<b>İletişim:</b> <a href="mailto:mehmet.nvrs@gmail.com">mehmet.nvrs@gmail.com</a><br>'
            '<b>LinkedIn:</b> <a href="https://www.linkedin.com/in/mehmet-nevresoglu-bb44341a/">Buraya tıklayın</a><br><br>'
            'Bu programı kaynak belirttiğiniz sürece her yerde kullanabilirsiniz. Lisans gerektirmez.'
        ),
        'settings_language': 'Dil',
        'language_english': 'İngilizce',
        'language_turkish': 'Türkçe'
    }
}


def load_language():
    if os.path.exists(LANGUAGE_FILE):
        try:
            with open(LANGUAGE_FILE, 'r') as file:
                language = json.load(file).get('language', DEFAULT_LANGUAGE)
                return language if language in translations else DEFAULT_LANGUAGE
        except (json.JSONDecodeError, OSError):
            logging.warning("language.json could not be read, falling back to default language")
    return DEFAULT_LANGUAGE


def save_language(language):
    with open(LANGUAGE_FILE, 'w') as file:
        json.dump({'language': language}, file)


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

    def run(self):
        doc = None
        try:
            doc = fitz.open(self.pdf_path)
            if doc.needs_pass:
                raise ValueError("PDF_PASSWORD_PROTECTED")

            page_count = len(doc)
            zoom = 3  # 3x zoom, resulting in 216 DPI
            mat = fitz.Matrix(zoom, zoom)

            if self.combine_mode == 'vertical' and page_count > 1:
                images = self._extract_all_pages(doc, mat, page_count)
                widths, heights = zip(*(img.size for img in images))
                combined_image = Image.new("RGB", (max(widths), sum(heights)))
                y_offset = 0
                for img in images:
                    combined_image.paste(img, (0, y_offset))
                    y_offset += img.height
                combined_image.save(os.path.join(self.save_path, f"output_combined_vertical.{self.file_type}"))
                logging.debug("Images merged vertically")
            elif self.combine_mode == 'horizontal' and page_count > 1:
                images = self._extract_all_pages(doc, mat, page_count)
                widths, heights = zip(*(img.size for img in images))
                combined_image = Image.new("RGB", (sum(widths), max(heights)))
                x_offset = 0
                for img in images:
                    combined_image.paste(img, (x_offset, 0))
                    x_offset += img.width
                combined_image.save(os.path.join(self.save_path, f"output_combined_horizontal.{self.file_type}"))
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

            self.finished.emit(True, "")
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


class PDFToImageConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = load_language()
        self.translations = translations[self.language]
        self.pdf_worker = None
        self.image_worker = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.translations['title'])

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout()
        central_widget.setLayout(self.layout)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(15)

        self.tabs = QTabWidget()
        self.pdf_to_image_tab = QWidget()
        self.image_to_pdf_tab = QWidget()

        self.tabs.addTab(self.pdf_to_image_tab, self.translations['tab1'])
        self.tabs.addTab(self.image_to_pdf_tab, self.translations['tab2'])

        self.init_pdf_to_image_tab()
        self.init_image_to_pdf_tab()

        self.layout.addWidget(self.tabs)
        self.create_menu()

        # Set window icon
        self.setWindowIcon(QIcon(resource_path('icon.ico')))

        self.adjustSize()

        self.pdf_path = ''
        self.save_path = ''
        self.image_folder = ''

        self.update_button_states()
        logging.debug("UI initialized")

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
        self.pdf_label.setStyleSheet("color: #1b1c1c;")
        self.pdf_to_image_layout.addWidget(self.pdf_label)

        self.save_btn = QPushButton(self.translations['select_output_folder'], self)
        self.save_btn.setFont(font)
        self.save_btn.clicked.connect(self.save_location)
        self.save_btn.setStyleSheet("color: white; padding: 10px; background-color: #3b3b3b; border-radius: 5px;")
        self.pdf_to_image_layout.addWidget(self.save_btn)

        self.output_label = QLabel('', self)
        self.output_label.setFont(QFont("", 12))  # Bilgi etiketlerinin fontu 12
        self.output_label.setStyleSheet("color: #1b1c1c;")
        self.pdf_to_image_layout.addWidget(self.output_label)

        self.combine_options = QComboBox(self)
        self.combine_options.setFont(font)
        self.combine_options.setStyleSheet("padding: 5px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.combine_options.addItem(self.translations['convert_to_image'], 'single')
        self.combine_options.addItem(self.translations['merge_vertically'], 'vertical')
        self.combine_options.addItem(self.translations['merge_horizontally'], 'horizontal')
        self.combine_options.currentIndexChanged.connect(self.clear_status)
        self.pdf_to_image_layout.addWidget(self.combine_options)

        self.file_type_options = QComboBox(self)
        self.file_type_options.setFont(font)
        self.file_type_options.setStyleSheet("padding: 5px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.file_type_options.addItem("JPG")
        self.file_type_options.addItem("PNG")
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
        self.status_label.setStyleSheet("color: #1b1c1c;")
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
        self.images_label.setStyleSheet("color: #1b1c1c;")
        self.image_to_pdf_layout.addWidget(self.images_label)

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
        self.image_to_pdf_status_label.setStyleSheet("color: #1b1c1c;")
        self.image_to_pdf_layout.addWidget(self.image_to_pdf_status_label)

        self.image_to_pdf_tab.setLayout(self.image_to_pdf_layout)

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

        if self.image_folder:
            self.select_images_btn.setStyleSheet("background-color: #77dd77; color: white; padding: 10px; border-radius: 5px;")
        else:
            self.select_images_btn.setStyleSheet("background-color: #ff6961; color: white; padding: 10px; border-radius: 5px;")

    def clear_status(self):
        self.status_label.setText('')

    def upload_pdf(self):
        options = QFileDialog.Options()
        self.pdf_path, _ = QFileDialog.getOpenFileName(self, self.translations['select_pdf'], "", "PDF Files (*.pdf);;All Files (*)", options=options)
        self.update_button_states()
        self.clear_status()
        logging.debug(f"PDF selected: {self.pdf_path}")

    def save_location(self):
        options = QFileDialog.Options()
        self.save_path = QFileDialog.getExistingDirectory(self, self.translations['select_output_folder'], "", options=options)
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
        if not self.pdf_path or not self.save_path:
            self.show_message(self.translations['error'], self.translations['select_pdf_error'])
            logging.error("PDF file or output folder not selected")
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

    def on_pdf_progress(self, current, total):
        self.pdf_progress_bar.setMaximum(total)
        self.pdf_progress_bar.setValue(current)
        self.status_label.setText(f"{current}/{total}")

    def on_pdf_conversion_finished(self, success, error_message):
        self._set_pdf_controls_enabled(True)
        self.process_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border-radius: 5px;")
        self.pdf_progress_bar.setVisible(False)

        if success:
            self.show_message(self.translations['success'], self.translations['conversion_successful'])
            self.reset_state()
        elif error_message == "PDF_PASSWORD_PROTECTED":
            self.show_message(self.translations['error'], self.translations['password_protected_error'])
        else:
            self.show_message(self.translations['error'], f"{self.translations['conversion_failed']}{error_message}")

        self.pdf_worker = None

    def select_images(self):
        options = QFileDialog.Options()
        self.image_folder = QFileDialog.getExistingDirectory(self, self.translations['select_images'], "", options=options)
        self.update_button_states()
        self.images_label.setText(f"{self.translations['selected_folder_prefix']}{self.image_folder}" if self.image_folder else "")
        logging.debug(f"Image folder selected: {self.image_folder}")

    def _set_image_controls_enabled(self, enabled):
        self.select_images_btn.setEnabled(enabled)
        self.convert_images_btn.setEnabled(enabled)

    def convert_images_to_pdf(self):
        if not self.image_folder:
            self.show_message(self.translations['error'], self.translations['select_image_folder_error'])
            logging.error("Image folder not selected")
            return

        if self.image_worker is not None and self.image_worker.isRunning():
            return

        image_files = [os.path.join(self.image_folder, f) for f in os.listdir(self.image_folder) if f.lower().endswith(("png", "jpg", "jpeg"))]
        image_files.sort()

        if not image_files:
            self.show_message(self.translations['error'], self.translations['no_images_found_error'])
            logging.error("No images found in the selected folder")
            return

        pdf_path = os.path.join(self.image_folder, "output.pdf")

        self._set_image_controls_enabled(False)
        self.convert_images_btn.setStyleSheet("padding: 10px; background-color: #3b3b3b; color: white; border: 2px solid green; border-radius: 5px;")
        self.image_progress_bar.setVisible(True)
        self.image_progress_bar.setValue(0)
        self.image_to_pdf_status_label.setText('')

        self.image_worker = ImageToPdfWorker(image_files, pdf_path)
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
            self.show_message(self.translations['success'], f"{self.translations['pdf_created_success']}{pdf_path}")
            self.reset_state()
        else:
            self.show_message(self.translations['error'], f"{self.translations['conversion_failed']}{error_message}")

        self.image_worker = None

    def reset_state(self):
        self.pdf_path = ""
        self.save_path = ""
        self.image_folder = ""
        self.update_button_states()
        self.pdf_label.setText("")
        self.output_label.setText("")
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
        about_text = self.translations['about_message']
        about_msg = QMessageBox(self)
        about_msg.setWindowTitle(self.translations['menu_about'])
        about_msg.setTextFormat(Qt.RichText)
        about_msg.setText(about_text)
        about_msg.exec_()

    def show_settings(self):
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle(self.translations['menu_settings'])

        layout = QVBoxLayout()

        language_label = QLabel(self.translations['settings_language'])
        layout.addWidget(language_label)

        language_combo = QComboBox()
        language_combo.addItem(self.translations['language_english'], 'en')
        language_combo.addItem(self.translations['language_turkish'], 'tr')
        language_combo.setCurrentIndex(0 if self.language == 'en' else 1)
        layout.addWidget(language_combo)

        save_button = QPushButton(self.translations['save'])
        save_button.clicked.connect(lambda: self.save_settings(language_combo.currentData(), settings_dialog))
        layout.addWidget(save_button)

        settings_dialog.setLayout(layout)
        settings_dialog.resize(300, 150)
        settings_dialog.exec_()

    def save_settings(self, language, dialog):
        self.language = language
        save_language(language)
        self.translations = translations[self.language]
        self.retranslate_ui()
        dialog.accept()

    def retranslate_ui(self):
        self.setWindowTitle(self.translations['title'])
        self.tabs.setTabText(0, self.translations['tab1'])
        self.tabs.setTabText(1, self.translations['tab2'])
        self.upload_btn.setText(self.translations['select_pdf'])
        self.save_btn.setText(self.translations['select_output_folder'])
        self.process_btn.setText(self.translations['start_conversion'])
        self.select_images_btn.setText(self.translations['select_images'])
        self.convert_images_btn.setText(self.translations['convert_to_pdf'])
        self.settings_action.setText(self.translations['menu_settings'])
        self.about_action.setText(self.translations['menu_about'])
        self.update_button_states()

    def closeEvent(self, event):
        # Arka planda çalışan bir dönüştürme varsa pencereyi kapatmadan önce bitmesini bekle;
        # aksi halde çalışan bir QThread yok edilirken çökme riski oluşur.
        for worker in (self.pdf_worker, self.image_worker):
            if worker is not None and worker.isRunning():
                worker.wait()
        event.accept()


if __name__ == "__main__":
    try:
        # Enable High DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(resource_path("icon.ico")))  # Set app icon

        ex = PDFToImageConverter()
        ex.adjustSize()

        # Set the window width to 1.5 times its original width
        ex.resize(int(ex.width() * 1.5), ex.height())

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
