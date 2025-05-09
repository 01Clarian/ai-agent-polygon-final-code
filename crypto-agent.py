import os
import openai
import requests
from dotenv import load_dotenv
from web3 import Web3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from eth_account import Account
from safe_eth.eth import EthereumClient, EthereumNetwork
from safe_eth.safe.api.transaction_service_api import TransactionServiceApi
from safe_eth.safe import Safe
from web3.middleware import ExtraDataToPOAMiddleware

# ===📦 Load environment variables ===
load_dotenv()

# ===🔐 CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
SAFE_ADDRESS = os.getenv("SAFE_ADDRESS")
POLYGON_RPC = os.getenv("POLYGON_RPC")
OPENAI_KEY = os.getenv("OPENAI_KEY")
SAFE_OWNER_KEY = os.getenv("SAFE_OWNER_KEY")

# ===🔗 Polygon Web3 Setup ===
web3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

polygon_client = EthereumClient(POLYGON_RPC)

safe_instance = Safe(
    address=SAFE_ADDRESS,
    ethereum_client=polygon_client
)

owners = safe_instance.retrieve_owners()
threshold = safe_instance.retrieve_threshold()

safe_api = TransactionServiceApi(
    network=EthereumNetwork.GNOSIS,  # GNOSIS used as fallback for Polygon
    ethereum_client=polygon_client
)

# ===🔢 GET SAFE NONCE FROM BACKEND ===
def get_safe_nonce_from_service(safe_address):
    base_url = "https://safe-transaction-polygon.safe.global"
    response = requests.get(f"{base_url}/api/v1/safes/{safe_address}/")
    if response.status_code != 200:
        raise Exception(f"Error fetching Safe info: {response.text}")
    return response.json()["nonce"]

# ===💸 INITIATE SAFE TRANSACTION ===
def initiate_safe_tx(pol_amount, to_address):
    pol_wei = int(float(pol_amount) * 10**18)
    safe_nonce = get_safe_nonce_from_service(SAFE_ADDRESS)
    print(f"Using Safe nonce: {safe_nonce}")

    tx = safe_instance.build_multisig_tx(
        to=to_address,
        value=pol_wei,
        data=b"",
        operation=0,
        safe_nonce=safe_nonce
    )

    owner = Account.from_key(SAFE_OWNER_KEY)
    print("My address:", owner.address)
    print("tx.safe_tx_hash:", tx.safe_tx_hash.hex())

    signed = owner.unsafe_sign_hash(tx.safe_tx_hash)
    signature = (
        signed.r.to_bytes(32, byteorder="big") +
        signed.s.to_bytes(32, byteorder="big") +
        bytes([signed.v])
    )

    payload = {
        "to": tx.to,
        "value": tx.value,
        "data": tx.data.hex(),
        "operation": tx.operation,
        "safe_tx_gas": tx.safe_tx_gas,
        "base_gas": tx.base_gas,
        "gas_price": tx.gas_price,
        "gas_token": tx.gas_token,
        "refund_receiver": tx.refund_receiver,
        "nonce": tx.safe_nonce,
        "contract_transaction_hash": tx.safe_tx_hash.hex(),
        "sender": owner.address,
        "signature": "0x" + signature.hex(),
        "origin": "Telegram AI Agent"
    }

    response = requests.post(
        f"https://safe-transaction-polygon.safe.global/api/v1/safes/{SAFE_ADDRESS}/multisig-transactions/",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code not in [200, 201]:
        raise Exception(f"Error posting transaction: {response.text}")

    print("Posted TX hash:", tx.safe_tx_hash.hex())

    if threshold == 1:
        try:
            tx_hash = execute_safe_transaction(tx, signature, owner)
            print("Executed TX on-chain:", tx_hash)
        except Exception as exec_err:
            print("⚠️ Error executing transaction on-chain:", str(exec_err))

    return tx.safe_tx_hash.hex()

# ===🤖 EXECUTE SAFE TRANSACTION ===
def execute_safe_transaction(tx, signature, owner):
    safe_contract = web3.eth.contract(
        address=Web3.to_checksum_address(SAFE_ADDRESS),
        abi=safe_instance.contract.abi
    )

    tx_function = safe_contract.functions.execTransaction(
        tx.to,
        tx.value,
        tx.data,
        tx.operation,
        tx.safe_tx_gas,
        tx.base_gas,
        tx.gas_price,
        tx.gas_token,
        tx.refund_receiver,
        signature
    )

    tx_dict = tx_function.build_transaction({
        'from': owner.address,
        'nonce': web3.eth.get_transaction_count(owner.address),
        'gas': 300000,
        'maxFeePerGas': web3.to_wei(100, 'gwei'),
        'maxPriorityFeePerGas': web3.to_wei(30, 'gwei'),
        'chainId': web3.eth.chain_id
    })

    signed_tx = Account.sign_transaction(tx_dict, private_key=SAFE_OWNER_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"✅ On-chain TX Hash: {web3.to_hex(tx_hash)}")
    return web3.to_hex(tx_hash)

# ===🛡️ AI GUARD ===
def ai_guard(amount, recipient):
    openai.api_key = OPENAI_KEY

    prompt_text = f"""
    You are a blockchain wallet AI guard.
    A user wants to send {amount} POL to {recipient}.

    Reply with only "yes" or "no" based on:
    - If amount is ≤ 5 POL and the address does not look suspicious → say "yes"
    - If amount is greater than 5 POL, or the address looks suspicious → say "no"
    - Addresses are suspicious if they are short, zero addresses, or match known blacklists.
    """

    reply = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a secure crypto wallet AI."},
            {"role": "user", "content": prompt_text}
        ]
    )

    return reply.choices[0].message.content.strip().lower()

