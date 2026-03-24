from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QMessageBox
from PySide6.QtCore import QSize
from app.ui.widgets.navbar import NavBar
from app.ui.screens.login_screen import LoginScreen
from app.ui.screens.dashboard_screen import DashboardScreen
from app.ui.screens.accounts_screen import AccountsScreen
from app.ui.screens.deposit_screen import DepositScreen
from app.ui.screens.ai_mode_screen import AIModeScreen
from app.ui.screens.chatbot_screen import ChatbotScreen
from app.ui.screens.transfer_screen import TransferScreen
from app.ui.screens.transactions_screen import TransactionsScreen
from app.ui.screens.statement_screen import StatementScreen
from app.ui.screens.loan_screen import LoanScreen

BG = "#0b0f1a"

class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NexaBank")
        self.setMinimumSize(QSize(1200, 750))
        self.resize(1400, 860)
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG}; }}")
        self._build()

    def _build(self):
        central = QWidget()
        central.setStyleSheet(f"background-color: {BG};")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.navbar = NavBar()
        self.navbar.setFixedWidth(220)
        self.navbar.navigate.connect(self._switch)
        self.navbar.logout_requested.connect(self._logout)
        root.addWidget(self.navbar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {BG};")
        root.addWidget(self.stack, 1)

        # Screens
        self.login_screen = LoginScreen()
        self.login_screen.login_success.connect(self._on_login)

        self.dashboard    = DashboardScreen()
        self.dashboard.navigate.connect(self._switch)
        self.accounts     = AccountsScreen()
        self.deposit      = DepositScreen()
        self.ai_mode      = AIModeScreen()
        self.chatbot      = ChatbotScreen()
        self.transfer     = TransferScreen()
        self.transactions = TransactionsScreen()
        self.statement    = StatementScreen()
        self.loan         = LoanScreen()

        # Add to stack — order matters for index
        for w in [
            self.login_screen,   # 0
            self.dashboard,      # 1
            self.accounts,       # 2
            self.deposit,        # 3
            self.ai_mode,        # 4
            self.chatbot,        # 5
            self.transfer,       # 6
            self.transactions,   # 7
            self.statement,      # 8
            self.loan,           # 9
        ]:
            self.stack.addWidget(w)

        self.stack.setCurrentIndex(0)
        self.navbar.setVisible(False)

    def _on_login(self, user):
        self.navbar.setVisible(True)
        self.navbar.set_user(user)
        self._switch("dashboard")

    def _switch(self, name: str):
        mapping = {
            "dashboard":    (1,  self.dashboard),
            "accounts":     (2,  self.accounts),
            "deposit":      (3,  self.deposit),
            "ai_mode":      (4,  self.ai_mode),
            "chatbot":      (5,  self.chatbot),
            "transfer":     (6,  self.transfer),
            "transactions": (7,  self.transactions),
            "statement":    (8,  self.statement),
            "loan":         (9,  self.loan),
        }
        if name not in mapping: return
        idx, screen = mapping[name]
        if hasattr(screen, "refresh"): screen.refresh()
        self.stack.setCurrentIndex(idx)
        self.navbar.set_active(name)

    def _logout(self):
        if QMessageBox.question(self, "Logout", "Log out?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            from app.services.auth_service import logout_user
            logout_user()
            self.navbar.setVisible(False)
            self.stack.setCurrentIndex(0)