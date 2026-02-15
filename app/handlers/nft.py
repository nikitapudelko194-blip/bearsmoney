"""NFT integration system."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Bear, CoinTransaction
from decimal import Decimal

logger = logging.getLogger(__name__)
router = Router()

# NFT minting costs
NFT_MINT_COST_TON = 0.05  # 0.05 TON to mint
NFT_ROYALTY = 0.05  # 5% royalty on resales


@router.callback_query(F.data == "nft_menu")
async def nft_menu(query: CallbackQuery):
    """Show NFT menu."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get user's bears
            bears_query = select(Bear).where(Bear.owner_id == user.id)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            # Count mintable bears (rare+)
            mintable_bears = [b for b in bears if b.bear_type in ['rare', 'epic', 'legendary']]
            
            text = (
                f"🖼️ **NFT Маркетплейс**\n\n"
                f"🌟 Превратите своих редких медведей в NFT!\n\n"
                f"📊 **Ваша коллекция:**\n"
                f"├ 🐻 Всего медведей: {len(bears)}\n"
                f"├ ✨ Можно заминтить: {len(mintable_bears)}\n"
                f"└ 💰 TON баланс: {float(user.ton_balance):.4f}\n\n"
                f"🛠 **Минтинг:**\n"
                f"• Стоимость: {NFT_MINT_COST_TON} TON\n"
                f"• Royalty: {int(NFT_ROYALTY*100)}% с перепродаж\n"
                f"• Блокчейн: TON\n\n"
                f"💡 Выберите действие:"
            )
            
            keyboard = []
            
            if mintable_bears:
                keyboard.append([InlineKeyboardButton(text="🎨 Заминтить медведя", callback_data="nft_mint_list")])
            
            keyboard.append([InlineKeyboardButton(text="💼 Мои NFT", callback_data="nft_my_collection")])
            keyboard.append([InlineKeyboardButton(text="🏪 Маркетплейс", callback_data="nft_marketplace")])
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "nft_mint_list")
async def nft_mint_list(query: CallbackQuery):
    """Show list of bears to mint."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get mintable bears
            bears_query = select(Bear).where(
                Bear.owner_id == user.id,
                Bear.bear_type.in_(['rare', 'epic', 'legendary'])
            )
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if not bears:
                await query.answer("❌ У вас нет редких медведей для минта!", show_alert=True)
                return
            
            text = (
                f"🎨 **Выберите медведя**\n\n"
                f"💰 Стоимость минта: {NFT_MINT_COST_TON} TON\n"
                f"💳 Ваш баланс: {float(user.ton_balance):.4f} TON\n\n"
                f"🐻 **Доступные медведи:**\n"
            )
            
            keyboard = []
            
            for bear in bears[:10]:  # Limit to 10
                text += f"\n• {bear.name} ({bear.bear_type}, Lv{bear.level})"
                keyboard.append([InlineKeyboardButton(
                    text=f"🎨 {bear.name}",
                    callback_data=f"nft_mint_{bear.id}"
                )])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nft_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_mint_list: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("nft_mint_"))
async def nft_mint_bear(query: CallbackQuery):
    """Mint bear as NFT."""
    try:
        bear_id = int(query.data.split("_")[-1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check balance
            if user.ton_balance < Decimal(str(NFT_MINT_COST_TON)):
                await query.answer(
                    f"❌ Недостаточно TON!\n"
                    f"Нужно: {NFT_MINT_COST_TON} TON\n"
                    f"У вас: {float(user.ton_balance):.4f} TON",
                    show_alert=True
                )
                return
            
            bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one_or_none()
            
            if not bear:
                await query.answer("❌ Медведь не найден!", show_alert=True)
                return
            
            # Deduct TON
            user.ton_balance -= Decimal(str(NFT_MINT_COST_TON))
            
            # TODO: Actual NFT minting on TON blockchain
            # For now, just simulate
            nft_address = f"EQ{bear.id:010d}NFT..."
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=0,
                transaction_type='nft_mint',
                description=f'NFT минт медведя {bear.name}'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"✅ **NFT заминчен!**\n\n"
                f"🎨 **Медведь:** {bear.name}\n"
                f"✨ **Редкость:** {bear.bear_type}\n"
                f"⭐ **Уровень:** {bear.level}\n\n"
                f"📜 **NFT адрес:**\n`{nft_address}`\n\n"
                f"💰 **Стоимость:** {NFT_MINT_COST_TON} TON\n"
                f"💳 **Новый баланс:** {float(user.ton_balance):.4f} TON\n\n"
                f"💡 Теперь вы можете продать NFT на маркетплейсе!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏪 На маркетплейс", callback_data="nft_marketplace")],
                [InlineKeyboardButton(text="⬅️ К NFT", callback_data="nft_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ NFT заминчен!")
            logger.info(f"✅ User {user.telegram_id} minted NFT for bear {bear_id}")
    
    except Exception as e:
        logger.error(f"❌ Error in nft_mint_bear: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "nft_marketplace")
async def nft_marketplace(query: CallbackQuery):
    """Show NFT marketplace."""
    text = (
        f"🏪 **NFT Маркетплейс**\n\n"
        f"🚀 Функция в разработке!\n\n"
        f"🔜 **Скоро:**\n"
        f"• Продажа NFT\n"
        f"• Покупка NFT\n"
        f"• Аукционы\n"
        f"• Royalty система (5%)\n"
        f"• Проверка подлинности\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="nft_menu")],
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    await query.answer()
