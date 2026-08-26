// NexaBank Web App Core JavaScript
let currentUser = null;
let userAccounts = [];
let cashflowChart = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    lucide.createIcons();
    await checkAuth();
    if (currentUser) {
        await refreshDashboard();
        updateLoanCalc();
    }
}

function getToken() {
    return localStorage.getItem('nexabank_token');
}

async function apiRequest(endpoint, method = 'GET', body = null) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const config = { method, headers };
    if (body) config.body = JSON.stringify(body);

    const res = await fetch(endpoint, config);
    if (res.status === 401) {
        localStorage.removeItem('nexabank_token');
        localStorage.removeItem('nexabank_user');
        window.location.href = '/login';
        return null;
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'An error occurred');
    return data;
}

async function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = '/login';
        return;
    }
    try {
        currentUser = await apiRequest('/api/auth/me');
        if (!currentUser) return;
        
        document.getElementById('user-name-sidebar').innerText = currentUser.full_name;
        document.getElementById('user-email-sidebar').innerText = currentUser.email;
        const initials = currentUser.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        document.getElementById('user-avatar').innerText = initials || 'NB';

        const pinBadge = document.getElementById('pin-badge');
        if (currentUser.has_pin) {
            pinBadge.classList.remove('hidden');
            pinBadge.classList.add('flex');
        } else {
            pinBadge.classList.add('hidden');
        }
    } catch (err) {
        console.error('Auth verification error:', err);
        window.location.href = '/login';
    }
}

function handleLogout() {
    localStorage.removeItem('nexabank_token');
    localStorage.removeItem('nexabank_user');
    window.location.href = '/login';
}

function navigate(viewName) {
    const views = ['dashboard', 'accounts', 'transfer', 'deposit', 'loans', 'ai'];
    views.forEach(v => {
        const sec = document.getElementById(`view-${v}`);
        const nav = document.getElementById(`nav-${v}`);
        if (sec) sec.classList.add('hidden');
        if (nav) nav.classList.remove('active-nav');
    });

    const activeSec = document.getElementById(`view-${viewName}`);
    const activeNav = document.getElementById(`nav-${viewName}`);
    if (activeSec) activeSec.classList.remove('hidden');
    if (activeNav) activeNav.classList.add('active-nav');

    const titles = {
        'dashboard': 'Overview',
        'accounts': 'Bank Accounts',
        'transfer': 'Transfer Funds',
        'deposit': 'Deposit & Withdrawal',
        'loans': 'Loans & Credit Portfolio',
        'ai': 'NexaAI Assistant'
    };
    document.getElementById('header-title').innerText = titles[viewName] || 'Dashboard';

    if (viewName === 'accounts') renderFullAccounts();
    if (viewName === 'loans') loadLoans();
    
    lucide.createIcons();
}

async function refreshDashboard() {
    try {
        await loadAccounts();
        await loadSummary();
        await loadTransactions();
        lucide.createIcons();
    } catch (err) {
        console.error('Failed to load dashboard:', err);
    }
}

async function loadAccounts() {
    const data = await apiRequest('/api/accounts');
    userAccounts = data.accounts || [];

    const listEl = document.getElementById('dashboard-accounts-list');
    if (userAccounts.length === 0) {
        listEl.innerHTML = '<div class="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-slate-400 text-xs text-center">No accounts open yet. Open your first account!</div>';
    } else {
        listEl.innerHTML = userAccounts.map(a => `
            <div class="p-4 rounded-2xl glass-card border border-slate-800 flex items-center justify-between hover:border-cyan-500/30 transition-all">
                <div class="flex items-center gap-3">
                    <div class="p-2.5 rounded-xl ${a.account_type === 'CHECKING' ? 'bg-cyan-500/10 text-cyan-400' : (a.account_type === 'SAVINGS' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-indigo-500/10 text-indigo-400')}">
                        <i data-lucide="${a.account_type === 'CHECKING' ? 'credit-card' : (a.account_type === 'SAVINGS' ? 'piggy-bank' : 'briefcase')}" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-bold text-white">${a.account_type}</span>
                            <span class="text-[10px] text-slate-400 font-mono">...${a.account_number.slice(-4)}</span>
                        </div>
                        <p class="text-xs text-slate-400">Available Balance</p>
                    </div>
                </div>
                <div class="text-right">
                    <span class="text-sm font-extrabold text-white">$${a.balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                </div>
            </div>
        `).join('');
    }

    const selectIds = ['transfer-source', 'deposit-account', 'withdraw-account', 'repay-source-account'];
    selectIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = userAccounts.map(a => `
                <option value="${a.id}">${a.account_type} (${a.account_number}) - $${a.balance.toFixed(2)}</option>
            `).join('');
        }
    });

    renderFullAccounts();
}

