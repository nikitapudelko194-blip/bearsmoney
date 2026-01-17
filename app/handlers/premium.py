"""Premium subscription handlers."""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Subscription, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

# Premium tiers
PREMIUM_TIERS = {
    'basic': {
        'name': '🆓 Basic',
        'price_ton': 0,
        'income_bonus': 0,  # 0% bonus
        'commission_reduction': 0,  # No reduction
        'withdraw_limit': 100,  # TON
        'features': [
            '✅ Базовые функции',
            '✅ Обычные медведи',
            '✅ Стандартный обмен',
            '❌ Эксклюзивные медведи',
            '❌ Бонусы к доходу',
        ],
    },
    'premium': {
        'name': '⭐ Premium',
        'price_ton': 100,
        'income_bonus': 0.5,  # +50% к доходу
        'commission_reduction': 0.02,  # -2% (0% комиссии)
        'withdraw_limit': 1000,
        'features': [
            '✅ Все функции Basic',
            '✅ +50% к доходу от медведей',
            '✅ 0% комиссии на обмен',
            '✅ Эксклюзивные медведи',
            '✅ Приоритетная поддержка',
            '✅ Специальный бейдж ⭐',
        ],
    },
    'vip': {
        'name': '💎 VIP',
        'price_ton': 500,
        'income_bonus': 1.0,  # +100% к доходу (x2)
        'commission_reduction': 0.02,  # 0% комиссий
        'withdraw_limit': 10000,
        'features': [
            '✅ Все функции Premium',
            '✅ +100% к доходу (x2)',
            '✅ 0% комиссий везде',
            '✅ Легендарные медведи',
            '✅ VIP кейсы',
            '✅ Личный менеджер',
            '✅ Эксклюзивный бейдж 💎',
        ],
    },
}


