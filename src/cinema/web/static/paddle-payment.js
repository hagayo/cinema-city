import {getConfig, setStatus} from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const config = (await getConfig()).paddlePaymentLink;
    if (!config?.enabled || !config.clientToken.startsWith('test_')) {
      throw new Error('עמוד תשלום הבדיקה אינו מופעל');
    }
    const transactionId = new URLSearchParams(window.location.search).get('_ptxn');
    if (transactionId !== null && !/^txn_[a-z0-9]{26}$/.test(transactionId)) {
      throw new Error('קישור עסקת הבדיקה אינו תקין');
    }
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.paddle.com/paddle/v2/paddle.js';
      script.addEventListener('load', resolve, {once: true});
      script.addEventListener('error', () => reject(new Error('טעינת Paddle נכשלה')), {once: true});
      document.head.append(script);
    });
    window.Paddle.Environment.set('sandbox');
    // Paddle.js automatically opens the transaction supplied through _ptxn.
    // This page never creates transactions or treats browser events as server confirmation.
    window.Paddle.Initialize({
      token: config.clientToken,
      eventCallback(event) {
        if (event.name === 'checkout.completed') {
          setStatus('התשלום הסתיים בחלון הבדיקה. ניתן לאמת את סטטוס העסקה במערכת שממנה התחלתם.');
        } else if (event.name === 'checkout.closed') {
          setStatus('חלון הבדיקה נסגר. אפשר לחזור למערכת שממנה התחלתם לבדיקת סטטוס.');
        } else if (['checkout.error', 'checkout.payment.failed', 'checkout.payment.error'].includes(event.name)) {
          setStatus('לא ניתן להשלים את תשלום הבדיקה. בדקו את הקישור ופרטי כרטיס הבדיקה.', true);
        }
      },
    });
    setStatus(transactionId
      ? 'פותח את עסקת הבדיקה ב־Paddle Sandbox…'
      : 'עמוד Sandbox מוכן. לפתיחת תשלום, השתמשו בקישור העסקה שקיבלתם ממערכת הבדיקה.');
  } catch (error) { setStatus(error.message, true); }
});
