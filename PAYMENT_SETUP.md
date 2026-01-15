# 💳 Payment System Setup Guide

## 👁️ Overview

Ваша игра теперь поддерживает **3 способа пополнения TON**:

1. ✅ **Telegram Stars** - ГОТОВО К ИСПОЛЬЗОВАНИЮ
2. 🚧 **TON Wallet** - ТРЕБУЕТСЯ НАСТРОЙКА
3. 🚧 **Банковские карты (YooKassa)** - ТРЕБУЕТСЯ НАСТРОЙКА

---

## ⭐ 1. Telegram Stars (ГОТОВО!)

### ✅ Статус: ПОЛНОСТЬЮ РАБОТАЕТ

**Telegram Stars** - это внутренняя валюта Telegram, которую можно купить прямо в приложении.

### 🎯 Возможности:
- ✅ Оплата внутри Telegram
- ✅ Автоматическое зачисление
- ✅ Безопасность Telegram
- ✅ Не требует API ключей

### 💰 Пакеты:
```
0.5 TON = 50 Stars
1.0 TON = 100 Stars
2.5 TON = 250 Stars
5.0 TON = 500 Stars
10.0 TON = 1000 Stars
```

### 🚀 Как использовать:

1. Пользователь нажимает "💳 Купить TON" в главном меню
2. Выбирает пакет
3. Выбирает "⭐ Telegram Stars"
4. Telegram открывает страницу оплаты
5. После оплаты - автоматическое зачисление TON

### 🔍 Тестирование:

