"""Dialog for bulk downloading songs from a CSV/TXT file."""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRunnable, QThreadPool, Signal, QObject
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QFileDialog,
    QPlainTextEdit,
    QGroupBox,
)

from usdb_syncer.logger import logger
from usdb_syncer.bulk_download import (
    parse_bulk_import_file,
    search_and_get_songs,
    download_and_add_songs,
    DownloadSummary,
)
from usdb_syncer.gui import gui_utils
from usdb_syncer import db, utils


class ImportWorkerSignals(QObject):
    """Signals for import worker."""

    import_complete = Signal(DownloadSummary)
    progress_updated = Signal(int, int, str)
    error_occurred = Signal(str)


class ImportWorker(QRunnable):
    """Worker to handle bulk import in background thread."""

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path
        self.signals = ImportWorkerSignals()

    def run(self) -> None:
        """Run the import process."""
        try:
            with db.managed_connection(utils.AppPaths.db):
                # Phase 1: Parse file
                logger.info(f"Parsing file: {self.file_path}")
                entries = parse_bulk_import_file(self.file_path)
                logger.info(f"Parsed {len(entries)} entries")

                # Phase 2: Search for songs
                logger.info("Searching for songs in USDB...")
                results = search_and_get_songs(entries)

                # Count found vs not found
                found = sum(1 for r in results if r.usdb_song)
                not_found = len(results) - found
                logger.info(f"Found {found}/{len(results)} songs")

                # Phase 3: Download and add songs
                def progress_callback(current: int, total: int, song_name: str) -> None:
                    self.signals.progress_updated.emit(current, total, song_name)

                logger.info("Starting downloads...")
                summary = download_and_add_songs(results, progress_callback)

                logger.info(
                    f"Import complete: {summary.succeeded} succeeded, "
                    f"{summary.failed} failed, {summary.skipped} skipped"
                )
                self.signals.import_complete.emit(summary)

        except Exception as e:
            error_msg = f"Import error: {e}"
            logger.error(error_msg)
            self.signals.error_occurred.emit(error_msg)


class BulkDownloadDialog(QDialog):
    """Dialog for bulk downloading songs from a CSV/TXT file."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        gui_utils.cleanup_on_close(self)
        self.setWindowTitle("Bulk Download Songs")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._thread_pool = QThreadPool()
        self._current_worker: Optional[ImportWorker] = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # File selection section
        file_section = QGroupBox("File Selection")
        file_layout = QHBoxLayout(file_section)
        file_layout.addWidget(QLabel("Select a .txt file with comma-separated entries formatted as song artist:"))
        self.btn_select_file = QPushButton("Browse...")
        file_layout.addWidget(self.btn_select_file)
        layout.addWidget(file_section)

        # Progress section
        progress_section = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_section)
        progress_layout.addWidget(QLabel("Current Song:"))
        self.label_current_song = QLabel("No file selected")
        progress_layout.addWidget(self.label_current_song)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_section)

        # Results section
        results_section = QGroupBox("Results & Errors")
        results_layout = QVBoxLayout(results_section)
        self.text_errors = QPlainTextEdit()
        self.text_errors.setReadOnly(True)
        self.text_errors.setMaximumHeight(150)
        results_layout.addWidget(self.text_errors)
        layout.addWidget(results_section)

        # Summary section
        summary_section = QGroupBox("Summary")
        summary_layout = QVBoxLayout(summary_section)
        self.label_summary = QLabel("Ready to import")
        summary_layout.addWidget(self.label_summary)
        layout.addWidget(summary_section)

        # Buttons
        button_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_add_to_library = QPushButton("Add to Library")
        self.btn_add_to_library.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_add_to_library)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        self.btn_select_file.clicked.connect(self._on_select_file)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_add_to_library.clicked.connect(self.accept)

    def _on_select_file(self) -> None:
        """Handle file selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select bulk import file",
            "",
            "Text Files (*.txt);;All Files (*)",
        )

        if not file_path:
            return

        self.label_current_song.setText("Processing...")
        self.text_errors.clear()
        self.label_summary.setText("Importing...")
        self.btn_add_to_library.setEnabled(False)
        self.progress_bar.setValue(0)

        # Start import worker
        self._current_worker = ImportWorker(Path(file_path))
        self._current_worker.signals.progress_updated.connect(self._on_progress_updated)
        self._current_worker.signals.import_complete.connect(self._on_import_complete)
        self._current_worker.signals.error_occurred.connect(self._on_error_occurred)

        self._thread_pool.start(self._current_worker)

    def _on_progress_updated(self, current: int, total: int, song_name: str) -> None:
        """Handle progress update from worker."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.label_current_song.setText(f"{song_name} ({current}/{total})")

    def _on_import_complete(self, summary: DownloadSummary) -> None:
        """Handle import completion."""
        self.progress_bar.setValue(summary.succeeded + summary.failed + summary.skipped)

        # Update summary label
        summary_text = (
            f"Complete: {summary.succeeded} succeeded, "
            f"{summary.failed} failed, {summary.skipped} skipped"
        )
        self.label_summary.setText(summary_text)

        # Show errors
        if summary.errors:
            error_text = "Errors:\n" + "\n".join(summary.errors)
            self.text_errors.setPlainText(error_text)

        # Enable add to library button if any succeeded
        self.btn_add_to_library.setEnabled(summary.succeeded > 0)

        logger.info(summary_text)

    def _on_error_occurred(self, error_msg: str) -> None:
        """Handle import error."""
        self.label_current_song.setText("Error occurred")
        self.label_summary.setText("Import failed")
        self.text_errors.setPlainText(error_msg)
        logger.error(error_msg)