function renderFullAccounts() {
    const grid = document.getElementById('full-accounts-grid');
    if (!grid) return;
    if (userAccounts.length === 0) {
        grid.innerHTML = '<div class="col-span-3 text-center py-12 text-slate-500 text-sm">No accounts found. Click "Open New Account" to get started.</div>';
        return;
    }
    grid.innerHTML = userAccounts.map(a => `
        <div class="glass-card rounded-3xl p-6 relative overflow-hidden flex flex-col justify-between h-52 bg-gradient-to-br from-slate-900/90 to-slate-950/90 border border-slate-800">
            <div class="flex items-start justify-between">
                <div>
                    <span class="text-xs font-bold uppercase tracking-wider text-cyan-400">${a.account_type} ACCOUNT</span>
                    <h4 class="text-2xl font-black text-white mt-1">$${a.balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                </div>
                <div class="p-2.5 rounded-xl bg-slate-800/80 text-cyan-400">
                    <i data-lucide="landmark" class="w-5 h-5"></i>
                </div>
            </div>

            <div class="flex items-end justify-between pt-4 border-t border-slate-800/80">
                <div>
                    <span class="text-[10px] uppercase tracking-wider text-slate-500 block">Account Number</span>
                    <span class="text-sm font-mono font-bold text-slate-200 tracking-wider">${a.account_number}</span>
                </div>
                <button onclick="copyText('${a.account_number}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 transition-all">
                    <i data-lucide="copy" class="w-3 h-3"></i> Copy
                </button>
            </div>
        </div>
    `).join('');
    lucide.createIcons();
}

