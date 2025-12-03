import sys
import serial
import time
import json
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import serial.tools.list_ports

BAUD_RATE = 115200
TAGS_FILE = "allowed_tags.json"


class RFIDApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.allowed_tags = self.load_tags_from_json()
        self.scanning_enabled = False
        self.buffer = ""
        self.esp = None
        self.initUI()

    # -------------------------
    # JSON FILE HANDLING
    # -------------------------
    def load_tags_from_json(self):
        """Load allowed tags from JSON file, create if doesn't exist"""
        try:
            if os.path.exists(TAGS_FILE):
                with open(TAGS_FILE, 'r') as f:
                    tags = json.load(f)
                    # Ensure we have a list with default tags if file is empty/corrupt
                    if isinstance(tags, list):
                        return tags
                    else:
                        # If file exists but doesn't contain a list, create default
                        default_tags = ["0001234567", "0009876543", "0005555555", "12345", "67890"]
                        self.save_tags_to_json(default_tags)
                        return default_tags
            else:
                # Create JSON file with default tags
                default_tags = ["0001234567", "0009876543", "0005555555", "12345", "67890"]
                self.save_tags_to_json(default_tags)
                return default_tags
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading tags: {e}")
            # Return default tags and try to create file
            default_tags = ["0001234567", "0009876543", "0005555555", "12345", "67890"]
            self.save_tags_to_json(default_tags)
            return default_tags

    def save_tags_to_json(self, tags):
        """Save allowed tags to JSON file"""
        try:
            with open(TAGS_FILE, 'w') as f:
                json.dump(tags, f, indent=2)
        except IOError as e:
            print(f"Error saving tags: {e}")

    def add_tag_to_json(self, tag):
        """Add a new tag to both memory and JSON file"""
        if tag not in self.allowed_tags:
            self.allowed_tags.append(tag)
            self.save_tags_to_json(self.allowed_tags)
            return True
        return False

    def remove_tag_from_json(self, tag):
        """Remove tag from both memory and JSON file"""
        if tag in self.allowed_tags:
            self.allowed_tags.remove(tag)
            self.save_tags_to_json(self.allowed_tags)
            return True
        return False

    # -------------------------
    # MAIN UI SETUP
    # -------------------------
    def initUI(self):
        self.setWindowTitle("RFID Access Control")
        self.setFixedSize(500, 600)
        
        # Set window icon (you can replace 'icon.png' with your own icon file)
        self.setWindowIcon(QIcon("Icon.png"))
        
        # Enable window translucency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Set dark theme palette
        self.set_dark_palette()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QStackedLayout(central_widget)

        # --- MAIN SCREEN ---
        self.main_screen = QWidget()
        self.main_screen.setObjectName("mainScreen")
        main_vbox = QVBoxLayout(self.main_screen)
        main_vbox.setContentsMargins(25, 20, 25, 15)
        main_vbox.setSpacing(10)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Settings Button - Top right with gear emoji
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setFixedSize(40, 40)
        
        top_bar.addStretch()
        top_bar.addWidget(self.settings_btn)

        # Main Content Container - Centered
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setSpacing(8)

        # Status Card
        status_card = QFrame()
        status_card.setObjectName("statusCard")
        status_card.setFixedSize(440, 190)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 12, 20, 12)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.setSpacing(6)
        
        # Status indicator at top
        self.status_indicator = QLabel("● Disconnected")
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.scan_icon = QLabel("📱")
        self.scan_icon.setObjectName("scanIcon")
        self.scan_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.scan_label = QLabel("Ready to Scan")
        self.scan_label.setObjectName("scanLabel")
        self.scan_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.tag_display = QLabel("")
        self.tag_display.setObjectName("tagDisplay")
        self.tag_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tag_display.setMinimumWidth(250)
        
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.scan_icon)
        status_layout.addWidget(self.scan_label)
        status_layout.addWidget(self.tag_display)

        # Combined Start/Stop Button
        self.scan_control_btn = QPushButton("▶ Start Scanning")
        self.scan_control_btn.setObjectName("scanControlBtn")
        self.scan_control_btn.setFixedSize(200, 45)
        self.scan_control_btn.clicked.connect(self.toggle_scanning)

        # Recent Activity
        activity_label = QLabel("Recent Activity")
        activity_label.setObjectName("activityLabel")
        activity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.activity_list = QListWidget()
        self.activity_list.setFixedHeight(140)
        self.activity_list.setObjectName("activityList")

        # Footer with credit
        footer_label = QLabel("rfid access control be @edward1stark")
        footer_label.setObjectName("footerLabel")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Assemble content
        content_layout.addWidget(status_card)
        content_layout.addSpacing(15)
        content_layout.addWidget(self.scan_control_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        content_layout.addSpacing(12)
        content_layout.addWidget(activity_label)
        content_layout.addWidget(self.activity_list)
        content_layout.addSpacing(5)
        content_layout.addWidget(footer_label)

        # Assemble main screen
        main_vbox.addLayout(top_bar)
        main_vbox.addSpacing(15)
        main_vbox.addWidget(content_widget)
        main_vbox.addStretch()

        self.main_layout.addWidget(self.main_screen)

        # --- SETTINGS PANEL ---
        self.settings_panel = QWidget()
        self.settings_panel.setObjectName("settingsPanel")  # Changed ID
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(25, 20, 25, 20)  # Same margins as main screen
        settings_layout.setSpacing(12)

        # Header with back button - Properly centered
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("←")
        back_btn.setObjectName("backBtn")
        back_btn.setFixedSize(40, 40)
        back_btn.clicked.connect(self.close_settings_panel)
        
        settings_title = QLabel("Settings")
        settings_title.setObjectName("settingsTitle")
        settings_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add empty widget for spacing to center the title
        spacer = QWidget()
        spacer.setFixedSize(40, 40)
        
        header_layout.addWidget(back_btn)
        header_layout.addStretch()
        header_layout.addWidget(settings_title)
        header_layout.addStretch()
        header_layout.addWidget(spacer)  # Balance the back button on the left

        # Settings Content in Scroll Area - FIXED
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("scrollArea")
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins

        # COM Port Section
        port_group = QGroupBox("Connection")
        port_group.setObjectName("settingsGroupBox")
        port_layout = QVBoxLayout(port_group)
        port_layout.setSpacing(8)
        
        port_combo_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setFixedHeight(35)
        self.port_combo.setMinimumWidth(200)
        refresh_btn = QPushButton("⟳")
        refresh_btn.setObjectName("refreshBtn")
        refresh_btn.setFixedSize(35, 35)
        refresh_btn.clicked.connect(self.refresh_ports)
        
        port_combo_layout.addWidget(QLabel("Port:"))
        port_combo_layout.addWidget(self.port_combo)
        port_combo_layout.addWidget(refresh_btn)
        
        self.connection_status = QLabel("Select a port")
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        port_layout.addLayout(port_combo_layout)
        port_layout.addWidget(self.connection_status)
        self.refresh_ports()

        # Tags Management Section
        tags_group = QGroupBox("Allowed Tags")
        tags_group.setObjectName("settingsGroupBox")
        tags_layout = QVBoxLayout(tags_group)
        tags_layout.setSpacing(8)
        
        self.tag_list = QListWidget()
        self.tag_list.setObjectName("tagList")
        self.tag_list.setMinimumHeight(140)
        self.load_tags()
        
        # Add tag section
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("Enter tag ID")
        self.new_tag_input.setFixedHeight(35)
        
        add_tag_button = QPushButton("+ Add")
        add_tag_button.setObjectName("addBtn")
        add_tag_button.setFixedHeight(35)
        add_tag_button.clicked.connect(self.add_new_tag)
        
        add_layout.addWidget(self.new_tag_input)
        add_layout.addWidget(add_tag_button)
        
        remove_button = QPushButton("Remove Selected")
        remove_button.setObjectName("removeBtn")
        remove_button.clicked.connect(self.remove_selected_tag)
        remove_button.setFixedHeight(35)
        
        tags_layout.addWidget(self.tag_list)
        tags_layout.addLayout(add_layout)
        tags_layout.addWidget(remove_button)

        # Add sections to scroll area
        scroll_layout.addWidget(port_group)
        scroll_layout.addWidget(tags_group)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)

        # Assemble settings panel
        settings_layout.addLayout(header_layout)
        settings_layout.addSpacing(8)
        settings_layout.addWidget(scroll_area)

        self.main_layout.addWidget(self.settings_panel)

        # Connect signals
        self.settings_btn.clicked.connect(self.open_settings_panel)

        # Install event filter for keyboard
        self.installEventFilter(self)
        
        # Show main screen
        self.show_main_screen()

    def set_dark_palette(self):
        palette = QPalette()
        
        palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 24, 200))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 38, 180))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(25, 25, 32, 180))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(45, 45, 55))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 50, 180))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Link, QColor(100, 150, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(100, 150, 255, 100))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        self.setPalette(palette)
        self.setStyleSheet(self.get_stylesheet())

    def get_stylesheet(self):
        return """
            /* Main Window */
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 rgba(18, 18, 28, 220), 
                                            stop:1 rgba(28, 28, 48, 220));
                border: 1px solid rgba(70, 70, 100, 100);
                border-radius: 15px;
            }
            
            /* Main Screen */
            QWidget#mainScreen {
                background: transparent;
                border-radius: 15px;
            }
            
            /* Settings Panel - NO BACKGROUND */
            QWidget#settingsPanel {
                background: transparent;
                border-radius: 15px;
            }
            
            /* Scroll Area Content - Remove all backgrounds */
            QWidget#scrollContent {
                background: transparent;
            }
            
            /* Footer Label */
            QLabel#footerLabel {
                font-size: 10px;
                color: rgba(255, 255, 255, 100);
                font-style: italic;
                padding: 5px;
            }
            
            /* Settings Title - PROPERLY CENTERED */
            QLabel#settingsTitle {
                font-size: 22px;
                font-weight: bold;
                color: #ffffff;
                padding: 0px;
                margin: 0px;
                qproperty-alignment: AlignCenter;
            }
            
            /* Settings Button */
            QPushButton#settingsBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #2d3436, stop:1 #222831);
                color: #ffffff;
                font-size: 18px;
                border: 1px solid #4a4a6a;
                border-radius: 8px;
                padding: 0px;
            }
            
            QPushButton#settingsBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3742fa, stop:1 #5352ed);
                border-color: #70a1ff;
            }
            
            /* Status Indicator */
            QLabel#statusIndicator {
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 8px;
                background-color: #ff4757;
                color: white;
                font-weight: bold;
            }
            
            /* Status Card */
            QFrame#statusCard {
                background: qradialgradient(cx:0.5, cy:0.5, radius:1,
                                            fx:0.5, fy:0.5,
                                            stop:0 rgba(40, 40, 60, 200),
                                            stop:1 rgba(25, 25, 40, 250));
                border-radius: 12px;
                border: 1px solid #2d3436;
            }
            
            /* Scan Icon */
            QLabel#scanIcon {
                font-size: 48px;
                color: #70a1ff;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            
            /* Scan Label */
            QLabel#scanLabel {
                font-size: 17px;
                font-weight: bold;
                color: #ffffff;
                padding: 4px;
                background: transparent;
            }
            
            /* Tag Display */
            QLabel#tagDisplay {
                font-size: 13px;
                font-family: 'Courier New', monospace;
                color: #70a1ff;
                padding: 5px 8px;
                background-color: rgba(30, 30, 45, 0.8);
                border-radius: 5px;
                border: 1px solid #3742fa;
            }
            
            /* Combined Scan Control Button */
            QPushButton#scanControlBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3742fa, stop:1 #5352ed);
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }
            
            QPushButton#scanControlBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5352ed, stop:1 #6c5ce7);
            }
            
            QPushButton#scanControlBtn:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #4a4a4a, stop:1 #3a3a3a);
                color: #777777;
            }
            
            /* Activity Label */
            QLabel#activityLabel {
                font-size: 13px;
                font-weight: bold;
                color: #70a1ff;
                padding: 3px 0;
            }
            
            /* Activity List */
            QListWidget#activityList {
                background-color: rgba(30, 30, 45, 0.8);
                border: 1px solid #2d3436;
                border-radius: 8px;
                font-size: 10px;
                padding: 5px;
                color: #dddddd;
            }
            
            QListWidget#activityList::item {
                padding: 3px;
                border-bottom: 1px solid rgba(45, 52, 54, 0.5);
                background-color: transparent;
            }
            
            QListWidget#activityList::item:last-child {
                border-bottom: none;
            }
            
            QListWidget#activityList::item:selected {
                background-color: rgba(112, 161, 255, 0.3);
                color: white;
            }
            
            /* Back Button */
            QPushButton#backBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #2d3436, stop:1 #222831);
                color: #70a1ff;
                font-size: 18px;
                border: 1px solid #4a4a6a;
                border-radius: 8px;
            }
            
            QPushButton#backBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3742fa, stop:1 #5352ed);
                border-color: #70a1ff;
            }
            
            /* Scroll Area */
            QScrollArea#scrollArea {
                border: none;
                background: transparent;
            }
            
            QScrollBar:vertical {
                background: #2d3436;
                width: 6px;
                border-radius: 3px;
            }
            
            QScrollBar::handle:vertical {
                background: #70a1ff;
                border-radius: 3px;
                min-height: 15px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #5352ed;
            }
            
            /* Settings Group Box - Keep the box styling but remove surrounding gray */
            QGroupBox#settingsGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #2d3436;
                border-radius: 10px;
                padding: 12px;
                color: #70a1ff;
                margin-top: 5px;
                background: qradialgradient(cx:0.5, cy:0.5, radius:1,
                                            fx:0.5, fy:0.5,
                                            stop:0 rgba(40, 40, 60, 180),
                                            stop:1 rgba(25, 25, 40, 200));
            }
            
            QGroupBox#settingsGroupBox::title {
                color: #70a1ff;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
            
            /* Combo Box */
            QComboBox {
                background-color: rgba(40, 40, 60, 0.8);
                border: 1px solid #4a4a6a;
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
                color: #ffffff;
            }
            
            QComboBox:hover {
                border-color: #70a1ff;
            }
            
            QComboBox::drop-down {
                border: none;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #70a1ff;
            }
            
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                border: 1px solid #70a1ff;
                color: #ffffff;
                selection-background-color: #3742fa;
            }
            
            /* Refresh Button */
            QPushButton#refreshBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3742fa, stop:1 #5352ed);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            
            QPushButton#refreshBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5352ed, stop:1 #6c5ce7);
            }
            
            /* Connection Status */
            QLabel#connectionStatus {
                color: #7f8c8d;
                font-size: 10px;
                font-style: italic;
            }
            
            /* Tag List */
            QListWidget#tagList {
                background-color: rgba(40, 40, 60, 0.8);
                border: 1px solid #4a4a6a;
                border-radius: 6px;
                font-size: 11px;
                padding: 5px;
                color: #dddddd;
            }
            
            QListWidget#tagList::item {
                padding: 5px;
                background-color: rgba(30, 30, 45, 0.6);
                margin: 2px;
                border-radius: 4px;
                border-left: 3px solid #3742fa;
            }
            
            QListWidget#tagList::item:selected {
                background-color: rgba(112, 161, 255, 0.3);
                color: white;
                border-left: 3px solid #ff6b6b;
            }
            
            /* Line Edit */
            QLineEdit {
                background-color: rgba(40, 40, 60, 0.8);
                border: 1px solid #4a4a6a;
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
                color: #ffffff;
                selection-background-color: #3742fa;
            }
            
            QLineEdit:focus {
                border-color: #70a1ff;
                border-width: 2px;
            }
            
            QLineEdit::placeholder {
                color: #7f8c8d;
            }
            
            /* Add Button */
            QPushButton#addBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #1dd1a1, stop:1 #10ac84);
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 12px;
                font-size: 11px;
            }
            
            QPushButton#addBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #26de85, stop:1 #20bf6b);
            }
            
            /* Remove Button */
            QPushButton#removeBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #ff6b6b, stop:1 #ee5a52);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            
            QPushButton#removeBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #ff5252, stop:1 #ff3838);
            }
            
            QPushButton#removeBtn:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #c0392b, stop:1 #a93226);
            }
        """

    # -------------------------
    # Scanning Mode
    # -------------------------
    def toggle_scanning(self):
        if self.scanning_enabled:
            self.disable_scanning()
        else:
            self.enable_scanning()

    def enable_scanning(self):
        com_text = self.port_combo.currentText()
        if not com_text or "No ports" in com_text:
            self.show_message_dialog("No Port", "Please select a valid COM port first.")
            return

        try:
            port = com_text.split(" - ")[0]
            self.esp = serial.Serial(port, BAUD_RATE, timeout=1)
            time.sleep(0.5)
            self.scanning_enabled = True
            self.scan_label.setText("SCANNING...")
            self.scan_icon.setText("🔍")
            self.status_indicator.setText("● Connected")
            self.status_indicator.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    padding: 4px 10px;
                    border-radius: 8px;
                    background-color: #1dd1a1;
                    color: white;
                    font-weight: bold;
                }
            """)
            self.scan_control_btn.setText("⏹ Stop Scanning")
            self.scan_control_btn.setStyleSheet("""
                QPushButton#scanControlBtn {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #ff6b6b, stop:1 #ee5a52);
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                }
                
                QPushButton#scanControlBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #ff5252, stop:1 #ff3838);
                }
            """)
            self.connection_status.setText(f"Connected to {port}")
            self.connection_status.setStyleSheet("color: #1dd1a1; font-weight: bold;")
            
            self.add_activity("📡 Scanning started", "success")
            
        except Exception as e:
            self.scan_label.setText("CONNECTION FAILED")
            self.add_activity(f"❌ Connection failed: {str(e)[:40]}", "error")
            self.show_message_dialog("Connection Error", f"Failed to connect:\n{str(e)}", is_error=True)

    def disable_scanning(self):
        self.scanning_enabled = False
        if self.esp:
            self.esp.close()
            self.esp = None
        
        self.scan_label.setText("READY TO SCAN")
        self.scan_icon.setText("📱")
        self.status_indicator.setText("● Disconnected")
        self.status_indicator.setStyleSheet("""
            QLabel {
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 8px;
                background-color: #ff4757;
                color: white;
                font-weight: bold;
            }
        """)
        self.scan_control_btn.setText("▶ Start Scanning")
        self.scan_control_btn.setStyleSheet("""
            QPushButton#scanControlBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3742fa, stop:1 #5352ed);
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }
            
            QPushButton#scanControlBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5352ed, stop:1 #6c5ce7);
            }
        """)
        self.buffer = ""
        self.tag_display.setText("")
        
        self.add_activity("⏹️ Scanning stopped", "info")

    # -------------------------
    # Custom Message Dialogs (Consistent Theming)
    # -------------------------
    def show_message_dialog(self, title, message, is_error=False):
        """Show a themed message dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setFixedSize(400, 180)
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | 
                            Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        
        # Match app theme
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 rgba(13, 13, 21, 220), 
                                            stop:1 rgba(26, 26, 46, 220));
                border: 1px solid rgba(70, 70, 100, 150);
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
                padding: 10px;
                background: transparent;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3742fa, stop:1 #5352ed);
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5352ed, stop:1 #6c5ce7);
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Message label
        msg_label = QLabel(message)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)
        
        # OK button
        ok_btn = QPushButton("OK")
        ok_btn.setFixedSize(100, 35)
        ok_btn.clicked.connect(dialog.accept)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addStretch()
        
        layout.addWidget(msg_label)
        layout.addLayout(button_layout)
        
        dialog.exec()

    # -------------------------
    # Event Filter (Keyboard RFID)
    # -------------------------
    def eventFilter(self, obj, event):
        if self.scanning_enabled and event.type() == QEvent.Type.KeyPress:
            key = event.key()

            if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
                self.buffer += event.text()
                self.tag_display.setText(self.buffer)
                self.scan_icon.setText("⌨️")

            if key == Qt.Key.Key_Return:
                tag = self.buffer
                self.buffer = ""
                self.tag_display.setText("")
                self.check_tag(tag)

        return super().eventFilter(obj, event)

    # -------------------------
    # Tag validation
    # -------------------------
    def check_tag(self, tag):
        if not tag:  # Empty tag
            self.show_tag_result("EMPTY TAG", False)
            self.add_activity(f"❌ Empty tag", "error")
            return
            
        if tag in self.allowed_tags:
            self.show_tag_result(f"ACCESS GRANTED\n{tag}", True)
            if self.esp:
                self.esp.write(b"open\n")
            self.add_activity(f"✅ Access granted: {tag}", "success")
        else:
            self.show_tag_result(f"ACCESS DENIED\n{tag}", False)
            self.add_activity(f"❌ Access denied: {tag}", "error")

    def show_tag_result(self, text, success):
        color = "#1dd1a1" if success else "#ff4757"
        icon = "✅" if success else "❌"
        status = "ACCESS GRANTED" if success else "ACCESS DENIED"
        
        self.scan_label.setText(status)
        self.scan_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: bold;
            color: {color};
            padding: 4px;
            background: transparent;
        """)
        self.scan_icon.setText(icon)
        self.scan_icon.setStyleSheet(f"""
            font-size: 48px;
            color: {color};
            background: transparent;
            border: none;
            padding: 0px;
            margin: 0px;
        """)
        
        # Show tag ID if available
        if "\n" in text:
            tag_id = text.split('\n')[1]
            self.tag_display.setText(tag_id)
        else:
            self.tag_display.setText("")
            
        self.tag_display.setStyleSheet(f"""
            color: {color};
            border-color: {color};
            background-color: rgba(30, 30, 45, 0.8);
        """)
        
        # Pulse animation effect
        self.pulse_animation(color)
        
        # Reset after 2 seconds
        QTimer.singleShot(2000, self.reset_scan_display)

    def pulse_animation(self, color):
        animation = QPropertyAnimation(self.scan_icon, b"styleSheet")
        animation.setDuration(300)
        animation.setLoopCount(2)
        animation.setStartValue(f"font-size: 48px; color: {color}; background: transparent;")
        animation.setKeyValueAt(0.5, f"font-size: 56px; color: {color}; background: transparent;")
        animation.setEndValue(f"font-size: 48px; color: {color}; background: transparent;")
        animation.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def reset_scan_display(self):
        if self.scanning_enabled:
            self.scan_label.setText("SCANNING...")
            self.scan_label.setStyleSheet("""
                font-size: 17px;
                font-weight: bold;
                color: #ffffff;
                padding: 4px;
                background: transparent;
            """)
            self.scan_icon.setText("🔍")
            self.scan_icon.setStyleSheet("""
                font-size: 48px;
                color: #70a1ff;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            """)
            self.tag_display.setText("")
            self.tag_display.setStyleSheet("""
                color: #70a1ff;
                border-color: #3742fa;
                background-color: rgba(30, 30, 45, 0.8);
            """)

    def add_activity(self, message, type_="info"):
        timestamp = time.strftime("%H:%M:%S")
        item = QListWidgetItem(f"[{timestamp}] {message}")
        
        if type_ == "success":
            item.setForeground(QColor("#1dd1a1"))
        elif type_ == "error":
            item.setForeground(QColor("#ff4757"))
        elif type_ == "info":
            item.setForeground(QColor("#70a1ff"))
            
        self.activity_list.insertItem(0, item)
        
        # Keep only last 6 items (more compact)
        if self.activity_list.count() > 6:
            self.activity_list.takeItem(6)

    # -------------------------
    # SETTINGS LOGIC
    # -------------------------
    def refresh_ports(self):
        self.port_combo.clear()
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            self.port_combo.addItem("No ports available")
            self.port_combo.setEnabled(False)
        else:
            for p in ports:
                self.port_combo.addItem(f"{p.device} - {p.description}")
            self.port_combo.setEnabled(True)

    def load_tags(self):
        self.tag_list.clear()
        for tag in self.allowed_tags:
            self.tag_list.addItem(tag)

    def add_new_tag(self):
        tag = self.new_tag_input.text().strip()
        if not tag:
            self.show_message_dialog("Empty Tag", "Please enter a tag ID.")
            return
            
        if tag in self.allowed_tags:
            self.show_message_dialog("Duplicate Tag", "This tag is already in the list.")
            return
        
        # Add to JSON file and memory
        if self.add_tag_to_json(tag):
            self.tag_list.addItem(tag)
            self.new_tag_input.clear()
            self.add_activity(f"➕ Tag added: {tag}", "info")
        else:
            self.show_message_dialog("Error", "Failed to add tag to storage.")

    def remove_selected_tag(self):
        selected = self.tag_list.currentItem()
        if selected:
            tag = selected.text()
            
            # Create custom dialog with app theme
            dialog = QDialog(self)
            dialog.setWindowTitle("")
            dialog.setFixedSize(380, 180)
            dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
            
            # Match app theme
            dialog.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                stop:0 rgba(13, 13, 21, 220), 
                                                stop:1 rgba(26, 26, 46, 220));
                    border: 2px solid #ff4757;
                    border-radius: 12px;
                }
                QLabel {
                    color: #ffffff;
                    font-size: 15px;
                    font-weight: bold;
                    padding: 8px;
                    background: transparent;
                }
            """)
            
            # Layout
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(25, 25, 25, 25)
            layout.setSpacing(20)
            
            # Message label
            message = QLabel(f"Remove tag '{tag}'?")
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            message.setWordWrap(True)
            
            # Button layout
            button_layout = QHBoxLayout()
            button_layout.setSpacing(25)
            
            # No button
            no_btn = QPushButton("NO")
            no_btn.setFixedSize(100, 40)
            no_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #3742fa, stop:1 #5352ed);
                    color: white;
                    font-size: 13px;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #5352ed, stop:1 #6c5ce7);
                    border: 2px solid #70a1ff;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #2c34c9, stop:1 #1a23a5);
                }
            """)
            
            # Yes button
            yes_btn = QPushButton("YES")
            yes_btn.setFixedSize(100, 40)
            yes_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #ff6b6b, stop:1 #ee5a52);
                    color: white;
                    font-size: 13px;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #ff5252, stop:1 #ff3838);
                    border: 2px solid #ff6b6b;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #c0392b, stop:1 #a93226);
                }
            """)
            
            button_layout.addStretch()
            button_layout.addWidget(no_btn)
            button_layout.addWidget(yes_btn)
            button_layout.addStretch()
            
            # Connect buttons
            def on_yes():
                try:
                    # Remove from JSON file and memory
                    if self.remove_tag_from_json(tag):
                        self.tag_list.takeItem(self.tag_list.row(selected))
                        self.add_activity(f"🗑️ Tag removed: {tag}", "info")
                    else:
                        self.add_activity(f"⚠️ Failed to remove: {tag}", "error")
                except ValueError:
                    pass  # Tag was already removed
                dialog.accept()
            
            def on_no():
                dialog.reject()
            
            yes_btn.clicked.connect(on_yes)
            no_btn.clicked.connect(on_no)
            
            # Also close on Escape key
            def on_key_press(event):
                if event.key() == Qt.Key.Key_Escape:
                    dialog.reject()
                else:
                    QDialog.keyPressEvent(dialog, event)
            
            dialog.keyPressEvent = on_key_press
            
            # Add widgets to dialog
            layout.addWidget(message)
            layout.addLayout(button_layout)
            
            # Show dialog centered
            dialog.exec()

    # -------------------------
    # Page Navigation
    # -------------------------
    def show_main_screen(self):
        self.main_layout.setCurrentWidget(self.main_screen)

    def open_settings_panel(self):
        self.main_layout.setCurrentWidget(self.settings_panel)
        self.refresh_ports()
        self.load_tags()

    def close_settings_panel(self):
        self.show_main_screen()

    def closeEvent(self, event):
        if self.esp:
            self.esp.close()
        event.accept()


# Run App
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Set application icon (fallback if file doesn't exist)
    if not QIcon.themeName():
        app_icon = QIcon.fromTheme("application-icon")
        app.setWindowIcon(app_icon)
    
    window = RFIDApp()
    window.show()
    sys.exit(app.exec())
