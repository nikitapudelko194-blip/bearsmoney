"""NFT integration handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Bear, P2PListing, CoinTransaction
from app.services.bears import BEAR_CLASSES
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()

# NFT minting costs
NFT_MINT_COST = {
    "rare": 0.01,  # 0.01 TON
    "epic": 0.02,  # 0.02 TON
    "legendary": 0.05,  # 0.05 TON
}

# Royalty percentage on resale
ROYALTY_PERCENT = 0.05  # 5%


@router.callback_query(F.data == "nft")
async def nft_menu(query: CallbackQuery):
    """Show NFT marketplace menu."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Count NFT-eligible bears
            bears_query = select(Bear).where(
                Bear.owner_id == user.id,
                Bear.bear_type.in_(['rare', 'epic', 'legendary'])
            )
            bears_result = await session.execute(bears_query)
            nft_bears = bears_result.scalars().all()
            
            # Count listings
            listings_query = select(P2PListing).where(
                P2PListing.seller_id == user.id,
                P2PListing.status == 'active'
            )
            listings_result = await session.execute(listings_query)
            active_listings = listings_result.scalars().all()
            
            text = (
                f"🖼️ **NFT Marketplace**\n\n"
                f"🎯 **TON Blockchain**\n"
                f"├ 🐻 Доступно для NFT: {len(nft_bears)}\n"
                f"├ 📊 Активных продаж: {len(active_listings)}\n"
                f"└ 💰 Баланс: {float(user.ton_balance):.4f} TON\n\n"
                f"💡 **Что такое NFT?**\n"
                f"NFT - это уникальный цифровой актив на блокчейне TON. "
                f"Вы можете конвертировать редких медведей в NFT и продавать их!\n\n"
                f"✨ **Преимущества:**\n"
                f"├ 🔒 Полное владение\n"
                f"├ 💸 Продажа на маркетплейсе\n"
                f"├ 📈 Royalty 5% с перепродаж\n"
                f"└ 🌟 Коллекционная ценность"
            )
            
            keyboard = [
                [InlineKeyboardButton(text="📄 Мои NFT медведи", callback_data="nft_my_bears")],
                [InlineKeyboardButton(text="🏪 Маркетплейс", callback_data="nft_marketplace")],
                [InlineKeyboardButton(text="➕ Создать NFT", callback_data="nft_create")],
                [InlineKeyboardButton(text="📊 Мои продажи", callback_data="nft_my_listings")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ]
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "nft_my_bears")
async def nft_my_bears(query: CallbackQuery):
    """Show user's NFT-eligible bears."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            bears_query = select(Bear).where(
                Bear.owner_id == user.id,
                Bear.bear_type.in_(['rare', 'epic', 'legendary'])
            ).order_by(Bear.coins_per_hour.desc())
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if not bears:
                text = (
                    f"🖼️ **Мои NFT медведи**\n\n"
                    f"❌ У вас нет редких медведей!\n\n"
                    f"💡 NFT можно создавать только из:\n"
                    f"├ 🔵 Rare медведей\n"
                    f"├ 🟪 Epic медведей\n"
                    f"└ 🟫 Legendary медведей\n\n"
                    f"🎪 Купите кейсы, чтобы получить редких медведей!"
                )
                keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="nft")]]
            else:
                text = (
                    f"🖼️ **Мои NFT медведи**\n\n"
                    f"🐻 Доступно: {len(bears)}\n\n"
                )
                
                keyboard = []
                for bear in bears[:10]:  # Show first 10
                    class_info = BEAR_CLASSES[bear.bear_type]
                    mint_cost = NFT_MINT_COST[bear.bear_type]
                    bear_text = f"{class_info['emoji']} {bear.name} (Lv{bear.level}) - {mint_cost} TON"
                    keyboard.append([InlineKeyboardButton(
                        text=bear_text,
                        callback_data=f"nft_mint_{bear.id}"
                    )])
                
                keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nft")])
                
                text += "👇 Выберите медведя для конвертации в NFT:"
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_my_bears: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("nft_mint_"))
async def nft_mint(query: CallbackQuery):
    """Mint NFT from bear."""
    try:
        bear_id = int(query.data.split("_")[-1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one_or_none()
            
            if not bear:
                await query.answer("❌ Медведь не найден!", show_alert=True)
                return
            
            if bear.bear_type not in ['rare', 'epic', 'legendary']:
                await query.answer("❌ NFT можно создавать только из редких медведей!", show_alert=True)
                return
            
            mint_cost = NFT_MINT_COST[bear.bear_type]
            
            if float(user.ton_balance) < mint_cost:
                await query.answer(f"❌ Недостаточно TON! Нужно: {mint_cost} TON", show_alert=True)
                return
            
            class_info = BEAR_CLASSES[bear.bear_type]
            
            text = (
                f"🖼️ **Создание NFT**\n\n"
                f"🐻 **Медведь:**\n"
                f"├ {class_info['emoji']} {bear.name}\n"
                f"├ ⭐ Уровень: {bear.level}\n"
                f"├ 💰 Доход: {bear.coins_per_hour:.1f} к/ч\n"
                f"└ 🎯 Редкость: {class_info['rarity']}\n\n"
                f"💸 **Стоимость:**\n"
                f"├ 💎 Minting: {mint_cost} TON\n"
                f"├ 📊 Gas: ~0.001 TON\n"
                f"└ 💰 Всего: {mint_cost + 0.001:.4f} TON\n\n"
                f"✨ **После конвертации:**\n"
                f"├ 🔒 Полное владение NFT\n"
                f"├ 💸 Продажа на маркетплейсе\n"
                f"├ 📈 5% royalty с перепродаж\n"
                f"└ 🌟 Коллекционная ценность\n\n"
                f"⚠️ Подтвердите конвертацию!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Создать NFT", callback_data=f"nft_mint_confirm_{bear_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="nft_my_bears")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_mint: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("nft_mint_confirm_"))
async def nft_mint_confirm(query: CallbackQuery):
    """Confirm NFT minting."""
    try:
        bear_id = int(query.data.split("_")[-1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one_or_none()
            
            if not bear:
                await query.answer("❌ Медведь не найден!", show_alert=True)
                return
            
            mint_cost = NFT_MINT_COST[bear.bear_type]
            total_cost = mint_cost + 0.001  # Add gas
            
            if float(user.ton_balance) < total_cost:
                await query.answer(f"❌ Недостаточно TON!", show_alert=True)
                return
            
            # Deduct cost
            user.ton_balance -= Decimal(str(total_cost))
            
            # Mark bear as NFT (in real implementation, this would interact with TON blockchain)
            bear.is_locked = True  # Lock from being deleted/modified
            # TODO: Add nft_token_id field to Bear model and mint actual NFT on TON
            
            await session.commit()
            
            class_info = BEAR_CLASSES[bear.bear_type]
            
            text = (
                f"✅ **NFT создан!**\n\n"
                f"🎉 Поздравляем! Ваш медведь теперь NFT!\n\n"
                f"🐻 **Информация:**\n"
                f"├ {class_info['emoji']} {bear.name}\n"
                f"├ ⭐ Уровень: {bear.level}\n"
                f"├ 💰 Доход: {bear.coins_per_hour:.1f} к/ч\n"
                f"└ 🔒 NFT ID: #{bear.id}\n\n"
                f"💸 **Списано:** {total_cost:.4f} TON\n"
                f"💼 **Новый баланс:** {float(user.ton_balance):.4f} TON\n\n"
                f"💡 Теперь вы можете продать NFT на маркетплейсе!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💸 Выставить на продажу", callback_data=f"nft_list_{bear.id}")],
                [InlineKeyboardButton(text="🖼️ Мои NFT", callback_data="nft_my_bears")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="nft")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ NFT создан!")
            
            logger.info(f"User {user.telegram_id} minted NFT from bear {bear.id}")
    
    except Exception as e:
        logger.error(f"❌ Error in nft_mint_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "nft_marketplace")
async def nft_marketplace(query: CallbackQuery):
    """Show NFT marketplace with active listings."""
    try:
        text = (
            f"🏪 **NFT Marketplace**\n\n"
            f"🚀 Функция в разработке!\n\n"
            f"⚡ **Скоро:**\n"
                f"├ 🐻 Покупка NFT медведей\n"
            f"├ 📊 История цен\n"
            f"├ 🔍 Фильтры по редкости\n"
            f"└ 🎯 Аукционы"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nft")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_marketplace: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
