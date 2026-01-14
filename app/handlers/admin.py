"""Admin commands handler."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Bear
from app.services.bears import BearsService, BEAR_CLASSES
from config import settings
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    """
    Check if user is admin.
    """
    return user_id == settings.ADMIN_ID


@router.message(Command("admin"))
async def admin_menu(message: Message):
    """
    Show admin menu.
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Не имеете доступа")
        return
    
    text = (
        "⚡ **Админ Панель**\n\n"
        "📄 **Команды**:\n"
        "/admin_give_vip <user_id> <days> - Обычай ВИП\n"
        "/admin_give_premium <user_id> <days> - Премиум (для легендарных)\n"
        "/admin_give_coins <user_id> <amount> - Выдать коины\n"
        "/admin_boost_bear <user_id> <bear_id> <hours> - Буст медведя\n"
        "/admin_boost_all <user_id> <hours> - Буст всем медведям\n"
        "/admin_create_bear <user_id> <type> <variant> - Создать медведя\n"
        "/admin_user_info <user_id> - Инфо о пользователе\n\n"
        "🔗 **Напримеры**:\n"
        "/admin_give_vip 123456789 30\n"
        "/admin_give_coins 123456789 10000\n"
        "/admin_boost_bear 123456789 1 24\n"
        "/admin_create_bear 123456789 rare 5\n"
    )
    
    await message.answer(text, parse_mode="markdown")


@router.message(Command("admin_give_vip"))
async def admin_give_vip(message: Message):
    """
    Give VIP status to user.
    Usage: /admin_give_vip <user_id> <days>
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Не имеете доступа")
        return
    
    try:
        args = message.text.split()
        if len(args) < 3:
            await message.answer("⚡ Ю Неверный формат: /admin_give_vip <user_id> <days>")
            return
        
        user_id = int(args[1])
        days = int(args[2])
        
        async with get_session() as session:
            query = select(User).where(User.telegram_id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                await message.answer(f"❌ Пользователь {user_id} не найден")
                return
            
            user.is_premium = True
            user.premium_until = datetime.utcnow() + timedelta(days=days)
            await session.commit()
            
            await message.answer(
                f"✅ ВИП присвоен пользователю {user_id}\n"
                f"На {days} дней до {user.premium_until.strftime('%d.%m.%Y')}"
            )
    except ValueError:
        await message.answer("❌ Ошибка: user_id и days должны быть числами")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("admin_give_premium"))
async def admin_give_premium(message: Message):
    """
    Give Premium status to user (for legendary bears).
    Usage: /admin_give_premium <user_id> <days>
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Не имеете доступа")
        return
    
    try:
        args = message.text.split()
        if len(args) < 3:
            await message.answer("⚡ Неверный формат: /admin_give_premium <user_id> <days>")
            return
        
        user_id = int(args[1])
        days = int(args[2])
        
        async with get_session() as session:
            query = select(User).where(User.telegram_id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                await message.answer(f"❌ Пользователь {user_id} не найден")
                return
            
            user.is_premium = True
            user.premium_until = datetime.utcnow() + timedelta(days=days)
            await session.commit()
            
            await message.answer(
                f"✅ Премиум присвоен пользователю {user_id}\n"
                f"теперь доступны легендарные медведи\n"
                f"На {days} дней до {user.premium_until.strftime('%d.%m.%Y')}"
            )
    except ValueError:
        await message.answer("❌ Ошибка: user_id и days должны быть числами")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("admin_give_coins"))
async def admin_give_coins(message: Message):
    """
    Give coins to user.
    Usage: /admin_give_coins <user_id> <amount>
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Не имеете доступа")
        return
    
    try:
        args = message.text.split()
        if len(args) < 3:
            await message.answer("⚡ Неверный формат: /admin_give_coins <user_id> <amount>")
            return
        
        user_id = int(args[1])
        amount = float(args[2])
        
        async with get_session() as session:
            query = select(User).where(User.telegram_id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                await message.answer(f"❌ Пользователь {user_id} не найден")
                return
            
            old_coins = user.coins
            user.coins += amount
            await session.commit()
            
            await message.answer(
                f"✅ Коины выданы:\n"
                f"Пользователь: {user_id}\n"
                f"Выдано: {amount:.0f}\n"
                f"Было: {old_coins:.0f}\n"
                f"Теперь: {user.coins:.0f}"
            )
    except ValueError:
        await message.answer("❌ Ошибка: user_id и amount должны быть числами")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("admin_boost_bear"))
async def admin_boost_bear(message: Message):
    """
    Give boost to specific bear.
    Usage: /admin_boost_bear <user_id> <bear_id> <hours>
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Не имеете доступа")
        return
    
    try:
        args = message.text.split()
        if len(args) < 4:
            await message.answer("⚡ Неверный формат: /admin_boost_bear <user_id> <bear_id> <hours>")
            return
        
        user_id = int(args[1])
        bear_id = int(args[2])
        hours = int(args[3])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                await message.answer(f"❌ Пользователь {user_id} не найден")
                return
            
            try:
                bear = await BearsService.apply_boost(session, bear_id, user.id, hours)
                await message.answer(
                    f"✅ Буст наложен:\n"
                    f"Медведь: {bear.name}\n"
                    f"Эффект: x2 доход\n"
                    f"Дулка: {hours}ч"
                )
            except ValueError as e:
                await message.answer(f"❌ {str(e)}")
    except ValueError:
        await message.answer("❌ Ошибка: user_id, bear_id и hours должны быть числами")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("admin_boost_all"))
