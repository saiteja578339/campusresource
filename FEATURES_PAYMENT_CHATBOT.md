# Payment Option and AI Chatbot

## 1. Payment option

The project includes an academic payment simulation so the complete workflow can be demonstrated without real bank credentials.

- Open any active listing that belongs to another user.
- Select **Pay / Reserve**.
- Choose **UPI**, **Card**, **Wallet**, or **Net Banking**.
- Django creates a `Payment` record with a transaction reference.
- The listing status changes from `active` to `reserved`.
- Buyer and seller receive notifications.
- Open **Payments** in the navigation menu to view payment history.

Important: no real money is charged. A production version would replace `demo_checkout` with a verified provider such as Razorpay or Stripe and would validate provider webhooks.

## 2. AI chatbot

Open **AI Assistant** in the navigation menu. The chatbot can:

- find active listings using natural-language questions;
- filter results using a budget such as “under ₹800”;
- explain payment, pricing, image analysis, fraud safety, and listing creation;
- return links to matching marketplace items.

### Algorithm

The chatbot is a retrieval-based AI system written in Python:

1. Student text is normalized.
2. FAQ knowledge and active listing text are converted into TF-IDF vectors.
3. Cosine similarity compares the question with every knowledge item.
4. The best FAQ response or top matching listings are returned.
5. The latest conversation is stored in the Django session.

Main implementation files:

- `marketplace/ai/chatbot.py`
- `marketplace/views.py` — `ai_assistant`
- `marketplace/templates/marketplace/assistant.html`
- `marketplace/static/marketplace/app.js`

## Interview answer

> “The project has a simulated multi-method payment workflow and a retrieval-based AI chatbot. The payment module records UPI, card, wallet, or net-banking transactions in SQLite and reserves the listing. The chatbot uses TF-IDF and cosine similarity over marketplace FAQs and active listings, so it can answer help questions and recommend relevant items without requiring an external API.”