Для тестирования используйте [Telegram's Bot Payments API Testing](https://core.telegram.org/bots/payments#testing-payments):

```bash
# Добавьте бота в тестовую группу BotFather
# Используйте тестовые Stars (бесплатно)
```

---

## 💎 2. TON Wallet Integration

### 🚧 Статус: ТРЕБУЕТСЯ НАСТРОЙКА

Интеграция с реальным TON blockchain для приёма криптовалюты.

### 🛠️ Что нужно сделать:

#### 1. Установить библиотеки:

```bash
pip install pytonlib ton-python
```

#### 2. Настроить TON кошелёк:

```python
# config.py
class Settings(BaseSettings):
    # ... existing settings ...
    
    # TON Wallet
    TON_WALLET_ADDRESS: str = "UQA..."  # Ваш адрес для приёма платежей
    TON_API_KEY: str = ""  # API ключ TON Center (https://toncenter.com)
    TON_NETWORK: str = "mainnet"  # mainnet или testnet
```

#### 3. Создать сервис проверки платежей:

```python
# app/services/ton_payments.py
from pytonlib import TonlibClient
import asyncio

class TONPaymentService:
    def __init__(self, api_key: str, wallet_address: str):
        self.api_key = api_key
        self.wallet_address = wallet_address
        self.client = TonlibClient(...)
    
    async def check_transaction(self, comment: str, expected_amount: float):
        """
        Check if transaction with specific comment exists.
        """
        # TODO: Implement blockchain checking
        transactions = await self.client.get_transactions(self.wallet_address)
        
        for tx in transactions:
            if tx.comment == comment and tx.amount == expected_amount:
                return True
        return False
    
    async def monitor_payments(self):
        """
        Background worker to monitor incoming payments.
        """
        while True:
            # Check for new transactions
            await asyncio.sleep(30)  # Check every 30 seconds
```

#### 4. Обновить `payment.py`:

```python
# В функции pay_with_ton_wallet:
# Заменить placeholder адрес на реальный:
deposit_address = settings.TON_WALLET_ADDRESS

# В функции check_ton_payment:
# Добавить реальную проверку:
ton_service = TONPaymentService(settings.TON_API_KEY, settings.TON_WALLET_ADDRESS)
if await ton_service.check_transaction(payment_memo, package['ton_crypto']):
    # Credit TON to user
    ...
```

#### 5. Запустить мониторинг:

```python
# main.py
async def main():
    # ... existing code ...
    
    # Start TON payment monitoring
    ton_service = TONPaymentService(...)
    asyncio.create_task(ton_service.monitor_payments())
    
    await dp.start_polling(bot)
```

### 🔗 Полезные ссылки:
- [TON Center API](https://toncenter.com/api/v2/)
- [PyTONLib Documentation](https://github.com/toncenter/pytonlib)
- [TON Documentation](https://docs.ton.org/)

---

## 💳 3. YooKassa (Russian Rubles)

### 🚧 Статус: ТРЕБУЕТСЯ НАСТРОЙКА

Приём платежей в российских рублях через банковские карты.

### 🛠️ Что нужно сделать:

#### 1. Зарегистрироваться в YooKassa:

1. Перейти на [yookassa.ru](https://yookassa.ru)
2. Создать аккаунт
3. Получить:
   - `shopId` - ID вашего магазина
   - `secret_key` - Секретный ключ

#### 2. Установить библиотеку:

```bash
pip install yookassa
```

#### 3. Настроить конфиг:

```python
# config.py
class Settings(BaseSettings):
    # ... existing settings ...
    
    # YooKassa
    YOOKASSA_SHOP_ID: str = "123456"
    YOOKASSA_SECRET_KEY: str = "live_..."
    YOOKASSA_WEBHOOK_SECRET: str = "your_webhook_secret"
```

#### 4. Создать сервис платежей:

```python
# app/services/yookassa_payments.py
from yookassa import Configuration, Payment
import uuid

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

class YooKassaService:
    @staticmethod
    def create_payment(amount_rub: float, user_id: int, package_id: str):
        """
        Create payment in YooKassa.
        """
        idempotence_key = str(uuid.uuid4())
        
        payment = Payment.create({
            "amount": {
                "value": f"{amount_rub:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/bearsmoney_bot"
            },
            "capture": True,
            "description": f"TON purchase - {package_id}",
            "metadata": {
                "user_id": user_id,
                "package_id": package_id
            }
        }, idempotence_key)
        
        return payment.confirmation.confirmation_url
```

#### 5. Настроить webhook:

```python
# app/api/webhooks.py (create new file)
from fastapi import FastAPI, Request, HTTPException
from yookassa.domain.notification import WebhookNotification

app = FastAPI()

@app.post("/yookassa-webhook")
async def yookassa_webhook(request: Request):
    """
    Handle YooKassa payment notifications.
    """
    try:
        event_json = await request.json()
        notification = WebhookNotification(event_json)
        
        if notification.event == "payment.succeeded":
            payment = notification.object
            user_id = payment.metadata["user_id"]
            package_id = payment.metadata["package_id"]
            
            # Credit TON to user
            async with get_session() as session:
                user = await get_user(session, user_id)
                package = TON_PACKAGES[package_id]
                user.ton_balance += package['ton_amount']
                await session.commit()
                
            # Notify user
            await bot.send_message(
                user_id,
                f"✅ Платёж успешен!\n"
                f"💎 Начислено: {package['ton_amount']} TON"
            )
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
```

#### 6. Обновить `payment.py`:

```python
# В функции pay_with_card:
payment_url = YooKassaService.create_payment(
    amount_rub=package['rub'],
    user_id=query.from_user.id,
    package_id=package_id
)

# Добавить кнопку:
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"select_package:{package_id}")],
])
```

#### 7. Зарегистрировать webhook в YooKassa:

```python
from yookassa import Webhook

# Ваш сервер должен быть доступен из интернета
Webhook.add({
    "event": "payment.succeeded",
    "url": "https://your-domain.com/yookassa-webhook"
})
```

### 🔗 Полезные ссылки:
- [YooKassa Documentation](https://yookassa.ru/developers)
- [YooKassa Python SDK](https://github.com/yoomoney/yookassa-sdk-python)
- [API Reference](https://yookassa.ru/developers/api)

---

## 🔒 Security

### Важные рекомендации:

1. **Никогда не коммитьте API ключи в Git!**
   ```bash
   # .env
   TON_API_KEY=your_key_here
   YOOKASSA_SECRET_KEY=your_key_here
   ```

2. **Проверяйте webhook подписи:**
   ```python
   # YooKassa webhook verification
   if not verify_webhook_signature(request):
       raise HTTPException(status_code=401)
   ```

3. **Используйте idempotency keys:**
   ```python
   # Предотвращает дублирование платежей
   idempotence_key = str(uuid.uuid4())
   ```

4. **Логируйте все транзакции:**
   ```python
   logger.info(f"Payment: user={user_id}, amount={amount}, status={status}")
   ```

5. **Тестируйте на testnet/sandbox:**
   - TON: testnet
   - YooKassa: sandbox mode

---

## 🔍 Testing

### Telegram Stars:
```bash
# Просто используйте бота - работает сразу!
```

### TON Wallet:
```bash
# 1. Используйте testnet
export TON_NETWORK=testnet

# 2. Получите тестовые TON
# https://t.me/testgiver_ton_bot

# 3. Отправьте тестовый платёж
```

### YooKassa:
```bash
# 1. Используйте тестовые ключи
export YOOKASSA_SECRET_KEY=test_...

# 2. Тестовые карты:
# 5555 5555 5555 4444 - успешный платёж
# 5555 5555 5555 5599 - ошибка платежа
```

---

## ❓ Troubleshooting

### Telegram Stars не работает:

1. Проверьте что бот не заблокирован BotFather
2. Проверьте payload формат
3. Проверьте логи: `journalctl -u bearsmoney -f`

### TON платежи не приходят:

1. Проверьте что мониторинг запущен
2. Проверьте API ключ TON Center
3. Проверьте адрес кошелька

### YooKassa webhook не работает:

1. Проверьте что сервер доступен из интернета
2. Проверьте webhook URL в панели YooKassa
3. Проверьте логи webhook: `/var/log/nginx/access.log`

---

## 🚀 Quick Start Checklist

- [x] **Telegram Stars** - ГОТОВО!
- [ ] **TON Wallet:**
  - [ ] Установить pytonlib
  - [ ] Получить API ключ TON Center
  - [ ] Создать кошелёк
  - [ ] Настроить мониторинг
- [ ] **YooKassa:**
  - [ ] Зарегистрироваться
  - [ ] Получить API ключи
  - [ ] Настроить webhook
  - [ ] Протестировать

---

## 💬 Support

Если возникли проблемы:

1. Проверьте логи: `tail -f logs/bot.log`
2. Проверьте эту документацию
3. Обратитесь в поддержку:
   - TON: https://t.me/tondev
   - YooKassa: support@yookassa.ru
   - Telegram Bots: https://t.me/BotSupport

---

**Удачи с интеграцией!** 🚀🐻
