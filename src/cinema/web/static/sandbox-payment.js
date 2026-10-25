import {api, getConfig, initializeAuth, setStatus} from './api.js';

const endpoint = '/api/customer/payments/sandbox-checkout';
const storageKey = 'cinema-paddle-sandbox-transaction';
let transactionId = null;
let completed = false;
const openButton = document.querySelector('#open-checkout');
const verifyButton = document.querySelector('#verify-payment');

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const config = await getConfig();
    if (!config.paddle?.enabled || config.paddle.environment !== 'sandbox' ||
        !config.paddle.clientToken.startsWith('test_')) {
      throw new Error('תשלום Sandbox אינו מוגדר בפרופיל הפעיל');
    }
    await initializeAuth(document.querySelector('#auth-controls'));
    await loadPaddle();
    window.Paddle.Environment.set('sandbox');
    window.Paddle.Initialize({token: config.paddle.clientToken, eventCallback: checkoutEvent});
    transactionId = sessionStorage.getItem(storageKey);
    if (transactionId && !/^txn_[a-z0-9]{26}$/.test(transactionId)) transactionId = null;
    showReference();
    openButton.disabled = false;
    verifyButton.disabled = !transactionId;
    setStatus('סביבת הבדיקה מוכנה. לא יתבצע חיוב אמיתי.');
  } catch (error) { setStatus(error.message, true); }
});

openButton.addEventListener('click', async () => {
  openButton.disabled = true;
  try {
    // Reuse an unfinished checkout instead of creating duplicates after closing it.
    if (transactionId) {
      const previous = await api(`${endpoint}/${transactionId}`);
      if (['completed', 'canceled'].includes(previous.status)) transactionId = null;
    }
    if (!transactionId) {
      const transaction = await api(endpoint, {method: 'POST'});
      transactionId = transaction.transaction_id;
      sessionStorage.setItem(storageKey, transactionId);
    }
    completed = false;
    showReference();
    verifyButton.disabled = false;
    setStatus('פותח חלון תשלום ב־Sandbox…');
    window.Paddle.Checkout.open({
      transactionId,
      settings: {displayMode: 'overlay', showAddDiscounts: false, allowedPaymentMethods: ['card']},
    });
  } catch (error) {
    setStatus(error.message, true);
    openButton.disabled = false;
  }
});

verifyButton.addEventListener('click', verifyPayment);

async function verifyPayment() {
  if (!transactionId) return;
  verifyButton.disabled = true;
  try {
    const transaction = await api(`${endpoint}/${transactionId}`);
    completed = transaction.status === 'completed';
    setStatus(completed
      ? 'Paddle אישר בשרת: תשלום הבדיקה הושלם. לא בוצע חיוב אמיתי.'
      : `סטטוס העסקה ב־Paddle: ${transaction.status}. אפשר לבדוק שוב בעוד כמה שניות.`);
  } catch (error) { setStatus(error.message, true); }
  finally { verifyButton.disabled = false; }
}

function checkoutEvent(event) {
  if (event.name === 'checkout.completed') {
    setStatus('התשלום הסתיים בחלון. בודק אישור מול Paddle…');
    void verifyPayment();
  } else if (event.name === 'checkout.closed') {
    openButton.disabled = false;
    if (!completed) setStatus('חלון התשלום נסגר. אפשר לפתוח שוב או לבדוק סטטוס.');
  } else if (['checkout.error', 'checkout.payment.failed', 'checkout.payment.error'].includes(event.name)) {
    openButton.disabled = false;
    setStatus('תשלום הבדיקה לא הושלם. בדקו את פרטי כרטיס הבדיקה ונסו שוב.', true);
  }
}

function showReference() {
  document.querySelector('#transaction-reference').textContent = transactionId ? `עסקת בדיקה: ${transactionId}` : '';
}

function loadPaddle() {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.paddle.com/paddle/v2/paddle.js';
    script.addEventListener('load', resolve, {once: true});
    script.addEventListener('error', () => reject(new Error('טעינת Paddle נכשלה')), {once: true});
    document.head.append(script);
  });
}