async function loadSummary() {
    const summary = await apiRequest('/api/transactions/summary');
    if (!summary) return;

    document.getElementById('metric-total-balance').innerText = `$${summary.total_balance.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('metric-accounts-count').innerText = `${summary.accounts_count} Accounts`;
    document.getElementById('metric-inflow').innerText = `+$${summary.total_inflow_30d.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('metric-outflow').innerText = `-$${summary.total_outflow_30d.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

    const ctx = document.getElementById('cashflowChart');
    if (ctx && summary.chart_data) {
        const labels = summary.chart_data.map(d => d.date);
        const incomeData = summary.chart_data.map(d => d.income);
        const expenseData = summary.chart_data.map(d => d.expense);

        if (cashflowChart) cashflowChart.destroy();

        cashflowChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Inflow ($)',
                        data: incomeData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Outflow ($)',
                        data: expenseData,
                        borderColor: '#f43f5e',
                        backgroundColor: 'rgba(244, 63, 94, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: {
                    x: { grid: { color: '#1e293b' }, ticks: { color: '#64748b' } },
                    y: { grid: { color: '#1e293b' }, ticks: { color: '#64748b' } }
                }
            }
        });
    }
}

async function loadTransactions() {
    const data = await apiRequest('/api/transactions/history?limit=15');
    const tbody = document.getElementById('dashboard-transactions-tbody');
    if (!tbody) return;

    if (!data.transactions || data.transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="py-8 text-center text-slate-500">No transaction activity recorded yet.</td></tr>';
        return;
    }

    tbody.innerHTML = data.transactions.map(t => {
        const isPositive = t.amount > 0 && t.transaction_type !== 'WITHDRAWAL';
        return `
            <tr class="hover:bg-slate-900/40 transition-colors">
                <td class="py-3.5 flex items-center gap-3">
                    <div class="p-2 rounded-xl ${isPositive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}">
                        <i data-lucide="${isPositive ? 'arrow-down-left' : 'arrow-up-right'}" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <span class="font-bold text-white block text-xs">${t.transaction_type}</span>
                        <span class="text-[11px] text-slate-400 font-mono">Acc: ${t.account_number}</span>
                    </div>
                </td>
                <td class="py-3.5 text-slate-300 text-xs max-w-xs truncate">${t.description || '-'}</td>
                <td class="py-3.5 text-slate-400 text-xs">${t.created_at}</td>
                <td class="py-3.5 text-right font-extrabold text-xs ${isPositive ? 'text-emerald-400' : 'text-rose-400'}">
                    ${isPositive ? '+' : '-'}$${Math.abs(t.amount).toLocaleString('en-US', {minimumFractionDigits: 2})}
                </td>
            </tr>
        `;
    }).join('');
    lucide.createIcons();
}

async function executeTransfer() {
    const btn = document.getElementById('btn-transfer-submit');
    const from_account_id = document.getElementById('transfer-source').value;
    const to_account_number = document.getElementById('transfer-recipient').value;
    const amount = parseFloat(document.getElementById('transfer-amount').value);
    const note = document.getElementById('transfer-note').value;
    const pin = document.getElementById('transfer-pin').value;

    if (!to_account_number || isNaN(amount) || amount <= 0 || !pin) {
        alert('Please fill in all required transfer fields and Security PIN.');
        return;
    }

    try {
        btn.disabled = true;
        btn.innerHTML = '<span class="animate-spin mr-2">⏳</span> Authorizing Transfer...';

        const res = await apiRequest('/api/transactions/transfer', 'POST', {
            from_account_id, to_account_number, amount, note, pin
        });

        alert(`✅ ${res.message}`);
        document.getElementById('transfer-recipient').value = '';
        document.getElementById('transfer-amount').value = '';
        document.getElementById('transfer-note').value = '';
        document.getElementById('transfer-pin').value = '';
        navigate('dashboard');
        await refreshDashboard();
    } catch (err) {
        alert(`❌ ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="send" class="w-4 h-4"></i> Confirm & Send Transfer';
        lucide.createIcons();
    }
}

async function handleDeposit() {
    const account_id = document.getElementById('deposit-account').value;
    const amount = parseFloat(document.getElementById('deposit-amount').value);
    const pin = document.getElementById('deposit-pin').value;

    if (isNaN(amount) || amount <= 0 || !pin) {
        alert('Please enter a valid amount and your Security PIN.');
        return;
    }

    try {
        const res = await apiRequest('/api/transactions/deposit', 'POST', {
            account_id, amount, pin, description: 'Web Instant Deposit'
        });
        alert(`✅ ${res.message}`);
        document.getElementById('deposit-amount').value = '';
        document.getElementById('deposit-pin').value = '';
        navigate('dashboard');
        await refreshDashboard();
    } catch (err) {
        alert(`❌ ${err.message}`);
    }
}

async function handleWithdraw() {
    const account_id = document.getElementById('withdraw-account').value;
    const amount = parseFloat(document.getElementById('withdraw-amount').value);
    const pin = document.getElementById('withdraw-pin').value;

    if (isNaN(amount) || amount <= 0 || !pin) {
        alert('Please enter a valid amount and your Security PIN.');
        return;
    }

    try {
        const res = await apiRequest('/api/transactions/withdraw', 'POST', {
            account_id, amount, pin, description: 'Web ATM Withdrawal'
        });
        alert(`✅ ${res.message}`);
        document.getElementById('withdraw-amount').value = '';
        document.getElementById('withdraw-pin').value = '';
        navigate('dashboard');
        await refreshDashboard();
    } catch (err) {
        alert(`❌ ${err.message}`);
    }
}