# ===📊 BALANCE COMMAND ===
async def check_wallet_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance = web3.eth.get_balance(SAFE_ADDRESS)
    pol = web3.from_wei(balance, "ether")
    await update.message.reply_text(f"🔹 Wallet Balance: {pol:.4f} POL")

# ===📤 SEND COMMAND ===
async def handle_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /send <amount> <wallet_address>")
        return

    pol = context.args[0]
    to_addr = context.args[1]

    decision = ai_guard(pol, to_addr)

    if decision == "yes":
        try:
            tx_hash = initiate_safe_tx(pol, to_addr)
            await update.message.reply_text(f"✅ Sent! TX Hash: {tx_hash}")
        except Exception as err:
            print("Error:", str(err))
            await update.message.reply_text("❌ Transaction failed. Check logs.")
    else:
        await update.message.reply_text("❌ AI declined this transaction for safety.")

# ===💬 ABOUT COMMAND ===
async def handle_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        "🤖 *I am your AI Wallet Assistant on Polygon!*\n\n"
        "I can:\n"
        "🔹 Check your wallet balance with /balance\n"
        "🔹 Send POL safely with AI verification using /send <amount> <wallet_address>\n\n"
        "🛡️ Every transaction is guarded by an AI rule system that checks for suspicious behavior.\n"
        "If it looks risky, I’ll stop it.\n"
        "\n_Stay safe out there!_"
    )
    await update.message.reply_text(about_text, parse_mode="Markdown")

# ===👋 START COMMAND ===
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "👋 Hello! I'm your Polygon AI wallet bot.\n"
        "Type /about to learn what I can do.\n"
        "Try /balance or /send to get started."
    )
    await update.message.reply_text(welcome)

# ===🧠 AI CHAT FOR GENERAL TEXT ===
async def handle_general_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    openai.api_key = OPENAI_KEY
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful AI wallet bot that knows your own functions and answers user questions clearly."},
            {"role": "user", "content": user_msg}
        ]
    )

    answer = response.choices[0].message.content.strip()
    await update.message.reply_text(answer)

# ===🤖 TELEGRAM BOT SETUP ===
def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("about", handle_about))
    app.add_handler(CommandHandler("balance", check_wallet_balance))
    app.add_handler(CommandHandler("send", handle_send))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message))
    print("🤖 Bot is active...")
    app.run_polling()

# ===▶ START ===
if __name__ == "__main__":
    run_bot()
