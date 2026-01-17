#!/bin/bash
# BearsMoney Bot - Force Restart Script
# This script completely restarts the bot with cache cleanup

set -e

echo "================================"
echo "🐻 BearsMoney Bot Restart"
echo "================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📂 Working directory: $SCRIPT_DIR"
echo ""

# Step 1: Stop the bot
echo "1️⃣ Stopping bot service..."
sudo systemctl stop bearsmoney || echo "Service not running or doesn't exist"
sleep 3

# Step 2: Kill any remaining processes
echo ""
echo "2️⃣ Killing remaining Python processes..."
sudo pkill -9 -f "bearsmoney" || echo "No processes to kill"
sleep 2

# Step 3: Clear Python cache
echo ""
echo "3️⃣ Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
echo "✅ Cache cleared"

# Step 4: Check config values
echo ""
echo "4️⃣ Checking configuration..."
echo "----------------------------"
grep "COIN_TO_TON_RATE" config.py || echo "⚠️ COIN_TO_TON_RATE not found in config.py"

if [ -f ".env" ]; then
    echo ""
    echo "📄 Checking .env file:"
    if grep -q "COIN_TO_TON_RATE" .env; then
        echo "⚠️ COIN_TO_TON_RATE found in .env:"
        grep "COIN_TO_TON_RATE" .env
        echo ""
        echo "🔧 Removing COIN_TO_TON_RATE from .env (using config.py default)..."
        sed -i '/COIN_TO_TON_RATE/d' .env
        echo "✅ Removed from .env"
    else
        echo "✅ No COIN_TO_TON_RATE override in .env"
    fi
else
    echo "ℹ️  No .env file found"
fi

# Step 5: Verify final config
echo ""
echo "5️⃣ Final configuration:"
echo "----------------------------"
python3 -c "from config import settings; print(f'COIN_TO_TON_RATE: {settings.COIN_TO_TON_RATE}')"
python3 -c "from config import settings; print(f'1 TON = {int(1/settings.COIN_TO_TON_RATE):,} Coins')"
python3 -c "from config import settings; print(f'3,000 Coins = {3000 * settings.COIN_TO_TON_RATE:.4f} TON')"
echo ""

# Step 6: Start the bot
echo "6️⃣ Starting bot service..."
sudo systemctl start bearsmoney
sleep 2

# Step 7: Check status
echo ""
echo "7️⃣ Service status:"
sudo systemctl status bearsmoney --no-pager -l | head -n 20

echo ""
echo "================================"
echo "✅ Bot restarted successfully!"
echo "================================"
echo ""
echo "📊 To view logs in real-time:"
echo "sudo journalctl -u bearsmoney -f"
echo ""
echo "🔍 To check exchange rate in logs:"
echo "sudo journalctl -u bearsmoney | grep 'Exchange menu'"
echo ""
