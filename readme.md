# 🤖 Polygon AI Agent - Final Project README

This project is a fully operational **Telegram AI Agent** that interacts with the **Polygon blockchain** through a **Safe (Gnosis) multisig wallet**, powered by **OpenAI** for real-time transaction moderation.

## 🚀 Overview
This AI-powered Telegram bot allows users to:

- Check the current MATIC balance of a Safe
- Send MATIC from the Safe to another address
- Automatically get approval or rejection from an AI guard before sending
- Understand its own capabilities via `/about` and `/start`
- Answer natural-language questions using GPT-4

---

## 🧠 Core Technologies Used
| Stack | Description |
|-------|-------------|
| **Python** | Main programming language |
| **Web3.py** | Blockchain interaction with Polygon RPC |
| **Safe-eth-py** | Official Gnosis Safe SDK |
| **OpenAI GPT-4** | AI decision-making and chat |
| **Telegram Bot API** | User interaction platform |
| **dotenv** | Securely manage environment variables |

---

## ⚙️ Setup Instructions

### 1. 🔐 Create `.env` File
```
BOT_TOKEN=your_telegram_bot_token
SAFE_ADDRESS=your_safe_address
SAFE_OWNER_KEY=private_key_of_safe_owner
POLYGON_RPC=https://polygon-rpc.com
OPENAI_KEY=your_openai_api_key
```

### 2. 📦 Install Requirements
Create a virtual environment (recommended), then install:
```bash
pip install -r requirements.txt
```

**requirements.txt**:
```txt
openai>=1.0.0
requests
python-dotenv
web3>=6.0.0
eth-account>=0.9.0
python-telegram-bot==20.7
git+https://github.com/safe-global/safe-eth-py.git
```

### 3. ▶️ Run the Bot
```bash
python bot.py
```

---

## 💡 Bot Commands and Features

### `/start`
Introduces the bot and gives users a starting point.

### `/about`
Explains the bot's features and how it ensures secure transactions.

### `/balance`
Fetches and displays the current MATIC balance of the Safe wallet.

### `/send <amount> <wallet_address>`
Sends MATIC to a recipient address **only after AI approval**.

The AI guard will check:
- If the amount is **less than or equal to 5 MATIC**
- If the address is **not suspicious** (e.g., not too short, not a zero address)

If approved, the bot:
- Builds a Safe transaction
- Signs it using the owner's private key
- Submits it to the Safe API
- Executes it if the Safe threshold is 1

---

## 🧠 AI Guard Logic
Uses OpenAI GPT-4 with a simple rule-based prompt to determine if a transaction is safe:

> If amount ≤ 5 MATIC and address looks normal ➔ YES  
> If amount > 5 or address is suspicious ➔ NO

This allows for basic fraud protection before executing transactions.

---

## 🧠 Natural Language Chat
Any message that isn't a command will be passed to GPT-4:
- Users can ask "What can you do?"
- "How do I send MATIC?"
- Or any general question

The bot replies contextually as a helpful AI wallet assistant.

---

## 🔗 How Safe Transactions Work
1. The bot builds a Safe-compatible multisig transaction
2. It signs it using the owner private key
3. Sends the signed tx to Safe's Polygon backend API
4. If threshold == 1, it immediately executes the transaction

---

## 🛠️ Functions Breakdown

### `get_safe_nonce_from_service(safe_address)`
Fetches the current transaction nonce from Safe’s backend.

### `initiate_safe_tx(matic_amount, to_address)`
Builds, signs, and posts the transaction. Executes it if needed.

### `execute_safe_transaction(tx, signature, owner)`
Sends the signed transaction directly to the blockchain.

### `ai_guard(amount, recipient)`
Uses OpenAI to determine if a transaction is safe to proceed with.

### `check_wallet_balance()`
Returns the MATIC balance of the Safe.

### `handle_send()`
Handles the entire `/send` command logic — from AI check to execution.

### `handle_general_message()`
Chat handler for general user messages (non-command). Powered by GPT-4.

---

## ✅ Security Notes
- The private key is loaded securely from `.env` and never exposed
- Transactions must be signed and optionally executed depending on the Safe threshold
- AI logic is intentionally simple — real deployments should incorporate blacklist checks, anomaly detection, and user whitelisting

---

## 📈 Future Improvements
- Inline button confirmation ("Approve? Yes/No")
- Add support for transaction history (/history)
- Role-based controls (only allow certain Telegram users to send)
- Advanced AI security policies (learn from past TX patterns)
- NFT or ERC20 transfer capabilities

---

## 🧪 Testing
To test safely:
- Use a Safe deployed on Polygon Mumbai Testnet
- Replace `POLYGON_RPC` with a testnet RPC (e.g. Alchemy or Infura)
- Create a test wallet and load test MATIC

---

## 🏁 Final Notes
This bot showcases how AI agents can integrate with decentralized infrastructure in real time. By using GPT-4 as a logic layer and Gnosis Safe for secure execution, this project is a small but powerful step toward intelligent, autonomous blockchain apps.

---

## 📬 Contact / Questions
For issues or improvements, feel free to open a GitHub issue or message me on Telegram.

Happy building! ⚒️