function updateLoanCalc() {
    const principal = parseFloat(document.getElementById('loan-amount-range').value);
    const tenure = parseInt(document.getElementById('loan-tenure-range').value);
    document.getElementById('calc-amount-label').innerText = principal.toLocaleString();
    document.getElementById('calc-tenure-label').innerText = tenure;

    const rate = 8.5;
    const r = (rate / 100) / 12;
    const emi = (principal * r * Math.pow(1 + r, tenure)) / (Math.pow(1 + r, tenure) - 1);
    const totalPayable = emi * tenure;
    const totalInterest = totalPayable - principal;

    document.getElementById('calc-emi').innerText = `$${emi.toFixed(2)}`;
    document.getElementById('calc-interest').innerText = `$${totalInterest.toFixed(2)}`;
    document.getElementById('calc-total').innerText = `$${totalPayable.toFixed(2)}`;
}

async function applyLoan() {
    const principal = parseFloat(document.getElementById('loan-amount-range').value);
    const tenure_months = parseInt(document.getElementById('loan-tenure-range').value);
    const purpose = document.getElementById('loan-purpose').value || 'Personal Loan';

    try {
        const res = await apiRequest('/api/loans/apply', 'POST', {
            principal, tenure_months, purpose, annual_rate: 8.5
        });
        alert(`🎉 ${res.message}`);
        document.getElementById('loan-purpose').value = '';
        loadLoans();
    } catch (err) {
        alert(`❌ ${err.message}`);
    }
}