async def admin_boost_all(message: Message):
    """
    Give boost to all bears of user.
    Usage: /admin_boost_all <user_id> <hours>
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Не имеете доступа")
        return
    
    try:
        args = message.text.split()
        if len(args) < 3:
            await message.answer("⚡ Неверный формат: /admin_boost_all <user_id> <hours>")
            return
        
        user_id = int(args[1])
        hours = int(args[2])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                await message.answer(f"❌ Пользователь {user_id} не найден")
                return
            
            bears = await BearsService.get_user_bears(session, user.id)
            
            if not bears:
                await message.answer("❌ О пользователя нет медведей")
                return
            
            boosted = 0
            for bear in bears:
                await BearsService.apply_boost(session, bear.id, user.id, hours)
                boosted += 1
            
            await message.answer(
                f"✅ Буст наложен на всех медведей:\n"
                f"Обладатель: {user_id}\n"
                f"Медведей: {boosted}\n"
                f"Эффект: x2 доход\n"
                f"Дулка: {hours}ч"
            )
    except ValueError:
        await message.answer("❌ Ошибка: user_id и hours должны быть числами")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("admin_create_bear"))
async def admin_create_bear(message: Message):
    """
    Create bear for user.
    Usage: /admin_create_bear <user_id> <type> <variant>
    Types: common, rare, epic, legendary
    Variants: 1-15
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Не имеете доступа")
        return
    
    try:
        args = message.text.split()
        if len(args) < 4:
            await message.answer(
                "⚡ Неверный формат: /admin_create_bear <user_id> <type> <variant>\n"
                "Например: /admin_create_bear 123456789 rare 5"
            )
            return
        
        user_id = int(args[1])
        bear_type = args[2]
        variant = int(args[3])
        
        if bear_type not in BEAR_CLASSES:
            await message.answer(f"❌ Неизвестный тип: {bear_type}")
            return
        
        if not 1 <= variant <= 15:
            await message.answer("❌ Вариант должен быть от 1 до 15")
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                await message.answer(f"❌ Пользователь {user_id} не найден")
                return
            
            bear = await BearsService.create_bear(session, user.id, bear_type, variant=variant)
            stats = BearsService.get_bear_stats(bear_type, variant)
            class_info = BEAR_CLASSES[bear_type]
            
            await message.answer(
                f"✅ Медведь создан:\n"
                f"{class_info['emoji']} {bear.name}\n"
                f"Класс: {class_info['rarity']}\n"
                f"Вариант: {variant}/15\n"
                f"💰 Доход: {stats['income']:.2f} коин/ч\n"
                f"Обладатель: {user_id}"
            )
    except ValueError as e:
        logger.error(f"❌ Error: {e}")
        await message.answer("❌ Ошибка: Неверные параметры")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("admin_user_info"))
async def admin_user_info(message: Message):
    """
    Get user info.
    Usage: /admin_user_info <user_id>
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Не имеете доступа")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("⚡ Неверный формат: /admin_user_info <user_id>")
            return
        
        user_id = int(args[1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                await message.answer(f"❌ Пользователь {user_id} не найден")
                return
            
            # Get bears
            bears_query = select(Bear).where(Bear.owner_id == user.id)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            total_income = sum(bear.coins_per_hour for bear in bears)
            
            premium_status = "⭕ Нет"
            if user.is_premium:
                if user.premium_until:
                    premium_status = f"💳 Да ({user.premium_until.strftime('%d.%m.%Y')})"
                else:
                    premium_status = "💳 Да (бессрочно)"
            
            text = (
                f"👤 **Комерсовая инфо**\n\n"
                f"🆔 ID: `{user.telegram_id}`\n"
                f"👤 @{user.username or 'не указано'}\n"
                f"⭐ Уровень: {user.level}\n"
                f"💳 Премиум: {premium_status}\n\n"
                f"💰 **Финансы**\n"
                f"Баланс: {user.coins:.0f} коинов\n"
                f"Доход: {total_income:.1f} коин/ч\n\n"
                f"🐻 **Медведи**: {len(bears)}\n"
                f"📅 Пользователь с: {user.created_at.strftime('%d.%m.%Y')}"
            )
            
            await message.answer(text, parse_mode="markdown")
    except ValueError:
        await message.answer("❌ Ошибка: user_id должен быть числом")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