@router.callback_query(F.data == "premium")
async def premium_menu(query: CallbackQuery):
    """
    Show premium subscription menu.
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get active subscription
            sub_query = select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == 'active'
            ).order_by(Subscription.expires_at.desc())
            sub_result = await session.execute(sub_query)
            subscription = sub_result.scalar_one_or_none()
            
            current_tier = subscription.tier if subscription else 'basic'
            
            text = (
                f"⭐ **Premium подписка**\n\n"
                f"💼 **Текущий статус:** {PREMIUM_TIERS[current_tier]['name']}\n"
            )
            
            if subscription and subscription.expires_at:
                days_left = (subscription.expires_at - datetime.utcnow()).days
                text += f"⏰ Действует: {days_left} дней\n"
                text += f"🔄 Авто-продление: {'✅' if subscription.auto_renew else '❌'}\n"
            
            text += (
                f"\n📊 **Доступные тарифы:**\n\n"
            )
            
            keyboard = []
            
            for tier_id, tier in PREMIUM_TIERS.items():
                if tier_id == 'basic':
                    continue  # Skip basic (free tier)
                
                status = " ✅" if current_tier == tier_id else ""
                button_text = f"{tier['name']} - {tier['price_ton']} TON/мес{status}"
                keyboard.append([InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"premium_tier_{tier_id}"
                )])
            
            keyboard.append([InlineKeyboardButton(text="ℹ️ Сравнить тарифы", callback_data="premium_compare")])
            
            if subscription and subscription.auto_renew:
                keyboard.append([InlineKeyboardButton(text="❌ Отменить авто-продление", callback_data="premium_cancel_autorenew")])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("premium_tier_"))
async def premium_tier_details(query: CallbackQuery):
    """
    Show premium tier details.
    """
    try:
        tier_id = query.data.split("_")[-1]
        tier = PREMIUM_TIERS.get(tier_id)
        
        if not tier:
            await query.answer("❌ Тариф не найден", show_alert=True)
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                f"{tier['name']} **Подписка**\n\n"
                f"💰 **Стоимость:** {tier['price_ton']} TON/месяц\n"
                f"📈 **Бонус к доходу:** +{int(tier['income_bonus']*100)}%\n"
                f"📉 **Комиссия:** {0 if tier['commission_reduction'] > 0 else 2}%\n"
                f"💸 **Лимит вывода:** {tier['withdraw_limit']} TON\n\n"
                f"✨ **Преимущества:**\n"
            )
            
            for feature in tier['features']:
                text += f"{feature}\n"
            
            text += (
                f"\n💼 **Ваш баланс:** {float(user.ton_balance):.4f} TON\n"
            )
            
            if float(user.ton_balance) < tier['price_ton']:
                text += f"\n⚠️ Недостаточно средств. Нужно ещё {tier['price_ton'] - float(user.ton_balance):.4f} TON"
            
            keyboard = []
            
            if float(user.ton_balance) >= tier['price_ton']:
                keyboard.append([InlineKeyboardButton(
                    text=f"✅ Купить за {tier['price_ton']} TON",
                    callback_data=f"premium_buy_{tier_id}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    text="💱 Обменять Coins → TON",
                    callback_data="exchange_coins_to_ton"
                )])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ К тарифам", callback_data="premium")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_tier_details: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("premium_buy_"))
async def premium_buy(query: CallbackQuery):
    """
    Purchase premium subscription.
    """
    try:
        tier_id = query.data.split("_")[-1]
        tier = PREMIUM_TIERS.get(tier_id)
        
        if not tier:
            await query.answer("❌ Тариф не найден", show_alert=True)
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check balance
            if float(user.ton_balance) < tier['price_ton']:
                await query.answer("❌ Недостаточно TON", show_alert=True)
                return
            
            # Deduct payment
            user.ton_balance -= Decimal(str(tier['price_ton']))
            
            # Create or update subscription
            sub_query = select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == 'active'
            )
            sub_result = await session.execute(sub_query)
            subscription = sub_result.scalar_one_or_none()
            
            now = datetime.utcnow()
            expires_at = now + timedelta(days=30)
            
            if subscription:
                # Extend existing
                subscription.tier = tier_id
                subscription.expires_at = expires_at
                subscription.coins_bonus = tier['income_bonus']
                subscription.commission_reduction = tier['commission_reduction']
                subscription.withdraw_limit = tier['withdraw_limit']
                subscription.auto_renew = True
            else:
                # Create new
                subscription = Subscription(
                    user_id=user.id,
                    tier=tier_id,
                    coins_bonus=tier['income_bonus'],
                    commission_reduction=tier['commission_reduction'],
                    withdraw_limit=tier['withdraw_limit'],
                    status='active',
                    started_at=now,
                    expires_at=expires_at,
                    auto_renew=True
                )
                session.add(subscription)
            
            # Update user premium status
            user.is_premium = True
            user.premium_until = expires_at
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-tier['price_ton'],
                transaction_type='premium_purchase',
                description=f'Покупка {tier["name"]} подписки на 30 дней'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"✅ **Подписка активирована!**\n\n"
                f"🎉 Поздравляем с покупкой {tier['name']}!\n\n"
                f"✨ **Ваши преимущества:**\n"
            )
            
            for feature in tier['features']:
                text += f"{feature}\n"
            
            text += (
                f"\n⏰ **Действует до:** {expires_at.strftime('%d.%m.%Y')}\n"
                f"🔄 **Авто-продление:** включено\n\n"
                f"💼 **Новый баланс:** {float(user.ton_balance):.4f} TON\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐻 К медведям", callback_data="bears")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 Подписка активирована!")
            
            logger.info(f"✅ User {user.telegram_id} purchased {tier_id} subscription for {tier['price_ton']} TON")
    
    except Exception as e:
        logger.error(f"❌ Error in premium_buy: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "premium_compare")
async def premium_compare(query: CallbackQuery):
    """
    Compare premium tiers.
    """
    try:
        text = (
            "📊 **Сравнение тарифов**\n\n"
        )
        
        # Create comparison table
        for tier_id, tier in PREMIUM_TIERS.items():
            text += f"**{tier['name']}**\n"
            text += f"💰 Цена: {tier['price_ton']} TON/мес\n"
            text += f"📈 Бонус: +{int(tier['income_bonus']*100)}%\n"
            text += f"📉 Комиссия: {0 if tier['commission_reduction'] > 0 else 2}%\n"
            text += f"💸 Лимит: {tier['withdraw_limit']} TON\n\n"
        
        text += (
            "💡 **Рекомендация:**\n"
            "• Basic - для начинающих\n"
            "• Premium - лучший баланс\n"
            "• VIP - для профи\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Premium", callback_data="premium_tier_premium")],
            [InlineKeyboardButton(text="💎 VIP", callback_data="premium_tier_vip")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="premium")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_compare: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "premium_cancel_autorenew")
async def premium_cancel_autorenew(query: CallbackQuery):
    """
    Cancel auto-renewal.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get subscription
            sub_query = select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == 'active'
            )
            sub_result = await session.execute(sub_query)
            subscription = sub_result.scalar_one_or_none()
            
            if not subscription:
                await query.answer("❌ Активная подписка не найдена", show_alert=True)
                return
            
            subscription.auto_renew = False
            await session.commit()
            
            text = (
                "✅ **Авто-продление отменено**\n\n"
                f"Ваша подписка {PREMIUM_TIERS[subscription.tier]['name']} "
                f"будет действовать до {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
                "После этой даты подписка не продлится автоматически."
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К подпискам", callback_data="premium")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Авто-продление отменено")
    
    except Exception as e:
        logger.error(f"❌ Error in premium_cancel_autorenew: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def check_expired_subscriptions():
    """
    Background task to check and expire subscriptions.
    Run this periodically (e.g., every hour).
    """
    try:
        async with get_session() as session:
            now = datetime.utcnow()
            
            # Get expired subscriptions
            query = select(Subscription).where(
                Subscription.status == 'active',
                Subscription.expires_at < now
            )
            result = await session.execute(query)
            expired_subs = result.scalars().all()
            
            for sub in expired_subs:
                # Get user
                user_query = select(User).where(User.id == sub.user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one()
                
                if sub.auto_renew:
                    # Try to renew
                    tier = PREMIUM_TIERS[sub.tier]
                    if float(user.ton_balance) >= tier['price_ton']:
                        # Renew subscription
                        user.ton_balance -= Decimal(str(tier['price_ton']))
                        sub.expires_at = now + timedelta(days=30)
                        
                        # Log transaction
                        transaction = CoinTransaction(
                            user_id=user.id,
                            amount=-tier['price_ton'],
                            transaction_type='premium_renewal',
                            description=f'Продление {tier["name"]} подписки'
                        )
                        session.add(transaction)
                        
                        logger.info(f"✅ Auto-renewed subscription for user {user.telegram_id}")
                    else:
                        # Not enough balance - expire
                        sub.status = 'expired'
                        sub.auto_renew = False
                        user.is_premium = False
                        user.premium_until = None
                        logger.info(f"⚠️ Failed to renew subscription for user {user.telegram_id} - insufficient balance")
                else:
                    # Just expire
                    sub.status = 'expired'
                    user.is_premium = False
                    user.premium_until = None
                    logger.info(f"✅ Expired subscription for user {user.telegram_id}")
            
            await session.commit()
            
            logger.info(f"✅ Checked {len(expired_subs)} expired subscriptions")
    
    except Exception as e:
        logger.error(f"❌ Error in check_expired_subscriptions: {e}", exc_info=True)