async function loadLoans() {
    const data = await apiRequest('/api/loans');
    const listEl = document.getElementById('active-loans-list');
    if (!listEl) return;

    if (!data.loans || data.loans.length === 0) {
        listEl.innerHTML = '<div class="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 text-slate-400 text-xs text-center">No active loans. Calculate EMI and apply on the left!</div>';
        return;
    }

    listEl.innerHTML = data.loans.map(l => `
        <div class="p-5 rounded-2xl glass-card border border-slate-800 space-y-3">
            <div class="flex items-center justify-between">
                <div>
                    <h5 class="text-sm font-bold text-white">${l.purpose}</h5>
                    <span class="text-[11px] text-slate-400">Principal: $${l.principal.toLocaleString()} @ ${l.annual_rate}%</span>
                </div>
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold ${l.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}">
                    ${l.status}
                </span>
            </div>

            <div class="flex items-center justify-between text-xs pt-2 border-t border-slate-800/80">
                <div>
                    <span class="text-slate-500 block text-[10px]">Outstanding Balance</span>
                    <span class="font-extrabold text-cyan-400 text-sm">$${l.outstanding_balance.toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
                </div>
                <div>
                    <span class="text-slate-500 block text-[10px]">Monthly EMI</span>
                    <span class="font-bold text-white text-xs">$${l.emi_amount.toFixed(2)}</span>
                </div>
                ${l.status === 'ACTIVE' ? `
                    <button onclick="openRepayModal('${l.id}', ${l.emi_amount})" class="px-3 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-lg transition-all">
                        Pay EMI
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
    lucide.createIcons();
}

function openRepayModal(loanId, emiAmount) {
    document.getElementById('repay-loan-id').value = loanId;
    document.getElementById('repay-amount').value = emiAmount.toFixed(2);
    document.getElementById('modal-repay-loan').classList.remove('hidden');
}

function closeRepayModal() {
    document.getElementById('modal-repay-loan').classList.add('hidden');
}

async function submitRepayment() {
    const loan_id = document.getElementById('repay-loan-id').value;
    const account_id = document.getElementById('repay-source-account').value;
    const amount = parseFloat(document.getElementById('repay-amount').value);
    const pin = document.getElementById('repay-pin').value;

    if (!pin || isNaN(amount) || amount <= 0) {
        alert('Please enter valid repayment amount and Security PIN.');
        return;
    }

    try {
        const res = await apiRequest('/api/loans/repay', 'POST', { loan_id, account_id, amount, pin });
        alert(`✅ ${res.message}`);
        closeRepayModal();
        loadLoans();
        refreshDashboard();
    } catch (err) {
        alert(`❌ ${err.message}`);
    }
}

let aiChatSessionId = null;

function insertAiPrompt(text) {
    document.getElementById('ai-chat-input').value = text;
    sendAiMessage();
}

async function sendAiMessage() {
    const input = document.getElementById('ai-chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    const container = document.getElementById('ai-chat-messages');

    container.innerHTML += `
        <div class="flex items-start justify-end gap-3">
            <div class="p-4 rounded-2xl rounded-tr-none bg-gradient-to-r from-cyan-600 to-indigo-600 text-white text-sm leading-relaxed shadow-lg max-w-xl">
                ${escapeHtml(msg)}
            </div>
        </div>
    `;
    container.scrollTop = container.scrollHeight;

    const typingId = 'typing-' + Date.now();
    container.innerHTML += `
        <div id="${typingId}" class="flex items-start gap-3 max-w-2xl">
            <div class="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 flex items-center justify-center flex-shrink-0 mt-0.5">
                <i data-lucide="bot" class="w-4 h-4"></i>
            </div>
            <div class="p-3.5 rounded-2xl rounded-tl-none bg-slate-900 border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
                <span class="animate-bounce">●</span><span class="animate-bounce delay-100">●</span><span class="animate-bounce delay-200">●</span> NexaAI is thinking...
            </div>
        </div>
    `;
    container.scrollTop = container.scrollHeight;
    lucide.createIcons();

    try {
        const res = await apiRequest('/api/ai/chat', 'POST', { message: msg, session_id: aiChatSessionId });
        aiChatSessionId = res.session_id;
        document.getElementById(typingId)?.remove();

        container.innerHTML += `
            <div class="flex items-start gap-3 max-w-2xl">
                <div class="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <i data-lucide="bot" class="w-4 h-4"></i>
                </div>
                <div class="p-4 rounded-2xl rounded-tl-none bg-slate-900 border border-slate-800 text-sm text-slate-200 leading-relaxed shadow-lg whitespace-pre-wrap">
                    ${escapeHtml(res.reply)}
                </div>
            </div>
        `;
        container.scrollTop = container.scrollHeight;
        lucide.createIcons();
    } catch (err) {
        document.getElementById(typingId)?.remove();
        container.innerHTML += `
            <div class="p-3 text-xs text-rose-400 bg-rose-500/10 rounded-xl border border-rose-500/30">
                Error getting response: ${err.message}
            </div>
        `;
    }
}

function openPinModal() { document.getElementById('modal-pin').classList.remove('hidden'); }
function closePinModal() { document.getElementById('modal-pin').classList.add('hidden'); }

async function savePin() {
    const pin = document.getElementById('modal-pin-input').value;
    if (!pin || pin.length < 4) {
        alert('PIN must be 4–6 digits.');
        return;
    }
    try {
        const res = await apiRequest('/api/auth/pin/set', 'POST', { pin });
        alert(`✅ ${res.message}`);
        closePinModal();
        checkAuth();
    } catch (err) {
        alert(`❌ ${err.message}`);
    }
}

function openNewAccountModal() { document.getElementById('modal-new-account').classList.remove('hidden'); }
function closeNewAccountModal() { document.getElementById('modal-new-account').classList.add('hidden'); }

async function submitNewAccount() {
    const account_type = document.getElementById('new-account-type').value;
    const initial_deposit = parseFloat(document.getElementById('new-account-deposit').value) || 0;

    try {
        const res = await apiRequest('/api/accounts/open', 'POST', { account_type, initial_deposit });
        alert(`✅ ${res.message}`);
        closeNewAccountModal();
        refreshDashboard();
    } catch (err) {
        alert(`❌ ${err.message}`);
    }
}

function copyText(txt) {
    navigator.clipboard.writeText(txt);
    alert(`Copied Account Number: ${txt}`);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}
